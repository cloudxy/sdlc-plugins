#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path
from check_research_sources import has_source

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("explain", ROOT / "skills/schema/scripts/check-explain.py")
explain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(explain)

class EvidenceTests(unittest.TestCase):
    def test_empty_unknown_and_headerless_plans_never_pass(self):
        for text in ("", "Seq Scan on users", "| 1 | SIMPLE | t | ALL | NULL | NULL | 10 |"):
            self.assertTrue(explain.parse(text))

    def test_named_columns_use_rows_not_key_length(self):
        text = "| id | select_type | table | partitions | type | possible_keys | key | key_len | ref | rows | filtered | Extra |\n"
        text += "| 1 | SIMPLE | t | NULL | ALL | idx_t | NULL | 4 | NULL | 50000 | 100 | |"
        self.assertTrue(any("rows=50000" in x and "key=NULL" in x for x in explain.parse(text)))

    def test_small_scan_and_explicit_budget(self):
        head = "| table | type | key | rows | Extra |\n"
        self.assertEqual(explain.parse(head + "| t | ALL | NULL | 12 | Using filesort |"), [])
        self.assertEqual(explain.parse(head + "| t | ALL | NULL | 5000 | |", max_scan_rows=6000), [])
        self.assertTrue(explain.parse(head + "| t | ALL | NULL | unknown | |"))

    def test_dated_internal_source_and_missing_reference(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            note = root / "market.md"
            (root / "customer.md").write_text("observed request")
            note.write_text("2026-09-19 [request](customer.md)")
            self.assertTrue(has_source(note))
            note.write_text("2026-09-19 [request](missing.md)")
            self.assertFalse(has_source(note))
            note.write_text("[request](customer.md)")
            self.assertFalse(has_source(note))
            note.write_text("2026-09-19 https://example.com/source")
            self.assertTrue(has_source(note))

if __name__ == '__main__':
    unittest.main(verbosity=2)
