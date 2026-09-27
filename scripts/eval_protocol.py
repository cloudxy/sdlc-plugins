#!/usr/bin/env python3
"""Deterministic eval setup and contamination checks. Does not spend model calls."""
from __future__ import annotations
import datetime as dt
import importlib.util
import shutil
import uuid
import random
from pathlib import Path
from zoneinfo import ZoneInfo

from runtime_protocol import (digest, file_hash, load, object_keys, path_inside, require,
                              safe_id, snapshot, write_json)
from workflow import ROOT, load_registry, resolve_task

COMPARISONS={'plugin','skill','chain'}
TREATMENTS={'with_without','old_new'}
SPEC_KEYS={'comparison','treatment','scope','role','stage','task','skill','steps','case','model','settings','tools',
           'budget','plugin_old','plugin_new','contract_version','seed'}
META_NAMES={'state.yaml','cycle.yaml','manifest.json','result.json','observation.json','eval-manifest.json'}


def neutral_preamble(role, task, tools):
    """Build from an explicit source whitelist; never edit a full role shell in place.

    IDENTITY assignments, LOOP, Skills and Contract can all contain method directives.
    Whitelisting identity/authority data prevents a newly added section leaking a procedure.
    """
    r=load_registry(); meta=r['roles'][role]
    t=resolve_task(r,role,task['stage'],task['task'])
    fresh=meta['fresh']
    return ('Role: '+role+'; function: '+meta['function']+'.\n'
            'Task: '+task['stage']+'/'+task['task']+'.\n'
            'Use only the supplied project copy and declared tools: '+', '.join(tools)+'.\n'
            'Respect the provided task scope and existing decisions. Explain unresolved issues with their owner and affected work.\n'
            + ('Return the full report in your final message; do not write files or execute commands.\n' if fresh else
               'Write only the requested deliverables and explicitly authorized project paths. Report evidence for checks you execute.\n')
            + 'Product files owned by this role (assignment may narrow): '+(', '.join(meta['product_writes']) or 'none')+'.\n'
            'Do not spawn additional agents. Do not infer unavailable checks passed.\n')


def forbidden_deliverable(rel):
    p=Path(rel)
    return (any(x in {'runs','.task-objects','memory','blind','blind-swap'} for x in p.parts)
            or p.name in META_NAMES or p.name.startswith('.blind')
            or any(p.name.endswith('-'+suffix) for suffix in ('manifest.json','result.json','start.json','packet.md','return.txt','observation.json')))


