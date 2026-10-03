#!/usr/bin/env python3
"""Scoped work completion over the existing task graph. Never closes a feature or grants release authority."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from runtime_protocol import (CAPABILITIES, file_hash, load, now, object_keys,
                              path_inside, require, safe_id, state_read, version, write_json)

WORK_REQUIRED = {'id', 'kind', 'intent_quote', 'scope', 'target', 'tasks', 'continuation', 'status'}
WORK_KEYS = WORK_REQUIRED | {'result', 'result_sha256', 'origin', 'reason', 'uncertainty'}


def work_definition(work):
    return {k: work[k] for k in ('id', 'kind', 'intent_quote', 'scope', 'target', 'tasks', 'continuation', 'origin') if k in work}


def work_context(work, task_id):
    value = {k: v for k, v in work_definition(work).items() if k != 'tasks'}
    value['completion'] = next(e for e in work['tasks'] if e['task'] == task_id)
    return value


def validate_work_items(state, graph):
    items = state.get('work_items', [])
    require(isinstance(items, list), 'work_items must be a list')
    if items:
        require('work-scope-v1' in state.get('required_capabilities', []), 'work_items require work-scope-v1')
    works = {}
    for work in items:
        object_keys(work, WORK_KEYS, WORK_REQUIRED, 'work item')
        safe_id(work['id'], 'work id')
        require(work['id'] not in works, 'duplicate work id')
        require(work['kind'] in ('create', 'refine', 'fix'), 'unknown work kind')
        for field in ('intent_quote', 'scope', 'target'):
            require(isinstance(work[field], str) and bool(work[field].strip()), 'work missing ' + field)
        require(work['continuation'] in ('stop', 'continue'), 'unknown work continuation')
        require(work['status'] in ('active', 'completed', 'cancelled'), 'unknown work status')
        require(work.get('uncertainty', 'bounded') in ('spike', 'bounded', 'architectural'), 'unknown work uncertainty')
        require(isinstance(work['tasks'], list) and bool(work['tasks']), 'work needs selected tasks')
        seen = set()
        for edge in work['tasks']:
            object_keys(edge, {'task', 'requires'}, {'task', 'requires'}, 'work completion')
            require(edge['task'] in graph and edge['task'] not in seen, 'unknown/duplicate work task')
            require(edge['requires'] in ('produced', 'accepted', 'verified'), 'unknown work completion level')
            seen.add(edge['task'])
        if work['status'] == 'completed':
            require(work.get('result') and work.get('result_sha256'), 'completed work needs immutable completion record')
        if work['status'] == 'cancelled':
            require(isinstance(work.get('reason'), str) and bool(work['reason'].strip()), 'cancelled work needs reason')
        if work['kind'] == 'fix':
            require(isinstance(work.get('origin'), str) and bool(work['origin'].strip()), 'fix work needs defect/baseline origin')
        works[work['id']] = work
    active = state.get('active_work')
    if active:
        require(active in works and works[active]['status'] == 'active', 'active_work must name active work')
    for task in graph.values():
        if task.get('work_id'):
            require(task['work_id'] in works, 'task references unknown work')
            require(task['id'] in {e['task'] for e in works[task['work_id']]['tasks']}, 'work omits owned task')
    return works


def completion_evidence(root, task, level):
    if level == 'produced':
        return None
    from task_runtime import decision
    field = 'acceptance' if level == 'accepted' else 'verification'
    require(task.get(field), task['id'] + ' lacks ' + field)
    result = decision(root / task[field], scope=root)
    d = result['record']
    require(d['kind'] == field and d.get('result_sha256') == task['result_sha256'], 'completion decision must bind task result')
    require(not d['obligations'], 'completion decision has unresolved obligations')
    return result


def check_work(root, work_id):
    from task_state import check_tasks, validate_graph
    root = Path(root).resolve()
    state = state_read(root / 'state.yaml'); graph = validate_graph(state)
    works = validate_work_items(state, graph)
    require(work_id in works, 'unknown work id')
    work = works[work_id]
    require(work['status'] != 'cancelled', 'work is cancelled')
    ids = [e['task'] for e in work['tasks']]
    report = check_tasks(root, closure=True, task_ids=ids)
    errors = report['errors']
    evidence = {}
    for edge in work['tasks']:
        task = graph[edge['task']]
        try:
            lineage = []
            while task['status'] == 'superseded':
                successor = graph[task['successor']]
                require((successor['role'], successor['stage'], successor['task']) == (task['role'], task['stage'], task['task']),
                        'work successor must fulfil the same task contract')
                require(successor['id'] in ids, 'select the successor in this work before completion')
                lineage.append(task['id']); task = successor
            require(task['status'] == 'done', task['id'] + ': select the completed successor or finish the task')
            row = report['tasks'][task['id']]
            drift = row.get('source_drift_from')  # source changes all written by tasks of this same work
            require(row['validity'] == 'current' or (drift and set(drift) <= set(ids)), task['id'] + ': result needs revalidation')
            evidence[edge['task']] = {'task': task['id'], 'superseded': lineage,
                                    'result': task['result'], 'result_sha256': task['result_sha256'],
                                    'decision': completion_evidence(root, task, edge['requires'])}
        except (OSError, ValueError, KeyError, TypeError) as e:
            errors.append(str(e))
    # Removing issued work from a new selection cannot manufacture completion.
    for manifest in (root / 'runs').glob('*/*-manifest.json'):
        run = load(manifest); version(run)
        ctx = run['prepared']['context']
        if ctx.get('work', {}).get('id') == work_id:
            if run['bindings']['task_id'] not in ids:
                errors.append('issued work task removed: ' + run['bindings']['task_id'])
            elif ctx['work'] != work_context(work, run['bindings']['task_id']):
                errors.append('work definition changed after dispatch; create a successor work item')
    if work['status'] == 'completed':
        saved = path_inside(work['result'], root, True)
        require(file_hash(saved) == work['result_sha256'], 'work completion digest mismatch')
        old = load(saved); version(old)
        require(old.get('kind') == 'work-completion' and old.get('feature_root') == str(root)
                and old.get('definition') == work_definition(work), 'work completion does not match this work')
        if not errors and old.get('evidence') != evidence:
            errors.append('completed work evidence changed; use a new work item')
    return {'work_id': work_id, 'claim': 'scoped-task-completion', 'feature_complete': False,
            'target': work['target'], 'continuation': work['continuation'],
            'historical_completion': work['status'] == 'completed', 'tasks': report['tasks'],
            'evidence': evidence, 'definition': work_definition(work), 'errors': list(dict.fromkeys(errors))}


def complete_work(root, work_id, out):
    root = Path(root).resolve()
    report = check_work(root, work_id)
    require(not report['errors'], 'work not complete: ' + '; '.join(report['errors']))
    state = state_read(root / 'state.yaml')
    require(next(w for w in state['work_items'] if w['id'] == work_id)['status'] == 'active', 'work already completed')
    target = path_inside(out, root)
    require(target.is_relative_to(root / 'work'), 'completion record must be under feature/work/')
    value = {'protocol_version': 1, 'required_capabilities': sorted(CAPABILITIES), 'kind': 'work-completion',
             'feature_root': str(root), 'at': now(), 'definition': report['definition'],
             'evidence': report['evidence'], 'claim': report['claim'], 'feature_complete': False}
    write_json(target, value)
    return {'work_id': work_id, 'result': str(target.relative_to(root)), 'result_sha256': file_hash(target),
            'status': 'completed', 'feature_complete': False,
            'next': 'Manager records these fields in work_items and clears active_work; do not add hats_done or set phase Closed.'}


def impact(root, task_id):
    from task_state import check_tasks, validate_graph
    root = Path(root).resolve(); graph = validate_graph(state_read(root / 'state.yaml'))
    require(task_id in graph, 'unknown task id')
    affected = {task_id}
    while True:
        more = {key for key, task in graph.items() if any(e['task'] in affected for e in task['depends_on'])}
        if more <= affected: break
        affected |= more
    readiness = check_tasks(root)
    return {'changed_task': task_id, 'affected_tasks': sorted(affected),
            'tasks': {key: readiness['tasks'][key] for key in sorted(affected)},
            'note': 'Declared dependency impact only, including previously passed acceptance tasks. Use trace and owner review for missing links. No files or states changed.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for cmd in ('check-work', 'complete-work', 'impact'):
        p = sub.add_parser(cmd); p.add_argument('--root', required=True)
        p.add_argument('--task-id' if cmd == 'impact' else '--work-id', required=True)
        if cmd == 'complete-work': p.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'impact': value = impact(args.root, args.task_id)
        elif args.command == 'complete-work': value = complete_work(args.root, args.work_id, args.out)
        else: value = check_work(args.root, args.work_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return int(bool(value.get('errors')))
    except (OSError, ValueError, TypeError, KeyError) as e:
        print('work scope: ' + str(e)); return 2


if __name__ == '__main__':
    raise SystemExit(main())
