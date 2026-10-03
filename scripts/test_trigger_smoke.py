#!/usr/bin/env python3
"""trigger_smoke.py with a fake `claude` on PATH: which skill a prompt loads, scored per arm; no model calls."""
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
SCRIPT = ROOT / 'scripts' / 'trigger_smoke.py'
sys.path.insert(0, str(ROOT / 'scripts'))
import trigger_smoke  # noqa: E402

# Loads prd-gwt through the Skill tool when the prompt says PRD, reads tdd's SKILL.md when it says tdd, and stops
# at the turn limit when it says "slow"; FAKE_LIMIT=1 answers like an exhausted session quota.
FAKE = r'''#!/usr/bin/env python3
import json, os, sys
if sys.argv[1:2] == ['--version']:
    print('0.0.0 (fake claude)'); sys.exit(0)
prompt = sys.argv[sys.argv.index('-p') + 1]
print(json.dumps({'type': 'system', 'subtype': 'init', 'model': 'fake', 'tools': ['Read', 'Skill'],
                  'skills': ['sdlc-workflow:prd-gwt', 'sdlc-workflow:tdd']}))
uses = []
if 'PRD' in prompt:
    uses.append({'type': 'tool_use', 'name': 'Skill', 'input': {'skill': 'sdlc-workflow:prd-gwt'}})
if 'tdd' in prompt:
    uses.append({'type': 'tool_use', 'name': 'Read', 'input': {'file_path': '/x/sdlc-workflow/skills/tdd/SKILL.md'}})
print(json.dumps({'type': 'assistant', 'message': {'content': uses or [{'type': 'text', 'text': 'ok'}]}}))
if os.environ.get('FAKE_LIMIT'):
    print(json.dumps({'type': 'result', 'subtype': 'success', 'is_error': True, 'api_error_status': 429,
                      'result': "You've hit your session limit", 'total_cost_usd': 0}))
    sys.exit(1)
sub = 'error_max_turns' if 'slow' in prompt else ('error_max_budget_usd' if 'long' in prompt else 'success')
print(json.dumps({'type': 'result', 'subtype': sub, 'is_error': sub != 'success', 'result': 'done',
                  'total_cost_usd': 0.05}))
sys.exit(0 if sub == 'success' else 1)
'''


class TriggerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='trigger test.'))
        bin_dir = self.tmp / 'bin'
        bin_dir.mkdir()
        (bin_dir / 'claude').write_text(FAKE)
        os.chmod(bin_dir / 'claude', 0o755)
        self.env = dict(os.environ, PATH=f'{bin_dir}{os.pathsep}{os.environ["PATH"]}',
                        SDLC_SMOKE_CACHE=str(self.tmp / 'cache'))
        self.out = self.tmp / 'out'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_trigger(self, *args, env=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True,
                              env=env or self.env)

    def test_parse_counts_skill_calls_and_skill_reads(self):
        stream = '\n'.join(json.dumps(e) for e in [
            {'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'name': 'Skill', 'input': {'skill': 'sdlc-workflow:discover'}},
                {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': '/t/skills/tdd/SKILL.md'}},
                {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': '/t/skills/tdd/references/x.md'}}]}},
            {'type': 'result', 'subtype': 'success', 'result': 'r', 'total_cost_usd': 0.1}])
        parsed = trigger_smoke.parse_stream(stream)
        self.assertEqual(parsed['loaded'], ['sdlc-workflow:discover', 'read:tdd'])
        self.assertTrue(trigger_smoke.loaded_target(parsed['loaded'], 'tdd'))
        self.assertFalse(trigger_smoke.loaded_target(parsed['loaded'], 'prd-gwt'))

    def test_run_and_score_per_arm(self):
        p = self.run_trigger('run', '--skills', 'prd-gwt,tdd', '--reps', '2', '--arm', 'current',
                             '--out', str(self.out), '--budget-usd', '5')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        recs = list((self.out / 'current').glob('*.json'))
        self.assertEqual(len(recs), 16)
        self.assertEqual(len(list((self.out / 'trees').glob('*/manifest.json'))), 1)
        s = json.loads(self.run_trigger('score', '--out', str(self.out), '--json').stdout)
        row = next(r for r in s['rows'] if r['skill'] == 'prd-gwt' and r['trigger_id'] == '1')
        self.assertEqual((row['triggered'], row['runs']), (2, 2))  # the real prompt 1 says PRD
        self.assertEqual(s['arms']['current']['should'][1] + s['arms']['current']['should_not'][1], 16)

    def test_turn_limit_is_an_outcome_and_quota_is_a_host_failure(self):
        rows = {'triggers': [{'id': 1, 'prompt': 'slow PRD', 'should_trigger': True},
                             {'id': 2, 'prompt': 'a long schema design', 'should_trigger': False}]}
        skill_dir = self.tmp / 'plugin'
        shutil.copytree(ROOT / 'scripts', skill_dir / 'scripts')
        evals = skill_dir / 'skills' / 'prd-gwt' / 'evals'
        evals.mkdir(parents=True)
        (evals / 'triggers.json').write_text(json.dumps(rows))
        subprocess.run(['git', 'init', '-q', str(skill_dir)], check=True)
        script = skill_dir / 'scripts' / 'trigger_smoke.py'
        p = subprocess.run([sys.executable, str(script), 'run', '--skills', 'prd-gwt', '--reps', '1', '--arm',
                            'current', '--out', str(self.out), '--budget-usd', '1'], text=True,
                           capture_output=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        rec = json.loads((self.out / 'current' / 'prd-gwt-t1-r1.json').read_text())
        self.assertEqual((rec['status'], rec['triggered']), ('ok', True))
        rec2 = json.loads((self.out / 'current' / 'prd-gwt-t2-r1.json').read_text())
        self.assertEqual((rec2['status'], rec2['subtype'], rec2['triggered']), ('ok', 'error_max_budget_usd', False))
        (self.out / 'current' / 'prd-gwt-t1-r1.json').unlink()
        p = subprocess.run([sys.executable, str(script), 'run', '--skills', 'prd-gwt', '--reps', '1', '--arm',
                            'current', '--out', str(self.out), '--budget-usd', '1'], text=True,
                           capture_output=True, env=dict(self.env, FAKE_LIMIT='1'))
        self.assertEqual(p.returncode, 4, p.stdout + p.stderr)
        rec = json.loads((self.out / 'current' / 'prd-gwt-t1-r1.json').read_text())
        self.assertEqual(rec['status'], 'host_failure')

    def test_trigger_rows_are_well_formed(self):
        for skill in ('prd-gwt', 'discover', 'tdd'):
            rows = trigger_smoke.load_rows(skill)
            self.assertEqual(sorted(r['should_trigger'] for r in rows), [False, False, True, True])


if __name__ == '__main__':
    unittest.main()