def prepare_eval(spec, out):
    object_keys(spec,SPEC_KEYS,{'comparison','treatment','scope','role','stage','task','case','model','settings','tools','budget','plugin_new','contract_version','seed'},'eval spec')
    require(spec['comparison'] in COMPARISONS and spec['treatment'] in TREATMENTS,'unknown comparison/treatment')
    require(spec['scope'] in ('role_task','workflow'),'unknown eval scope')
    require(spec['contract_version']==1,'eval arms must use the same supported contract version')
    require(isinstance(spec['model'],str) and spec['model'] and isinstance(spec['settings'],dict),'explicit model/settings required')
    require(isinstance(spec['tools'],list) and spec['tools'] and all(isinstance(t,str) for t in spec['tools']),'explicit identical tool list required')
    object_keys(spec['budget'],{'calls','output_tokens','seconds'},{'calls','output_tokens','seconds'},'eval budget')
    require(all(type(x) is int and x>0 for x in spec['budget'].values()),'positive eval budget required')
    case=spec['case']
    object_keys(case,{'id','prompt','fixture_root','inputs','deliverables','rubric'},{'id','prompt','fixture_root','inputs','deliverables','rubric'},'case')
    safe_id(case['id']); require(case['prompt'] and case['deliverables'] and case['rubric'],'case prompt/deliverables/rubric required')
    require(isinstance(case['inputs'],list) and all(isinstance(x,str) for x in case['inputs']),'explicit fixture input list required')
    require(all(not forbidden_deliverable(p) for p in case['deliverables']),'audit metadata cannot be a blind deliverable')
    task=resolve_task(load_registry(),spec['role'],spec['stage'],spec['task'])
    if spec['comparison']=='skill':
        require(spec.get('skill')==task['skill'] or spec.get('skill') in task.get('companions',[]),'skill is not a method of the task')
    if spec['comparison']=='chain':
        require(isinstance(spec.get('steps'),list) and len(spec['steps'])>=2,'chain needs at least two concrete steps')
        for step in spec['steps']:
            object_keys(step,{'role','stage','task','consumes','produces'},{'role','stage','task','consumes','produces'},'chain step')
            resolve_task(load_registry(),step['role'],step['stage'],step['task'])
    require(spec['comparison']=='plugin' or spec['scope']=='role_task','workflow scope measures the plugin, not a single method')
    fixture=Path(case['fixture_root']).resolve()
    out=Path(out).resolve(); require(not out.exists(),'eval run path exists; use a new dated run')
    require(not out.is_relative_to(fixture),'eval workspace must be outside the fixture')
    plugin_new=Path(spec['plugin_new']).resolve()
    require((plugin_new/'workflow/registry.json').is_file(),'plugin_new snapshot missing')
    if spec['treatment']=='old_new':
        require(spec.get('plugin_old'),'old_new requires frozen old plugin content')
        require(Path(spec['plugin_old']).resolve()!=plugin_new,'old and new snapshots must be distinct')
    stamp=dt.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d-%H%M%S%z')+'-'+case['id']+'-'+uuid.uuid4().hex[:8]
    out.mkdir(parents=True)
    preamble=neutral_preamble(spec['role'],spec,spec['tools'])
    arm_names=['without','with'] if spec['treatment']=='with_without' else ['old','new']
    arms={}; inputs={}
    for rel in case['inputs']:
        p=path_inside(rel,fixture,True); require(not p.is_symlink(),'fixture symlink not supported')
        require(not forbidden_deliverable(rel),'input fixture contains previous run metadata')
        inputs[rel]=file_hash(p)
    for arm in arm_names:
        home=out/arm; project=home/'project'; project.mkdir(parents=True)
        (home/'outputs').mkdir()
        for rel in inputs:
            target=path_inside(rel,project); target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(fixture/rel,target)
        method_root=None; methods_hash=None
        if arm!='without' or spec['comparison']=='chain':
            source=Path(spec['plugin_old']) if arm=='old' else plugin_new
            method_root=home/'methods'
            method_root.mkdir()
            # Skill/chain treatments copy methods only; control and both role shells remain neutral.
            if spec['comparison']=='skill':
                name=spec['skill']; shutil.copytree(source/'skills'/name,method_root/'skills'/name)
            elif spec['comparison']=='chain':
                for index,step in enumerate(spec['steps']):
                    if index==0 and arm=='without': continue
                    name=resolve_task(load_registry(),step['role'],step['stage'],step['task'])['skill']
                    # Only the upstream treatment varies; downstream method content is fixed in both arms.
                    step_source=source if index==0 else plugin_new
                    shutil.copytree(step_source/'skills'/name,method_root/f'step-{index+1}'/'skills'/name)
            else:
                for folder in ('agents','skills','workflow','adapters','commands','scripts'):
                    shutil.copytree(source/folder,method_root/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            methods_hash=digest({str(Path(p).relative_to(method_root)):v for p,v in snapshot([method_root])['files'].items()})
        treatment='Solve using your general professional knowledge. No bundled method material is provided.\n'
        if method_root:
            if spec['comparison']=='skill': treatment=f"Read {method_root}/skills/{spec['skill']}/SKILL.md and apply its relevant procedure.\n"
            elif spec['comparison']=='plugin': treatment=f"Read {method_root}/agents/{spec['role']}.md and use the assigned plugin task.\n" if spec['scope']=='role_task' else f'Read {method_root}/skills/sdlc/SKILL.md and manage the supplied workflow case.\n'
            else:
                treatment='Run these steps in separate fresh sessions; downstream consumes the actual preceding output.\n'
                for index,step in enumerate(spec['steps']):
                    name=resolve_task(load_registry(),step['role'],step['stage'],step['task'])['skill']
                    treatment+=f"Step {index+1}: {step['role']}/{step['stage']}/{step['task']}; consumes {step['consumes']}; produces {step['produces']}. "
                    treatment+=('Use general professional knowledge.\n' if index==0 and arm=='without' else f'Read {method_root}/step-{index+1}/skills/{name}/SKILL.md.\n')
        prompt=preamble+'\n'+case['prompt']+'\n\n'+treatment+f'Project copy: {project}\nDeliverables: {home}/outputs/\n'
        prompt+='Do not read sibling arms, live project, baseline answers, eval manifests or judge materials.\n'
        prompt_path=home/(stamp+'-prompt.md'); prompt_path.write_text(prompt)
        arms[arm]={'project':str(project),'outputs':str(home/'outputs'),'prompt':str(prompt_path),'prompt_sha256':file_hash(prompt_path),
                   'method_root':str(method_root) if method_root else None,'methods_sha256':methods_hash,'input_sha256':digest(inputs)}
    manifest={'protocol_version':1,'comparison':spec['comparison'],'treatment':spec['treatment'],'scope':spec['scope'],
              'run_id':stamp,'spec':spec,'inputs':inputs,'neutral_preamble':preamble,'arms':arms,
              'status':'prepared-not-executed','quality_acceptance':'pending','actual_calls':0,
              'limits':['host must enforce or observe cross-arm isolation','no model quality claim from preparation or mechanical tests']}
    path=out/(stamp+'-eval-manifest.json'); write_json(path,manifest)
    return {'manifest':str(path),'arms':arms,'status':manifest['status'],'errors':[]}


def validate_observations(manifest, observations):
    """Complete host trace is required for a valid controlled comparison; self-report cannot substitute."""
    errors=[]; spec=manifest['spec']; calls=0
    for arm,setup in manifest['arms'].items():
        obs=observations.get(arm)
        if not obs: errors.append(arm+': missing host observations'); continue
        object_keys(obs,{'model','settings','tools','calls','reads','method_loads','complete_trace'},
                    {'model','settings','tools','calls','reads','method_loads','complete_trace'},'arm observations')
        if obs['model']!=spec['model'] or obs['settings']!=spec['settings'] or sorted(obs['tools'])!=sorted(spec['tools']): errors.append(arm+': unequal model/settings/tools')
        require(type(obs['calls']) is int and obs['calls']>=0,'calls must be nonnegative integer'); calls+=obs['calls']
        if obs['complete_trace'] is not True: errors.append(arm+': contamination unobservable')
        allowed=[Path(setup['project']),Path(setup['outputs']),Path(setup['prompt'])]
        if setup['method_root']: allowed.append(Path(setup['method_root']))
        for raw in obs['reads']:
            p=Path(raw).resolve()
            if not any(p==a or p.is_relative_to(a) for a in allowed): errors.append(arm+': read outside isolated arm: '+str(p))
        if arm=='without' and obs['method_loads']:
            if spec['comparison']!='chain': errors.append('without: bundled method loaded')
            else:
                allowed_methods={resolve_task(load_registry(),s['role'],s['stage'],s['task'])['skill'] for s in spec['steps'][1:]}
                if not set(obs['method_loads']) <= allowed_methods: errors.append('without: upstream treatment loaded')
    if calls>spec['budget']['calls']: errors.append('model-call budget exceeded')
    return {'valid':not errors,'actual_calls':calls,'errors':errors}


def blind_deliverables(manifest, destination):
    """Copy explicit deliverables only. Caller passes the resulting sides to existing blind judging."""
    destination=Path(destination); require(not destination.exists(),'blind destination already exists')
    sides={}
    for label,(arm,setup) in zip(('A','B'),manifest['arms'].items()):
        target=destination/label; target.mkdir(parents=True)
        for rel in manifest['spec']['case']['deliverables']:
            require(not forbidden_deliverable(rel),'run metadata cannot reach judge')
            source=path_inside(rel,setup['outputs'],True); output=path_inside(rel,target)
            output.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,output)
        sides[label]=arm
    return sides  # Persist privately; never give this map to a judge.


