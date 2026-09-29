#!/usr/bin/env python3
"""Register isolated Git worktrees; import results without weakening root identity checks."""
from __future__ import annotations
from pathlib import Path
import subprocess
from runtime_protocol import (file_hash, load, object_keys, require, safe_id, state_read, write_json)
from state_store import locked


def git(path, *args):
    proc = subprocess.run(['git', '-C', str(path), *args], capture_output=True, text=True)
    require(proc.returncode == 0, 'git: ' + proc.stderr.strip())
    return proc.stdout.strip()


def inspect_workspace(project, workspace_id):
    from coordination import home
    safe_id(workspace_id)
    value = load(home(project) / 'workspaces' / (workspace_id + '.json'))
    require(value['schema_version'] == 1, 'unsupported workspace schema')
    require(value['coordinator'] == str(Path(project).resolve()), 'workspace coordinator mismatch')
    workspace = Path(value['project_root']).resolve()
    require(git(workspace, 'rev-parse', '--path-format=absolute', '--git-common-dir') == value['git_common_dir'], 'workspace repository changed')
    require(git(project, 'rev-parse', '--path-format=absolute', '--git-common-dir') == value['git_common_dir'], 'coordinator repository changed')
    require(git(workspace, 'rev-parse', '--show-toplevel') == str(workspace), 'workspace must be repository root')
    for root in (value['canonical_feature'], value['feature_root']):
        require(state_read(Path(root) / 'state.yaml').get('project_id') == value['project_id'], 'workspace logical project changed')
    return value


def register(project, workspace_id, workspace, canonical_feature, feature_root, product_root):
    from coordination import home
    safe_id(workspace_id)
    project, workspace, canonical, feature, product = map(lambda x: Path(x).resolve(),
                                                        (project, workspace, canonical_feature, feature_root, product_root))
    require(not workspace.is_relative_to(project) and not project.is_relative_to(workspace), 'workspace roots must be disjoint')
    require(feature.is_relative_to(workspace) and product.is_relative_to(workspace), 'feature and product must be isolated inside worktree')
    require(not feature.is_relative_to(product) and not product.is_relative_to(feature), 'feature/product overlap')
    require(canonical.is_relative_to(project), 'canonical feature outside coordinator')
    common = git(project, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    require(git(workspace, 'rev-parse', '--path-format=absolute', '--git-common-dir') == common, 'not a worktree of the coordinator repository')
    require(git(workspace, 'rev-parse', '--show-toplevel') == str(workspace), 'workspace must be repository root')
    state = state_read(canonical / 'state.yaml'); other = state_read(feature / 'state.yaml')
    require(state.get('project_id') and other.get('project_id') == state['project_id'], 'workspace project identity mismatch')
    value = {'schema_version': 1, 'id': workspace_id, 'coordinator': str(project), 'project_root': str(workspace),
             'canonical_feature': str(canonical), 'feature_root': str(feature), 'product_root': str(product),
             'project_id': state['project_id'], 'git_common_dir': common, 'base_head': git(workspace, 'rev-parse', 'HEAD')}
    with locked(home(project) / 'workspaces.lock'):
        for path in (home(project) / 'workspaces').glob('*.json'):
            old = load(path); oldroot = Path(old['project_root'])
            require(not workspace.is_relative_to(oldroot) and not oldroot.is_relative_to(workspace), 'workspace already registered or overlapping')
        write_json(home(project) / 'workspaces' / (workspace_id + '.json'), value)
    return value


def validate_isolation(binding, req, bindings, active=True):
    from coordination import check
    object_keys(binding, {'coordinator', 'workspace_id', 'key', 'token', 'owner'},
                {'coordinator', 'workspace_id', 'key', 'token', 'owner'}, 'isolation binding')
    info = inspect_workspace(binding['coordinator'], binding['workspace_id'])
    require(info['project_root'] == str(Path(bindings['project_root']).resolve()), 'isolated project root mismatch')
    require(info['feature_root'] == str(Path(req['root']).resolve()), 'isolated feature mismatch')
    require(info['product_root'] == str(Path(bindings['product_root']).resolve()), 'isolated product mismatch')
    require(binding['key'] == info['canonical_feature'] + '#' + bindings['task_id'], 'isolated task identity mismatch')
    require(not bindings.get('store_roots'), 'external file stores require serial execution or an isolated adapter')
    if active: check(binding['coordinator'], binding['key'], binding['token'], binding['owner'], binding['workspace_id'])
    return info


def import_result(project, workspace_id, task_id, result_path, token, expected_state):
    from coordination import home, check
    from state_store import update
    from task_state import result_for
    from task_runtime import context
    info = inspect_workspace(project, workspace_id)
    root = Path(info['canonical_feature']); execution = Path(info['feature_root'])
    # The same lock as claim/release prevents a stale worker completing during reassignment.
    with locked(home(project) / 'claims.lock'):
        row = check(project, str(root) + '#' + task_id, token, workspace=workspace_id)
        state = state_read(root / 'state.yaml'); local = state_read(execution / 'state.yaml')
        task = next(t for t in state['selected_tasks'] if t['id'] == task_id)
        run_task = dict(next(t for t in local['selected_tasks'] if t['id'] == task_id),
                        status='done', result=str(Path(result_path).resolve()), result_sha256=file_hash(result_path))
        result, manifest = result_for(execution, run_task)
        isolation = manifest['bindings'].get('isolation')
        require(isolation and isolation['token'] == token, 'result does not belong to this claim')
        validate_isolation(isolation, manifest['request'], manifest['bindings'])
        if task['status'] == 'done' and task.get('result_sha256') == file_hash(result_path) and task.get('execution'):
            result_for(root, task)
            return {'state_sha256': file_hash(root / 'state.yaml'), 'idempotent': True}
        expected = context(state, task_id); actual = manifest['prepared']['context']
        for value in (expected, actual): value['state'].pop('product_root', None)
        require(expected == actual, 'canonical task changed during isolated execution')
        require(task['status'] in ('todo', 'doing', 'blocked'), 'canonical task already completed or replaced')
        name = result['run_id']; out = root / 'imports' / (name + '-result.json')
        proof_path = root / 'imports' / (name + '-import.json')
        proof = {'schema_version': 1, 'workspace': info, 'task_id': task_id, 'result_sha256': file_hash(result_path),
                 'manifest_sha256': file_hash(result['manifest']), 'token': token, 'owner': row['owner']}
        for path, value in ((out, result), (proof_path, proof)):
            if path.exists(): require(load(path) == value, 'import collision')
            else: write_json(path, value)
        task.update(status='done', result=str(out.relative_to(root)), result_sha256=file_hash(out),
                    execution={'import_record': str(proof_path.relative_to(root)), 'sha256': file_hash(proof_path)})
        return update(root, expected_state, {'selected_tasks': state['selected_tasks']})


def imported_root(root, task, result):
    from runtime_protocol import path_inside
    e = task['execution']; object_keys(e, {'import_record', 'sha256'}, {'import_record', 'sha256'}, 'execution import')
    p = path_inside(e['import_record'], root, True)
    require(file_hash(p) == e['sha256'], 'import record changed')
    proof = load(p); info = proof['workspace']
    current = inspect_workspace(info['coordinator'], info['id'])
    require(current == info and info['canonical_feature'] == str(root), 'import project/root mismatch')
    require(proof['task_id'] == task['id'] and proof['result_sha256'] == task['result_sha256']
            and proof['manifest_sha256'] == result['manifest_sha256'], 'imported result identity mismatch')
    return Path(info['feature_root'])
