#!/usr/bin/env python3
"""Local, compare-and-swap state updates. Preserve unrelated legacy YAML sections."""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
import time

from runtime_protocol import file_hash, require, state_read


@contextmanager
def locked(path, timeout=10):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                require(time.monotonic() < deadline, 'coordination lock timeout')
                time.sleep(.02)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def yaml_rows(value, indent=0):
    if isinstance(value, dict):
        rows = []
        for key, item in value.items():
            require(re.fullmatch(r'[\w.-]+', key), 'invalid state key')
            prefix = ' ' * indent + key + ':'
            if isinstance(item, (dict, list)) and item:
                rows.append(prefix)
                rows.extend(yaml_rows(item, indent + 2))
            else:
                rows.append(prefix + ' ' + json.dumps(item, ensure_ascii=False))
        return rows
    rows = []
    for item in value:
        if isinstance(item, dict):
            nested = yaml_rows(item, indent + 2)
            rows.append(' ' * indent + '- ' + nested[0].lstrip())
            rows.extend(nested[1:])
        else:
            rows.append(' ' * indent + '- ' + json.dumps(item, ensure_ascii=False))
    return rows


def replace_sections(raw, updates):
    rows = raw.splitlines(keepends=True)
    starts = [(i, m[1]) for i, row in enumerate(rows)
              if (m := re.match(r'^([\w-]+):', row))]
    replacements = {key: '\n'.join(yaml_rows({key: value})) + '\n' for key, value in updates.items()}
    for index in reversed(range(len(starts))):
        start, key = starts[index]
        if key in replacements:
            end = starts[index + 1][0] if index + 1 < len(starts) else len(rows)
            rows[start:end] = [replacements.pop(key)]
    return ''.join(rows).rstrip() + '\n' + ''.join(replacements.values())


def update(root, expected_sha256, updates):
    """Only manager calls this, between runs or in the canonical coordinator workspace."""
    root = Path(root).resolve()
    path = root / 'state.yaml'
    allowed = {'selected_tasks', 'work_items', 'active_work', 'obligations', 'task_decisions',
               'required_capabilities', 'project_id', 'state_revision'}
    require(updates and set(updates) <= allowed - {'state_revision'}, 'unknown/empty state update')
    with locked(root / '.control/state.lock'):
        require(file_hash(path) == expected_sha256, 'state conflict: read current state and retry')
        old = state_read(path)
        require('coordinated-state-v1' in updates.get('required_capabilities', old.get('required_capabilities', [])),
                'coordinated-state-v1 required for CAS updates')
        require(type(old.get('state_revision', 0)) is int and old.get('state_revision', 0) >= 0, 'invalid state revision')
        require(set(old.get('required_capabilities', [])) <= set(updates.get('required_capabilities', old.get('required_capabilities', []))),
                'state capability downgrade forbidden')
        value = dict(updates, state_revision=old.get('state_revision', 0) + 1)
        raw = replace_sections(path.read_text(), value)
        fd, name = tempfile.mkstemp(prefix='.state-', dir=root)
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            proposed = state_read(name)
            from task_state import validate_graph
            validate_graph(proposed)
            from runtime_protocol import load
            before_tasks = {t['id']: t for t in old.get('selected_tasks', [])}
            after_tasks = {t['id']: t for t in proposed.get('selected_tasks', [])}
            issued = {load(p)['bindings']['task_id'] for p in (root / 'runs').glob('*/*-manifest.json')}
            require(issued <= after_tasks.keys(), 'cannot remove an issued task')
            for key, task in before_tasks.items():
                if task.get('result'):
                    require(key in after_tasks and all(after_tasks[key].get(k) == task.get(k)
                            for k in ('result', 'result_sha256', 'execution')), 'historical result cannot be replaced; create a successor task')
            old_issues = {x['id'] for x in old.get('obligations', [])}
            require(old_issues <= {x['id'] for x in proposed.get('obligations', [])}, 'obligation history cannot be removed')
            for key, expected in value.items():
                require(proposed.get(key) == expected, 'state serialization changed value: ' + key)
            # A writer that bypasses this API is detected before replacement where possible.
            require(file_hash(path) == expected_sha256, 'state changed outside coordinator')
            os.replace(name, path)
        finally:
            if os.path.exists(name): os.unlink(name)
    return {'state_sha256': file_hash(path), 'revision': value['state_revision']}


def bind_result(root, task_id, result_path, expected_sha256):
    """Retry safely after result publication; never rerun a completed external operation."""
    from copy import deepcopy
    from runtime_protocol import load, path_inside
    from task_state import result_for
    root = Path(root).resolve()
    state = state_read(root / 'state.yaml')
    tasks = deepcopy(state['selected_tasks'])
    task = next((t for t in tasks if t['id'] == task_id), None)
    require(task is not None, 'unknown task')
    path = path_inside(result_path, root, True)
    fields = {'status': 'done', 'result': str(path.relative_to(root)), 'result_sha256': file_hash(path)}
    if all(task.get(k) == v for k, v in fields.items()):
        result_for(root, task)
        return {'state_sha256': file_hash(root / 'state.yaml'), 'idempotent': True}
    require(task['status'] in ('todo', 'doing', 'blocked'), 'new task instance required')
    task.update(fields)
    result_for(root, task)
    require(not load(load(path)['manifest'])['bindings'].get('isolation'),
            'isolated results require fenced import-result')
    return update(root, expected_sha256, {'selected_tasks': tasks})