def prepare_blind(manifest_path, observation_path):
    """Reuse the existing quote-validated, position-swapped judging format after contamination audit."""
    manifest=load(manifest_path); observations=load(observation_path)
    audit=validate_observations(manifest,observations)
    require(audit['valid'],'invalid controlled comparison: '+'; '.join(audit['errors']))
    from blind_eval import _prepare_case, _validate_rubric
    home=Path(manifest_path).parent; case=manifest['spec']['case']
    require(not (home/'blind').exists() and not (home/'blind-swap').exists(),'blind run already exists; preserve judgments and use a new run')
    for arm in manifest['arms'].values():
        for rel in case['deliverables']: path_inside(rel,arm['outputs'],True)
    mapping=_prepare_case(str(home),tuple(manifest['arms']),case['id'],case['prompt'],'',
                          _validate_rubric(case['rubric'],'controlled case'),random.Random(manifest['spec']['seed']),
                          manifest['spec'].get('skill','controlled-comparison'),case['deliverables'],[])
    private=home/(manifest['run_id']+'-blind-map.json')
    write_json(private,{'mapping':mapping,'comparison':manifest['comparison'],'treatment':manifest['treatment'],'audit':audit})
    return {'judge_folders':[str(home/'blind'),str(home/'blind-swap')],'private_map':str(private),'errors':[]}
