#!/usr/bin/env python3
"""Read-only task DAG/closure checks. Never edits a historical result or advances state."""
from __future__ import annotations

from pathlib import Path
import re
from runtime_protocol import (ProtocolError, digest, file_hash, load, object_keys, path_inside,
                              require, safe_id, state_read, version)
from workflow import load_registry, resolve_task

TASK_KEYS = {'id','role','stage','task','gate_stage','depends_on','status','result','result_sha256',
             'selection','reason','decision','successor','acceptance','verification','successor_versions'}
TASK_REQUIRED = {'id','role','stage','task','gate_stage','depends_on','status','selection'}
STATUSES = {'todo','doing','done','blocked','skipped','superseded'}


def validate_graph(state, registry=None):
    r=registry or load_registry()
    require(state.get('task_protocol')==1, 'legacy/unverified: explicit migration to task_protocol: 1 required')
    tasks=state.get('selected_tasks')
    require(isinstance(tasks,list) and bool(tasks), 'strict selected_tasks must be a nonempty list of block mappings')
    graph={}
    for task in tasks:
        object_keys(task,TASK_KEYS,TASK_REQUIRED,'selected task')
        safe_id(task['id'],'task id'); require(task['id'] not in graph,'duplicate task id: '+task['id'])
        contract=resolve_task(r,task['role'],task['stage'],task['task'])
        require(task['gate_stage'] in contract.get('gate_stages',[task['stage']]), 'invalid gate_stage for '+task['id'])
        require(task['status'] in STATUSES,'invalid task status')
        object_keys(task['selection'],{'required','reason','source'},{'required','reason','source'},'selection')
        require(type(task['selection']['required']) is bool and bool(task['selection']['reason']) and bool(task['selection']['source']), 'selection requires boolean required and reason/source')
        require(isinstance(task['depends_on'],list),'depends_on must be a list')
        seen=set()
        for edge in task['depends_on']:
            object_keys(edge,{'task','requires'},{'task','requires'},'dependency')
            require(edge['requires'] in ('produced','accepted','verified'),'unknown dependency level')
            require(edge['task'] not in seen,'duplicate dependency'); seen.add(edge['task'])
        if task['status']=='done':
            require(task.get('result') and task.get('result_sha256'),'done needs result path and digest')
        if task['status']=='skipped':
            require(not task['selection']['required'],'cannot skip a required selected task')
            require(contract.get('skip_policy')!='never','registry does not allow skipping this selected task')
            require(task.get('reason') and task.get('decision'),'skip requires reason and decision record')
        if task['status']=='superseded': require(task.get('successor'),'superseded requires successor instance')
        graph[task['id']]=task
    visiting, done=set(),set()
    def visit(key):
        require(key in graph,'dangling task dependency: '+str(key))
        require(key not in visiting,'task dependency/successor cycle: '+key)
        if key in done: return
        visiting.add(key)
        task=graph[key]
        for edge in task['depends_on']: visit(edge['task'])
        if task.get('successor'): visit(task['successor'])
        visiting.remove(key); done.add(key)
    for key in graph: visit(key)
    for task in graph.values():
        contract=resolve_task(r,task['role'],task['stage'],task['task'])
        accepted={i.get('ref') for i in contract.get('inputs',[]) if i.get('requires_acceptance')}
        for edge in task['depends_on']:
            dep=graph[edge['task']]; dc=resolve_task(r,dep['role'],dep['stage'],dep['task'])
            if accepted & set(dc.get('required',[])):
                require(edge['requires']=='accepted','accepted artifact dependency cannot downgrade to '+edge['requires'])
    obligations=state.get('obligations',[])
    require(isinstance(obligations,list),'obligations must be block mapping list')
    ids=set()
    for o in obligations:
        object_keys(o,{'id','raised_by','owner','blocks','gate_stage','status','resolution'},
                    {'id','raised_by','owner','blocks','gate_stage','status'},'obligation')
        safe_id(o['id']); require(o['id'] not in ids,'duplicate obligation'); ids.add(o['id'])
        require(o['raised_by'] in graph and o['owner'] in r['roles'],'unknown obligation source/owner')
        require(isinstance(o['blocks'],list) and all(x in graph for x in o['blocks']),'unknown blocked task')
        require(o['gate_stage'] in r['stages'],'unknown obligation gate_stage')
        require(o['status'] in ('open','resolved'),'invalid obligation status')
        if o['status']=='resolved': require(o.get('resolution'),'resolved obligation needs resolution evidence')
    return graph


