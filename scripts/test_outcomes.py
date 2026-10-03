#!/usr/bin/env python3
"""outcomes.py: closed features leave a result record; bets come due; escapes and readouts feed the statistics."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'outcomes.py'

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
        self.assertEqual(s['bets_by_grade'], {'E1': {'supported': 1, 'refuted': 0, 'inconclusive': 0, 'open': 0}})

    def test_check_sdlc_stats_delegates(self):
        self.run_outcomes('record', '--feature', str(self.tmp / '.sdlc' / 'export'))
        p = subprocess.run(['bash', str(ROOT / 'scripts' / 'check-sdlc.sh'), '--stats', str(self.tmp / '.sdlc')],
                           text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('泳道分布', p.stdout)
        self.assertIn('赌注', p.stdout)


if __name__ == '__main__':
    unittest.main()
