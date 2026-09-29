#!/usr/bin/env python3
"""Exact integration candidates. Component success alone never proves integration."""
from __future__ import annotations
import hashlib
import subprocess
from pathlib import Path

from runtime_protocol import (digest, file_hash, load, now, object_keys, require, safe_id, state_read, write_json)
from task_runtime import source_snapshot


def git_base(project, ref):
    def run(*args):
        p = subprocess.run(['git', '-C', str(project), *args], capture_output=True)
        require(p.returncode == 0, 'candidate base: ' + p.stderr.decode(errors='replace'))
        return p.stdout
    commit = run('rev-parse', '--verify', ref + '^{commit}').decode().strip()
    files = {}
    for line in run('ls-tree', '-r', '-z', commit).split(b'\0'):
        if not line: continue
        meta, name = line.split(b'\t', 1); mode, kind, blob = meta.split()
        require(kind == b'blob' and mode in (b'100644', b'100755', b'120000'), 'candidate base requires files or symlinks (submodules need an explicit adapter)')
        content = run('cat-file', 'blob', blob.decode())
        # A symlink is pinned by its link text; components cannot change it, so it must match the base.
        files[name.decode()] = ({'symlink': content.decode(errors='surrogateescape')} if mode == b'120000' else
                                {'sha256': hashlib.sha256(content).hexdigest(), 'mode': int(mode[-3:], 8)})
    return commit, files


def live_files(project, root, product):
    snap = source_snapshot(project, root, product)
    values = {}
    for path, entry in snap['files'].items():
        relative = Path(path).relative_to(project).as_posix()
        if relative == '.git': continue  # worktree administrative pointer is not shipped source
        values[relative] = ({'symlink': entry['target']} if entry['type'] == 'symlink' else
                            {'sha256': entry['sha256'], 'mode': entry['mode']})
    return snap, values


def external_links(project, files):
    """Symlinks that leave the repository: their link text is pinned, the content they reach is not."""
    out = []
    for relative, value in sorted(files.items()):
        if 'symlink' in value:
            target = (project / relative).parent / value['symlink']
            if not Path(target).resolve().is_relative_to(project): out.append({'path': relative, 'target': value['symlink']})
    return out


def create(project, root, product, candidate_id, base, components, checks, versions=()):
    from task_state import validate_graph, check_tasks, result_for
    from runtime_protocol import state_read
    from artifact_versions import resolve
    project, root, product = map(lambda p: Path(p).resolve(), (project, root, product))
    safe_id(candidate_id)
    require(root.is_relative_to(project), 'candidate feature root outside project')
    owner_state = state_read(root / 'state.yaml')
    require('candidate-v1' in owner_state.get('required_capabilities', []), 'candidate-v1 required')
    require(owner_state.get('project_id'), 'candidate needs logical project identity')
    require(isinstance(components, list) and components, 'candidate needs explicit components')
    require(checks and any(x.get('id') == 'integration' for x in checks), 'candidate needs an integration execution check')
    for check in checks:
        object_keys(check, {'id', 'scope', 'environment', 'build_required'}, {'id', 'scope', 'environment', 'build_required'}, 'candidate check')
        require(check['scope'] == candidate_id and isinstance(check['build_required'], bool), 'candidate check must bind this candidate scope')
    commit, original = git_base(project, base)
    snap, actual = live_files(project, root, product)
    excluded = [root, product, project / '.sdlc']
    original = {p: v for p, v in original.items() if not any((project / p).is_relative_to(x) for x in excluded)}
    expected = {}; pinned = []; seen = set()
    for component in components:
        object_keys(component, {'root', 'task', 'result_sha256'}, {'root', 'task', 'result_sha256'}, 'candidate component')
        owner = Path(component['root']).resolve(); key = str(owner) + '#' + component['task']
        require(key not in seen, 'duplicate candidate component'); seen.add(key)
        component_state = state_read(owner / 'state.yaml')
        require(component_state.get('project_id') == owner_state['project_id'], 'candidate component project mismatch')
        graph = validate_graph(component_state); task = graph[component['task']]
        require(task['status'] == 'done' and task['result_sha256'] == component['result_sha256'], 'candidate component version mismatch')
        ready = check_tasks(owner, closure=True, task_ids=[task['id']])
        require(not ready['errors'], 'candidate component not ready: ' + '; '.join(ready['errors']))
        result, manifest = result_for(owner, task)
        for item in result['declared_inputs'].values():
            if 'source_snapshot' in item:
                require(item['source_snapshot']['head'] == commit,
                        'component uses a different Git baseline; record integration against the candidate baseline')
        source = Path(manifest['bindings']['project_root']); feature = Path(manifest['request']['root'])
        product_source = Path(manifest['bindings']['product_root'])
        for path, record in result['outputs'].items():
            p = Path(path)
            if not p.is_relative_to(source) or p.is_relative_to(feature) or p.is_relative_to(product_source) or p.is_relative_to(source / '.sdlc'): continue
            relative = p.relative_to(source).as_posix()
            require(record['type'] in ('file', 'deleted'), 'unsupported component file type')
            value = None if record['type'] == 'deleted' else {'sha256': record['sha256'], 'mode': record['mode']}
            require(relative not in expected or expected[relative] == value, 'component output conflict: integrate and record a separate integration task')
            expected[relative] = value
        pinned.append({'component': component, 'result': task['result'], 'manifest_sha256': result['manifest_sha256'],
                       'dependencies': task['depends_on'], 'external_dependencies': task.get('external_dependencies', [])})
    changed = {p for p in set(original) | set(actual) if original.get(p) != actual.get(p)}
    require(changed <= expected.keys(), 'candidate contains unaccounted source changes: ' + ', '.join(sorted(changed - expected.keys())))
    require(all(actual.get(p) == v for p, v in expected.items()), 'candidate does not contain exact component outputs')
    for ref in versions: resolve(ref)
    manifest = {'schema_version': 1, 'kind': 'integration-candidate', 'id': candidate_id, 'at': now(),
                'project_root': str(project), 'feature_root': str(root), 'product_root': str(product), 'base': commit,
                'source': snap, 'components': pinned, 'artifact_versions': list(versions), 'required_checks': checks,
                'changed_paths': sorted(changed), 'expected_outputs': expected,
                'external_links': external_links(project, actual)}
    target = project / '.sdlc/candidates' / candidate_id / 'manifest.json'
    write_json(target, manifest)
    return {'manifest': str(target), 'sha256': file_hash(target), 'claim': 'candidate-defined', 'verified': False}