def result_for(root, task):
    from task_runtime import RESULT_KEYS, load_manifest
    p=path_inside(task['result'],root,True)
    require(file_hash(p)==task['result_sha256'], 'result digest mismatch: '+task['id'])
    result=load(p); version(result); object_keys(result,RESULT_KEYS,RESULT_KEYS,'result')
    require(result['kind']=='result' and result['task_id']==task['id'],'result instance mismatch')
    req=result['request']
    require((req['role'],req['stage'],req['task'])==(task['role'],task['stage'],task['task']),'result task key mismatch')
    require(req['scope']=='feature' and Path(req['root']).resolve()==root.resolve(),'result scope/project mismatch')
    m=load_manifest(result['manifest'])
    require(file_hash(result['manifest'])==result['manifest_sha256'],'result manifest modified')
    require(m['run_id']==result['run_id'] and m['bindings']['task_id']==task['id'],'result run mismatch')
    require(file_hash(m['paths']['return'])==result['return_sha256'],'saved return modified')
    require(result['execution_complete'] is True and not result['errors'],'task execution incomplete: '+task['id'])
    # Do not silently choose an old pass over a newer failed/interrupted attempt.
    for other in (root/'runs').glob('*/*-manifest.json'):
        newer=load(other)
        if newer.get('bindings',{}).get('task_id')==task['id'] and newer.get('sealed_at','')>m['sealed_at']:
            raise ProtocolError('newer attempt exists for '+task['id']+'; reconcile state before reuse')
    return result,m


def current_validity(root, task, result, manifest):
    """Historical execution stays complete; reuse checks current read inputs and post-write outputs."""
    from task_runtime import source_snapshot, plugin_digest, decision, context
    reasons=[]
    if plugin_digest()!=manifest['prepared']['plugin_sha256']:
        reasons.append('plugin contract/method version changed')
    cfg=manifest['prepared']['config']
    if not Path(cfg['path']).is_file() or file_hash(cfg['path'])!=cfg['sha256']:
        reasons.append('project configuration changed')
    checks={item['path']:item['sha256'] for item in result['declared_inputs'].values() if 'path' in item and item['access']=='read'}
    checks.update({d['path']:d['sha256'] for d in manifest['prepared']['decisions']})
    current_context=context(state_read(root/'state.yaml'),task['id'])
    recorded_context=manifest['prepared']['context']
    if current_context['selection']!=recorded_context['selection'] or any(
            current_context['state'].get(k)!=v for k,v in recorded_context['state'].items() if k!='rework_rounds'):
        reasons.append('applicable task conditions/selection changed')
    checks.update({p:v.get('sha256') for p,v in result['outputs'].items() if v['type']=='file'})
    for p,v in result['outputs'].items():
        if v['type']=='deleted' and Path(p).exists(): reasons.append('deleted output reappeared: '+p)
    for path,sha in checks.items():
        if Path(path).is_file() and file_hash(path)==sha: continue
        valid_successor=False
        for ref in task.get('successor_versions',[]):
            d=decision(root/ref,scope=root)['record']
            if d['kind']=='successor' and d.get('supersedes_sha256')==sha and d['target']==path and d.get('result_sha256'):
                # A successor must link to another complete result, not only an authority sentence.
                for candidate in (root/'runs').glob('*/*-result.json'):
                    if file_hash(candidate)==d['result_sha256']:
                        newer=load(candidate)
                        if newer.get('execution_complete') and newer.get('outputs',{}).get(path,{}).get('sha256')==d['target_sha256']:
                            valid_successor=True
        if not valid_successor: reasons.append('version changed/missing: '+path)
    if result['applicability'].get('post_source'):
        b=manifest['bindings']
        if source_snapshot(Path(b['project_root']),root,Path(b['product_root'])) != result['applicability']['post_source']:
            reasons.append('source snapshot changed since completion')
    if manifest['bindings'].get('required_checks'):
        try:
            from evidence import verify_bound_records
            verify_bound_records(root,result['judgments']['check_records'],manifest['bindings']['required_checks'],
                                 Path(manifest['bindings']['project_root']),Path(manifest['bindings']['product_root']))
        except (OSError,ValueError,KeyError,TypeError) as e: reasons.append(str(e))
    return ('needs-revalidation' if reasons else 'current'),reasons


