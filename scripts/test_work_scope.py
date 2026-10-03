#!/usr/bin/env python3
"""Scoped requests exercise real sealed runs, version changes and completion boundaries."""
import copy
import subprocess
import sys
import unittest
from pathlib import Path

import test_task_runtime as fixtures
from runtime_protocol import ProtocolError, file_hash, load, now, write_json
from task_runtime import prepare, seal, record
from task_state import check_tasks, validate_graph
from work_scope import check_work, complete_work, impact
from workflow import ROOT, resolve_task, load_registry


class WorkTests(unittest.TestCase):
    put = fixtures.RuntimeTests.put
    save_state = fixtures.RuntimeTests.save_state
    prepared = fixtures.RuntimeTests.prepared
    sealed = fixtures.RuntimeTests.sealed
    response = fixtures.RuntimeTests.response
    finish_pm = fixtures.RuntimeTests.finish_pm
    mark_done = fixtures.RuntimeTests.mark_done
    run_check = fixtures.RuntimeTests.run_check

    def setUp(self):
        fixtures.RuntimeTests.setUp(self)
        self.work = {'id': 'requirements-r2', 'kind': 'refine', 'intent_quote': 'Clarify export permissions only',
                     'scope': 'export permissions', 'target': 'requirements handoff',
                     'tasks': [{'task': 'pm-spec', 'requires': 'produced'}], 'continuation': 'stop', 'status': 'active'}
        self.task['work_id'] = self.work['id']
        self.state.update(work_items=[self.work], active_work=self.work['id'])
        self.state['required_capabilities'].append('work-scope-v1')
        self.save_state()

    def finish(self):
        paths = self.sealed(); result = self.finish_pm(paths)
        self.assertTrue(result['execution_complete'], result['errors']); self.mark_done(paths)
        return paths

    def decision(self, target, kind='acceptance', result=None):
        p = self.root / ('decision-' + str(len(list(self.root.glob('decision-*')))) + '.json')
        d = {'id': 'A-1', 'kind': kind, 'target': str(target), 'target_sha256': file_hash(target),
             'scope': str(self.root), 'by': 'user', 'authority': 'explicit task scope decision',
             'quote': 'Use this baseline', 'at': now(), 'status': 'accepted', 'obligations': []}
        if result: d['result_sha256'] = file_hash(result)
        write_json(p, d); return str(p)

    def switch(self, role, stage, task, inputs, outputs, **bindings):
        self.task.update(role=role, stage=stage, task=task,
                         gate_stage=resolve_task(load_registry(), role, stage, task)['gate_stages'][0])
        self.req.update(role=role, stage=stage, task=task)
        self.bindings.update(inputs=inputs, deliverable_paths=outputs, product_writes=[], **bindings)
        self.save_state()

    def test_requirements_handoff_without_app_or_feature_closure(self):
        self.finish()
        self.assertFalse(check_work(self.root, self.work['id'])['errors'])
        self.assertTrue(check_tasks(self.root, closure=True)['errors'])
        before = (self.root / 'state.yaml').read_bytes()
        result = complete_work(self.root, self.work['id'], self.root / 'work/2026-09-28-requirements.json')
        self.assertFalse(result['feature_complete'])
        self.assertEqual(before, (self.root / 'state.yaml').read_bytes())
        self.work.update({k: result[k] for k in ('result', 'result_sha256', 'status')})
        self.state.pop('active_work'); self.save_state()
        self.assertFalse(check_work(self.root, self.work['id'])['errors'])
        with self.assertRaisesRegex(ProtocolError, 'already completed'):
            complete_work(self.root, self.work['id'], self.root / 'work/duplicate.json')

    def test_accepted_target_cannot_end_at_production(self):
        self.work['tasks'][0]['requires'] = 'accepted'; self.save_state(); paths = self.finish()
        self.assertTrue(check_work(self.root, self.work['id'])['errors'])
        self.task['acceptance'] = self.decision(self.root / '01-define/spec.md', result=paths['result']); self.save_state()
        self.assertFalse(check_work(self.root, self.work['id'])['errors'])
        self.put(self.root / '01-define/spec.md', 'Changed rule after approval\n')
        self.assertTrue(check_work(self.root, self.work['id'])['errors'])

    def test_historical_work_completion_survives_current_revalidation_need(self):
        self.finish()
        result = complete_work(self.root, self.work['id'], self.root / 'work/complete.json')
        self.work.update({k: result[k] for k in ('result', 'result_sha256', 'status')})
        self.state.pop('active_work'); self.save_state()
        self.put(self.root / '01-define/spec.md', 'A later requirement revision\n')
        report = check_work(self.root, self.work['id'])
        self.assertTrue(report['historical_completion'])
        self.assertTrue(report['errors'])
        self.assertEqual(file_hash(self.root / result['result']), result['result_sha256'])

    def test_work_scope_cannot_change_after_dispatch(self):
        self.finish(); self.work['scope'] = 'All export features'; self.save_state()
        self.assertTrue(check_work(self.root, self.work['id'])['errors'])

    def test_uncertainty_is_optional_and_enumerated(self):
        self.work['uncertainty'] = 'bounded'; self.save_state(); self.finish()
        self.assertFalse(check_work(self.root, self.work['id'])['errors'])
        from work_scope import validate_work_items
        bad = copy.deepcopy(self.state); bad['work_items'][0]['uncertainty'] = 'huge'
        with self.assertRaises(ProtocolError):
            validate_work_items(bad, {t['id']: t for t in bad['selected_tasks']})

    def test_later_request_does_not_rewrite_old_task_intent(self):
        self.finish(); self.state['intent'] = {'class': 'fix', 'quote': 'A later unrelated request'}; self.save_state()
        self.assertEqual(check_tasks(self.root)['tasks']['pm-spec']['validity'], 'current')

    def test_unrelated_invalid_task_does_not_block_scoped_handoff(self):
        self.finish()
        other = copy.deepcopy(self.task); other.update(id='unrelated', result='missing.json'); other.pop('work_id')
        self.state['selected_tasks'].append(other); self.save_state()
        self.assertFalse(check_work(self.root, self.work['id'])['errors'])
        self.assertTrue(check_tasks(self.root, closure=True)['errors'])

    def test_unresolved_dependency_blocks_only_consumers(self):
        paths = self.sealed()
        self.finish_pm(paths, [{'id': 'Q-1', 'owner': 'pm', 'blocks': ['pm-spec'], 'item': 'Unknown permission', 'severity': 'major'}])
        self.mark_done(paths)
        self.assertTrue(any('Q-1' in e for e in check_work(self.root, self.work['id'])['errors']))

    def test_normal_iteration_does_not_require_technical_debug(self):
        self.state['rework_rounds'] = 8
        self.task.update(attempt_kind='iteration', rework_rounds=0); self.save_state()
        _, draft = self.prepared(); self.assertFalse(draft['prepared']['methods']['debug'])
        self.task.update(attempt_kind='rework', rework_rounds=2); self.save_state()
        with self.assertRaisesRegex(ProtocolError, 'requires debug'): self.prepared()

    def test_graph_impact_includes_previously_passed_acceptance(self):
        self.finish()
        t = copy.deepcopy(self.task); t.update(id='qa-old', role='qa', stage='verify', task='risk-based-tests', gate_stage='verify',
                                             depends_on=[{'task': 'pm-spec', 'requires': 'accepted'}]); t.pop('work_id')
        a = copy.deepcopy(t); a.update(id='pm-accepted', role='pm', stage='accept', task='walkthrough', gate_stage='accept',
                                      depends_on=[{'task': 'qa-old', 'requires': 'verified'}])
        self.state['selected_tasks'] += [t, a]; self.save_state()
        self.assertEqual(impact(self.root, 'pm-spec')['affected_tasks'], ['pm-accepted', 'pm-spec', 'qa-old'])

    def test_work_files_cannot_be_worker_outputs(self):
        self.bindings['deliverable_paths'].append('work/fake-completion.json')
        with self.assertRaisesRegex(ProtocolError, 'manager-only'): self.prepared()

    def test_scope_requires_capability_and_fix_origin(self):
        self.work['kind'] = 'fix'; self.save_state()
        with self.assertRaisesRegex(ProtocolError, 'origin'): validate_graph(self.state)
        self.work['origin'] = 'BUG-1, release abc'; self.state['required_capabilities'].remove('work-scope-v1')
        with self.assertRaisesRegex(ProtocolError, 'work-scope'): validate_graph(self.state)

    def test_collector_source_needs_no_ui_tracking_or_schema(self):
        need = self.put(self.root / 'data-need.md', 'Fetch public product prices daily\n')
        constraints = self.put(self.root / 'source.md', 'Source API, field list and update constraints\n')
        self.switch('data-collector', 'collect', 'source', {'data_need': str(need), 'source_constraints': str(constraints)},
                    ['02-shape/collect/data-source-analysis.md'])
        paths = self.sealed()
        self.put(self.root / '02-shape/collect/data-source-analysis.md', 'Source fields and freshness assessed; next: implementation\n')
        self.response(); result = record(paths['manifest'], self.return_path)
        self.assertTrue(result['execution_complete'], result['errors']); self.mark_done(paths)
        self.assertFalse(check_work(self.root, self.work['id'])['errors'])

    def test_designer_exploration_uses_accepted_spec_without_architecture(self):
        spec = self.put(self.root / '01-define/spec.md', 'Accepted FR-1 behavior\n')
        design = self.put(self.root / 'design-context.md', 'Reuse existing direction and tokens\n')
        self.switch('designer', 'designer', 'explore', {'design_context': str(design)},
                    ['02-shape/design-brief.md', '02-shape/design-directions.md', '02-shape/prototypes/D1/index.html'],
                    decisions=[self.decision(spec)])
        _, draft = self.prepared()
        self.assertEqual(draft['missing'], [])
        self.assertEqual(draft['prepared']['packet']['evidence_required'], ['screenshots'])

    def test_schema_cannot_prepare_without_accepted_contract(self):
        baseline = self.put(self.root / 'baseline.md', 'Existing schema\n')
        self.switch('dba', 'dba', 'model', {'baseline': str(baseline)}, ['02-shape/db-spec.md', '02-shape/schema.dbml'])
        _, draft = self.prepared()
        self.assertTrue(any('accepted_contract' in e for e in draft['missing']))

    def test_security_architecture_requires_and_can_bind_the_diagram(self):
        spec = self.put(self.root / '01-define/spec.md', 'FR-1 restricted tenant export\n')
        baseline = self.put(self.root / 'baseline.md', 'Tenant boundaries and current modules\n')
        self.state['q_security'] = True
        self.switch('architect', 'shape', 'contract', {'baseline': str(baseline)},
                    ['02-shape/contract.md'], decisions=[self.decision(spec)])
        self.assertTrue(any('VISUALS' in e for e in self.prepared()[1]['missing']))
        self.bindings.update(visuals=['trust-boundary'])
        self.bindings['deliverable_paths'].append('02-shape/assets/trust.svg')
        draft = self.prepared()[1]
        self.assertFalse(draft['missing'], draft['missing'])
        self.assertTrue(any('diagram/lint.py' in cmd for cmd in draft['prepared']['packet']['success_checks']))

    def test_warehouse_design_does_not_require_metrics_or_tags(self):
        need = self.put(self.root / 'data-need.md', 'Daily serving dataset\n')
        source = self.put(self.root / 'sources.md', 'Accepted source schema\n')
        self.switch('data-warehouse-engineer', 'warehouse', 'design', {'data_need': str(need), 'source_contracts': str(source)},
                    ['02-shape/warehouse/design.md'], decisions=[self.decision(need), self.decision(source)])
        self.assertFalse(self.prepared()[1]['missing'])

    def test_backend_fix_uses_accepted_baseline_without_full_prd(self):
        self.work.update(kind='fix', origin='BUG-7 on release abc', target='repair verified')
        defect = self.put(self.root / 'BUG-7.md', 'Reproduce export at exact limit; expected success\n')
        baseline = self.put(self.root / 'baseline.md', 'Accepted API limit and stored behavior\n')
        self.switch('backend', 'implement', 'fix', {'defect': str(defect), 'accepted_behavior': str(baseline),
                    'accepted_contract': str(baseline), 'implementation_context': str(baseline)},
                    ['03-impl/fix-backend-evidence.md', '03-impl/fix-integration.md'], source_writes=['src/'],
                    slice_integrator='backend', decisions=[self.decision(baseline)],
                    required_checks=[{'id': 'unit', 'scope': 'T-3', 'environment': 'local', 'build_required': False}])
        paths = self.sealed(); self.put(self.project / 'src/app.py', 'x = 2\n'); rec = self.run_check()
        for path in self.bindings['deliverable_paths']: self.put(self.root / path, 'Reproduction and regression passed\n')
        self.response([rec]); result = record(paths['manifest'], self.return_path)
        self.assertTrue(result['execution_complete'], result['errors'])
        self.assertFalse((self.root / '01-define/spec.md').exists())

    def test_added_revalidation_supersedes_result_without_erasing_history(self):
        paths = self.finish()
        old = self.task
        successor = copy.deepcopy(old); successor.update(id='pm-spec-r3', status='todo', attempt_kind='revalidation')
        for key in ('result', 'result_sha256'): successor.pop(key)
        old.update(status='superseded', successor=successor['id'])
        self.work['tasks'].append({'task': successor['id'], 'requires': 'produced'})
        self.state['selected_tasks'].append(successor); self.task = successor
        self.bindings['task_id'] = successor['id']; self.save_state()
        self.finish()
        self.assertTrue(Path(paths['result']).exists())
        self.assertFalse(check_work(self.root, self.work['id'])['errors'])

    def test_superseding_a_task_cannot_erase_its_open_obligation(self):
        paths = self.sealed()
        self.finish_pm(paths, [{'id': 'Q-1', 'owner': 'pm', 'blocks': ['pm-spec'], 'item': 'Unresolved permission', 'severity': 'major'}])
        self.mark_done(paths)
        successor = copy.deepcopy(self.task); successor.update(id='pm-r3', status='todo')
        for key in ('result', 'result_sha256'): successor.pop(key)
        self.task.update(status='superseded', successor='pm-r3')
        self.work['tasks'].append({'task': 'pm-r3', 'requires': 'produced'})
        self.state['selected_tasks'].append(successor); self.task = successor
        self.bindings['task_id'] = 'pm-r3'; self.save_state(); self.finish()
        self.assertTrue(any('Q-1' in e for e in check_work(self.root, self.work['id'])['errors']))

    def test_shell_work_gate_is_distinct_from_feature_gate(self):
        self.finish()
        cmd = ['bash', str(ROOT / 'scripts/check-sdlc.sh'), '--work', self.work['id'], str(self.root)]
        run = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn('scoped-task-completion', run.stdout)
        self.assertEqual(subprocess.run(cmd + ['--hat', 'define'], capture_output=True).returncode, 64)

    def test_third_rework_requires_owner_escalation(self):
        self.task.update(attempt_kind='rework', rework_rounds=3); self.save_state()
        self.bindings.update(allowed_companion_skills=['debug'], required_companion_skills=['debug'])
        _, draft = self.prepared()
        self.assertTrue(any(e.startswith('REWORK: round 3') for e in draft['missing']), draft['missing'])
        route = self.put(self.root / '04-verify/escalation-FR-1.md',
                         'Diagnosis: FR-1 mixes export and permission rules. Route: reslice into two tickets.\n')
        by_producer = self.decision(route, kind='escalation')
        record = load(by_producer); record['by'] = 'pm'; write_json(Path(by_producer), record, exclusive=False)
        self.bindings['decisions'] = [by_producer]
        _, draft = self.prepared()
        self.assertTrue(any(e.startswith('REWORK') for e in draft['missing']), 'the producer cannot escalate its own rework')
        self.bindings['decisions'] = [self.decision(route, kind='escalation')]
        _, draft = self.prepared()
        self.assertFalse([e for e in draft['missing'] if e.startswith('REWORK')], draft['missing'])
        self.task.update(attempt_kind='iteration', rework_rounds=5); self.save_state()
        self.bindings.update(decisions=[], allowed_companion_skills=[], required_companion_skills=[])
        _, draft = self.prepared(); self.assertFalse([e for e in draft['missing'] if e.startswith('REWORK')])

    def test_schema_design_completion_is_not_a_migration(self):
        spec = self.put(self.root / '01-define/spec.md', 'FR-1: an order keeps an integer amount_cents; zero is valid\n')
        contract = self.put(self.root / '02-shape/contract.md', 'GET /orders returns amount_cents (integer)\n')
        baseline = self.put(self.root / 'baseline.md', 'CREATE TABLE orders(id INTEGER PRIMARY KEY);\n')
        self.switch('dba', 'dba', 'model', {'baseline': str(baseline)}, ['02-shape/db-spec.md', '02-shape/schema.dbml'],
                    decisions=[self.decision(spec), self.decision(contract)])
        source_before = file_hash(self.project / 'src/app.py')
        paths = self.sealed()
        self.put(self.root / '02-shape/db-spec.md', 'Add orders.amount_cents INTEGER NOT NULL DEFAULT 0; expand-only.\n')
        self.put(self.root / '02-shape/schema.dbml', 'Table orders {\n  id integer [pk]\n  amount_cents integer [not null, default: 0]\n}\n')
        self.response(); result = record(paths['manifest'], self.return_path)
        self.assertTrue(result['execution_complete'], result['errors']); self.mark_done(paths)
        self.assertFalse(check_work(self.root, self.work['id'])['errors'])
        self.assertEqual(source_before, file_hash(self.project / 'src/app.py'))
        done = complete_work(self.root, self.work['id'], self.root / 'work/schema-design.json')
        self.assertFalse(done['feature_complete'])
        # The migration is its own source-writing task; the design output needs an explicit approval first.
        migration = {**self.task, 'id': 'dba-migration', 'task': 'migration', 'status': 'todo', 'depends_on': [{'task': 'pm-spec', 'requires': 'produced'}]}
        for key in ('result', 'result_sha256', 'work_id'): migration.pop(key, None)
        self.state['selected_tasks'].append(migration); self.save_state()
        self.assertTrue(resolve_task(load_registry(), 'dba', 'dba', 'migration').get('writes_source'))
        self.req.update(task='migration')
        scope = self.put(self.root / '02-shape/migration-scope.md', 'Expand orders with amount_cents only\n')
        self.bindings.update(task_id='dba-migration', decisions=[], source_writes=['migrations/'],
                             inputs={'approved_schema': str(self.root / '02-shape/schema.dbml'), 'migration_scope': str(scope)},
                             deliverable_paths=['02-shape/migration-review.md'])
        _, draft = self.prepared()
        self.assertTrue(any('approved_schema' in e for e in draft['missing']), draft['missing'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
