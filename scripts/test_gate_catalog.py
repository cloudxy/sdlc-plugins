#!/usr/bin/env python3
"""gate_catalog.py: every gate tag has a fixture that asserts it and a recorded origin."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'gate_catalog.py'
sys.path.insert(0, str(ROOT / 'scripts'))
import gate_catalog  # noqa: E402


class CatalogTests(unittest.TestCase):
    def make(self, d: Path, provenance: dict):
        (d / 'scripts').mkdir(parents=True)
        (d / 'maintainers').mkdir()
        (d / 'scripts' / 'check-sdlc.sh').write_text(
            'red ALPHA "x"\nred BETA "y"\nneed_images "$f" GAMMA "z"\n', encoding='utf-8')
        (d / 'scripts' / 'workflow.py').write_text('bad("DELTA", "w")\nrows.append(("error", "EPSILON", "v"))\n')
        (d / 'scripts' / 'test-check-sdlc.sh').write_text('assert_tag ALPHA\nassert_tag SDLC-GAMMA\n', encoding='utf-8')
        (d / 'scripts' / 'test_workflow.py').write_text('self.assertIn("DELTA", codes)\n')
        (d / 'maintainers' / 'gate-provenance.json').write_text(json.dumps(provenance))

    def test_lists_tags_without_fixture_or_origin(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.make(d, {'ALPHA': {'added': '2026-09-18', 'origin': 'x', 'review_by': '2027-03-18'},
                          'ZETA': {'added': '2026-09-18', 'origin': 'gone', 'review_by': '2027-03-18'}})
            cat = gate_catalog.catalog(d)
            self.assertEqual(set(cat['tags']), {'ALPHA', 'BETA', 'GAMMA', 'DELTA', 'EPSILON'})
            self.assertEqual(cat['without_fixture'], ['BETA', 'EPSILON'])
            self.assertEqual(cat['without_origin'], ['BETA', 'DELTA', 'EPSILON', 'GAMMA'])
            self.assertEqual(cat['stale_origin'], ['ZETA'])
            p = subprocess.run([sys.executable, str(SCRIPT), '--root', str(d), 'check', '--strict'],
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, 1)
            self.assertIn('GATECATALOG', p.stdout)

    def test_overdue_review_is_listed(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.make(d, {t: {'added': '2026-01-01', 'origin': 'x', 'review_by': '2026-06-01'}
                          for t in ('ALPHA', 'BETA', 'GAMMA', 'DELTA', 'EPSILON')})
            cat = gate_catalog.catalog(d, today='2026-10-02')
            self.assertEqual(cat['review_due'], ['ALPHA', 'BETA', 'DELTA', 'EPSILON', 'GAMMA'])

    def test_escapes_from_project_outcomes_are_counted(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            out = d / '.sdlc' / '_outcomes'
            out.mkdir(parents=True)
            (out / 'fix-1.json').write_text(json.dumps({'feature': 'fix-1', 'escape': {'gate': 'OPENQ'}}))
            (out / 'fix-2.json').write_text(json.dumps({'feature': 'fix-2', 'escape': {'gate': 'OPENQ'}}))
            (out / 'feat.json').write_text(json.dumps({'feature': 'feat'}))
            self.assertEqual(gate_catalog.escapes(d), {'OPENQ': ['fix-1', 'fix-2']})

    def test_real_repository_is_fully_catalogued(self):
        cat = gate_catalog.catalog(ROOT)
        self.assertGreaterEqual(len(cat['tags']), 58)
        self.assertEqual(cat['without_fixture'], [], 'every gate tag needs a fixture that asserts it')
        self.assertEqual(cat['without_origin'], [], 'every gate tag needs a recorded origin')
        self.assertEqual(cat['stale_origin'], [])


if __name__ == '__main__':
    unittest.main()
