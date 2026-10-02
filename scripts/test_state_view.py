#!/usr/bin/env python3
"""state_view.py rows and runtime_protocol.parse_time: the inputs that used to change gate verdicts silently."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_protocol import ProtocolError, parse_time  # noqa: E402
from state_view import read_items, read_map, skipped_roles  # noqa: E402
import state_view  # noqa: E402

STATE = '''feature: t
current_hat: implement   # 英文主词
roles_skipped: [growth, designer]   # 注释
roles_skipped_why: {growth: "issue #12, 内部工具"}
discovery:
  status: skipped
  skip_why: ""        # 必填
  tracks:
    growth: skipped
gates:   # 三类记录
  # fresh-context:{name, kind: fresh-context, stage: <stage-id>, result}
  - {name: fresh-context, kind: fresh-context, stage: define, result: fail}
  - name: e2e
    result: null
  - {name: lint, result: null, reason: 无 lint 配置}
open_questions:
  - Q-1
  - {id: Q-TIER-B, status: answered}
  - id: Q-TIER
    status: unanswered
'''


def rows(view, text):
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write(text)
    real = sys.stdout
    try:
        import io
        sys.stdout = buf = io.StringIO()
        state_view.main([view, f.name])
    finally:
        sys.stdout = real
        Path(f.name).unlink()
    return [line.split('\t') for line in buf.getvalue().splitlines()]


class StateViewTests(unittest.TestCase):
    def test_questions_keep_bare_strings_and_exact_ids(self):
        self.assertEqual(rows('questions', STATE), [['Q-1', 'open'], ['Q-TIER-B', 'answered'], ['Q-TIER', 'unanswered']])

    def test_inline_flow_list_of_maps(self):
        text = 'open_questions: [{id: Q-OPEN-GATE, status: open}, {id: Q-SORT, status: answered, quote: "a, b"}]\n'
        self.assertEqual(read_items(text, 'open_questions'),
                         [{'id': 'Q-OPEN-GATE', 'status': 'open'}, {'id': 'Q-SORT', 'status': 'answered', 'quote': 'a, b'}])

    def test_null_gates_need_their_own_reason(self):
        self.assertEqual(rows('null-gates', STATE), [['e2e']])

    def test_last_fresh_reads_flow_records_not_comments(self):
        self.assertEqual(rows('last-fresh', STATE), [['fail', 'define']])

    def test_skips_pair_roles_with_reasons(self):
        self.assertEqual(rows('skips', STATE), [['growth', 'issue #12, 内部工具'], ['designer', '']])
        self.assertEqual(skipped_roles('roles_skipped:\n  - growth\n'), [], 'block style is not a skip list')

    def test_discovery_strips_comments(self):
        self.assertEqual(rows('discovery', STATE), [['skipped', '', '']])
        self.assertEqual(read_map('discovery:\n  status: killed\n  reopened: {by: user}\n', 'discovery')['status'], 'killed')

    def test_template_has_no_records(self):
        template = (Path(__file__).resolve().parents[1] / 'skills/sdlc/templates/state.yaml').read_text(encoding='utf-8')
        for view in ('questions', 'null-gates', 'last-fresh', 'skips'):
            self.assertEqual(rows(view, template), [], view)


class ParseTimeTests(unittest.TestCase):
    def test_offsets_people_write(self):
        self.assertEqual(parse_time('2026-10-01T10:00:00Z').utcoffset().total_seconds(), 0)
        self.assertEqual(parse_time('2026-10-01T10:00:00+0800').utcoffset().total_seconds(), 8 * 3600)
        self.assertEqual(parse_time('2026-10-01').year, 2026)

    def test_rejects_non_times(self):
        with self.assertRaises(ValueError):
            parse_time('yesterday')
        with self.assertRaises(ProtocolError):
            parse_time('')


if __name__ == '__main__':
    unittest.main()