def verify(path, records, approvals=(), release=False):
    from evidence import verify_bound_records
    from artifact_versions import resolve
    from task_runtime import decision
    from task_state import check_tasks
    m = load(path)
    require(m['schema_version'] == 1 and m['kind'] == 'integration-candidate', 'unsupported candidate')
    project, root, product = map(Path, (m['project_root'], m['feature_root'], m['product_root']))
    require(source_snapshot(project, root, product) == m['source'], 'candidate source changed; create a new candidate')
    for component in m['components']:
        c = component['component']; state = state_read(Path(c['root']) / 'state.yaml')
        task = next(t for t in state['selected_tasks'] if t['id'] == c['task'])
        require(task.get('result_sha256') == c['result_sha256'], 'candidate component changed')
        report = check_tasks(c['root'], closure=True, task_ids=[c['task']])
        require(not report['errors'], 'candidate has unresolved/invalid component: ' + '; '.join(report['errors']))
    for ref in m['artifact_versions']: resolve(ref)
    verified = verify_bound_records(root, records, m['required_checks'], project, product)
    decisions = {}
    for entry in approvals:
        object_keys(entry, {'purpose', 'path'}, {'purpose', 'path'}, 'candidate approval')
        require(entry['purpose'] not in decisions, 'duplicate candidate approval')
        d = decision(entry['path'], target=path, scope=root)
        require(not d['record']['obligations'], 'candidate approval has unresolved conditions')
        expected_kind = 'acceptance' if entry['purpose'] == 'product' else 'verification'
        require(d['record']['kind'] == expected_kind, 'wrong candidate proof kind')
        decisions[entry['purpose']] = d
    if release:
        require({'product', 'quality', 'operations'} <= decisions.keys(), 'release requires product acceptance, independent quality review and operations readiness')
        require(any(x['build_required'] for x in m['required_checks']), 'release candidate needs build-bound execution')
    outcome = {'schema_version': 1, 'candidate_sha256': file_hash(path), 'at': now(), 'checks': verified,
               'approvals': decisions, 'claim': 'release-ready' if release else 'integration-verified', 'deployed': False}
    out = Path(path).parent / ('verification-' + digest(outcome) + '.json')
    write_json(out, outcome)
    return {'result': str(out), **outcome}
