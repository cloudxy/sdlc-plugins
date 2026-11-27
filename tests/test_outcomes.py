#!/usr/bin/env python3
"""outcomes.py: closed features leave a result record; bets come due; escapes and readouts feed the statistics."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1] / 'scripts')  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'gates' / 'outcomes.py'

EXPORT_STATE = """feature: export   # 功能名
sdlc_version: 4
lane: L2              # L0-L4
delivery_goal: release_ready
phase: Closed
current_hat: review
hats_done: [define, shape, implement, verify, accept, review]
rework_rounds: 1
bet:
  hypothesis: H-2
  metric: weekly_export_tenants
  evidence_grade: E1
  readout_due: 2026-09-25
gates:
  - {name: fresh-context, kind: fresh-context, stage: define, result: pass, findings_total: 3}
  - name: fresh-context
    kind: fresh-context
    stage: review
    result: pass
    findings_total: 2
"""

FIX_STATE = """feature: fix-export-safari
sdlc_version: 4
lane: L1
phase: Closed
current_hat: review
hats_done: [implement, review]
escape:
  origin_feature: export
  should_have_caught_at: verify
  gate: E2E
  defect_class: code
"""


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='outcomes test.'))  # a space in the path on purpose
        (self.tmp / 'sdlc.config.yaml').write_text('product_root: docs/product\n')
        for name, text in (('export', EXPORT_STATE), ('fix-export-safari', FIX_STATE)):
            d = self.tmp / '.sdlc' / name
            d.mkdir(parents=True)
            (d / 'state.yaml').write_text(text, encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_outcomes(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True)

    def test_record_from_closed_state(self):
        p = self.run_outcomes('record', '--feature', str(self.tmp / '.sdlc' / 'export'))
        self.assertEqual(p.returncode, 0, p.stderr)
        rec = json.loads((self.tmp / '.sdlc' / '_outcomes' / 'export.json').read_text())
        self.assertEqual(rec['lane'], 'L2')
        self.assertEqual(rec['rework_rounds'], 1)
        self.assertEqual(rec['intercepts'], 5)
        self.assertEqual(rec['bet'], {'hypothesis': 'H-2', 'metric': 'weekly_export_tenants',
                                      'evidence_grade': 'E1', 'readout_due': '2026-09-25'})
        self.assertIsNone(rec['readout'])
        index = json.loads((self.tmp / '.sdlc' / '_outcomes' / 'index.json').read_text())
        self.assertEqual(index['bets'][0]['feature'], 'export')

    def test_open_feature_is_not_recorded(self):
        state = self.tmp / '.sdlc' / 'export' / 'state.yaml'
        state.write_text(EXPORT_STATE.replace('phase: Closed', 'phase: HatReady'), encoding='utf-8')
        p = self.run_outcomes('record', '--feature', str(state.parent))
        self.assertEqual(p.returncode, 2)

    def test_due_lists_overdue_bets(self):
        self.run_outcomes('record', '--feature', str(self.tmp / '.sdlc' / 'export'))
        p = self.run_outcomes('due', '--project-root', str(self.tmp), '--today', '2026-10-02')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('export', p.stdout)
        self.assertIn('H-2', p.stdout)
        p = self.run_outcomes('due', '--project-root', str(self.tmp), '--today', '2026-09-20')
        self.assertEqual(p.stdout.strip(), '')

    def test_readout_closes_the_bet(self):
        self.run_outcomes('record', '--feature', str(self.tmp / '.sdlc' / 'export'))
        p = self.run_outcomes('readout', '--project-root', str(self.tmp), '--feature', 'export',
                              '--status', 'refuted', '--evidence', '07-retro/retro.md')
        self.assertEqual(p.returncode, 0, p.stderr)
        p = self.run_outcomes('due', '--project-root', str(self.tmp), '--today', '2026-10-02')
        self.assertEqual(p.stdout.strip(), '')
        # recording the feature again keeps the readout
        self.run_outcomes('record', '--feature', str(self.tmp / '.sdlc' / 'export'))
        rec = json.loads((self.tmp / '.sdlc' / '_outcomes' / 'export.json').read_text())
        self.assertEqual(rec['readout']['status'], 'refuted')

    def test_stats_hit_rate_by_grade_and_escapes(self):
        for name in ('export', 'fix-export-safari'):
            self.run_outcomes('record', '--feature', str(self.tmp / '.sdlc' / name))
        self.run_outcomes('readout', '--project-root', str(self.tmp), '--feature', 'export',
                          '--status', 'supported', '--evidence', 'r.md')
        p = self.run_outcomes('stats', '--root', str(self.tmp / '.sdlc'), '--json')
        self.assertEqual(p.returncode, 0, p.stderr)
        s = json.loads(p.stdout)
        self.assertEqual(s['lanes'], {'L1': 1, 'L2': 1})
        self.assertEqual(s['intercepts'], 5)
        self.assertEqual(s['escapes_by_gate'], {'E2E': 1})
        self.assertEqual(s['escapes_by_stage'], {'verify': 1})
        self.assertEqual(s['escapes_seam_closed'], 0)
        self.assertEqual(s['escapes_seam_open'], 1)
        self.assertEqual(s['bets_by_grade'], {'E1': {'supported': 1, 'refuted': 0, 'inconclusive': 0, 'open': 0}})

    def test_process_qa_seam_closure_counted_in_stats(self):
        d = self.tmp / '.sdlc' / 'fix-contract-drift'
        d.mkdir(parents=True)
        (d / 'state.yaml').write_text(
            FIX_STATE.replace('fix-export-safari', 'fix-contract-drift')
            + '  seam_fix: "Added check-contract.py CI gate on /api/v1/exports"\n'
            + '  verified_by: "qa TC-R012 + check-contract.py exit 0"\n',
            encoding='utf-8',
        )
        self.run_outcomes('record', '--feature', str(d))
        p = self.run_outcomes('stats', '--root', str(self.tmp / '.sdlc'), '--json')
        self.assertEqual(p.returncode, 0, p.stderr)
        s = json.loads(p.stdout)
        self.assertEqual(s['escapes_seam_closed'], 1)

    def test_check_sdlc_stats_delegates(self):
        self.run_outcomes('record', '--feature', str(self.tmp / '.sdlc' / 'export'))
        p = subprocess.run(['bash', str(ROOT / 'scripts' / 'check-sdlc.sh'), '--stats', str(self.tmp / '.sdlc')],
                           text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('泳道分布', p.stdout)
        self.assertIn('赌注', p.stdout)

    def test_record_run_lightweight_and_missing_metrics_reporting(self):
        # Write a legacy _outcomes record with NO efficiency key to guarantee backward compatibility
        legacy_dir = self.tmp / '.sdlc' / '_outcomes'
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / 'legacy-feature.json').write_text(json.dumps({
            'feature': 'legacy-feature',
            'lane': 'L2',
            'phase': 'Closed',
            'hats_done': ['define', 'implement'],
            'rework_rounds': 0,
            'intercepts': 1,
            'bet': None,
            'escape': None,
        }), encoding='utf-8')

        # Record a lightweight fast_track run without requiring state.yaml or phase: Closed
        digest_json = self.tmp / 'digest.json'
        digest_json.write_text(json.dumps({
            'wall_duration_min': 6.5,
            'spawns': 1,
            'model_calls': 8,
            'tool_calls': 12,
            'input_tokens': 45000,
            'output_tokens': 3200,
        }), encoding='utf-8')
        p = self.run_outcomes(
            'record-run', '--project-root', str(self.tmp),
            '--id', 'log-audit-01', '--track', 'fast_track',
            '--domain', 'log_analysis', '--role', 'sre',
            '--quality-status', 'pass', '--overhead-ratio', '0.18',
            '--session-digest', str(digest_json),
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        run_file = self.tmp / '.sdlc' / '_outcomes' / 'runs' / 'log-audit-01.json'
        self.assertTrue(run_file.is_file())
        run_rec = json.loads(run_file.read_text(encoding='utf-8'))
        self.assertEqual(run_rec['efficiency']['wall_duration_min'], 6.5)
        self.assertEqual(run_rec['efficiency']['spawn_count'], 1)
        self.assertEqual(run_rec['efficiency']['missing_metrics'], [])

        # stats must combine legacy closed record + lightweight run and explicitly report missing metrics
        ps = self.run_outcomes('stats', '--root', str(self.tmp / '.sdlc'), '--json')
        self.assertEqual(ps.returncode, 0, ps.stderr)
        s = json.loads(ps.stdout)
        eff = s['efficiency']
        self.assertEqual(eff['records_total'], 2)
        self.assertEqual(eff['closed_outcomes'], 1)
        self.assertEqual(eff['lightweight_runs'], 1)
        self.assertEqual(eff['tracks']['fast_track'], 1)
        self.assertEqual(eff['metrics']['wall_duration_min'], {'count': 1, 'missing': 1, 'mean': 6.5})
        self.assertTrue(any('缺测' in m for m in eff['missing_metrics']))

        # Text output must show efficiency section and missing metric note
        pt = self.run_outcomes('stats', '--root', str(self.tmp / '.sdlc'))
        self.assertEqual(pt.returncode, 0, pt.stderr)
        self.assertIn('效率度量', pt.stdout)
        self.assertIn('缺测', pt.stdout)


if __name__ == '__main__':
    unittest.main()
