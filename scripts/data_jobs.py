#!/usr/bin/env python3
"""Durable external-job adapter. Submission is never completion; uncertain starts are reconciled."""
from __future__ import annotations
from pathlib import Path
import subprocess
from runtime_protocol import (digest, file_hash, load, loads, now, object_keys, require,
                              safe_id, write_json)
from state_store import locked

STATUSES = {'submitted', 'running', 'succeeded', 'failed', 'cancelled', 'unknown'}


def _directory(project, key):
    safe_id(key, 'job operation id')
    return Path(project).resolve() / '.sdlc/jobs' / key


def request(project, key, plan):
    object_keys(plan, {'environment', 'dataset', 'start_argv', 'status_argv', 'lookup_argv', 'cwd', 'intent_quote'},
                {'environment', 'dataset', 'start_argv', 'status_argv', 'cwd', 'intent_quote'}, 'job plan')
    for field in ('environment', 'dataset', 'cwd', 'intent_quote'):
        require(isinstance(plan[field], str) and plan[field].strip(), 'job plan missing ' + field)
    require(Path(plan['cwd']).is_absolute() and Path(plan['cwd']).is_dir(), 'job cwd must exist and be absolute')
    for field in ('start_argv', 'status_argv', 'lookup_argv'):
        if field not in plan: continue
        require(isinstance(plan[field], list) and plan[field] and all(isinstance(x, str) for x in plan[field]), 'job adapter argv required')
    require(any('{operation_id}' in x for x in plan['start_argv']), 'start adapter must consume operation id for idempotency')
    require(any('{job_id}' in x for x in plan['status_argv']), 'status adapter must query exact job id')
    if plan.get('lookup_argv'):
        require(any('{operation_id}' in x for x in plan['lookup_argv']), 'lookup adapter must query exact operation id')
    home = _directory(project, key); out = home / 'request.json'
    with locked(home / 'job.lock'):
        if out.exists():
            value = load(out)
            require(value['plan'] == plan, 'operation id reused with a different job plan')
        else:
            value = {'schema_version': 1, 'kind': 'job-request', 'id': key, 'project_root': str(Path(project).resolve()),
                     'plan': plan, 'at': now()}
            write_json(out, value)
    return {'path': str(out), 'sha256': file_hash(out)}


def resolve(ref):
    object_keys(ref, {'path', 'sha256'}, {'path', 'sha256'}, 'job reference')
    require(file_hash(ref['path']) == ref['sha256'], 'job request modified')
    value = load(ref['path'])
    require(value['schema_version'] == 1 and value['kind'] == 'job-request', 'unsupported job protocol')
    require(Path(ref['path']).resolve() == _directory(value['project_root'], value['id']) / 'request.json', 'job request identity mismatch')
    return value


def state(ref):
    value = resolve(ref); home = _directory(value['project_root'], value['id'])
    pointer = home / 'latest.json'
    if not pointer.exists():
        return {'status': 'unknown' if (home / 'start-intent.json').exists() else 'not-started', 'job_id': None}
    index = load(pointer); observation = home / index['file']
    require(observation.parent == home and file_hash(observation) == index['sha256'], 'job observation modified')
    return {**load(observation), 'observation': str(observation), 'sha256': index['sha256']}


def _execute(ref, action, timeout=60):
    value = resolve(ref); plan = value['plan']; home = _directory(value['project_root'], value['id'])
    with locked(home / 'job.lock'):
        previous = state(ref)
        if action == 'start':
            if (home / 'start-intent.json').exists():
                return {**previous, 'reused': True}  # never submit again after ambiguous launch
            write_json(home / 'start-intent.json', {'request_sha256': ref['sha256'], 'at': now()})
        elif action == 'status':
            require(previous.get('job_id'), 'unknown launch outcome; lookup by operation id or explicitly adopt a verified job')
        else:
            require(action == 'lookup' and plan.get('lookup_argv'), 'no lookup adapter configured')
        argv = [s.replace('{operation_id}', value['id']).replace('{job_id}', previous.get('job_id') or '')
                for s in plan[action + '_argv']]
        started = now()
        try:
            run = subprocess.run(argv, cwd=plan['cwd'], capture_output=True, text=True, timeout=timeout)
            # Adapters must redact credentials/data in stdout/stderr before returning them.
            output = {'stdout': run.stdout, 'stderr': run.stderr, 'exit_code': run.returncode}
            require(run.returncode == 0, 'job adapter failed: ' + run.stderr[-1000:])
            result = loads(run.stdout)
            object_keys(result, {'job_id', 'status', 'result_refs', 'checkpoint'}, {'job_id', 'status', 'result_refs'}, 'adapter response')
            require(isinstance(result['job_id'], str) and result['job_id'], 'job id required')
            require(result['status'] in STATUSES and isinstance(result['result_refs'], list)
                    and all(isinstance(x, str) for x in result['result_refs']), 'invalid job status/results')
            require(not previous.get('job_id') or result['job_id'] == previous['job_id'], 'adapter returned a different job')
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            result = {'job_id': previous.get('job_id'), 'status': 'unknown', 'result_refs': [], 'error': str(error)}
            output = locals().get('output', {'stdout': '', 'stderr': str(error), 'exit_code': None})
        observation = {'schema_version': 1, 'request_sha256': ref['sha256'], 'action': action, 'started': started,
                       'finished': now(), 'execution': output, **result}
        path = home / ('observation-' + digest(observation) + '.json')
        write_json(path, observation)
        write_json(home / 'latest.json', {'file': path.name, 'sha256': file_hash(path)}, exclusive=False)
        return state(ref)


def start(ref, timeout=60): return _execute(ref, 'start', timeout)
def poll(ref, timeout=60): return _execute(ref, 'status', timeout)
def reconcile(ref, timeout=60): return _execute(ref, 'lookup', timeout)


def completed(ref):
    value = state(ref)
    require(value['status'] == 'succeeded', 'job not completed: ' + value['status'])
    require(value.get('result_refs'), 'completed job needs actual result references')
    return value