def check_tasks(root, stage=None, closure=False, task_id=None):
    root=Path(root).resolve(); errors=[]; details={}
    raw=(root/'state.yaml').read_text()
    has_runs=any((root/'runs').glob('*/*-manifest.json'))
    # Legacy syntax/errors remain owned by legacy gates (avoid counting the same error twice).
    if not re.search(r'^\s*(task_protocol|required_capabilities):',raw,re.M) and not has_runs:
        return {'mode':'legacy','validity':'unverified','errors':[], 'note':'legacy aggregate gates remain; migrate explicitly before protocol dispatch'}
    state=state_read(root/'state.yaml')
    if 'task_protocol' not in state:
        require(not has_runs, 'protocol downgrade: runs exist but task_protocol was removed')
        return {'mode':'legacy','validity':'unverified','errors':[], 'note':'legacy aggregate gates remain; migrate explicitly before protocol dispatch'}
    r=load_registry(); graph=validate_graph(state,r)
    require(stage is None or stage in r['stages'],'unknown stage')
    require(task_id is None or task_id in graph,'unknown task_id')
    results={}
    for key,task in graph.items():
        info={'status':task['status'],'validity':'unverified','historical_execution':'unknown','reasons':[]}
        try:
            if task['status']=='done':
                result,m=result_for(root,task); results[key]=(result,m)
                info['historical_execution']='complete'
                info['validity'],info['reasons']=current_validity(root,task,result,m)
            elif task['status']=='skipped':
                from task_runtime import decision
                d=decision(root/task['decision'],scope=root)['record']
                require(d['kind']=='skip','skip needs a skip decision')
            elif task['status']=='superseded':
                require(graph[task['successor']]['status']=='done','successor not complete')
        except (OSError,ValueError,TypeError,KeyError) as e:
            info['validity']='invalid'; info['reasons'].append(str(e)); errors.append(f'{key}: {e}')
        details[key]=info
    wanted={key for key,t in graph.items() if (task_id==key if task_id else (t['gate_stage']==stage if stage else closure))}
    # Dependency failures are actionable for the selected dispatch / closing stage, not future todo tasks.
    for key in wanted:
        task=graph[key]
        for edge in task['depends_on']:
            dep=graph[edge['task']]; info=details[edge['task']]
            if dep['status']!='done' or info['validity']!='current':
                errors.append(f"{key}: dependency {dep['id']} is not currently reusable"); continue
            if edge['requires']!='produced':
                from task_runtime import decision
                field='acceptance' if edge['requires']=='accepted' else 'verification'
                try:
                    require(dep.get(field), f"{dep['id']} lacks {field}")
                    d=decision(root/dep[field],scope=root)['record']
                    require(d['kind']==field and d.get('result_sha256')==dep['result_sha256'], 'dependency decision must bind result version')
                    require(not d['obligations'],'dependency decision has unresolved obligations')
                except (OSError,ValueError,TypeError,KeyError) as e: errors.append(f'{key}: {e}')
        if closure and (task['status'] not in ('done','skipped','superseded') or
                        (task['status']=='done' and details[key]['validity']!='current')):
            errors.append(f'{key}: closing task is unfinished or needs revalidation')
    obligations={o['id']:o for o in state.get('obligations',[])}
    # Immutable producer blockers must be resolved by separate evidence; deleting the state row cannot hide them.
    for key,(result,m) in results.items():
        for issue in (result['judgments'] or {}).get('unresolved',[]):
            if issue['severity'] not in ('blocker','major'): continue
            o=obligations.get(issue['id'])
            targets=set(issue['blocks']) or {key}
            due=bool(targets & wanted) or (closure and (stage is None or graph[key]['gate_stage']==stage))
            if not due: continue
            try:
                require(o is not None and o['raised_by']==key and o['status']=='resolved', 'unresolved obligation '+issue['id'])
                require(set(o['blocks']) >= targets,'obligation cannot narrow immutable blocked targets')
                from task_runtime import decision
                d=decision(root/o['resolution'],scope=root)['record']
                require(d['kind']=='resolution' and d.get('result_sha256')==graph[key]['result_sha256'], 'resolution must bind source result digest')
                require(not d['obligations'],'resolution carries unresolved obligations')
            except (OSError,ValueError,KeyError,TypeError) as e: errors.append(str(e))
    for o in obligations.values():
        if o['status']=='open' and (set(o['blocks']) & wanted or (closure and (stage is None or o['gate_stage']==stage))):
            errors.append('open obligation '+o['id'])
    if closure:
        # The selected set cannot erase issued tasks or replace the mandatory definition producer.
        if stage in (None,'define'):
            if not any(t['role']=='pm' and t['stage']=='define' and t['task']=='spec' for t in graph.values()):
                errors.append('define closure requires the selected pm/spec producer (reuse needs a verified result)')
        for issued in (root/'runs').glob('*/*-manifest.json'):
            run=load(issued); version(run)
            if stage is None or run['request']['stage']==stage:
                if run['bindings']['task_id'] not in graph:
                    errors.append('issued task removed from selected_tasks: '+run['bindings']['task_id'])
        if stage in (None,'implement'):
            required_tickets={t['id'] for t in state.get('tickets',[]) if isinstance(t,dict) and 'backend' in t.get('roles',[])}
            required_tickets.update(p.name.split('-backend-')[0] for p in (root/'03-impl').glob('T-*-backend-*evidence*.md'))
            selected_tickets={t['task'] for t in graph.values() if t['role']=='backend' and t['stage']=='implement'}
            if required_tickets-selected_tickets:
                errors.append('implementation closure omits backend tickets: '+', '.join(sorted(required_tickets-selected_tickets)))
        # This only verifies the recorded independent review boundary; check-sdlc retains all semantic gates.
        from evidence import read_list
        gates=read_list((root/'state.yaml').read_text(),'gates')
        stages={graph[k]['gate_stage'] for k in wanted if graph[k]['status']=='done'} & {'define','shape','implement','review'}
        for gate_stage in stages:
            fresh=[g for g in gates if g.get('kind')=='fresh-context' and g.get('stage')==gate_stage]
            if not fresh or fresh[-1].get('result')!='pass': errors.append('stage lacks passing independent review: '+gate_stage)
        # Selected graph does not replace required participation encoded in the existing lane gates.
        # Non-pilot roles keep their legacy participation checks in check-sdlc. Never
        # require an unsupported v3 designer result just to close a pilot-only graph.
    return {'mode':'strict','task_protocol':1,'closure':closure,'tasks':details,'errors':list(dict.fromkeys(errors))}


