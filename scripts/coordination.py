#!/usr/bin/env python3
"""Local leases and resource claims. A lease is coordination, not a sandbox."""
from __future__ import annotations
from pathlib import Path
import hashlib
import re
import subprocess
import sys
import time
import uuid
from runtime_protocol import load, require, safe_id, write_json, object_keys
from state_store import locked

_HOST = None


def host_id():
    """Stable local machine identity, hashed. Leases and locks are only valid on one host."""
    global _HOST
    if _HOST is None:
        raw = None
        for name in ('/etc/machine-id', '/var/lib/dbus/machine-id'):
            try: raw = Path(name).read_text().strip() or None
            except OSError: pass
            if raw: break
        if not raw and sys.platform == 'darwin':
            try:
                out = subprocess.run(['/usr/sbin/ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                                     capture_output=True, text=True, timeout=10).stdout
            except (OSError, subprocess.SubprocessError): out = ''
            match = re.search(r'"IOPlatformUUID" = "([^"]+)"', out)
            raw = match.group(1) if match else None
        _HOST = hashlib.sha256((raw or 'node:%d' % uuid.getnode()).encode()).hexdigest()[:16]
    return _HOST


def same_host(row):
    # Rows written before host binding stay readable; new rows fail closed on another machine.
    require(row.get('host') in (None, host_id()), 'claim belongs to another machine; cross-machine coordination is unsupported')


def home(project):
    return Path(project).resolve() / '.sdlc/control'


def _read(project):
    path = home(project) / 'claims.json'
    value = load(path) if path.exists() else {'schema_version': 1, 'next_token': 1, 'claims': {}}
    require(value['schema_version'] == 1, 'unsupported coordination schema')
    return path, value


def resources_valid(resources):
    require(isinstance(resources, list) and bool(resources), 'declare workspace and external resources')
    seen = set()
    for r in resources:
        object_keys(r, {'id', 'mode'}, {'id', 'mode'}, 'resource')
        require(isinstance(r['id'], str) and r['id'] and r['mode'] in ('read', 'write'), 'invalid resource')
        require(r['id'] not in seen, 'duplicate resource'); seen.add(r['id'])


def conflicts(left, right):
    # Hierarchical resource IDs let database-wide migration conflict with partition writers.
    a, b = left['id'].rstrip('/'), right['id'].rstrip('/')
    overlap = a == b or a.startswith(b + '/') or b.startswith(a + '/')
    return overlap and 'write' in (left['mode'], right['mode'])


def claim(project, key, owner, workspace, resources, ttl=300):
    from workspaces import inspect_workspace
    safe_id(owner, 'owner'); safe_id(workspace, 'workspace')
    require(isinstance(key, str) and '#' in key, 'claim key must be absolute feature root#task id')
    feature, task = key.rsplit('#', 1); safe_id(task)
    require(Path(feature).is_absolute(), 'claim feature root must be absolute')
    require(type(ttl) in (int, float) and 1 <= ttl <= 86400, 'lease ttl must be 1..86400 seconds')
    info = inspect_workspace(project, workspace)
    require(str(Path(feature).resolve()) == info['canonical_feature'], 'workspace belongs to another feature')
    require(key == info['canonical_feature'] + '#' + task, 'claim key must use canonical feature identity')
    from runtime_protocol import state_read
    state = state_read(Path(info['canonical_feature']) / 'state.yaml')
    selected = next((t for t in state['selected_tasks'] if t['id'] == task), None)
    require(selected and selected['status'] in ('todo', 'doing', 'blocked'), 'claim requires a selected unfinished task')
    if selected.get('work_id'):
        require(any(w['id'] == selected['work_id'] and w['status'] == 'active' for w in state.get('work_items', [])), 'claim work is not active')
    resources_valid(resources)
    needed = {'id': 'workspace/' + workspace, 'mode': 'write'}
    resources = [*resources, needed] if needed not in resources else resources
    resources_valid(resources)
    with locked(home(project) / 'claims.lock'):
        path, value = _read(project); now = time.time()
        for existing_key, existing in value['claims'].items():
            if existing['status'] != 'active': continue
            same_host(existing)
            # Expired does not imply stopped. Explicit reconciliation is required to reclaim.
            require(existing_key != key, 'task already claimed; reconcile expired claims before reassignment')
            require(not any(conflicts(a, b) for a in resources for b in existing['resources']), 'shared resource conflict')
        token = value['next_token']; value['next_token'] += 1
        row = {'owner': owner, 'workspace': workspace, 'token': token, 'expires': now + ttl,
               'resources': resources, 'status': 'active', 'host': host_id()}
        value['claims'][key] = row
        write_json(path, value, exclusive=False)
    return {'coordinator': str(Path(project).resolve()), 'key': key, **row}


def check(project, key, token, owner=None, workspace=None):
    _, value = _read(project); row = value['claims'].get(key)
    require(row and row['token'] == token and row['status'] == 'active', 'stale or released claim token')
    same_host(row)
    require(row['expires'] > time.time(), 'claim expired; reconcile before publishing')
    require(owner is None or row['owner'] == owner, 'claim owner mismatch')
    require(workspace is None or row['workspace'] == workspace, 'claim workspace mismatch')
    return row


def heartbeat(project, key, token, ttl=300):
    require(type(ttl) in (int, float) and 1 <= ttl <= 86400, 'invalid lease ttl')
    with locked(home(project) / 'claims.lock'):
        check(project, key, token)
        path, value = _read(project)
        value['claims'][key]['expires'] = time.time() + ttl
        write_json(path, value, exclusive=False)
    return value['claims'][key]


def release(project, key, token, reason, reconciled=False):
    require(isinstance(reason, str) and reason.strip(), 'release needs reconciliation/completion reason')
    with locked(home(project) / 'claims.lock'):
        path, value = _read(project); row = value['claims'].get(key)
        require(row and row['token'] == token and row['status'] == 'active', 'stale claim token')
        same_host(row)
        require(row['expires'] > time.time() or reconciled, 'expired claim requires process/job reconciliation')
        row.update(status='released', reason=reason, reconciled=reconciled)
        write_json(home(project) / 'history' / f'{token}.json', {'key': key, **row})
        write_json(path, value, exclusive=False)
    return row
