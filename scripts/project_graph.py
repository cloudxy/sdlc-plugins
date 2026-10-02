#!/usr/bin/env python3
"""Derived cross-feature graph; feature state remains the only task truth."""
from __future__ import annotations
from pathlib import Path
from runtime_protocol import (file_hash, object_keys, require, safe_id, state_read)


def validate_reference(edge):
    object_keys(edge, {'feature_root', 'project_id', 'task', 'result_sha256', 'requires', 'version'},
                {'feature_root', 'project_id', 'task', 'result_sha256', 'requires'}, 'external dependency')
    safe_id(edge['project_id'], 'project id'); safe_id(edge['task'])
    require(Path(edge['feature_root']).is_absolute(), 'external feature root must be absolute')
    require(edge['requires'] in ('produced', 'accepted', 'verified'), 'unknown external proof level')
    require(isinstance(edge['result_sha256'], str) and len(edge['result_sha256']) == 64, 'external result digest required')


def node_id(root, task):
    return str(Path(root).resolve()) + '#' + task


def graph(roots):
    from task_state import validate_graph
    pending = list(map(lambda p: Path(p).resolve(), roots)); states = {}; nodes = {}
    while pending:
        root = pending.pop()
        if str(root) in states: continue
        require(len(states) < 100, 'project graph exceeds 100 features; narrow explicit roots')
        state = state_read(root / 'state.yaml')
        local = validate_graph(state)
        states[str(root)] = state
        for task in local.values():
            key = node_id(root, task['id'])
            edges = [node_id(root, e['task']) for e in task['depends_on']]
            for edge in task.get('external_dependencies', []):
                validate_reference(edge)
                target = Path(edge['feature_root']).resolve()
                pending.append(target); edges.append(node_id(target, edge['task']))
            if task.get('successor'): edges.append(node_id(root, task['successor']))
            nodes[key] = {'root': str(root), 'task': task, 'dependencies': edges}
    visiting, done = set(), set()
    def visit(key):
        require(key in nodes, 'dangling project dependency: ' + key)
        require(key not in visiting, 'cross-feature dependency cycle: ' + key)
        if key in done: return
        visiting.add(key)
        for dep in nodes[key]['dependencies']: visit(dep)
        visiting.remove(key); done.add(key)
    for key, value in nodes.items():
        for edge in value['task'].get('external_dependencies', []):
            state = states[str(Path(edge['feature_root']).resolve())]
            require(state.get('project_id') == edge['project_id'], 'external project identity mismatch')
        visit(key)
    return {'nodes': nodes, 'states': states}


def check_reference(edge, stack=()):
    from task_state import check_tasks, current_validity, result_for, validate_graph
    from work_scope import completion_evidence
    validate_reference(edge)
    root = Path(edge['feature_root']).resolve()
    key = node_id(root, edge['task'])
    require(key not in stack, 'cross-feature dependency cycle')
    state = state_read(root / 'state.yaml'); local = validate_graph(state)
    require(state.get('project_id') == edge['project_id'], 'external project identity mismatch')
    require(edge['task'] in local, 'external task missing')
    task = local[edge['task']]
    require(task.get('result_sha256') == edge['result_sha256'], 'external result version mismatch')
    require(task['status'] in ('done', 'superseded'), 'external task incomplete')
    result, manifest = result_for(root, task)
    report = check_tasks(root, task_id=task['id'], external_stack=(*stack, key))
    require(not report['errors'], 'external obligations/dependencies: ' + '; '.join(report['errors']))
    proof = None
    if edge.get('version'):
        from artifact_versions import input_value, resolve
        v = resolve(edge['version'])
        require(v['feature_root'] == str(root) and v['producer'] and v['producer']['task'] == task['id']
                and v['producer']['sha256'] == edge['result_sha256'], 'external artifact producer mismatch')
        require(edge['requires'] != 'verified', 'artifact snapshot alone cannot prove current behavior verification')
        proof = input_value(edge['version'], {'source': 'binding', 'access': 'read',
                                            'requires_acceptance': edge['requires'] == 'accepted'})
    else:
        validity, reasons = current_validity(root, task, result, manifest)
        require(validity == 'current', 'external dependency needs revalidation: ' + '; '.join(reasons))
        proof = completion_evidence(root, task, edge['requires'])
    return {'reference': edge, 'result': task['result'], 'result_sha256': task['result_sha256'], 'proof': proof}


def readiness(roots, changed=None, coordinator=None):
    from task_state import check_tasks
    index = graph(roots); rows = {}
    claims = {}
    if coordinator:
        from coordination import _read
        claims = _read(coordinator)[1]['claims']
    for key, item in index['nodes'].items():
        root, task = item['root'], item['task']
        report = check_tasks(root, task_id=task['id'])
        reasons = list(report['errors'])
        state = index['states'][root]
        if task.get('work_id'):
            work = next(w for w in state['work_items'] if w['id'] == task['work_id'])
            if work['status'] != 'active': reasons.append('work is not active')
        if task['status'] not in ('todo', 'blocked'): reasons.append('task is ' + task['status'])
        if key in claims and claims[key]['status'] == 'active':
            import time
            claim = claims[key]
            reasons.append('claimed by ' + claim['owner'] if claim['expires'] > time.time() else 'expired claim needs process/job reconciliation')
        rows[key] = {'ready': not reasons, 'reasons': reasons, 'dependencies': item['dependencies']}
    affected = set(); coverage = {}
    if changed:
        require(changed in rows, 'unknown changed project task')
        affected.add(changed)
        undeclared, unverified = set(), set()
        while True:
            more = {k for k, v in rows.items() if set(v['dependencies']) & affected}
            # A completed result that read an affected output is a consumer even without a declared edge.
            found, unknown = _path_consumers(index, affected | more)
            undeclared |= found - more - affected; unverified |= unknown
            more |= found
            if more <= affected: break
            affected |= more
        coverage = {'undeclared_consumers': sorted(undeclared), 'unverified_consumers': sorted(unverified - affected),
                    'unreadable_affected': sorted(unverified & affected),
                    'impact_complete': not undeclared and not unverified}
    return {'tasks': rows, 'affected': sorted(affected), **coverage, 'derived': True,
            'limits': ['only the listed feature roots are searched; consumers elsewhere need owner review',
                       'completed tasks without a readable protocol result are unverified, never assumed unaffected',
                       'resource acquisition is checked atomically at claim time']}


def _result_paths(root, task):
    from task_state import result_for
    result, _ = result_for(Path(root), task)
    outputs = {p for p, v in result['outputs'].items() if v['type'] == 'file'}
    reads = {v['path'] for v in result['declared_inputs'].values() if isinstance(v, dict) and 'path' in v}
    return outputs, reads


def _path_consumers(index, changed_keys):
    """Match recorded input paths against outputs of changed results; unknown coverage is reported."""
    produced, unknown, results = set(), set(), {}
    for key, item in index['nodes'].items():
        task = item['task']
        if task['status'] not in ('done', 'superseded'): continue
        try: results[key] = _result_paths(item['root'], task)
        except (OSError, ValueError, KeyError, TypeError): unknown.add(key)
    for key in changed_keys:
        if key in results: produced |= results[key][0]
    found = {key for key, (_, reads) in results.items() if key not in changed_keys and reads & produced}
    # An unreadable changed result hides its outputs; an unreadable other result hides its reads.
    return found, unknown
