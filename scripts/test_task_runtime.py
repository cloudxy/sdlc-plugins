#!/usr/bin/env python3
"""Protocol behavior tests: real files, execution records, source changes and gate boundaries."""
from __future__ import annotations
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from runtime_protocol import ProtocolError, file_hash, load, loads, now, snapshot, changes, state_read, write_json
from task_runtime import prepare, seal, record, lint_packet_v3
from task_state import check_tasks, validate_graph
from workflow import load_registry, resolve_task
from check_packet import lint
from evidence import cmd_run, verify_bound_records


def yaml_rows(value, indent=0):
    rows=[]
    if isinstance(value,dict):
        for key,item in value.items():
            prefix=' '*indent+key+':'
            if isinstance(item,(dict,list)) and item:
                rows.append(prefix); rows+=yaml_rows(item,indent+2)
            else: rows.append(prefix+' '+json.dumps(item,ensure_ascii=False))
    elif isinstance(value,list):
        for item in value:
            if isinstance(item,dict):
                nested=yaml_rows(item,indent+2)
                rows.append(' '*indent+'- '+nested[0].lstrip()); rows+=nested[1:]
            else: rows.append(' '*indent+'- '+json.dumps(item))
    return rows


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name).resolve(); self.project=self.home/'project'; self.root=self.project/'.sdlc/f'
        self.product=self.home/'external-product'; self.root.mkdir(parents=True); self.product.mkdir()
        self.put(self.project/'sdlc.config.yaml',f'product_root: {self.product}\n')
        self.put(self.project/'src/app.py','x = 1\n')
        for name in ('strategy.md','feature-map.md','architecture.md'): self.put(self.product/name,'Accepted product facts\n')
        self.task={'id':'pm-spec','role':'pm','stage':'define','task':'spec','gate_stage':'define',
                   'depends_on':[],'status':'todo','selection':{'required':True,'reason':'user request','source':'user quote'}}
        self.state={'feature':'f','task_protocol':1,'required_capabilities':['input-contract-v1','result-v1','task-closure-v1'],
                    'lane':'L2','ui':False,'tracking':False,'q_security':False,'rework_rounds':0,
                    'selected_tasks':[self.task],'obligations':[]}
        self.save_state()
        self.brief=self.put(self.root/'00-discover/briefing.md','Problem and user intent\n')
        self.decisions=self.put(self.root/'00-discover/decisions.md','No unresolved strategic decisions; reuse user quote.\n')
        self.bindings={'task_id':'pm-spec','project_root':str(self.project),'product_root':str(self.product),
                       'intent_quote':'Define a small export feature','assignment':'Write measurable FR and GWT',
                       'inputs':{'briefing':str(self.brief),'decisions':str(self.decisions)},
                       'deliverable_paths':['01-define/spec.md'],
                       'product_writes':[str(self.product/'strategy.md'),str(self.product/'feature-map.md')]}
        self.req={'role':'pm','stage':'define','task':'spec','scope':'feature','root':str(self.root)}
        self.return_path=self.home/'return.txt'
    def put(self,p,text):
        p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text); return p
    def save_state(self): self.put(self.root/'state.yaml','\n'.join(yaml_rows(self.state))+'\n')
    def prepared(self,offline=False):
        p=self.root/f'draft-{len(list(self.root.glob("draft*")))}.json'
        value=prepare(self.req,self.bindings,p,offline)
        return p,value
    def sealed(self):
        p,value=self.prepared(); self.assertEqual(value['missing'],[]); return seal(p)
    def response(self,checks=None,unresolved=None):
        value={'methods_used':[{'skill':resolve_task(load_registry(),self.req['role'],self.req['stage'],self.req['task'])['skill'],
                               'reason':'Applied the assigned task procedure','provenance':'reported'}],
               'reported_reads':list(self.bindings['inputs']),'unresolved':unresolved or [],'proposed_changes':[],
               'product_delta':[],'lessons':[],'check_records':checks or []}
        self.put(self.return_path,'Summary\n```result\n'+json.dumps(value)+'\n```\n'); return value
    def finish_pm(self,paths,unresolved=None):
        self.put(self.root/'01-define/spec.md','# FR-1\nGiven an account When export Then a file\n')
        self.response(unresolved=unresolved); return record(paths['manifest'],self.return_path)
    def mark_done(self,paths):
        self.task.update(status='done',result=str(Path(paths['result']).relative_to(self.root)),result_sha256=file_hash(paths['result']))
        self.save_state()
    def use_backend(self):
        self.task.update(id='backend-T-3',role='backend',stage='implement',task='T-3',gate_stage='implement'); self.save_state()
        self.req.update(role='backend',stage='implement',task='T-3')
        contract=self.put(self.root/'02-shape/contract.md','Accepted API behavior and SEC obligations\n')
        self.put(self.root/'01-define/spec.md','FR-1 export GWT\n')
        ticket=self.put(self.root/'02-shape/T-3.md','T-3: implement FR-1\n')
        data=self.put(self.root/'02-shape/data.md','No database changes; existing export schema v1\n')
        acceptance=self.root/'contract-acceptance.json'
        write_json(acceptance,{'id':'A-1','kind':'acceptance','target':str(contract),'target_sha256':file_hash(contract),
                              'scope':str(self.root),'by':'user','authority':'recorded task authorization','quote':'Implement this API contract',
                              'at':now(),'status':'accepted','obligations':[]})
        self.bindings.update(task_id='backend-T-3',inputs={'ticket':str(ticket),'data_definitions':str(data)},
                             deliverable_paths=['03-impl/T-3-backend-evidence.md','03-impl/T-3-integration.md'],product_writes=[],source_writes=['src/'],
                             decisions=[str(acceptance)],slice_integrator='backend',
                             required_checks=[{'id':'unit','scope':'T-3','environment':'local','build_required':False}])
    def run_check(self,exit_code=0,scope='T-3',environment='local'):
        ctx={'check_id':'unit','scope':scope,'environment':environment,'executor':'test-host','build':None}
        cmd_run(self.root,'unit',[sys.executable,'-c',f'print("verification"); raise SystemExit({exit_code})'],ctx)
        files=list((self.root/'evidence/runs').glob('unit-*.json'))
        return str(max(files,key=lambda p:load(p)['finished']))
    def test_pm_end_to_end_and_review_is_separate(self):
        paths=self.sealed(); self.assertFalse(lint_packet_v3(Path(paths['packet']).read_text())['errors'])
        self.put(self.product/'strategy.md','PM updated owned product facts\n')
        result=self.finish_pm(paths); self.assertTrue(result['execution_complete'],result['errors'])
        self.assertEqual(result['read_observations']['level'],'unobservable')
        self.mark_done(paths)
        self.assertEqual(check_tasks(self.root)['tasks']['pm-spec']['validity'],'current')
        self.assertFalse(check_tasks(self.root)['errors'])
        self.assertTrue(check_tasks(self.root,'define',True)['errors'])
        self.state['gates']=[{'kind':'fresh-context','stage':'define','result':'pass'}]; self.save_state()
        self.assertFalse(check_tasks(self.root,'define',True)['errors'])
    def test_backend_legal_source_changes_and_bound_check(self):
        self.use_backend(); paths=self.sealed(); self.put(self.project/'src/app.py','x = 2\n')
        rec=self.run_check(); self.put(self.root/'03-impl/T-3-backend-evidence.md','FR-1 tested with unit check\n')
        self.put(self.root/'03-impl/T-3-integration.md','Consumer invocation verified in fixture\n')
        self.response([rec]); result=record(paths['manifest'],self.return_path)
        self.assertTrue(result['execution_complete'],result['errors']); self.mark_done(paths)
        self.assertEqual(check_tasks(self.root)['tasks']['backend-T-3']['validity'],'current')
        self.put(self.project/'src/app.py','x = 3\n')
        self.assertEqual(check_tasks(self.root)['tasks']['backend-T-3']['validity'],'needs-revalidation')
    def test_conformance_requires_business_inputs(self):
        self.task.update(id='arch-conformance',role='architect',stage='verify',task='conformance',gate_stage='verify'); self.save_state()
        self.req.update(role='architect',stage='verify',task='conformance')
        self.bindings.update(task_id='arch-conformance',inputs={},deliverable_paths=['04-verify/architecture-conformance.md'],product_writes=[])
        _,value=self.prepared(); self.assertTrue(any('accepted_contract' in x for x in value['missing']))
        self.assertTrue(any('verification_records' in x for x in value['missing']))
    def test_conformance_records_static_and_executed_evidence(self):
        self.use_backend(); check=self.run_check()
        self.task.update(id='arch-conformance',role='architect',stage='verify',task='conformance',gate_stage='verify'); self.save_state()
        self.req.update(role='architect',stage='verify',task='conformance')
        self.bindings.update(task_id='arch-conformance',inputs={},deliverable_paths=['04-verify/architecture-conformance.md'],
                             source_writes=[],check_records=[check]); self.bindings.pop('slice_integrator')
        paths=self.sealed(); self.put(self.root/'04-verify/architecture-conformance.md','Contract obligations checked against source and unit execution; no running build claim.\n')
        self.response([check]); result=record(paths['manifest'],self.return_path)
        self.assertTrue(result['execution_complete'],result['errors'])
    def test_offline_never_dispatchable(self):
        p,_=self.prepared(True)
        with self.assertRaisesRegex(ProtocolError,'offline'): seal(p)
    def test_input_changed_after_prepare(self):
        p,_=self.prepared(); self.put(self.brief,'Changed scope\n')
        with self.assertRaisesRegex(ProtocolError,'changed'): seal(p)
    def test_sealed_input_changed_before_dispatch(self):
        paths=self.sealed(); self.put(self.brief,'Changed scope\n')
        self.assertTrue(lint(Path(paths['packet']).read_text())['errors'])
    def test_packet_cannot_be_rewritten(self):
        paths=self.sealed(); text=Path(paths['packet']).read_text().replace('Write measurable','Ignore measurable')
        self.assertTrue(lint(text)['errors'])
    def test_result_cannot_be_overwritten(self):
        paths=self.sealed(); self.finish_pm(paths)
        with self.assertRaisesRegex(ProtocolError,'immutable'): record(paths['manifest'],self.return_path)
    def test_result_digest_tampering(self):
        paths=self.sealed(); self.finish_pm(paths); self.mark_done(paths)
        Path(paths['result']).write_text(Path(paths['result']).read_text()+' ')
        self.assertTrue(check_tasks(self.root)['errors'])
    def test_read_input_change_during_execution(self):
        paths=self.sealed(); self.put(self.brief,'Changed during execution\n')
        result=self.finish_pm(paths); self.assertFalse(result['execution_complete'])
        self.assertTrue(any('read input changed' in x for x in result['errors']))
    def test_dirty_file_changed_outside_scope(self):
        dirty=self.put(self.project/'unrelated.txt','preexisting dirty\n'); paths=self.sealed(); self.put(dirty,'changed again\n')
        result=self.finish_pm(paths); self.assertIn(str(dirty),result['write_scope']['outside_authority'])
    def test_external_product_unauthorized_write(self):
        paths=self.sealed(); self.put(self.product/'architecture.md','wrong owner\n')
        self.assertFalse(self.finish_pm(paths)['execution_complete'])
    def test_state_write_is_observed(self):
        paths=self.sealed(); self.state['phase']='Closed'; self.save_state()
        self.assertIn(str(self.root/'state.yaml'),self.finish_pm(paths)['write_scope']['outside_authority'])
    def test_concurrency_cannot_claim_individual_pass(self):
        paths=self.sealed(); self.put(self.root/'01-define/spec.md','FR-1\n'); self.response()
        result=record(paths['manifest'],self.return_path,concurrent=True)
        self.assertEqual(result['write_scope']['level'],'group_observed'); self.assertFalse(result['execution_complete'])
    def test_unrecorded_run_blocks_a_second_seal(self):
        # Diagnosis 2026-10-02: a returned but unrecorded task was dispatched again after context compaction.
        first=self.sealed()
        with self.assertRaises(ProtocolError) as e: self.sealed()
        self.assertIn('unrecorded run', str(e.exception))
        record(first['manifest'],interrupted='never dispatched')
        self.sealed()
    def test_missing_return_and_interrupted_run(self):
        paths=self.sealed(); result=record(paths['manifest'],interrupted='host timeout')
        self.assertFalse(result['execution_complete']); self.assertIsNone(result['judgments'])
    def test_missing_return_structure_not_empty_success(self):
        paths=self.sealed(); self.put(self.return_path,'passed'); result=record(paths['manifest'],self.return_path)
        self.assertFalse(result['execution_complete'])
    def test_return_commands_are_never_executed(self):
        paths=self.sealed(); self.put(self.root/'01-define/spec.md','FR-1\n'); value=self.response()
        marker=self.home/'owned'; value['success_checks']=[f'touch {marker}']
        self.put(self.return_path,'```result\n'+json.dumps(value)+'\n```\n')
        self.assertFalse(record(paths['manifest'],self.return_path)['execution_complete']); self.assertFalse(marker.exists())
    def test_newer_failure_overrides_old_pass_same_context(self):
        self.use_backend(); old=self.run_check(); self.run_check(3)
        with self.assertRaisesRegex(ValueError,'newer failure'):
            verify_bound_records(self.root,[old],self.bindings['required_checks'],self.project,self.product)
    def test_unrelated_environment_not_evidence(self):
        self.use_backend(); other=self.run_check(environment='staging')
        with self.assertRaisesRegex(ValueError,'exactly one'):
            verify_bound_records(self.root,[other],self.bindings['required_checks'],self.project,self.product)
    def test_missing_log_rejected(self):
        self.use_backend(); p=Path(self.run_check()); (p.parent/load(p)['log']).unlink()
        with self.assertRaisesRegex(ValueError,'missing file'):
            verify_bound_records(self.root,[str(p)],self.bindings['required_checks'],self.project,self.product)
    def test_reason_cannot_waive_missing_input(self):
        self.bindings['inputs_waived']=[{'reason':'enough','by':'manager'}]
        with self.assertRaisesRegex(ProtocolError,'unknown fields'): self.prepared()
    def test_debug_rework_on_pm_is_allowed_and_required(self):
        self.state['rework_rounds']=2; self.save_state()
        with self.assertRaisesRegex(ProtocolError,'requires debug'): self.prepared()
        self.bindings.update(allowed_companion_skills=['debug'],required_companion_skills=['debug'])
        _,value=self.prepared(); self.assertEqual(value['missing'],[])
    def test_v2_cannot_downgrade_pilot(self):
        from task_runtime import legacy_view
        _,value=self.prepared(); errors=lint(legacy_view(value['prepared']['packet']))['errors']
        self.assertIn('PROTOCOL',{e['code'] for e in errors})
    def test_unknown_scope_rejected(self):
        self.req['scope']='cycle'
        with self.assertRaisesRegex(ProtocolError,'feature only'): self.prepared()
    def test_same_day_run_names_unique_and_dated(self):
        a=self.sealed(); record(a['manifest'],interrupted='naming test: superseded before dispatch'); b=self.sealed()
        self.assertNotEqual(a['manifest'],b['manifest']); self.assertRegex(Path(a['manifest']).name,r'^\d{4}-\d{2}-\d{2}-\d{6}\+0800-pm-spec-')
    def test_duplicate_json_key_and_unknown_capability(self):
        with self.assertRaises(ProtocolError): loads('{"x":1,"x":2}')
        self.state['required_capabilities'].append('future-capability'); self.save_state()
        with self.assertRaisesRegex(ProtocolError,'unsupported required'): state_read(self.root/'state.yaml')
    def test_state_flow_objects_and_duplicate_fields_rejected(self):
        for text in ('task_protocol: 1\nselected_tasks: [{id: x}]\n',
                     'task_protocol: 1\nselected_tasks:\n  - id: x\n    id: y\n'):
            self.put(self.root/'state.yaml',text)
            with self.assertRaises(ProtocolError): state_read(self.root/'state.yaml')
    def test_legacy_roles_skipped_preserved(self):
        with (self.root/'state.yaml').open('a') as f: f.write('roles_skipped: [architect, growth]\n')
        self.assertEqual(state_read(self.root/'state.yaml')['roles_skipped'],['architect','growth'])
    def test_empty_strict_tasks_not_legacy(self):
        self.state['selected_tasks']=[]; self.save_state()
        with self.assertRaisesRegex(ProtocolError,'nonempty'): check_tasks(self.root)
    def test_deleted_protocol_not_legacy(self):
        self.sealed(); self.state.pop('task_protocol'); self.save_state()
        with self.assertRaisesRegex(ProtocolError,'downgrade'): check_tasks(self.root)
    def test_dependency_cycle_dangling_and_duplicate_ids(self):
        self.task['depends_on']=[{'task':'missing','requires':'produced'}]
        with self.assertRaisesRegex(ProtocolError,'dangling'): validate_graph(self.state)
        self.task['depends_on'][0]['task']=self.task['id']
        with self.assertRaisesRegex(ProtocolError,'cycle'): validate_graph(self.state)
        self.task['depends_on']=[]; self.state['selected_tasks'].append(copy.deepcopy(self.task))
        with self.assertRaisesRegex(ProtocolError,'duplicate task'): validate_graph(self.state)
    def test_required_skip_and_empty_supersession_rejected(self):
        self.task['status']='skipped'
        with self.assertRaisesRegex(ProtocolError,'cannot skip'): validate_graph(self.state)
        self.task['status']='superseded'
        with self.assertRaisesRegex(ProtocolError,'successor'): validate_graph(self.state)
    def test_future_todo_not_readiness_error(self):
        future=copy.deepcopy(self.task); future.update(id='future-spec')
        self.state['selected_tasks'].append(future); self.save_state()
        self.assertFalse(check_tasks(self.root)['errors'])
    def test_unresolved_blocker_cannot_be_deleted_from_state(self):
        paths=self.sealed(); self.finish_pm(paths,[{'id':'O-1','owner':'architect','blocks':['pm-spec'],'item':'Contract unclear','severity':'blocker'}]); self.mark_done(paths)
        self.assertFalse(check_tasks(self.root)['errors'])
        self.assertTrue(any('O-1' in x for x in check_tasks(self.root,'define',True)['errors']))
    def test_snapshot_detects_add_delete_mode_and_symlink(self):
        p=self.put(self.project/'dirty','old'); link=self.project/'link'; link.symlink_to(p)
        before=snapshot([self.project]); p.unlink(); link.unlink(); link.symlink_to('other')
        new=self.put(self.project/'new','new'); os.chmod(new,0o755)
        self.assertEqual(set(changes(before,snapshot([self.project]))),{str(p),str(link),str(new)})
    def test_l1_spec_does_not_require_briefing(self):
        self.state['lane']='L1'; self.save_state(); self.bindings['inputs'].pop('briefing')
        _,value=self.prepared(); self.assertEqual(value['missing'],[])
        self.assertFalse(value['prepared']['inputs']['briefing']['applicable'])
    def test_accepted_l2_short_spec_is_registered_alternative(self):
        self.use_backend(); self.state['path']='short'; self.save_state()
        spec=self.root/'01-define/spec.md'; self.bindings['inputs']['accepted_contract']=str(spec)
        p=Path(self.bindings['decisions'][0]); d=load(p); d.update(target=str(spec),target_sha256=file_hash(spec))
        write_json(p,d,exclusive=False)
        _,value=self.prepared(); self.assertEqual(value['missing'],[])
        self.state['path']='default'; self.save_state()
        _,value=self.prepared(); self.assertTrue(any('unregistered alternative' in x for x in value['missing']))
    def test_production_early_task_routes_still_allow_v2(self):
        from test_workflow import WorkflowTests
        helper=WorkflowTests(); helper.setUp(); self.addCleanup(helper.doCleanups)
        packet=helper.packet()
        self.assertFalse(lint(packet)['errors'])
        for role,stage,task,skill,outputs in [
            ('architect','define','feasibility','architecture',['01-define/architecture-feasibility.md']),
            ('qa','define','test-plan','coverage-matrix',['01-define/test-plan.md'])]:
            pk=helper.packet(role,stage,task,skill,outputs)
            self.assertFalse(lint(pk)['errors'],lint(pk)['errors'])
    def test_symlink_replacement_cannot_expand_sealed_authority(self):
        paths=self.sealed(); p=self.root/'01-define/spec.md'; p.parent.mkdir()
        p.symlink_to(self.root/'state.yaml'); self.response()
        result=record(paths['manifest'],self.return_path)
        self.assertTrue(any('targets changed' in e for e in result['errors']))
    def test_valid_resolution_closes_immutable_blocker(self):
        paths=self.sealed(); result=self.finish_pm(paths,[{'id':'O-1','owner':'architect','blocks':['pm-spec'],'item':'Unclear limit','severity':'blocker'}]); self.mark_done(paths)
        proof=self.put(self.root/'resolution-proof.md','Limit checked against accepted authority and independent review\n')
        ref=self.root/'resolution.json'
        write_json(ref,{'id':'R-1','kind':'resolution','target':str(proof),'target_sha256':file_hash(proof),'scope':str(self.root),
                        'by':'reviewer','authority':'independent review','quote':'Limit now covered','at':now(),'status':'accepted',
                        'obligations':[],'result_sha256':self.task['result_sha256']})
        self.state['obligations']=[{'id':'O-1','raised_by':'pm-spec','owner':'architect','blocks':['pm-spec'],'gate_stage':'define',
                                   'status':'resolved','resolution':'resolution.json'}]
        self.state['gates']=[{'kind':'fresh-context','stage':'define','result':'pass'}]; self.save_state()
        self.assertFalse(check_tasks(self.root,'define',True)['errors'])
        self.assertEqual(load(paths['result'])['judgments']['unresolved'],result['judgments']['unresolved'])
    def test_done_task_depends_on_produced_without_waiting_for_review(self):
        paths=self.sealed(); self.finish_pm(paths); self.mark_done(paths)
        next_task=copy.deepcopy(self.task)
        next_task.update(id='consumer',status='todo',depends_on=[{'task':'pm-spec','requires':'produced'}])
        next_task.pop('result'); next_task.pop('result_sha256'); self.state['selected_tasks'].append(next_task); self.save_state()
        self.assertFalse(check_tasks(self.root,task_id='consumer')['errors'])
        next_task['depends_on'][0]['requires']='accepted'; self.save_state()
        self.assertTrue(any('acceptance' in x for x in check_tasks(self.root,task_id='consumer')['errors']))
    def test_newer_interrupted_attempt_cannot_be_hidden(self):
        paths=self.sealed(); self.finish_pm(paths); newer=self.sealed(); record(newer['manifest'],interrupted='failed retry')
        self.mark_done(paths)
        self.assertTrue(any('newer attempt' in x for x in check_tasks(self.root)['errors']))
    def test_acceptance_input_dependency_cannot_be_downgraded(self):
        self.use_backend(); upstream=copy.deepcopy(self.task)
        upstream.update(id='contract',role='architect',stage='shape',task='contract',gate_stage='shape')
        self.state['selected_tasks'].append(upstream); self.task['depends_on']=[{'task':'contract','requires':'produced'}]
        with self.assertRaisesRegex(ProtocolError,'cannot downgrade'): validate_graph(self.state)
    def test_model_reported_pass_does_not_override_failed_check(self):
        self.use_backend(); paths=self.sealed(); check=self.run_check(2)
        self.put(self.root/'03-impl/T-3-backend-evidence.md','All checks passed (incorrect model statement)\n')
        self.put(self.root/'03-impl/T-3-integration.md','Integration done\n'); self.response([check])
        result=record(paths['manifest'],self.return_path)
        self.assertFalse(result['execution_complete']); self.assertTrue(any('execution failed' in e for e in result['errors']))
    def test_old_success_stays_historic_but_changed_conditions_need_revalidation(self):
        paths=self.sealed(); self.finish_pm(paths); self.mark_done(paths)
        self.state['tracking']=True; self.save_state()
        info=check_tasks(self.root)['tasks']['pm-spec']
        self.assertEqual(info['historical_execution'],'complete'); self.assertEqual(info['validity'],'needs-revalidation')
    def test_selection_cannot_make_pilot_skippable(self):
        self.task.update(status='skipped',reason='optional now',decision='skip.json')
        self.task['selection']['required']=False
        with self.assertRaisesRegex(ProtocolError,'does not allow skipping'): validate_graph(self.state)
    def test_closed_shell_gate_invokes_strict_task_check(self):
        import subprocess
        from workflow import ROOT
        self.state.update(phase='Closed',selected_tasks=[]); self.save_state()
        run=subprocess.run(['bash',str(ROOT/'scripts/check-sdlc.sh'),str(self.root)],text=True,capture_output=True,
                           env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        self.assertNotEqual(run.returncode,0); self.assertIn('TASKPROTOCOL',run.stdout); self.assertIn('nonempty',run.stdout)
    def test_closure_cannot_omit_issued_task(self):
        paths=self.sealed(); self.finish_pm(paths)
        self.task['id']='replacement'; self.save_state()
        self.assertTrue(any('issued task removed' in x for x in check_tasks(self.root,'define',True)['errors']))
    def test_verify_closure_does_not_invent_fresh_stage(self):
        self.use_backend(); check=self.run_check()
        self.task.update(id='arch-conformance',role='architect',stage='verify',task='conformance',gate_stage='verify'); self.save_state()
        self.req.update(role='architect',stage='verify',task='conformance')
        self.bindings.update(task_id='arch-conformance',inputs={},deliverable_paths=['04-verify/architecture-conformance.md'],
                             source_writes=[],check_records=[check]); self.bindings.pop('slice_integrator')
        paths=self.sealed(); self.put(self.root/'04-verify/architecture-conformance.md','All declared static obligations checked\n')
        self.response([check]); result=record(paths['manifest'],self.return_path); self.assertTrue(result['execution_complete'])
        self.mark_done(paths); self.assertFalse(check_tasks(self.root,'verify',True)['errors'])


class LegacyMigrationInventory(unittest.TestCase):
    """migrate-tasks must inventory old free-form rows read-only, and stay strict for protocol states."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def state(self, text):
        (self.root/'state.yaml').write_text(text)
    def test_legacy_inline_rows_are_listed_not_converted(self):
        from task_state import migration_report
        self.state('selected_tasks:\n  - {role: backend, stage: implement, task: T-3, status: done}\n'
                   '  - role: pm\n    stage: define\n    task: spec\n  - backend T-4 in progress\n'
                   '  - {role: qa, role: pm}\nlane: L2\nhats_done: [define, shape]\n')
        report=migration_report(self.root)
        self.assertEqual(report['source_protocol'],'legacy'); self.assertEqual(report['historical_validity'],'unverified')
        forms=[t['form'] for t in report['selected_tasks']]
        self.assertEqual(forms,['inline-legacy','block','unparsed','unparsed'])
        self.assertEqual(report['selected_tasks'][0]['fields']['task'],'T-3')
        self.assertTrue(all('id' not in (t['fields'] or {}) for t in report['selected_tasks']))
        self.assertEqual(check_tasks(self.root)['mode'],'legacy')
    def test_protocol_state_stays_strict(self):
        from task_state import migration_report
        self.state('task_protocol: 1\nselected_tasks:\n  - {role: backend, stage: implement, task: T-3, status: done}\n')
        with self.assertRaisesRegex(ProtocolError,'block mappings'): migration_report(self.root)
    def test_removed_protocol_with_runs_is_downgrade(self):
        from task_state import migration_report
        self.state('selected_tasks: []\n')
        run=self.root/'runs/r1'; run.mkdir(parents=True); (run/'r1-manifest.json').write_text('{}')
        with self.assertRaisesRegex(ProtocolError,'downgrade'): migration_report(self.root)


if __name__=='__main__': unittest.main()
