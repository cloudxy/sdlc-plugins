#!/usr/bin/env python3
"""method_ledger.py on a temporary copy of the plugin: an unregistered method edit is an error."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'method_ledger.py'


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='ledger-test.'))
        self.root = self.tmp / 'plugin'
        for top in ('skills', 'agent-sources', 'workflow', 'adapters', 'agents', 'scripts', 'commands'):
            shutil.copytree(ROOT / top, self.root / top, ignore=shutil.ignore_patterns('__pycache__', '*.png'))
        (self.root / 'maintainers').mkdir()
        self.ledger('seed', '--reason', 'initial baseline for the test copy')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ledger(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), *args],
                              text=True, capture_output=True)

    def edit(self, rel, text='\nOne more sentence.\n'):
        with (self.root / rel).open('a', encoding='utf-8') as fh:
            fh.write(text)

    def test_clean_copy_passes(self):
        p = self.ledger('check')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_unregistered_change_is_methodchange(self):
        self.edit('skills/tdd/SKILL.md')
        p = self.ledger('check')
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn('METHODCHANGE', p.stdout)
        self.assertIn('skills/tdd/SKILL.md', p.stdout)

    def test_editorial_record_clears_it(self):
        self.edit('skills/tdd/SKILL.md')
        p = self.ledger('record', '--id', 'typo', '--kind', 'editorial', '--reason', 'fix a typo')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.ledger('check').returncode, 0)
        rec = json.loads(next((self.root / 'maintainers' / 'method-changes').glob('*-typo.json')).read_text())
        self.assertIn('skills/tdd/SKILL.md', rec['files'])

    def test_later_edit_needs_a_new_record(self):
        self.edit('skills/tdd/SKILL.md')
        self.ledger('record', '--id', 'first', '--kind', 'editorial', '--reason', 'first edit')
        self.edit('skills/tdd/SKILL.md', '\nA second edit.\n')
        p = self.ledger('check')
        self.assertEqual(p.returncode, 1)
        self.assertIn('METHODCHANGE', p.stdout)

    def test_hand_edited_baseline_is_caught(self):
        self.edit('skills/tdd/SKILL.md')
        base = self.root / 'maintainers' / 'method-baseline.json'
        data = json.loads(base.read_text())
        import hashlib
        data['files']['skills/tdd/SKILL.md'] = hashlib.sha256((self.root / 'skills/tdd/SKILL.md').read_bytes()).hexdigest()
        base.write_text(json.dumps(data))
        p = self.ledger('check')
        self.assertEqual(p.returncode, 1)
        self.assertIn('no change record', p.stdout)

    def test_generated_files_are_not_registered(self):
        data = json.loads((self.root / 'maintainers' / 'method-baseline.json').read_text())
        self.assertFalse(any(k.startswith('agents/') or '/agents/' in k for k in data['files']))
        self.assertNotIn('skills/sdlc/references/stage-map.md', data['files'])  # carries a GENERATED header
        self.assertNotIn('commands/sdlc.md', data['files'])
        self.assertFalse(any('/evals/' in k for k in data['files']))
        self.edit('agents/pm.md')
        self.assertEqual(self.ledger('check').returncode, 0, 'generated drift is render --check territory')

    def test_pending_behavioral_is_warning_not_error(self):
        self.edit('skills/tdd/SKILL.md')
        self.ledger('record', '--id', 'tdd-rule', '--kind', 'behavioral', '--failure-form', 'omission',
                    '--reason', 'add a counter-example', '--verdict', 'pending')
        p = self.ledger('check')
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn('METHODPENDING', p.stdout)

    def test_record_can_split_changes_by_file(self):
        self.edit('skills/tdd/SKILL.md')
        self.edit('skills/refactor/SKILL.md')
        p = self.ledger('record', '--id', 'tdd-only', '--kind', 'editorial', '--reason', 'r',
                        '--files', 'skills/tdd/SKILL.md')
        self.assertEqual(p.returncode, 0, p.stderr)
        p = self.ledger('check')
        self.assertEqual(p.returncode, 1)
        self.assertIn('skills/refactor/SKILL.md', p.stdout)
        self.assertNotIn('skills/tdd/SKILL.md:', p.stdout)

    def test_behavioral_record_needs_failure_form(self):
        self.edit('skills/tdd/SKILL.md')
        p = self.ledger('record', '--id', 'x', '--kind', 'behavioral', '--reason', 'r', '--verdict', 'pending')
        self.assertEqual(p.returncode, 2)


if __name__ == '__main__':
    unittest.main()
