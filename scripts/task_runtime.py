#!/usr/bin/env python3
"""Manager-side task protocol. Preparation and collection never execute project commands."""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo

from runtime_protocol import (CAPABILITIES, ProtocolError, changes, digest, enabled, encoded,
                              file_hash, file_record, load, loads, now, object_keys, parse_time, path_inside,
                              require, safe_id, snapshot, state_read, version, write_json)
from workflow import ROOT, artifact_paths, check_task, deliverable, load_registry, resolve_task, ticket_pattern

BINDING_KEYS = {'task_id', 'project_root', 'product_root', 'intent_quote', 'assignment', 'inputs',
                'deliverable_paths', 'source_writes', 'product_writes', 'memory_file', 'slice_integrator',
                'explore_roots', 'allowed_companion_skills', 'required_companion_skills', 'decisions',
                'required_checks', 'check_records', 'execution_mode', 'store_roots', 'supporting_inputs', 'visuals', 'imagery',
                'version_inputs', 'isolation', 'required_jobs'}
BINDING_REQUIRED = {'task_id', 'project_root', 'product_root', 'intent_quote', 'assignment', 'inputs', 'deliverable_paths'}
JUDGMENT_KEYS = {'methods_used', 'reported_reads', 'unresolved', 'proposed_changes', 'product_delta', 'lessons', 'check_records'}
DRAFT_KEYS = {'protocol_version', 'required_capabilities', 'kind', 'created_at', 'offline', 'request',
              'bindings', 'prepared', 'missing', 'draft_sha256'}
MANIFEST_KEYS = {'protocol_version', 'required_capabilities', 'kind', 'run_id', 'sealed_at', 'request',
                 'bindings', 'prepared', 'objects', 'paths', 'start_sha256'}
RESULT_KEYS = {'protocol_version', 'required_capabilities', 'kind', 'run_id', 'task_id', 'request',
               'manifest', 'manifest_sha256', 'finished_at', 'return_sha256', 'declared_inputs',
               'read_observations', 'outputs', 'checks', 'write_scope', 'judgments', 'errors',
               'execution_complete', 'applicability', 'objects'}
STATE_CONTEXT = ('lane', 'ui', 'tracking', 'q_security', 'intent', 'rework_rounds', 'delivery_goal', 'product_root', 'path')


def string_list(value, label):
    require(isinstance(value, list) and all(isinstance(x, str) and x for x in value), f'{label}: expected string list')
    require(len(set(value)) == len(value), f'{label}: duplicate entries')
    return value


