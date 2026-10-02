#!/usr/bin/env python3
"""behavior_smoke.py with a fake `claude` on PATH: no model calls, no network."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'behavior_smoke.py'
FAKE = ROOT / 'scripts' / 'fixtures' / 'fake-claude.sh'


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='smoke-test.'))
        bin_dir = self.tmp / 'bin'
        bin_dir.mkdir()
        shutil.copy(FAKE, bin_dir / 'claude')
        os.chmod(bin_dir / 'claude', 0o755)
        self.env = dict(os.environ, PATH=f'{bin_dir}{os.pathsep}{os.environ["PATH"]}')
        self.out = self.tmp / 'out'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_smoke(self, *args, env=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True,
                              capture_output=True, env=env or self.env)

    def records(self, arm=None):
        base = self.out / arm if arm else self.out
        return sorted(p for p in base.rglob('*.json') if p.parent.name in ('current', 'baseline'))

    def test_reps_and_arms_produce_one_record_per_run(self):
        for arm in (['--arm', 'current'], ['--arm', 'baseline', '--baseline-ref', 'HEAD']):
            p = self.run_smoke('run', '--skill', 'sdlc', '--cases', '1,2', '--reps', '3', *arm,
                               '--out', str(self.out), '--budget-usd', '10')
            self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len(self.records('current')), 6)
        self.assertEqual(len(self.records('baseline')), 6)
        rec = json.loads(self.records('current')[0].read_text())
        for key in ('skill', 'case_id', 'arm', 'rep', 'tree_id', 'command', 'status', 'cost_usd', 'reply', 'fixtures'):
            self.assertIn(key, rec)
        self.assertEqual(rec['status'], 'ok')

    def test_budget_stops_before_exceeding(self):
        p = self.run_smoke('run', '--skill', 'sdlc', '--cases', '1', '--reps', '6', '--arm', 'current',
                           '--out', str(self.out), '--budget-usd', '1.0')
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        statuses = [json.loads(r.read_text())['status'] for r in self.records('current')]
        self.assertEqual(statuses.count('ok'), 4)
        self.assertEqual(statuses.count('budget_stop'), 1)

    def test_malformed_host_output_is_host_failure(self):
        env = dict(self.env, FAKE_MODE='malformed')
        p = self.run_smoke('run', '--skill', 'sdlc', '--cases', '1', '--reps', '1', '--arm', 'current',
                           '--out', str(self.out), '--budget-usd', '5', env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        rec = json.loads(self.records('current')[0].read_text())
        self.assertEqual(rec['status'], 'host_failure')
        # A host failure is retried on the next invocation and never counts as a scenario result.
        p = self.run_smoke('run', '--skill', 'sdlc', '--cases', '1', '--reps', '1', '--arm', 'current',
                           '--out', str(self.out), '--budget-usd', '5')
        self.assertEqual(json.loads(self.records('current')[-1].read_text())['status'], 'ok')

    def test_baseline_arm_only_sees_exported_tree(self):
        p = self.run_smoke('run', '--skill', 'sdlc', '--cases', '1', '--reps', '1', '--arm', 'baseline',
                           '--baseline-ref', 'HEAD', '--out', str(self.out), '--budget-usd', '5')
        self.assertEqual(p.returncode, 0, p.stderr)
        rec = json.loads(self.records('baseline')[0].read_text())
        joined = '\n'.join(rec['command'])
        self.assertNotIn(str(ROOT) + os.sep, joined)  # no argument points into the live repo
        self.assertFalse(any(arg == str(ROOT) or arg.startswith(str(ROOT) + os.sep) for arg in rec['command']))
        tree = Path(rec['tree_path'])
        self.assertTrue((tree / 'skills' / 'sdlc' / 'SKILL.md').is_file())
        self.assertNotIn('baseline', str(tree), 'tree paths stay neutral so the arm label cannot leak')
        self.assertNotIn('current', str(tree))

    def test_secret_like_values_are_redacted(self):
        env = dict(self.env, FAKE_REPLY='token sk-abcdefghijklmnopqrstuvwxyz and Bearer abcdefghijklmnopqrstuvwxyz0123')
        self.run_smoke('run', '--skill', 'sdlc', '--cases', '1', '--reps', '1', '--arm', 'current',
                       '--out', str(self.out), '--budget-usd', '5', env=env)
        text = self.records('current')[0].read_text()
        self.assertNotIn('sk-abcdefghijklmnopqrstuvwxyz', text)
        self.assertNotIn('abcdefghijklmnopqrstuvwxyz0123', text)
        self.assertIn('<REDACTED>', text)

    def test_redaction_spares_ordinary_words(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        from behavior_smoke import redact
        self.assertEqual(redact('<task-notification> risk-assessment-document'), '<task-notification> risk-assessment-document')
        self.assertIn('<REDACTED>', redact('key sk-ant-api03-abcdefghijklmnopqrstuvwxyz012345'))

    def test_judgment_quote_must_come_from_that_run(self):
        env1 = dict(self.env, FAKE_REPLY='回复一：只读审查，不回退。')
        self.run_smoke('run', '--skill', 'sdlc', '--cases', '1', '--reps', '1', '--arm', 'current',
                       '--out', str(self.out), '--budget-usd', '5', env=env1)
        env2 = dict(self.env, FAKE_REPLY='回复二：派 general-purpose。')
        self.run_smoke('run', '--skill', 'sdlc', '--cases', '2', '--reps', '1', '--arm', 'current',
                       '--out', str(self.out), '--budget-usd', '5', env=env2)
        recs = [r.relative_to(self.out).as_posix() for r in self.records('current')]
        judgments = self.out / 'judgments.json'
        judgments.write_text(json.dumps({recs[0]: {'verdict': 'pass', 'quote': '只读审查，不回退'},
                                         recs[1]: {'verdict': 'fail', 'quote': '只读审查，不回退'}}, ensure_ascii=False))
        p = self.run_smoke('judge', '--out', str(self.out), '--file', str(judgments))
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn('quote not found', p.stdout)
        judgments.write_text(json.dumps({recs[0]: {'verdict': 'pass', 'quote': '只读审查，不回退'},
                                         recs[1]: {'verdict': 'fail', 'quote': '派 general-purpose'}}, ensure_ascii=False))
        p = self.run_smoke('judge', '--out', str(self.out), '--file', str(judgments))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn('sdlc', p.stdout)

    def test_dry_run_calls_no_host(self):
        env = dict(self.env, PATH='/usr/bin:/bin')  # no claude on PATH: a dry run must not need it
        p = self.run_smoke('run', '--skill', 'sdlc', '--cases', '1', '--reps', '2', '--arm', 'current',
                           '--out', str(self.out), '--budget-usd', '5', '--dry-run', env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('--plugin-dir', p.stdout)
        self.assertEqual(self.records(), [])


if __name__ == '__main__':
    unittest.main()
