#!/usr/bin/env python3
"""VENDORDRIFT: an adapted reference names the upstream file and digest it was reviewed against; a moved lock warns."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import vendorlib  # noqa: E402

OLD, NEW = 'a' * 64, 'b' * 64


class DriftTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='vendor drift.'))
        (self.tmp / 'vendor').mkdir()
        ref = self.tmp / 'skills' / 'design' / 'references' / 'visual.md'
        ref.parent.mkdir(parents=True)
        ref.write_text(f'# Visual\n\n<!-- upstream: up skills/fd/SKILL.md sha256={OLD} reviewed=2026-10-02 -->\nbody\n',
                       encoding='utf-8')
        self.write_lock(OLD)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_lock(self, sha):
        lock = {'source': 'up', 'files': [{'path': 'skills/fd/SKILL.md', 'sha256': sha, 'purpose': 'runtime'}]}
        (self.tmp / 'vendor' / 'up.lock.json').write_text(json.dumps(lock), encoding='utf-8')

    def test_no_drift_while_lock_matches(self):
        self.assertEqual(vendorlib.drift(self.tmp), [])

    def test_drift_warns_when_lock_changes(self):
        self.write_lock(NEW)
        found = vendorlib.drift(self.tmp)
        self.assertEqual(len(found), 1)
        self.assertIn('skills/design/references/visual.md', found[0])
        self.assertIn(NEW[:12], found[0])

    def test_lock_without_the_file_or_missing_lock_warns(self):
        (self.tmp / 'vendor' / 'up.lock.json').write_text(json.dumps({'files': []}), encoding='utf-8')
        self.assertIn('no longer includes', vendorlib.drift(self.tmp)[0])
        (self.tmp / 'vendor' / 'up.lock.json').unlink()
        self.assertIn('is missing', vendorlib.drift(self.tmp)[0])

    def test_repository_adaptations_carry_headers_and_match(self):
        for rel in ('skills/design-contract/references/visual-direction.md',
                    'skills/design-contract/references/ux-writing.md'):
            self.assertRegex((ROOT / rel).read_text(encoding='utf-8'), vendorlib.UPSTREAM)
        self.assertEqual(vendorlib.drift(ROOT), [])

    def test_health_check_reports_drift_as_a_warning(self):
        self.write_lock(NEW)
        p = subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0, sys.argv[1]); import health_check as h;'
                            'w=[]; h.check_vendor_drift(sys.argv[2], lambda *a: w.append(("err",)+a),'
                            'lambda *a: w.append(("warn",)+a), lambda *a: None); print(w)',
                            str(ROOT / 'scripts'), str(self.tmp)], text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("('warn', 'VENDORDRIFT'", p.stdout)
        self.assertNotIn("'err'", p.stdout)


if __name__ == '__main__':
    unittest.main()