def plugin_digest():
    files = {}
    for folder in ('scripts', 'workflow', 'agents', 'agent-sources', 'skills', 'adapters', 'commands'):
        for p in sorted((ROOT / folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
                files[p.relative_to(ROOT).as_posix()] = file_hash(p)
    return digest(files)


CLOSURE_LINK = re.compile(r'\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')
CLOSURE_SKILL = re.compile(r'(?:skills/|\.\./|sdlc-workflow:|\$)([a-z0-9][a-z0-9-]*)(/[A-Za-z0-9_./-]*[A-Za-z0-9_-])?')
CLOSURE_PATH = re.compile(r'\b((?:agents|adapters|commands|workflow|vendor)/[A-Za-z0-9_./-]*[A-Za-z0-9_-])')
CLOSURE_TEXT = {'.md', '.txt', '.yaml', '.yml', '.json', '.toml', '.html', '.css', '.js', '.sh', '.sql', '.csv', ''}


def method_closure(role, methods, reads=(), base=None):
    """Plugin files one task's executor can reach: its role file, skills (whole directories) and
    their transitive references, task reads, the registry and every script. A link that leaves the
    plugin is a coverage gap, so validity falls back to the whole-plugin digest."""
    base = Path(base or ROOT).resolve()
    names = {p.name for p in (base / 'skills').iterdir() if (p / 'SKILL.md').is_file()}
    skills = {methods['primary'], *methods.get('allowed', []), *(['debug'] if methods.get('debug') else [])}
    queue = [base / 'agents' / (role + '.md'), base / 'workflow/registry.json', base / 'scripts',
             *(base / 'skills' / n for n in skills), *(base / r for r in reads)]
    # Host-specific prompts/tool boundaries are part of this role's method too.
    # Packets carry a logical role rather than a host, so conservatively cover every
    # generated variant of that role; changes to another role do not invalidate it.
    hosts_path = base / 'adapters/hosts.json'
    if hosts_path.is_file():
        hosts = json.loads(hosts_path.read_text())
        for host, suffix in (('codex', '.toml'), ('kimi', '.md')):
            if host in hosts:
                queue.append(base / 'adapters' / host / 'agents' /
                             (hosts[host]['agent_prefix'] + role + suffix))
    seen, files, gaps, unresolved = set(), {}, set(), set()
    while queue:
        p = queue.pop()
        if p in seen: continue
        seen.add(p)
        if p.is_dir():
            queue += [c for c in sorted(p.rglob('*')) if c.is_file() and '__pycache__' not in c.parts and c.suffix != '.pyc']
            continue
        if not p.is_file():
            unresolved.add(p.relative_to(base).as_posix()); continue  # nothing there for an executor to read
        files[p.relative_to(base).as_posix()] = file_hash(p)
        # Registry names every skill and scripts are hashed whole; neither expands the method closure.
        if p.suffix not in CLOSURE_TEXT or p.is_relative_to(base / 'scripts') or p == base / 'workflow/registry.json': continue
        text = p.read_text(errors='replace')
        for name, sub in CLOSURE_SKILL.findall(text):
            if name not in names: continue
            # A named skill is loaded whole; a path inside it adds only that file.
            target = base / 'skills' / name / sub.lstrip('/')
            if not sub or sub == '/SKILL.md': queue.append(base / 'skills' / name)
            elif target.exists() or target.with_suffix('.md').exists(): queue.append(target if target.exists() else target.with_suffix('.md'))
        queue += [base / m for m in CLOSURE_PATH.findall(text) if (base / m).exists()]
        for raw in CLOSURE_LINK.findall(text):
            raw = raw.split('#', 1)[0].replace('<PLUGIN_ROOT>', str(base)).replace('PLUGIN_ROOT', str(base))
            if not raw or re.match(r'^[a-z][a-z0-9+.-]*:', raw): continue
            target = Path(raw) if raw.startswith('/') else (p.parent / raw).resolve()
            if target.is_relative_to(base): queue.append(target)
            else: gaps.add(p.relative_to(base).as_posix() + ' -> ' + raw)
    return {'sha256': digest(files), 'files': len(files), 'complete': not gaps,
            'gaps': sorted(gaps)[:20], 'unresolved_links': len(unresolved)}


def source_snapshot(project, feature, product):
    # This is a content identity, not a build ID or the write audit (which observes .sdlc too).
    snap = snapshot([project], exclude=[feature, product, project / '.sdlc'])
    require(not snap['gaps'], 'source snapshot coverage gaps: ' + '; '.join(snap['gaps']))
    git = subprocess.run(['git', '-C', str(project), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    return {'project_root': str(project), 'head': git.stdout.strip() if git.returncode == 0 else None,
            'content_sha256': digest(snap['files']), 'files': snap['files'],
            'excluded_paths': snap['excluded_paths'], 'excluded_directory_names': snap['excluded_directory_names']}


def file_input(path, access='read', allow_unfilled=False):
    p = Path(path)
    require(p.is_absolute() and p.is_file(), f'missing absolute input file: {p}')
    require(not p.is_symlink(), f'bind the real input file, not a symlink: {p}')
    require(p.stat().st_size > 0, f'empty input: {p}')
    require(allow_unfilled or deliverable(p), f'unfilled input: {p}')
    return {'path': str(p.resolve()), 'sha256': file_hash(p), 'access': access, 'size': p.stat().st_size}


def decision(path, target=None, scope=None):
    """A recorded authority assertion, not authentication of the named decision maker."""
    p = Path(path)
    d = load(p)
    object_keys(d, {'id','kind','target','target_sha256','scope','by','authority','quote','at','status','obligations',
                    'result_sha256','supersedes_sha256'},
                {'id','kind','target','target_sha256','scope','by','authority','quote','at','status','obligations'}, 'decision')
    safe_id(d['id']); require(d['kind'] in ('acceptance','verification','resolution','skip','successor','escalation'), 'unknown decision kind')
    for key in ('by','authority','quote','at','scope','target','target_sha256'):
        require(isinstance(d[key], str) and bool(d[key].strip()), f'decision missing {key}')
    require(d['status'] == 'accepted', 'decision is not accepted')
    require(isinstance(d['obligations'], list), 'decision obligations must be a list')
    parse_time(d['at'])
    target_path = Path(d['target']).resolve()
    require(target_path.is_file() and file_hash(target_path) == d['target_sha256'], 'decision target version changed')
    if target:
        require(target_path == Path(target).resolve(), 'decision target mismatch')
    if scope:
        require(Path(d['scope']).resolve() == Path(scope).resolve(), 'decision scope mismatch')
    return {'path': str(p.resolve()), 'sha256': file_hash(p), 'record': d, 'provenance': 'recorded-authority'}


def context(state, task_id):
    task = next((x for x in state.get('selected_tasks', []) if isinstance(x, dict) and x.get('id') == task_id), None)
    selection = {k:v for k,v in (task or {}).items() if k in ('id','role','stage','task','gate_stage','depends_on','selection','work_id','attempt_kind','rework_rounds','external_dependencies')}
    keys = STATE_CONTEXT
    result = {'selection': selection}
    if (task or {}).get('work_id'):
        from work_scope import work_context
        work = next((w for w in state.get('work_items', []) if w['id'] == task['work_id']), None)
        require(work is not None, 'unknown work_id')
        result['work'] = work_context(work, task_id)
        # A later request does not change the authority of an earlier task instance.
        keys = tuple(k for k in keys if k not in ('intent', 'delivery_goal', 'rework_rounds'))
    result['state'] = {k:state[k] for k in keys if k in state}
    return result


def needs_escalation(selected):
    return bool(selected.get('work_id')) and selected.get('attempt_kind', 'initial') == 'rework' and selected.get('rework_rounds', 0) >= 3


def needs_debug(state, selected):
    if selected.get('work_id'):
        return selected.get('attempt_kind', 'initial') == 'rework' and selected.get('rework_rounds', 0) >= 2
    return state.get('rework_rounds', 0) >= 2


def authority_packet(req, bindings, task, state, inputs, methods):
    root, project, product = map(str, (req['root'], bindings['project_root'], bindings['product_root']))
    paths = [x['path'] for x in inputs.values() if 'path' in x]
    paths += [str(ROOT / p) for p in task.get('reads', [])]
    command = ['python3', str(ROOT / 'scripts/workflow.py'), 'check-task', '--role', req['role'], '--stage', req['stage'],
               '--task', req['task'], '--root', root]
    p = {'hat':req['role'], 'stage':req['stage'], 'task':req['task'], 'subagent_type':'sdlc-workflow:' + req['role'],
         'PLUGIN_ROOT':str(ROOT), 'feature_dir':root, 'project_root':project, 'product_root':product,
         'run_scope':req['scope'], 'lane':state.get('lane'), 'primary_skill':'sdlc-workflow:' + task['skill'],
         'intent_quote':bindings['intent_quote'], 'assignment':bindings['assignment'],
         'inputs':list(dict.fromkeys(paths)), 'deliverable_paths':bindings['deliverable_paths'],
         'source_writes':bindings.get('source_writes', []), 'product_writes':bindings.get('product_writes', []),
         'memory_file':bindings.get('memory_file','none'), 'explore_roots':bindings.get('explore_roots',[]),
         'companion_skills':['sdlc-workflow:' + x for x in methods['allowed']],
         'allowed_companion_skills':methods['allowed'], 'required_companion_skills':methods['required'],
         'success_checks':[shlex.join(command)], 'return':'summary + fenced result JSON (protocol 1)',
         'forbidden':['Do not spawn further subagents (host depth 1).', 'Do not edit state, run records or version objects.']}
    p['evidence_required'] = [ev if isinstance(ev, str) else ev['kind'] for ev in task.get('evidence', [])
                              if isinstance(ev, str) or enabled(ev['when'], state)]
    for flag in ('ui', 'q_security'):
        if flag in state:
            p[flag] = 'yes' if enabled(flag, state) else 'no'
    registry = load_registry()
    for kind, metadata, reference in (('visuals', 'diagram', 'diagram_reference'), ('imagery', 'imagery', 'imagery_reference')):
        requested = bindings.get(kind, [])
        p[kind] = requested
        if requested and task.get(reference):
            rule = registry[metadata]
            p['inputs'] += [str(ROOT / rule['guide']), str(ROOT / task[reference])]
            if kind == 'visuals':
                for output in bindings['deliverable_paths']:
                    if str(output).endswith('.svg'):
                        p['success_checks'].append(shlex.join(['python3', str(ROOT / rule['lint']), '--root', root, str(Path(root) / output)]))
            else:
                p['success_checks'].append(shlex.join(['python3', str(ROOT / rule['check']), '--root', root]))
    p['inputs'] = list(dict.fromkeys(p['inputs']))
    if task.get('lane_file'):
        p['lane_file'] = task['lane_file']; p['slice_integrator'] = bindings.get('slice_integrator')
    if methods['debug']:
        p['debug_protocol'] = str(ROOT / 'skills/debug/SKILL.md')
    p['input_bindings'] = compact_inputs(inputs)
    return p


def compact_inputs(inputs):
    """The worker sees IDs/versions and search roots, not a huge audit inventory."""
    view={}
    for key,item in inputs.items():
        entry=dict(item)
        if 'source_snapshot' in entry:
            entry['source_snapshot']={k:v for k,v in entry['source_snapshot'].items() if k!='files'}
        view[key]=entry
    return view


def write_targets(req, bindings):
    root, project = Path(req['root']), Path(bindings['project_root'])
    targets=[{'declared':str(root/p),'path':str((root/p).resolve()),'recursive':False} for p in bindings['deliverable_paths']]
    targets += [{'declared':p,'path':str(Path(p).resolve()),'recursive':False} for p in bindings.get('product_writes',[])]
    targets += [{'declared':str(project/p),'path':str((project/p).resolve()),'recursive':p.endswith('/')} for p in bindings.get('source_writes',[])]
    if bindings.get('memory_file') not in (None,'','none','empty'):
        p=bindings['memory_file']; targets.append({'declared':p,'path':str(Path(p).resolve()),'recursive':False})
    return targets


def legacy_view(packet):
    # Only an internal adapter for existing authority checks, never a dispatchable v2 bypass.
    rows = ['## SPAWN PACKET v2']
    for key, value in packet.items():
        if key in ('allowed_companion_skills','required_companion_skills','input_bindings'):
            continue
        if isinstance(value, list):
            rows += [key + ':'] + ['  - ' + str(x) for x in value]
        elif value is not None:
            rows.append(f'{key}: {value}')
    return '\n'.join(rows) + '\n'


def prepare_value(req, bindings):
    object_keys(req, {'role','stage','task','scope','root'}, {'role','stage','task','scope','root'}, 'request')
    object_keys(bindings, BINDING_KEYS, BINDING_REQUIRED, 'bindings')
    safe_id(bindings['task_id'], 'task_id')
    safe_id(req['task'], 'concrete task'); safe_id(req['role'], 'role')
    require(all(isinstance(bindings[k],str) and Path(bindings[k]).is_absolute() for k in ('project_root','product_root')), 'project/product roots must be absolute')
    require(req['scope'] == 'feature', 'task protocol 1 currently supports feature only; product/cycle use their existing commands')
    r = load_registry(); task = resolve_task(r, req['role'], req['stage'], req['task'])
    require(task.get('protocol_required') == 1 or task.get('protocol_supported') == 1,
            'task has no protocol 1 input contract; use its explicit legacy v2 route')
    root = Path(req['root']).resolve(); project = Path(bindings['project_root']).resolve(); product = Path(bindings['product_root']).resolve()
    require(root.is_dir() and project.is_dir() and product.is_dir(), 'root/project_root/product_root must exist')
    require(root.is_relative_to(project) and root != project, 'feature root must be inside project_root')
    require(not product.is_relative_to(root) and not root.is_relative_to(product), 'product and feature roots must be separate')
    require(all(isinstance(bindings[k], str) and bindings[k].strip() for k in ('intent_quote','assignment')), 'intent_quote and assignment required')
    for key in ('deliverable_paths','source_writes','product_writes','explore_roots','decisions','check_records','store_roots','visuals','imagery'):
        string_list(bindings.get(key, []), key)
    require(isinstance(bindings.get('required_checks',[]),list), 'required_checks must be an array')
    for check in bindings.get('required_checks',[]):
        object_keys(check,{'id','scope','environment','build_required'},{'id','scope','environment','build_required'},'required check')
        require(all(isinstance(check[k],str) and check[k] for k in ('id','scope','environment')) and type(check['build_required']) is bool,
                'check ID/scope/environment must be strings and build_required boolean')
    require(bindings.get('execution_mode','serial') in ('serial','concurrent','group','isolated'), 'unknown execution_mode')
    require(isinstance(bindings['inputs'],dict), 'inputs must be an object keyed by contract ID')
    contract_ids = {x['id'] for x in task['inputs']}
    require(not set(bindings['inputs']) - contract_ids, 'unknown input bindings')
    version_inputs = bindings.get('version_inputs', {})
    require(isinstance(version_inputs, dict) and set(version_inputs) <= contract_ids, 'unknown version input bindings')
    require(not set(version_inputs) & set(bindings['inputs']), 'input has both live and version bindings')
    state = state_read(root / 'state.yaml')
    jobs = []
    if bindings.get('execution_mode') == 'isolated':
        from workspaces import validate_isolation
        require('isolated-execution-v1' in state.get('required_capabilities', []), 'isolated-execution-v1 required')
        require(bindings.get('isolation'), 'isolated execution requires workspace and active claim')
        validate_isolation(bindings['isolation'], req, bindings)
    else:
        require(not bindings.get('isolation'), 'isolation binding requires isolated execution mode')
    if version_inputs:
        require('artifact-versions-v1' in state.get('required_capabilities', []), 'artifact-versions-v1 required')
    if bindings.get('required_jobs'):
        from data_jobs import resolve as job_request
        require('data-jobs-v1' in state.get('required_capabilities', []), 'data-jobs-v1 required')
        require(isinstance(bindings['required_jobs'], list), 'required_jobs must be a list')
        for ref in bindings['required_jobs']:
            jobs.append({'reference': ref, 'request': job_request(ref)})
    require(state.get('task_protocol') == 1, 'explicit state task_protocol: 1 migration required')
    from task_state import validate_graph
    graph = validate_graph(state, r)
    selected = graph.get(bindings['task_id'])
    require(selected is not None and (selected['role'], selected['stage'], selected['task']) == (req['role'],req['stage'],req['task']), 'task_id not selected with matching registry key')
    require(selected['status'] in ('todo','doing','blocked'), 'prepare requires todo/doing/blocked task (new instance for repeated done task)')
    if selected.get('work_id'):
        work = next(w for w in state['work_items'] if w['id'] == selected['work_id'])
        require(work['status'] == 'active', 'work is not active; start a new work item for further changes')
    cfg = project / 'sdlc.config.yaml'
    require(cfg.is_file(), 'project sdlc.config.yaml required')
    from check_config import parse_yaml
    conf = parse_yaml(cfg.read_text())
    from check_config import check as check_config
    config_checks=check_config(str(project),probe=False)['findings']
    configured = Path(conf.get('product_root', 'docs/product'))
    require((project / configured).resolve() == product, 'product_root differs from project configuration')
    for key, meta in r.get('stores', {}).items():
        if conf.get(meta['config']):
            expected = str((project / str(conf[meta['config']])).resolve())
            require(expected in bindings.get('store_roots', []), f'configured store {key} must be observed: add store_roots {expected}')
    allowed = string_list(bindings.get('allowed_companion_skills', []), 'allowed_companion_skills')
    required = string_list(bindings.get('required_companion_skills', []), 'required_companion_skills')
    debug = needs_debug(state, selected)
    effective = set(task.get('companions', [])) | ({'debug'} if debug else set())
    require(set(allowed) <= effective, 'companion not allowed for this task/condition')
    require(set(required) <= set(allowed), 'required companions must be allowed')
    if debug:
        require('debug' in required, 'second rework requires debug in both allowed and required companions')
    methods = {'primary':task['skill'], 'allowed':allowed, 'required':required, 'debug':debug}
    inputs, missing, decisions = {}, [], []
    if any(x.get('build_required') is True for x in bindings.get('required_checks',[])):
        missing += ['CONFIG '+x['code']+': '+x['message'] for x in config_checks if x['level']=='blocker']
    for path in bindings.get('decisions', []):
        decisions.append(decision(path, scope=root))
    if needs_escalation(selected):
        # A third failure of the same criterion is not retried blindly: diagnosis plus an owner's route
        # (reslice, change approach, or stop) is recorded first. Open obligations are never waived here.
        if not any(d['record']['kind'] == 'escalation' and d['record']['by'].strip() != req['role'] for d in decisions):
            missing.append(f"REWORK: round {selected['rework_rounds']} of the same criterion needs an escalation decision "
                           "(kind escalation, by the owner, targeting the diagnosis and chosen route) before another attempt")
    for entry in task['inputs']:
        key = entry['id']
        try:
            if not enabled(entry['when'], state):
                inputs[key] = {'applicable':False, 'condition':entry['when'], 'source':'state'}; continue
            raw = bindings['inputs'].get(key)
            if key in version_inputs:
                from artifact_versions import input_value
                inputs[key] = input_value(version_inputs[key], entry)
                continue
            if entry['source'] == 'source_snapshot':
                inputs[key] = {'access':entry['access'], 'source_snapshot':source_snapshot(project,root,product)}; continue
            if entry['source'] == 'verification_records':
                from evidence import verify_bound_records
                expectations = bindings.get('required_checks', [])
                require(expectations, 'verification requires explicit required_checks')
                paths = string_list(bindings.get('check_records', []), 'check_records')
                records = verify_bound_records(root, paths, expectations, project, product)
                inputs[key] = {'access':'read', 'records':records}; continue
            if entry['source'] == 'product':
                raw = str(product / entry['ref'])
            elif entry['source'] == 'artifact':
                patterns = artifact_paths(r, [entry['ref']])
                matches = [p for pat in patterns for p in root.glob(pat) if p.is_file()]
                require(raw or len(matches) == 1, f'{key}: bind exactly one of {patterns}')
                raw = raw or str(matches[0])
                target = path_inside(raw, root, True)
                if not any(fnmatch.fnmatchcase(target.relative_to(root).as_posix(), pat) for pat in patterns):
                    alternatives=entry.get('alternatives',[])
                    allowed=any(a.get('rule')=='l2-short-spec' and state.get('lane')=='L2' and state.get('path')=='short'
                                and any(fnmatch.fnmatchcase(target.relative_to(root).as_posix(),pat) for pat in artifact_paths(r,[a['ref']]))
                                for a in alternatives)
                    require(allowed, f'{key}: wrong artifact path or unregistered alternative')
            require(isinstance(raw, str), f'{key}: bind an absolute file')
            item = file_input(raw, entry['access'], entry.get('allow_unfilled',False))
            if entry['access'] == 'read-write':
                require(item['path'] in bindings.get('product_writes', []), f'{key}: read-write input requires explicit owned product_writes')
            if entry.get('requires_acceptance'):
                accepted = [d for d in decisions if d['record']['kind']=='acceptance' and d['record']['target']==item['path'] and not d['record']['obligations']]
                require(accepted, f'{key}: accepted decision bound to this version required')
                item['acceptance'] = accepted
            inputs[key] = item
        except (OSError, ValueError, TypeError) as e:
            missing.append(f'{key}: {e}')
    packet = authority_packet(req, bindings, task, state, inputs, methods)
    if task.get('dataset_required'):
        try:
            from datasets import validate as validate_dataset
            require('dataset' in inputs and 'path' in inputs['dataset'], 'dataset input required')
            inputs['dataset']['dataset'] = validate_dataset(inputs['dataset']['path'])
        except (OSError, ValueError, KeyError, TypeError) as e:
            missing.append('dataset: ' + str(e))
    require(isinstance(bindings.get('supporting_inputs',[]),list),'supporting_inputs must be an array')
    for extra in bindings.get('supporting_inputs',[]):
        object_keys(extra,{'id','path'},{'id','path'},'supporting input'); safe_id(extra['id'])
        require(extra['id'] not in inputs,'duplicate supporting input ID')
        inputs[extra['id']]=file_input(extra['path'])
        packet['inputs'].append(inputs[extra['id']]['path'])
    packet['input_bindings']=compact_inputs(inputs)
    from check_packet import lint
    authority = lint(legacy_view(packet), enforce_protocol=False)
    missing += [f"{x['code']}: {x['message']}" for x in authority['errors']]
    # v2 permits broad artifact roots; protocol 1 reserves manager records and requires concrete file outputs.
    for raw in bindings['deliverable_paths']:
        p = (root / raw).resolve()
        require(not raw.endswith('/') and not any(c in raw for c in '*?['), 'protocol 1 deliverables must be concrete files')
        require(not p.is_relative_to(root / 'runs') and not p.is_relative_to(root / '.task-objects'), 'run/object paths are manager-only')
        require(not p.is_relative_to(root / 'work'), 'work completion paths are manager-only')
        require(not any(p.is_relative_to(root / d) for d in ('artifacts', 'imports', '.control')), 'coordinator paths are manager-only')
        require(p.name != 'state.yaml', 'state.yaml is manager-only')
    if req['stage']=='implement' and task.get('integration_required', True) and bindings.get('slice_integrator')==req['role']:
        integration=f"03-impl/{req['task']}-integration.md"
        require(str((root/integration).resolve()) in {str((root/p).resolve()) for p in bindings['deliverable_paths']},
                'slice integrator must declare '+integration)
    require(len([x for x in inputs.values() if 'path' in x]) <= 40, 'input file count exceeds 40')
    require(sum(x.get('size',0) for x in inputs.values()) <= 400000, 'text input budget exceeds 400000 bytes')
    return {'contract_sha256':digest(task), 'plugin_sha256':plugin_digest(),
            'method_closure':method_closure(req['role'], methods, task.get('reads', [])),
            'config':file_input(cfg), 'config_checks':config_checks,
            'context':context(state,bindings['task_id']), 'inputs':inputs, 'decisions':decisions,
            'methods':methods, 'packet':packet, 'write_targets':write_targets(req,bindings), 'jobs': jobs}, missing


def prepare(req, bindings, out, offline=False):
    prepared, missing = prepare_value(req, bindings)
    value = {'protocol_version':1, 'required_capabilities':sorted(CAPABILITIES), 'kind':'draft', 'created_at':now(),
             'offline':offline, 'request':req, 'bindings':bindings, 'prepared':prepared, 'missing':missing}
    value['draft_sha256'] = digest(value)
    write_json(out, value)
    return value


def freeze_files(root, files):
    """Retain content objects for reproducible old inputs/outputs; hashes alone are insufficient."""
    records = {}
    total = sum(Path(p).stat().st_size for p in files if Path(p).is_file())
    require(total <= 256 * 1024 * 1024, 'version object budget exceeds 256 MiB; narrow project fixture/scope explicitly')
    for raw in sorted(set(files)):
        p = Path(raw)
        if p.is_symlink() or not p.is_file():
            continue
        sha = file_hash(p); out = root / '.task-objects' / sha
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            require(file_hash(out) == sha, 'corrupt version object')
        else:
            with out.open('xb') as stream:
                stream.write(p.read_bytes())
            require(file_hash(out) == sha, 'input changed while copying version object')
        records[str(p)] = {'sha256':sha, 'object':str(out)}
    return records


def input_files(prepared):
    paths = [prepared['config']['path']]
    for value in prepared['inputs'].values():
        if 'path' in value:
            paths.append(value['path'])
        if 'artifact_version' in value:
            paths.append(value['artifact_version']['path'])
            paths.extend(d['path'] for d in value.get('acceptance', []))
        if 'dataset' in value:
            identity = value['dataset']['identity']
            if identity['type'] == 'file': paths.append(identity['path'])
            else: paths.extend(x['path'] for x in identity['evidence'])
        if 'source_snapshot' in value:
            paths.extend(value['source_snapshot']['files'])
        for rec in value.get('records', []):
            paths += [rec['path'], rec['log_path']]
    paths += [d['path'] for d in prepared['decisions']]
    paths += [j['reference']['path'] for j in prepared.get('jobs', [])]
    paths += prepared['packet']['inputs']
    for method in [prepared['methods']['primary'], *prepared['methods']['allowed']]:
        paths += [str(p) for p in (ROOT/'skills'/method).rglob('*') if p.is_file()]
    return paths


def packet_view(path, manifest):
    envelope = {'manifest':str(Path(path).resolve()), 'manifest_sha256':digest(manifest),
                'assignment':manifest['prepared']['packet']}
    return '## SPAWN PACKET v3\n\n```json\n' + encoded(envelope).decode() + '```\n'


def seal(draft_path):
    draft = load(draft_path); version(draft); object_keys(draft,DRAFT_KEYS,DRAFT_KEYS,'draft')
    require(draft['kind']=='draft' and not draft['offline'], 'offline/non-draft cannot be sealed')
    require(draft['draft_sha256']==digest({k:v for k,v in draft.items() if k!='draft_sha256'}), 'draft modified; run prepare again')
    require(not draft['missing'], 'draft has missing prerequisites: ' + '; '.join(draft['missing']))
    prepared, missing = prepare_value(draft['request'], draft['bindings'])
    require(not missing and prepared == draft['prepared'], 'inputs, configuration, authority or methods changed; prepare again')
    from task_state import check_tasks
    readiness = check_tasks(draft['request']['root'], task_id=draft['bindings']['task_id'])
    require(not readiness['errors'], 'task dependencies not ready: ' + '; '.join(readiness['errors']))
    root = Path(draft['request']['root']).resolve()
    task_id = draft['bindings']['task_id']
    for earlier in sorted((root / 'runs').glob('*/*-manifest.json')):
        m = load(earlier)
        if m.get('bindings', {}).get('task_id') == task_id and not Path(m['paths']['result']).exists():
            # A returned but unrecorded run must not be dispatched twice (diagnosis 2026-10-02: repeat after compaction).
            raise ProtocolError(f"task {task_id} has an unrecorded run {m['run_id']}: record its saved return "
                                "(workflow.py record) or mark it interrupted (record --interrupted REASON) before sealing again")
    run_id = dt.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d-%H%M%S%z') + '-' + draft['request']['role'] + '-' + draft['request']['task'] + '-' + uuid.uuid4().hex[:8]
    home = root / 'runs' / run_id
    home.mkdir(parents=True, exist_ok=False)
    paths = {key:str(home / f'{run_id}-{key}.{ext}') for key,ext in [('manifest','json'),('packet','md'),('start','json'),('return','txt'),('result','json')]}
    objects = freeze_files(root, input_files(prepared))
    # Recheck after copying: never seal an already-stale source/object pair.
    current, missing = prepare_value(draft['request'], draft['bindings'])
    require(current == prepared and not missing, 'inputs changed during sealing; prepare again (incomplete run retained)')
    b = draft['bindings']
    before = snapshot([b['project_root'],root,b['product_root'],*b.get('store_roots',[])], exclude=paths.values())
    start = {'protocol_version':1, 'required_capabilities':sorted(CAPABILITIES), 'run_id':run_id, 'at':now(),
             'snapshot':before, 'execution_mode':b.get('execution_mode','serial'), 'host':'unknown'}
    write_json(paths['start'],start)
    manifest = {'protocol_version':1, 'required_capabilities':sorted(CAPABILITIES), 'kind':'manifest', 'run_id':run_id,
                'sealed_at':now(), 'request':draft['request'], 'bindings':b, 'prepared':prepared, 'objects':objects,
                'paths':paths, 'start_sha256':file_hash(paths['start'])}
    write_json(paths['manifest'],manifest)
    Path(paths['packet']).write_text(packet_view(paths['manifest'],manifest))
    return paths


def load_manifest(path):
    m = load(path); version(m); object_keys(m,MANIFEST_KEYS,MANIFEST_KEYS,'manifest')
    require(m['kind']=='manifest', 'not a manifest')
    require(Path(m['paths']['manifest']).resolve()==Path(path).resolve(), 'manifest path mismatch')
    require(file_hash(m['paths']['start'])==m['start_sha256'], 'start record modified')
    require(Path(m['paths']['packet']).read_text()==packet_view(path,m), 'sealed packet/manifest disagreement')
    for raw, obj in m['objects'].items():
        require(file_hash(obj['object'])==obj['sha256'], f'version object modified: {raw}')
    return m


def lint_packet_v3(text):
    try:
        match = re.fullmatch(r'## SPAWN PACKET v3\n\n```json\n(.*)```\n?',text,re.S)
        require(match is not None, 'v3 packet must be the generated JSON view')
        e = loads(match[1]); object_keys(e,{'manifest','manifest_sha256','assignment'},{'manifest','manifest_sha256','assignment'},'packet')
        m = load_manifest(e['manifest'])
        require(file_hash(e['manifest'])==e['manifest_sha256'], 'manifest digest mismatch')
        require(text.rstrip()==packet_view(e['manifest'],m).rstrip(), 'packet differs from sealed manifest')
        require(not Path(m['paths']['result']).exists(), 'run already recorded; prepare a new run')
        prepared, missing = prepare_value(m['request'],m['bindings'])
        require(not missing and prepared==m['prepared'], 'sealed prerequisites changed before dispatch; prepare again')
        return {'errors':[], 'warnings':[], 'packet':{'hat':m['request']['role'],'stage':m['request']['stage']}}
    except (OSError,ValueError,TypeError,KeyError) as e:
        return {'errors':[{'code':'PROTOCOL','message':str(e)}], 'warnings':[], 'packet':{}}


def read_return(path, manifest):
    raw = Path(path).read_text()
    matches = re.findall(r'```result\s*\n(.*?)\n```',raw,re.S)
    require(len(matches)==1, 'return needs exactly one fenced result JSON block')
    value = loads(matches[0]); object_keys(value,JUDGMENT_KEYS,JUDGMENT_KEYS,'model result')
    for k in JUDGMENT_KEYS:
        require(isinstance(value[k],list), f'{k}: expected array; missing is not equivalent to empty')
    allowed = {manifest['prepared']['methods']['primary'], *manifest['prepared']['methods']['allowed']}
    used = set()
    for item in value['methods_used']:
        object_keys(item,{'skill','reason','provenance'},{'skill','reason','provenance'},'method')
        require(item['skill'] in allowed and item['provenance']=='reported' and bool(item['reason']), 'method must be allowed, reasoned and reported')
        used.add(item['skill'])
    require({manifest['prepared']['methods']['primary'], *manifest['prepared']['methods']['required']} <= used, 'required method missing from reported use')
    require(all(isinstance(x,str) and x in manifest['prepared']['inputs'] for x in value['reported_reads']), 'unknown reported input ID')
    for item in value['unresolved']:
        object_keys(item,{'id','owner','blocks','item','severity'}, {'id','owner','blocks','item','severity'},'unresolved')
        safe_id(item['id']); require(item['severity'] in ('blocker','major','minor'), 'unknown severity')
        require(bool(item['owner']) and bool(item['item']), 'unresolved owner and item required')
        string_list(item['blocks'],'unresolved.blocks')
        graph=state_read(Path(manifest['request']['root'])/'state.yaml')['selected_tasks']
        require(item['owner'] in load_registry()['roles'], 'unknown unresolved owner')
        require(set(item['blocks']) <= {t['id'] for t in graph}, 'unresolved references an unselected task')
    known = set(manifest['prepared']['inputs']) | set(manifest['bindings']['deliverable_paths'])
    for item in value['proposed_changes']:
        object_keys(item,{'target','change','evidence_refs'},{'target','change','evidence_refs'},'proposed change')
        require(item['target'] and item['change'], 'empty proposed change')
        require(set(string_list(item['evidence_refs'],'evidence_refs')) <= known, 'unbound evidence reference')
    string_list(value['check_records'],'check_records')
    for key in ('product_delta','lessons'):
        require(all(isinstance(x,str) and x.strip() for x in value[key]), f'{key}: nonempty text rows required')
    return value


def authorized(path, manifest):
    target = Path(path).resolve()
    for entry in manifest['prepared']['write_targets']:
        candidate=Path(entry['path'])
        if target == candidate or (entry['recursive'] and target.is_relative_to(candidate)):
            return True
    return False


def record(manifest_path, return_path=None, interrupted=None, concurrent=False):
    m = load_manifest(manifest_path); root=Path(m['request']['root'])
    require(not Path(m['paths']['result']).exists(), 'immutable result already exists; use a new run')
    start=load(m['paths']['start']); version(start)
    after=snapshot(start['snapshot']['roots'], exclude=start['snapshot']['excluded_paths'])
    changed=changes(start['snapshot'],after)
    errors=[]; judgments=None
    if interrupted:
        errors.append('interrupted: ' + interrupted)
        raw='Interrupted: ' + interrupted + '\n'
    else:
        require(return_path is not None, '--return or --interrupted required')
        raw=Path(return_path).read_text()
        try:
            judgments=read_return(return_path,m)
        except (OSError,ValueError,TypeError,KeyError) as e:
            errors.append('invalid return: ' + str(e))
    if plugin_digest()!=m['prepared']['plugin_sha256']:
        errors.append('plugin changed during run; result requires revalidation')
    if write_targets(m['request'],m['bindings'])!=m['prepared']['write_targets']:
        errors.append('authorized path targets changed during execution (including symlink replacement)')
    state=state_read(root/'state.yaml')
    if context(state,m['bindings']['task_id']) != m['prepared']['context']:
        errors.append('task authority/conditions changed during run')
    if file_hash(m['prepared']['config']['path'])!=m['prepared']['config']['sha256']:
        errors.append('project configuration changed during run')
    outside=[p for p in changed if not authorized(p,m)]
    # Resolve again and reuse existing owner checks: symlink changes cannot create new authority.
    from check_packet import lint
    auth=lint(legacy_view(m['prepared']['packet']),enforce_protocol=False)
    errors += ['authority: '+x['message'] for x in auth['errors']]
    if after['gaps'] or start['snapshot']['gaps']:
        errors.append('write observation coverage gaps')
    mode='concurrent' if concurrent else start['execution_mode']
    isolated = mode == 'isolated' and not concurrent
    if isolated:
        try:
            from workspaces import validate_isolation
            validate_isolation(m['bindings']['isolation'], m['request'], m['bindings'])
        except (OSError, ValueError, KeyError, TypeError) as e:
            errors.append('isolated attribution: ' + str(e))
    elif mode!='serial':
        errors.append('write attribution uncertain; independent revalidation required')
    for key,item in m['prepared']['inputs'].items():
        if item.get('access')!='read':
            continue
        try:
            if 'path' in item:
                require(file_hash(item['path'])==item['sha256'], f'read input changed: {key}')
            if 'artifact_version' in item:
                from artifact_versions import resolve
                resolve(item['artifact_version'])
                for d in item.get('acceptance', []):
                    require(file_hash(d['path']) == d['sha256'], 'artifact acceptance changed')
            if 'dataset' in item:
                from datasets import validate as validate_dataset
                require(validate_dataset(item['path']) == item['dataset'], 'dataset changed during run')
            if 'source_snapshot' in item:
                current=source_snapshot(Path(m['bindings']['project_root']),root,Path(m['bindings']['product_root']))
                require(current==item['source_snapshot'], f'read source snapshot changed: {key}')
        except (OSError,ValueError) as e:
            errors.append(str(e))
    outputs={}
    expected=[str((root/p).resolve()) for p in m['bindings']['deliverable_paths']]
    expected+=m['bindings'].get('product_writes',[])
    for p in sorted(set(expected+ [p for p in changed if authorized(p,m)])):
        if Path(p).is_file():
            outputs[p]=file_record(p)
        elif p in expected:
            errors.append('missing output: '+p)
        else:
            outputs[p]={'type':'deleted'}
    checks=[{'id':'check-task','level':'presence','findings':check_task(load_registry(),root,m['request']['role'],m['request']['stage'],m['request']['task'])}]
    if any(row[0]=='error' for row in checks[0]['findings']):
        errors.append('registered task presence check failed')
    expectations=m['bindings'].get('required_checks',[])
    contract = resolve_task(load_registry(), m['request']['role'], m['request']['stage'], m['request']['task'])
    if (m['request']['role']=='backend' or contract.get('execution_required') or m['bindings'].get('source_writes')) and not expectations:
        errors.append('task completion requires bound project checks; no required_checks declared')
    if expectations:
        try:
            from evidence import verify_bound_records
            records=verify_bound_records(root, (judgments or {}).get('check_records',[]), expectations,
                                         Path(m['bindings']['project_root']),Path(m['bindings']['product_root']))
            checks.append({'id':'project-checks','level':'execution-record','records':records})
            evidence_paths={p for r in records for p in (r['path'],r['log_path'])}
            outside=[p for p in outside if p not in evidence_paths]
        except (OSError,ValueError,KeyError,TypeError) as e:
            errors.append('project checks: '+str(e))
    if outside:
        errors.append('observed changes outside task authority')
    for ref in m['bindings'].get('required_jobs', []):
        try:
            from data_jobs import completed
            checks.append({'id': 'external-job', 'level': 'adapter-observation', 'record': completed(ref)})
        except (OSError, ValueError, KeyError, TypeError) as e:
            errors.append('external job: ' + str(e))
    # Freeze only after the audit, so manager object writes are not attributed to the producer.
    objects=freeze_files(root,[p for p in outputs if Path(p).is_file()])
    result={'protocol_version':1,'required_capabilities':sorted(CAPABILITIES),'kind':'result','run_id':m['run_id'],
            'task_id':m['bindings']['task_id'],'request':m['request'],'manifest':str(Path(manifest_path).resolve()),
            'manifest_sha256':file_hash(manifest_path),'finished_at':now(),'return_sha256':__import__('hashlib').sha256(raw.encode()).hexdigest(),
            'declared_inputs':m['prepared']['inputs'],'read_observations':{'reported':(judgments or {}).get('reported_reads',[]),'host':None,'level':'unobservable'},
            'outputs':outputs,'checks':checks,'write_scope':{'level':'task_observed' if mode=='serial' or isolated else 'group_observed',
            'changed':changed,'outside_authority':outside,'before_sha256':digest(start['snapshot']),'after':after,
            'attribution':'registered worktree and resource claim' if isolated else 'isolated window declared by manager' if mode=='serial' else 'uncertain'},
            'judgments':judgments,'errors':errors,'execution_complete':not errors,'objects':objects,
            'applicability':{'stage_accepted':False,'historical_execution':'complete' if not errors else 'incomplete',
                             'post_source':source_snapshot(Path(m['bindings']['project_root']),root,Path(m['bindings']['product_root']))
                             if any('source_snapshot' in x for x in m['prepared']['inputs'].values()) else None,
                             'reuse':'recompute with check-tasks'}}
    if Path(m['paths']['return']).exists():
        require(Path(m['paths']['return']).read_text()==raw, 'saved return differs')
    else:
        with Path(m['paths']['return']).open('x') as stream: stream.write(raw)
    write_json(m['paths']['result'],result)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare')
    for k in ('role','stage','task','scope','root','bindings','out'): p.add_argument('--'+k,required=True)
    p.add_argument('--offline',action='store_true')
    p=sub.add_parser('seal'); p.add_argument('--draft',required=True)
    p=sub.add_parser('record'); p.add_argument('--run',required=True); p.add_argument('--return',dest='return_path')
    p.add_argument('--interrupted'); p.add_argument('--concurrent',action='store_true')
    for cmd in ('check-tasks','migrate-tasks'):
        p=sub.add_parser(cmd); p.add_argument('--root',required=True); p.add_argument('--scope',default='feature')
        p.add_argument('--stage'); p.add_argument('--task-id'); p.add_argument('--closure',action='store_true')
    p=sub.add_parser('eval-prepare'); p.add_argument('--spec',required=True); p.add_argument('--out',required=True)
    for cmd in ('eval-audit','eval-blind'):
        p=sub.add_parser(cmd); p.add_argument('--run',required=True); p.add_argument('--observations',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='prepare':
            req={k:getattr(args,k) for k in ('role','stage','task','scope','root')}; req['root']=str(Path(req['root']).resolve())
            result=prepare(req,load(args.bindings),args.out,args.offline)
            print(json.dumps({'draft':args.out,'missing':result['missing'],'offline':args.offline},ensure_ascii=False,indent=2)); return int(bool(result['missing']))
        if args.command=='seal': result=seal(args.draft)
        elif args.command=='record': result=record(args.run,args.return_path,args.interrupted,args.concurrent)
        elif args.command=='eval-prepare':
            from eval_protocol import prepare_eval
            result=prepare_eval(load(args.spec),args.out)
        elif args.command=='eval-audit':
            from eval_protocol import validate_observations
            result=validate_observations(load(args.run),load(args.observations))
        elif args.command=='eval-blind':
            from eval_protocol import prepare_blind
            result=prepare_blind(args.run,args.observations)
        else:
            from task_state import check_tasks, migration_report
            require(args.scope=='feature','task state protocol currently supports feature only')
            result=migration_report(args.root) if args.command=='migrate-tasks' else check_tasks(args.root,args.stage,args.closure,args.task_id)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return int(bool(result.get('errors',[])))
    except (OSError,ValueError,KeyError,TypeError) as e:
        print('workflow protocol: '+str(e),file=sys.stderr); return 2


if __name__=='__main__': sys.exit(main())
