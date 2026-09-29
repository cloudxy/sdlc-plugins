#!/usr/bin/env python3
"""Immutable artifact versions and explicit, compare-and-swap baseline promotion."""
from __future__ import annotations

from pathlib import Path
from runtime_protocol import (digest, file_hash, load, now, object_keys, path_inside,
                              require, safe_id, state_read, write_json)
from state_store import locked

KEYS = {'schema_version', 'kind', 'logical_id', 'feature_root', 'project_id', 'artifact',
        'source_path', 'sha256', 'object', 'producer', 'at', 'product_file'}


def capture(root, logical_id, source, artifact=None, producer_task=None, product_file=None):
    from task_runtime import freeze_files
    from task_state import result_for
    from workflow import load_registry, artifact_paths
    import fnmatch
    root = Path(root).resolve()
    if product_file:
        from check_config import parse_yaml
        project = next((p for p in root.parents if (p / 'sdlc.config.yaml').is_file()), None)
        require(project is not None and not artifact, 'product version needs project configuration and no feature artifact type')
        config = parse_yaml((project / 'sdlc.config.yaml').read_text())
        product = (project / config.get('product_root', 'docs/product')).resolve()
        source = path_inside(source, product, True)
        require(source == path_inside(product_file, product, True), 'product version path mismatch')
    elif producer_task and not Path(source).resolve().is_relative_to(root):
        # An imported isolated result keeps its output in the registered worktree; ownership is proven below.
        source = Path(source).resolve(); require(source.is_file() and not source.is_symlink(), 'missing artifact source')
    else:
        source = path_inside(source, root, True)
    safe_id(logical_id, 'artifact logical id')
    state = state_read(root / 'state.yaml')
    require('artifact-versions-v1' in state.get('required_capabilities', []), 'artifact-versions-v1 required')
    producer, owner_root = None, root
    if producer_task:
        task = next((t for t in state['selected_tasks'] if t['id'] == producer_task), None)
        require(task is not None and task.get('result'), 'unknown producer or producer without a bound result')
        result, _ = result_for(root, task)
        owner_root = Path(result['request']['root']).resolve()
        require(product_file or source.is_relative_to(owner_root), 'artifact source is outside the producer run')
        require(result['outputs'].get(str(source), {}).get('sha256') == file_hash(source), 'producer does not own this output version')
        producer = {'task': producer_task, 'result': task['result'], 'sha256': task['result_sha256']}
    if artifact:
        patterns = artifact_paths(load_registry(), [artifact])
        require(any(fnmatch.fnmatchcase(source.relative_to(owner_root).as_posix(), p) for p in patterns), 'artifact source path mismatch')
    obj = freeze_files(root, [str(source)])[str(source)]
    value = {'schema_version': 1, 'kind': 'artifact-version', 'logical_id': logical_id,
             'feature_root': str(root), 'project_id': state.get('project_id'), 'artifact': artifact,
             'source_path': str(source), 'sha256': obj['sha256'], 'object': obj['object'],
             'producer': producer, 'at': now(), 'product_file': product_file}
    path = root / 'artifacts' / logical_id / (digest(value) + '.json')
    write_json(path, value)
    return {'path': str(path), 'sha256': file_hash(path)}


def resolve(ref):
    object_keys(ref, {'path', 'sha256', 'decision'}, {'path', 'sha256'}, 'artifact reference')
    p = Path(ref['path']).resolve()
    require(file_hash(p) == ref['sha256'], 'artifact record digest mismatch')
    v = load(p); object_keys(v, KEYS, KEYS, 'artifact version')
    require(v['schema_version'] == 1 and v['kind'] == 'artifact-version', 'unsupported artifact version')
    safe_id(v['logical_id'])
    root = Path(v['feature_root']).resolve()
    require(p.is_relative_to(root / 'artifacts' / v['logical_id']), 'artifact record outside owner')
    obj = path_inside(v['object'], root, True)
    require(obj == root / '.task-objects' / v['sha256'], 'artifact object identity mismatch')
    require(file_hash(obj) == v['sha256'], 'artifact content modified')
    state = state_read(root / 'state.yaml')
    require(v['project_id'] == state.get('project_id'), 'artifact project identity changed')
    return v


def input_value(ref, entry):
    from task_runtime import decision, file_input
    v = resolve(ref)
    require(entry['access'] == 'read', 'version inputs are immutable; propose a successor for writes')
    if entry['source'] == 'artifact':
        require(v['artifact'] == entry['ref'], 'version does not fulfil registered artifact input')
    elif entry['source'] == 'product':
        require(v['product_file'] == entry['ref'], 'version product input mismatch')
    else:
        require(entry['source'] == 'binding', 'version unsupported for this input type')
    value = file_input(v['object'], 'read', entry.get('allow_unfilled', False))
    value['artifact_version'] = dict(ref)
    if entry.get('requires_acceptance'):
        require(ref.get('decision'), 'accepted artifact version needs decision')
        d = decision(ref['decision'], target=v['object'], scope=v['feature_root'])
        require(d['record']['kind'] == 'acceptance' and not d['record']['obligations'], 'artifact version not accepted')
        value['acceptance'] = [d]
    return value


def promote(ref, expected_sha256, decision_path):
    """Publish a current pointer, never overwrite the old version or infer acceptance."""
    from task_runtime import decision
    v = resolve(ref); root = Path(v['feature_root'])
    d = decision(decision_path, target=v['object'], scope=root)
    require(d['record']['kind'] == 'acceptance' and not d['record']['obligations'], 'promotion needs acceptance without open obligations')
    pointer = root / 'artifacts' / v['logical_id'] / 'current.json'
    with locked(root / '.control/artifacts.lock'):
        actual = file_hash(pointer) if pointer.exists() else None
        require(actual == expected_sha256, 'artifact baseline conflict')
        value = {'version': ref, 'decision': d, 'previous_pointer_sha256': actual, 'at': now()}
        # Immutable promotion history survives replacement of the derived current pointer.
        history = pointer.parent / ('promotion-' + digest(value) + '.json')
        write_json(history, value)
        write_json(pointer, value, exclusive=False)
    return {'pointer': str(pointer), 'sha256': file_hash(pointer), 'history': str(history)}
