#!/usr/bin/env python3
"""Continuous-work scenarios using real protocol records, files and process locks."""
import copy
import json
import shutil
import subprocess
import sys
import concurrent.futures
import sqlite3
from unittest.mock import patch
from pathlib import Path
import unittest

import test_task_runtime as fixtures
from runtime_protocol import ProtocolError, file_hash, load, now, write_json
from task_runtime import record, prepare
from task_state import check_tasks, validate_graph
from artifact_versions import capture, promote
from state_store import update, bind_result
from project_graph import readiness, node_id
import coordination
import workspaces
import candidate
import data_jobs
import datasets


class ContinuousTests(unittest.TestCase):
    def fixture(self):
        f = fixtures.RuntimeTests(methodName='runTest'); f.setUp()
        self.addCleanup(f.doCleanups)
        f.state['project_id'] = 'test-project'
        f.state['required_capabilities'] += ['artifact-versions-v1', 'project-graph-v1', 'coordinated-state-v1',
                                             'isolated-execution-v1', 'candidate-v1', 'data-jobs-v1']
        f.save_state()
        return f

    def accept(self, f, path):
        out = f.root / ('accept-' + path.name + '.json')
        write_json(out, {'id': 'A-1', 'kind': 'acceptance', 'target': str(path), 'target_sha256': file_hash(path),
                        'scope': str(f.root), 'by': 'user', 'authority': 'explicit test fixture decision',
                        'quote': 'Use this version', 'at': now(), 'status': 'accepted', 'obligations': []})
        return str(out)

    def test_old_version_consumed_while_live_briefing_changes(self):
        f = self.fixture(); ref = capture(f.root, 'briefing', f.brief)
        f.bindings['inputs'].pop('briefing'); f.bindings['version_inputs'] = {'briefing': ref}
        paths = f.sealed()
        # A different workspace creates v2; the read-only version remains unchanged.
        f.put(f.brief, 'Second iteration, not yet accepted\n')
        # Shared workspace audit correctly rejects the concurrent edit; use a new run after it.
        f.response(); result = record(paths['manifest'], f.return_path)
        self.assertFalse(result['execution_complete'])
        paths = f.sealed(); result = f.finish_pm(paths)
        self.assertTrue(result['execution_complete'], result['errors'])
        content = Path(result['declared_inputs']['briefing']['path']).read_text()
        self.assertEqual(content, 'Problem and user intent\n')
        f.mark_done(paths)
        self.assertEqual(check_tasks(f.root)['tasks']['pm-spec']['validity'], 'current')

    def test_promotion_competing_versions_and_object_tampering(self):
        f = self.fixture(); a = capture(f.root, 'briefing', f.brief)
        a_obj = Path(load(a['path'])['object']); decision = self.accept(f, a_obj)
        first = promote(a, None, decision)
        with self.assertRaisesRegex(ProtocolError, 'conflict'): promote(a, None, decision)
        second = promote(a, first['sha256'], decision)
        self.assertTrue(Path(first['history']).exists()); self.assertTrue(Path(second['history']).exists())
        f.put(a_obj, 'tampered')
        with self.assertRaisesRegex(ProtocolError, 'modified'): promote(a, second['sha256'], decision)

    def test_state_cas_and_idempotent_result_binding(self):
        f = self.fixture(); paths = f.sealed(); f.finish_pm(paths)
        old = file_hash(f.root / 'state.yaml')
        bind_result(f.root, f.task['id'], paths['result'], old)
        replay = bind_result(f.root, f.task['id'], paths['result'], old)
        self.assertTrue(replay['idempotent'])
        with self.assertRaisesRegex(ProtocolError, 'conflict'):
            update(f.root, old, {'active_work': None})
        task = copy.deepcopy(f.state['selected_tasks'][0]); task['selection']['reason'] = 'Quoted "rule"\nsecond line'
        # A new task can preserve escaped text without rewriting unrelated feature metadata.
        task['id'] = 'new-task'
        from runtime_protocol import state_read
        state = state_read(f.root / 'state.yaml')
        update(f.root, file_hash(f.root / 'state.yaml'), {'selected_tasks': state['selected_tasks'] + [task]})
        self.assertEqual(state_read(f.root / 'state.yaml')['selected_tasks'][-1]['selection']['reason'], task['selection']['reason'])

    def test_external_dependency_readiness_and_identity(self):
        producer = self.fixture(); paths = producer.sealed(); producer.finish_pm(paths); producer.mark_done(paths)
        consumer = self.fixture()
        edge = {'feature_root': str(producer.root), 'project_id': 'test-project', 'task': producer.task['id'],
                'result_sha256': file_hash(paths['result']), 'requires': 'produced'}
        consumer.task['external_dependencies'] = [edge]; consumer.save_state()
        report = readiness([consumer.root], node_id(producer.root, producer.task['id']))
        self.assertTrue(report['tasks'][node_id(consumer.root, consumer.task['id'])]['ready'])
        self.assertIn(node_id(consumer.root, consumer.task['id']), report['affected'])
        edge['result_sha256'] = '0' * 64; consumer.save_state()
        self.assertTrue(check_tasks(consumer.root, task_id=consumer.task['id'])['errors'])
        edge['project_id'] = 'wrong-project'; consumer.save_state()
        with self.assertRaisesRegex(ProtocolError, 'identity'): readiness([consumer.root])

    def test_cross_feature_cycle_and_unknown_capability_fail_closed(self):
        a, b = self.fixture(), self.fixture()
        for source, target in [(a, b), (b, a)]:
            source.task['external_dependencies'] = [{'feature_root': str(target.root), 'project_id': 'test-project',
                'task': target.task['id'], 'result_sha256': '0' * 64, 'requires': 'produced'}]
            source.save_state()
        with self.assertRaisesRegex(ProtocolError, 'cycle'): readiness([a.root])
        a.state['required_capabilities'].remove('project-graph-v1')
        with self.assertRaisesRegex(ProtocolError, 'project-graph'): validate_graph(a.state)

    def test_standalone_negative_prototype_finishes_without_product_delivery(self):
        f = self.fixture()
        f.task.update(role='designer', stage='market', task='prototype', gate_stage='market'); f.save_state()
        f.req.update(role='designer', stage='market', task='prototype')
        f.bindings.update(inputs={'question': str(f.brief), 'constraints': str(f.decisions)},
                          deliverable_paths=['00-discover/prototypes/report.md'], product_writes=[])
        paths = f.sealed()
        f.put(f.root / '00-discover/prototypes/report.md', 'Observed prototype: hypothesis rejected; keep the existing behavior.\n')
        f.response(); result = record(paths['manifest'], f.return_path)
        self.assertTrue(result['execution_complete'], result['errors'])
        self.assertFalse(result['applicability']['stage_accepted'])

    def repository(self):
        f = self.fixture()
        f.product = f.project / 'docs/product'
        f.product.mkdir(parents=True)
        f.put(f.project / 'sdlc.config.yaml', 'product_root: docs/product\n')
        f.put(f.project / '.gitignore', '.sdlc/\n')
        for name in ('strategy.md', 'feature-map.md', 'architecture.md'):
            f.put(f.product / name, 'Accepted product facts\n')
        f.bindings.update(product_root=str(f.product), product_writes=[str(f.product / 'strategy.md'), str(f.product / 'feature-map.md')])
        for args in [('init', '-q'), ('config', 'user.name', 'SDLC test'), ('config', 'user.email', 'sdlc-test@example.invalid'),
                     ('add', '.'), ('commit', '-qm', 'baseline')]: workspaces.git(f.project, *args)
        return f

    def isolated(self, f, name, task_id=None):
        workspace = f.home / name
        workspaces.git(f.project, 'worktree', 'add', '--detach', str(workspace), 'HEAD')
        feature = workspace / '.sdlc/f'; shutil.copytree(f.root, feature)
        workspaces.register(f.project, name, workspace, f.root, feature, workspace / 'docs/product')
        key = str(f.root) + '#' + (task_id or f.task['id'])
        claim = coordination.claim(f.project, key, 'worker-' + name, name, [{'id': 'db/' + name, 'mode': 'read'}])
        bindings = copy.deepcopy(f.bindings)
        bindings.update(project_root=str(workspace), product_root=str(workspace / 'docs/product'),
                        task_id=task_id or f.task['id'], execution_mode='isolated',
                        isolation={'coordinator': str(f.project), 'workspace_id': name, 'key': key,
                                   'token': claim['token'], 'owner': claim['owner']})
        bindings['inputs'] = {k: str(feature / Path(v).relative_to(f.root)) for k, v in bindings['inputs'].items()}
        bindings['product_writes'] = [str(workspace / 'docs/product' / Path(p).name) for p in bindings.get('product_writes', [])]
        req = dict(f.req, root=str(feature))
        return feature, req, bindings, claim

    def test_two_isolated_runs_complete_and_import_with_stale_token_rejected(self):
        from task_runtime import seal
        f = self.repository()
        other = copy.deepcopy(f.task); other['id'] = 'pm-next'
        f.state['selected_tasks'].append(other); f.save_state()
        a = self.isolated(f, 'work-a'); b = self.isolated(f, 'work-b', 'pm-next')
        paths = []
        for feature, req, bindings, claim in (a, b):
            draft = feature / 'draft-isolated.json'; value = prepare(req, bindings, draft)
            self.assertFalse(value['missing'], value['missing']); paths.append(seal(draft))
        f.response()
        for (feature, req, bindings, claim), run in zip((a, b), paths):
            f.put(feature / '01-define/spec.md', 'Independent requirements proposal\n')
            result = record(run['manifest'], f.return_path)
            self.assertTrue(result['execution_complete'], result['errors'])
        old = file_hash(f.root / 'state.yaml')
        workspaces.import_result(f.project, 'work-a', f.task['id'], paths[0]['result'], a[3]['token'], old)
        replay = workspaces.import_result(f.project, 'work-a', f.task['id'], paths[0]['result'], a[3]['token'], old)
        self.assertTrue(replay['idempotent'])
        self.assertEqual(check_tasks(f.root)['tasks'][f.task['id']]['validity'], 'current')
        coordination.release(f.project, a[3]['key'], a[3]['token'], 'run imported')
        with self.assertRaisesRegex(ProtocolError, 'stale'):
            workspaces.import_result(f.project, 'work-a', f.task['id'], paths[0]['result'], a[3]['token'], old)

    def test_atomic_claim_and_shared_database_conflict(self):
        f = self.repository(); feature, req, bindings, claim = self.isolated(f, 'work-a')
        coordination.release(f.project, claim['key'], claim['token'], 'fixture reset')
        def compete(n):
            try: return coordination.claim(f.project, claim['key'], 'worker-' + str(n), 'work-a', [{'id': 'db/shared', 'mode': 'write'}])
            except ProtocolError: return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(compete, (1, 2)))
        self.assertEqual(sum(x is not None for x in outcomes), 1)
        self.assertTrue(coordination.conflicts({'id': 'db/shared', 'mode': 'write'}, {'id': 'db/shared/partition-1', 'mode': 'read'}))

    def test_candidate_rejects_unincluded_code_and_failed_integration(self):
        f = self.repository(); f.use_backend()
        # use_backend updates the existing fixture config-independent task and inputs.
        paths = f.sealed(); f.put(f.project / 'src/app.py', 'x = 2\n')
        rec = f.run_check()
        for output in f.bindings['deliverable_paths']: f.put(f.root / output, 'Real unit check and local integration evidence\n')
        f.response([rec]); result = record(paths['manifest'], f.return_path)
        self.assertTrue(result['execution_complete'], result['errors']); f.mark_done(paths)
        components = [{'root': str(f.root), 'task': f.task['id'], 'result_sha256': file_hash(paths['result'])}]
        checks = [{'id': 'integration', 'scope': 'candidate-1', 'environment': 'local', 'build_required': False}]
        c = candidate.create(f.project, f.root, f.product, 'candidate-1', 'HEAD', components, checks)
        self.assertFalse(c['verified'])
        from evidence import cmd_run
        cmd_run(f.root, 'integration', [sys.executable, '-c', 'raise SystemExit(1)'],
                {'check_id': 'integration', 'scope': 'candidate-1', 'environment': 'local', 'executor': 'test', 'build': None})
        records = [str(p) for p in (f.root / 'evidence/runs').glob('integration-*.json')]
        with self.assertRaises(ValueError): candidate.verify(c['manifest'], records)
        cmd_run(f.root, 'integration', [sys.executable, '-c', 'print("actual combined candidate check")'],
                {'check_id': 'integration', 'scope': 'candidate-1', 'environment': 'local', 'executor': 'test', 'build': None})
        newest = max((f.root / 'evidence/runs').glob('integration-*.json'), key=lambda p: load(p)['finished'])
        self.assertEqual(candidate.verify(c['manifest'], [str(newest)])['claim'], 'integration-verified')
        with self.assertRaisesRegex(ProtocolError, 'release requires'):
            candidate.verify(c['manifest'], [str(newest)], release=True)
        # Build and execute the exact candidate source, then bind all three decisions.
        release_checks = [dict(checks[0], scope='release-1', build_required=True)]
        released = candidate.create(f.project, f.root, f.product, 'release-1', 'HEAD', components, release_checks)
        build = f.put(f.root / 'evidence/build/app.py', (f.project / 'src/app.py').read_text())
        from task_runtime import source_snapshot
        source_sha = source_snapshot(f.project, f.root, f.product)['content_sha256']
        proof = f.root / 'evidence/build/association.json'
        write_json(proof, {'source_sha256': source_sha, 'artifact_sha256': file_hash(build), 'artifact': str(build)})
        cmd_run(f.root, 'integration', [sys.executable, '-c', 'import runpy,sys;assert runpy.run_path(sys.argv[1])["x"]==2', str(build)],
                {'check_id':'integration','scope':'release-1','environment':'local','executor':'test',
                 'build':{'id':file_hash(build),'source_sha256':source_sha,'association':'verified',
                          'evidence':str(proof),'evidence_sha256':file_hash(proof)}})
        release_record = max((f.root/'evidence/runs').glob('integration-*.json'), key=lambda p:load(p)['finished'])
        approvals=[]
        for purpose in ('product','quality','operations'):
            approval=f.root/('release-'+purpose+'.json')
            write_json(approval, {'id':'release-'+purpose,'kind':'acceptance' if purpose=='product' else 'verification',
                'target':released['manifest'],'target_sha256':released['sha256'],'scope':str(f.root),
                'by':purpose+'-fixture-reviewer','authority':'synthetic protocol fixture decision',
                'quote':'The isolated fixture meets this review scope','at':now(),'status':'accepted','obligations':[]})
            approvals.append({'purpose':purpose,'path':str(approval)})
        outcome=candidate.verify(released['manifest'],[str(release_record)],approvals,release=True)
        self.assertEqual(outcome['claim'],'release-ready'); self.assertFalse(outcome['deployed'])
        f.put(f.project / 'src/future.py', 'unfinished = True\n')
        with self.assertRaises(ProtocolError): candidate.create(f.project, f.root, f.product, 'candidate-2', 'HEAD', components,
            [dict(checks[0], scope='candidate-2')])

    def test_candidate_pins_symlinks_and_lists_external_targets(self):
        import os
        f = self.repository()
        os.symlink('src/app.py', f.project / 'app-link'); os.symlink(str(f.home), f.project / 'outside-link')
        for args in [('add', '-A'), ('commit', '-qm', 'links')]: workspaces.git(f.project, *args)
        f.use_backend(); paths = f.sealed(); f.put(f.project / 'src/app.py', 'x = 2\n'); rec = f.run_check()
        for output in f.bindings['deliverable_paths']: f.put(f.root / output, 'Real unit check evidence\n')
        f.response([rec]); self.assertTrue(record(paths['manifest'], f.return_path)['execution_complete']); f.mark_done(paths)
        components = [{'root': str(f.root), 'task': f.task['id'], 'result_sha256': file_hash(paths['result'])}]
        checks = [{'id': 'integration', 'scope': 'links-1', 'environment': 'local', 'build_required': False}]
        c = candidate.create(f.project, f.root, f.product, 'links-1', 'HEAD', components, checks)
        self.assertEqual([x['path'] for x in load(c['manifest'])['external_links']], ['outside-link'])
        (f.project / 'app-link').unlink(); os.symlink('README.md', f.project / 'app-link')  # unrecorded link change
        with self.assertRaisesRegex(ProtocolError, 'unaccounted|not ready'):  # stale component or unrecorded change
            candidate.create(f.project, f.root, f.product, 'links-2', 'HEAD', components, [dict(checks[0], scope='links-2')])

    def test_data_job_resume_does_not_repeat_submission_or_claim_early_success(self):
        f = self.fixture()
        script = f.put(f.home / 'adapter.py', '''import json, pathlib, sys
p=pathlib.Path(sys.argv[2]); mode=sys.argv[1]
if mode=="start": p.write_text(str(int(p.read_text())+1) if p.exists() else "1")
print(json.dumps({"job_id":"job-1","status":"submitted" if mode=="start" else "succeeded","result_refs":[] if mode=="start" else ["dataset:D21"]}))
''')
        counter = f.home / 'submissions'
        plan = {'environment': 'fixture', 'dataset': 'D20', 'cwd': str(f.home), 'intent_quote': 'Backfill the isolated fixture',
                'start_argv': [sys.executable, str(script), 'start', str(counter), '{operation_id}'],
                'status_argv': [sys.executable, str(script), 'status', str(counter), '{job_id}']}
        ref = data_jobs.request(f.project, 'backfill-1', plan)
        self.assertEqual(data_jobs.start(ref)['status'], 'submitted')
        with self.assertRaisesRegex(ProtocolError, 'not completed'): data_jobs.completed(ref)
        self.assertTrue(data_jobs.start(ref)['reused']); self.assertEqual(counter.read_text(), '1')
        self.assertEqual(data_jobs.poll(ref)['status'], 'succeeded')
        self.assertEqual(data_jobs.completed(ref)['result_refs'], ['dataset:D21'])

    def test_expired_claim_requires_reconciliation_and_fences_old_worker(self):
        f = self.repository(); feature, req, bindings, claim = self.isolated(f, 'work-a')
        with patch('coordination.time.time', return_value=claim['expires'] + 1):
            with self.assertRaisesRegex(ProtocolError, 'expired'): coordination.check(f.project, claim['key'], claim['token'])
            with self.assertRaisesRegex(ProtocolError, 'already claimed'):
                coordination.claim(f.project, claim['key'], 'replacement', 'work-a', [{'id': 'db/a', 'mode': 'read'}])
            with self.assertRaisesRegex(ProtocolError, 'reconciliation'):
                coordination.release(f.project, claim['key'], claim['token'], 'not checked')
            coordination.release(f.project, claim['key'], claim['token'], 'confirmed no active process/job in fixture', reconciled=True)
            new = coordination.claim(f.project, claim['key'], 'replacement', 'work-a', [{'id': 'db/a', 'mode': 'read'}])
            self.assertGreater(new['token'], claim['token'])
            with self.assertRaisesRegex(ProtocolError, 'stale'): coordination.heartbeat(f.project, claim['key'], claim['token'])

    def test_unknown_launch_is_not_retried_and_can_be_looked_up(self):
        f = self.fixture()
        plan = {'environment': 'fixture', 'dataset': 'D1', 'cwd': str(f.home), 'intent_quote': 'Start exactly one fixture job',
                'start_argv': [sys.executable, '-c', 'print("not-json")', '{operation_id}'],
                'status_argv': [sys.executable, '-c', 'print("not-json")', '{job_id}'],
                'lookup_argv': [sys.executable, '-c', 'import json;print(json.dumps({"job_id":"recovered-1","status":"running","result_refs":[]}))', '{operation_id}']}
        ref = data_jobs.request(f.project, 'recover-job', plan)
        self.assertEqual(data_jobs.start(ref)['status'], 'unknown')
        self.assertTrue(data_jobs.start(ref)['reused'])
        self.assertEqual(data_jobs.reconcile(ref)['job_id'], 'recovered-1')
        with self.assertRaisesRegex(ProtocolError, 'not completed'): data_jobs.completed(ref)

    def test_task_cannot_complete_with_unfinished_required_job(self):
        f=self.fixture(); coordinator=f.home/'job-coordinator'
        response=lambda status,refs: 'import json;print(json.dumps('+repr({'job_id':'job-1','status':status,'result_refs':refs})+'))'
        plan={'environment':'fixture','dataset':'D20','cwd':str(f.home),'intent_quote':'Run the isolated fixture job',
              'start_argv':[sys.executable,'-c',response('running',[]),'{operation_id}'],
              'status_argv':[sys.executable,'-c',response('succeeded',['dataset:D21']),'{job_id}']}
        ref=data_jobs.request(coordinator,'required-job',plan); data_jobs.start(ref)
        f.bindings['required_jobs']=[ref]; paths=f.sealed(); result=f.finish_pm(paths)
        self.assertFalse(result['execution_complete']); self.assertTrue(any('job not completed' in e for e in result['errors']))
        data_jobs.poll(ref); paths=f.sealed(); result=f.finish_pm(paths)
        self.assertTrue(result['execution_complete'],result['errors'])
        self.assertTrue(any(c['id']=='external-job' and c['record']['job_id']=='job-1' for c in result['checks']))
        f.mark_done(paths); self.assertEqual(check_tasks(f.root)['tasks'][f.task['id']]['validity'],'current')

    def test_new_labels_produce_a_separate_model_evaluation(self):
        from evidence import cmd_run
        f=self.fixture(); f.task.update(role='miner',stage='implement',task='evaluate',gate_stage='implement'); f.save_state()
        f.req.update(role='miner',stage='implement',task='evaluate')
        data=f.put(f.home/'labels.csv','id,split,feature,label\n1,train,0,0\n2,train,1,1\n3,test,0,0\n4,test,1,1\n')
        plan=f.put(f.root/'evaluation-plan.md','Feature is binary and observed before label. Fixed IDs 1,2 train; 3,4 test. Identity baseline; report accuracy, no production claim.\n')
        acceptance=self.accept(f,plan)
        results=[]
        for number in (20,21):
            if number==21:
                data.write_text(data.read_text().replace('4,test,1,1','4,test,1,0'))
                previous=copy.deepcopy(f.task); f.task=copy.deepcopy(f.task)
                f.task.update(id='model-d21',status='todo'); f.task.pop('result',None); f.task.pop('result_sha256',None)
                f.state['selected_tasks']=[previous,f.task]; f.save_state(); f.bindings['task_id']=f.task['id']
            version=datasets.capture(f.root,'labels-d'+str(number),data,'binary feature as-of event; corrected label in D21','fixed IDs 1..4')
            frozen=datasets.validate(version['path'])['identity']['path']
            f.bindings.update(inputs={'question':str(f.brief),'dataset':version['path'],'evaluation_plan':str(plan)},
                deliverable_paths=['03-impl/mining-evaluate-evidence.md'],product_writes=[],decisions=[acceptance],
                required_checks=[{'id':'model','scope':'D'+str(number),'environment':'local','build_required':False}])
            paths=f.sealed()
            expected=1 if number==20 else .5
            code='import csv,sys;rows=list(csv.DictReader(open(sys.argv[1])));train=[r for r in rows if r["split"]=="train"];test=[r for r in rows if r["split"]=="test"];model={r["feature"]:r["label"] for r in train};accuracy=sum(model[r["feature"]]==r["label"] for r in test)/len(test);assert accuracy==float(sys.argv[2]);print(accuracy)'
            cmd_run(f.root,'model',[sys.executable,'-c',code,frozen,str(expected)],
                {'check_id':'model','scope':'D'+str(number),'environment':'local','executor':'test','build':None})
            rec=max((f.root/'evidence/runs').glob('model-*.json'),key=lambda p:load(p)['finished'])
            f.put(f.root/'03-impl/mining-evaluate-evidence.md',f'D{number}: held-out accuracy={expected}; fixed train/test IDs and feature definition; synthetic sample only.\n')
            f.response([str(rec)]); result=record(paths['manifest'],f.return_path)
            self.assertTrue(result['execution_complete'],result['errors']);f.mark_done(paths);results.append(paths['result'])
        old,new=map(load,results)
        self.assertNotEqual(old['declared_inputs']['dataset']['sha256'],new['declared_inputs']['dataset']['sha256'])
        from task_state import result_for
        historical,_=result_for(f.root,f.state['selected_tasks'][0])
        old_output=historical['objects'][str(f.root/'03-impl/mining-evaluate-evidence.md')]['object']
        self.assertIn('accuracy=1;',Path(old_output).read_text())

    def test_sqlite_schema_collection_backfill_and_analysis_use_stable_data(self):
        f = self.fixture(); source = f.home / 'prices.sqlite'
        with sqlite3.connect(source) as db:
            db.execute('CREATE TABLE price(id INTEGER PRIMARY KEY, amount INTEGER NOT NULL)')
            db.executemany('INSERT INTO price VALUES (?,?)', [(1, 100), (2, 200)])
        d20 = datasets.capture(f.root, 'prices-d20', source, 'amount in cents; one row per source item', '2026-09-01..2026-09-14')
        with sqlite3.connect(source) as db:
            db.execute("ALTER TABLE price ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD'")
            self.assertEqual(db.execute('SELECT sum(amount) FROM price').fetchone()[0], 300)  # old consumer still works
            db.execute("INSERT INTO price VALUES (3, 50, 'USD')")  # new collector
        f.task.update(role='analyst', stage='retro', task='analyze', gate_stage='retro'); f.save_state()
        f.req.update(role='analyst', stage='retro', task='analyze')
        f.bindings.update(inputs={'question': str(f.brief), 'dataset': d20['path'], 'definitions': str(f.decisions)},
                          deliverable_paths=['07-retro/analysis.md'], product_writes=[],
                          required_checks=[{'id':'analysis','scope':'D20','environment':'local','build_required':False}])
        paths = f.sealed()
        with sqlite3.connect(source) as db: db.execute('UPDATE price SET amount=250 WHERE id=2')  # ongoing backfill elsewhere
        frozen = datasets.validate(d20['path'])['identity']['path']
        from evidence import cmd_run
        cmd_run(f.root, 'analysis', [sys.executable, '-c',
            'import sqlite3,sys;db=sqlite3.connect("file:"+sys.argv[1]+"?mode=ro",uri=True);v=db.execute("SELECT sum(amount) FROM price").fetchone()[0];assert v==300;print(v)', frozen],
            {'check_id':'analysis','scope':'D20','environment':'local','executor':'test','build':None})
        rec = max((f.root/'evidence/runs').glob('analysis-*.json'), key=lambda p:load(p)['finished'])
        f.put(f.root / '07-retro/analysis.md', 'D20 observed total: 300 cents; excludes newer collection and backfill.\n')
        f.response([str(rec)]); result = record(paths['manifest'], f.return_path)
        self.assertTrue(result['execution_complete'], result['errors'])
        d21 = datasets.capture(f.root, 'prices-d21', source, 'amount in cents; currency explicit', '2026-09-01..2026-09-15')
        self.assertNotEqual(datasets.validate(d20['path'])['identity']['sha256'], datasets.validate(d21['path'])['identity']['sha256'])
        self.assertEqual(sqlite3.connect(frozen).execute('SELECT sum(amount) FROM price').fetchone()[0], 300)

    def test_native_recovery_cannot_erase_historical_result(self):
        f = self.fixture(); paths = f.sealed(); f.finish_pm(paths)
        bind_result(f.root, f.task['id'], paths['result'], file_hash(f.root/'state.yaml'))
        with self.assertRaisesRegex(ProtocolError, 'issued task'):
            other = copy.deepcopy(f.task); other['id'] = 'replacement'
            update(f.root, file_hash(f.root/'state.yaml'), {'selected_tasks':[other]})

    def test_cli_rejects_unknown_request_fields(self):
        f = self.fixture(); args = f.put(f.home/'request.json', json.dumps({'roots':[str(f.root)], 'silently_skip_errors':True}))
        run = subprocess.run([sys.executable, str(Path(__file__).parent/'workflow.py'), 'continuous', 'project-ready', '--request', str(args)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('unexpected keyword', run.stderr)

    def test_each_independent_contract_prepares_without_a_whole_delivery_lane(self):
        from workflow import resolve_task, load_registry
        cases = [('backend','implement','diagnose'), ('frontend','implement','diagnose'),
                 ('data-collector','collect','diagnose'), ('analyst','retro','analyze'),
                 ('data-warehouse-engineer','warehouse','audit'), ('data-warehouse-engineer','warehouse','backfill'),
                 ('miner','implement','explore'), ('miner','implement','experiment'), ('miner','implement','evaluate')]
        for role, stage, action in cases:
            with self.subTest(role=role, action=action):
                f = self.fixture(); contract = resolve_task(load_registry(), role, stage, action)
                f.task.update(role=role, stage=stage, task=action, gate_stage=stage); f.save_state()
                f.req.update(role=role, stage=stage, task=action)
                dataset = datasets.capture(f.root, 'd20', f.project/'src/app.py', 'synthetic fixture content', 'fixed window')
                inputs={}; decisions=[]
                for item in contract['inputs']:
                    if item['source'] == 'source_snapshot': continue
                    source = Path(dataset['path']) if item['id']=='dataset' else f.put(f.root/(item['id']+'.md'), 'Explicit accepted scope and relevant baseline\n')
                    inputs[item['id']] = str(source)
                    if item.get('requires_acceptance'): decisions.append(self.accept(f, source))
                outputs = [load_registry()['artifacts'][a]['paths'][0] for a in contract['required']]
                f.bindings.update(inputs=inputs, deliverable_paths=outputs, product_writes=[], decisions=decisions,
                    required_checks=[{'id':'probe','scope':action,'environment':'local','build_required':False}])
                draft = f.prepared()[1]
                self.assertFalse(draft['missing'], draft['missing'])
                if stage=='implement': self.assertIsNone(draft['prepared']['packet'].get('slice_integrator'))

    def test_diagnosis_confirms_failure_without_repair_or_full_prd(self):
        f = self.fixture(); f.task.update(role='backend',stage='implement',task='diagnose',gate_stage='implement'); f.save_state()
        f.req.update(role='backend',stage='implement',task='diagnose')
        f.bindings.update(inputs={'symptom':str(f.brief),'behavior_baseline':str(f.decisions)},
            deliverable_paths=['04-verify/diagnosis-backend.md'],product_writes=[],
            required_checks=[{'id':'reproduce','scope':'diagnose','environment':'local','build_required':False}])
        before = file_hash(f.project/'src/app.py'); paths = f.sealed()
        from evidence import cmd_run
        cmd_run(f.root,'reproduce',[sys.executable,'-c','import runpy,sys;v=runpy.run_path(sys.argv[1]);assert v["x"]==1;print("confirmed original symptom x=1, expected baseline x=2")',str(f.project/'src/app.py')],
            {'check_id':'reproduce','scope':'diagnose','environment':'local','executor':'test','build':None})
        rec = max((f.root/'evidence/runs').glob('reproduce-*.json'),key=lambda p:load(p)['finished'])
        f.put(f.root/'04-verify/diagnosis-backend.md','Mechanism: constant is 1. Reproduction confirmed; code remains unchanged. Repair is a separate task.\n')
        f.response([str(rec)]);result=record(paths['manifest'],f.return_path)
        self.assertTrue(result['execution_complete'],result['errors'])
        self.assertEqual(before,file_hash(f.project/'src/app.py'))

    def test_repair_writes_do_not_strand_the_diagnosis_it_consumed(self):
        from evidence import cmd_run
        f = self.fixture(); f.task.update(id='diag', role='backend', stage='implement', task='diagnose', gate_stage='implement')
        f.bindings.update(task_id='diag', inputs={'symptom': str(f.brief), 'behavior_baseline': str(f.decisions)},
                          deliverable_paths=['04-verify/diagnosis-backend.md'], product_writes=[],
                          required_checks=[{'id': 'reproduce', 'scope': 'diagnose', 'environment': 'local', 'build_required': False}])
        f.req.update(role='backend', stage='implement', task='diagnose'); f.save_state(); paths = f.sealed()
        cmd_run(f.root, 'reproduce', [sys.executable, '-c', 'print("x is 1")'],
                {'check_id': 'reproduce', 'scope': 'diagnose', 'environment': 'local', 'executor': 'test', 'build': None})
        rec = max((f.root / 'evidence/runs').glob('reproduce-*.json'), key=lambda p: load(p)['finished'])
        f.put(f.root / '04-verify/diagnosis-backend.md', 'Mechanism: constant is 1\n')
        f.response([str(rec)]); self.assertTrue(record(paths['manifest'], f.return_path)['execution_complete']); f.mark_done(paths)
        diag = copy.deepcopy(f.task)
        f.task = {k: v for k, v in diag.items() if k not in ('result', 'result_sha256')}
        f.task.update(status='todo', depends_on=[{'task': 'diag', 'requires': 'produced'}])
        f.state['selected_tasks'] = [diag, f.task]; f.bindings.pop('required_checks'); f.use_backend()
        paths = f.sealed(); f.put(f.project / 'src/app.py', 'x = 2\n'); rec = f.run_check()
        for output in f.bindings['deliverable_paths']: f.put(f.root / output, 'Repair and unit check evidence\n')
        f.response([rec]); self.assertTrue(record(paths['manifest'], f.return_path)['execution_complete']); f.mark_done(paths)
        report = check_tasks(f.root, closure=True, task_ids=['diag', 'backend-T-3'])
        self.assertEqual(report['tasks']['diag']['validity'], 'needs-revalidation')  # it still describes x = 1
        self.assertEqual(report['tasks']['diag']['source_drift_from'], ['backend-T-3'])
        self.assertFalse([e for e in report['errors'] if 'diag' in e], report['errors'])
        f.put(f.project / 'src/app.py', 'x = 3\n')  # an unrecorded edit is not explained by any result
        report = check_tasks(f.root, closure=True, task_ids=['diag', 'backend-T-3'])
        self.assertNotIn('source_drift_from', report['tasks']['diag'])
        self.assertTrue(any('diag' in e for e in report['errors']))

    def test_two_workers_record_and_import_at_the_same_time(self):
        from task_runtime import seal
        f = self.repository()
        other = copy.deepcopy(f.task); other['id'] = 'pm-next'
        f.state['selected_tasks'].append(other); f.save_state()
        workers = [self.isolated(f, 'work-a'), self.isolated(f, 'work-b', 'pm-next')]
        runs = []
        for feature, req, bindings, claim in workers:
            draft = feature / 'draft-parallel.json'; value = prepare(req, bindings, draft)
            self.assertFalse(value['missing'], value['missing']); runs.append(seal(draft))
        f.response()
        for feature, *_ in workers: f.put(feature / '01-define/spec.md', 'Independent proposal from ' + feature.parent.parent.name + '\n')
        # Two OS processes collect their own workspace results concurrently.
        cli = [sys.executable, str(Path(__file__).with_name('workflow.py')), 'record', '--return', str(f.return_path), '--run']
        procs = [subprocess.Popen(cli + [run['manifest']], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for run in runs]
        for proc in procs:
            out, err = proc.communicate(timeout=120); self.assertEqual(proc.returncode, 0, err)
        for run in runs: self.assertTrue(load(run['result'])['execution_complete'], load(run['result'])['errors'])
        # Both imports race on the same canonical state digest: CAS lets one win; the loser retries.
        expected = file_hash(f.root / 'state.yaml')
        def publish(index):
            (_, _, bindings, claim), run = workers[index], runs[index]
            task = bindings['task_id']; state = expected; conflicts = 0
            for _ in range(5):
                try:
                    workspaces.import_result(f.project, claim['workspace'], task, run['result'], claim['token'], state)
                    return conflicts
                except ProtocolError as e:
                    self.assertIn('conflict', str(e)); conflicts += 1; state = file_hash(f.root / 'state.yaml')
            raise AssertionError('import never succeeded')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            conflicts = list(pool.map(publish, (0, 1)))
        self.assertGreaterEqual(sum(conflicts), 1)
        tasks = check_tasks(f.root)['tasks']
        self.assertEqual((tasks[f.task['id']]['validity'], tasks['pm-next']['validity']), ('current', 'current'))

    def test_unrelated_method_update_keeps_result_current(self):
        from task_runtime import method_closure, ROOT
        from task_state import result_for, current_validity
        f = self.fixture(); base = f.home / 'plugin-copy'
        for folder in ('agents', 'adapters', 'skills', 'scripts', 'workflow', 'vendor'):  # vendor/ is installed, not tracked
            if (ROOT / folder).is_dir():
                shutil.copytree(ROOT / folder, base / folder, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        methods = {'primary': 'prd-gwt', 'allowed': [], 'debug': False}
        before = method_closure('pm', methods, base=base)
        self.assertTrue(before['complete'], before['gaps'])
        unrelated = base / 'skills/warehouse/SKILL.md'; unrelated.write_text(unrelated.read_text() + '\nUnrelated note.\n')
        self.assertEqual(method_closure('pm', methods, base=base)['sha256'], before['sha256'])
        own = base / 'skills/prd-gwt/SKILL.md'; own.write_text(own.read_text() + '\nChanged method.\n')
        self.assertNotEqual(method_closure('pm', methods, base=base)['sha256'], before['sha256'])
        own.write_text(own.read_text() + '\nSee [outside notes](../../../outside.md).\n')
        self.assertFalse(method_closure('pm', methods, base=base)['complete'])
        # Validity: another plugin change leaves the task current only while its own closure is unchanged.
        paths = f.sealed(); f.finish_pm(paths); f.mark_done(paths)
        with patch('task_runtime.plugin_digest', return_value='0' * 64):
            self.assertEqual(check_tasks(f.root)['tasks'][f.task['id']]['validity'], 'current')
            with patch('task_runtime.method_closure', return_value={'sha256': '1' * 64}):
                self.assertEqual(check_tasks(f.root)['tasks'][f.task['id']]['validity'], 'needs-revalidation')
            result, manifest = result_for(f.root, f.state['selected_tasks'][0])
            manifest['prepared'].pop('method_closure')  # runs recorded before closures keep the whole-plugin rule
            self.assertEqual(current_validity(f.root, f.state['selected_tasks'][0], result, manifest)[0], 'needs-revalidation')

    def test_impact_finds_consumer_without_declared_edge(self):
        producer = self.fixture(); paths = producer.sealed(); producer.finish_pm(paths); producer.mark_done(paths)
        consumer = self.fixture()
        consumer.bindings['inputs']['briefing'] = str(producer.root / '01-define/spec.md')  # read, but no dependency declared
        consumer_paths = consumer.sealed(); consumer.finish_pm(consumer_paths); consumer.mark_done(consumer_paths)
        bystander = self.fixture(); bpaths = bystander.sealed(); bystander.finish_pm(bpaths); bystander.mark_done(bpaths)
        roots = [producer.root, consumer.root, bystander.root]
        changed = node_id(producer.root, producer.task['id']); found = node_id(consumer.root, consumer.task['id'])
        report = readiness(roots, changed)
        self.assertEqual(report['undeclared_consumers'], [found]); self.assertIn(found, report['affected'])
        self.assertNotIn(node_id(bystander.root, bystander.task['id']), report['affected'])
        self.assertFalse(report['impact_complete'])
        # A result that cannot be read is an explicit boundary, never "no impact".
        Path(bpaths['result']).write_text('{}')
        report = readiness(roots, changed)
        self.assertEqual(report['unverified_consumers'], [node_id(bystander.root, bystander.task['id'])])
        self.assertFalse(report['impact_complete'])

    def test_claim_from_another_machine_is_rejected(self):
        f = self.repository(); feature, req, bindings, claim = self.isolated(f, 'work-a')
        with patch('coordination.host_id', return_value='another-host'):
            for call in (lambda: coordination.check(f.project, claim['key'], claim['token']),
                         lambda: coordination.heartbeat(f.project, claim['key'], claim['token']),
                         lambda: coordination.release(f.project, claim['key'], claim['token'], 'done')):
                with self.assertRaisesRegex(ProtocolError, 'another machine'): call()
        self.assertEqual(coordination.check(f.project, claim['key'], claim['token'])['host'], coordination.host_id())


if __name__ == '__main__': unittest.main()