def legacy_selected_tasks(raw):
    """Display legacy selected_tasks read-only. Never converts them into protocol entries.

    Old states wrote free-form rows, often `- {role: backend, task: T-3, status: done}`. The strict reader
    rightly rejects that form, but the inventory must still show it: each row keeps its raw text, is parsed
    only when unambiguous, and anything else is reported as unparsed for manual migration.
    """
    from runtime_protocol import strict_yaml_block
    from check_config import _strip_comment, _scalar
    lines=[_strip_comment(x).rstrip() for x in raw.splitlines()]
    start=next((i for i,x in enumerate(lines) if re.match(r'selected_tasks:(\s|$)',x)),None)
    if start is None: return []
    inline=lines[start].split(':',1)[1].strip()
    if inline:
        return [] if inline=='[]' else [{'raw':inline,'form':'unparsed','fields':None,
                                         'note':'inline value; migrate manually'}]
    rows=[]
    for x in lines[start+1:]:
        if not x.strip(): continue
        if not x[0].isspace(): break
        rows.append((len(x)-len(x.lstrip()),x.strip()))
    items=[]
    for ind,body in rows:
        if body.startswith('- ') and (not items or ind<=items[0][0][0]): items.append([(ind,body)])
        elif items: items[-1].append((ind,body))
        else: items.append([(ind,body)])
    out=[]
    for item in items:
        text='\n'.join(' '*(i-item[0][0])+b for i,b in item); body=item[0][1][2:].strip() if item[0][1].startswith('- ') else None
        entry={'raw':text,'form':'unparsed','fields':None,'note':'manual migration required'}
        try:
            value=strict_yaml_block(item)[0]
            if isinstance(value,dict): entry.update(form='block',fields=value,note=None)
        except (ProtocolError,IndexError,KeyError,TypeError):
            m=re.fullmatch(r'\{(.*)\}',body or '')
            if m and len(item)==1 and not re.search(r'[{}\[\]"\']',m[1]):
                pairs=[p.partition(':') for p in m[1].split(',')]
                keys=[k.strip() for k,_,_ in pairs]
                if all(sep and re.fullmatch(r'[\w.-]+',k) for k,(_,sep,_) in zip(keys,pairs)) and len(set(keys))==len(keys):
                    entry.update(form='inline-legacy',fields={k:_scalar(v.strip()) for k,(_,_,v) in zip(keys,pairs)},note=None)
        out.append(entry)
    return out


def migration_report(root):
    """Inventory only. Manager must resolve IDs/contracts and create honest current evidence."""
    root=Path(root); raw=(root/'state.yaml').read_text()
    if re.search(r'^\s*(task_protocol|required_capabilities):',raw,re.M):
        state=state_read(root/'state.yaml'); source=state.get('task_protocol','legacy'); tasks=state.get('selected_tasks',[])
    else:
        # A protocol run without task_protocol is a downgrade, not legacy history.
        require(not any((root/'runs').glob('*/*-manifest.json')),'protocol downgrade: runs exist but task_protocol was removed')
        source='legacy'; tasks=legacy_selected_tasks(raw)
    return {'mode':'migration-inventory','source_protocol':source,
            'selected_tasks':tasks,'historical_validity':'unverified',
            'required_actions':['assign stable IDs and gate_stage from registry','record selection reason/source and dependency levels',
                                'bind existing verifiable results or rerun; never fabricate historic reads/times',
                                'add task_protocol and required_capabilities only after reviewing the graph'], 'errors':[]}
