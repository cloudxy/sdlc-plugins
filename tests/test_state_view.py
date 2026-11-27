#!/usr/bin/env python3
"""state_view.py rows and runtime_protocol.parse_time: the inputs that used to change gate verdicts silently."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1] / 'scripts')  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from runtime.runtime_protocol import ProtocolError, parse_time  # noqa: E402
from gates.state_view import read_items, read_map, skipped_roles  # noqa: E402
from gates import state_view  # noqa: E402

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


def capture(view, text):
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write(text)
    real = sys.stdout
    try:
        import io
        sys.stdout = buf = io.StringIO()
        rc = state_view.main([view, f.name])
    finally:
        sys.stdout = real
        Path(f.name).unlink()
    return rc, buf.getvalue()


def rows(view, text):
    _rc, raw = capture(view, text)
    return [line.split('\t') for line in raw.splitlines()]


FULL_V4 = '''feature: billing-export   # 账单导出
lane: L2
phase: Rework
sdlc_version: 4
delivery_goal: local_verified
current_hat: implement
hats_done: [define, shape]
discovery:
  status: skipped
  skip_why: "已有合同，不再探索"
  tracks:
    falsify: done
open_questions:
  - Q-1
  - {id: Q-PRICE, status: answered, quote: "按年付"}
  - id: Q-TIER
    status: unanswered
gates:
  - {name: lint, kind: script, stage: define, result: fail}
  - {name: lint, kind: script, stage: define, result: pass}
  - {name: check-sdlc, kind: script, stage: define, result: fail, exit_code: 1}
  - {name: fresh-context, kind: fresh-context, stage: shape, result: fail}
  - {name: e2e, result: null}
  - {name: unit, result: null, reason: 无单测配置}
host_spawn:
  researcher:
    requested: sdlc-workflow:researcher
    available: [sdlc-workflow:researcher]
    fallback: general-purpose
    reason: "宿主没有类型表"
bet:
  hypothesis: H-2
  metric: 周活
  evidence_grade: E1
  readout_due: 2026-12-01
escape:
  origin_feature: export
  origin_release: 2026-11-01
  should_have_caught_at: verify
  gate: e2e
  defect_class: code
roles_skipped: [growth, designer]
roles_skipped_why: {growth: "内部工具，无对外宣称"}
'''

BLOCKED = '''feature: blocked-pay
lane: L3
phase: Rework
sdlc_version: 4
delivery_goal: release_ready
current_hat: verify
hats_done:
  - define
  - shape
  - implement
discovery:
  status: done
  reopened:
    by: user
  skip_why: ""
open_questions:
  - {id: Q-KEEP, status: open}
  - {id: Q-DONE, status: answered, quote: "可以"}
  - id: Q-EXT
    status: external
gates:
  - {name: fresh-context, kind: fresh-context, stage: verify, result: pass}
  - {name: fresh-context, kind: fresh-context, stage: accept, result: fail}
  - name: e2e
    kind: script
    stage: verify
    result: fail
  - {name: lint, kind: script, stage: verify, result: null}
  - {name: typecheck, result: null, reason: 未配置}
'''

MINIMAL = '''feature: 极简   # 旧档
'''


class StateViewTests(unittest.TestCase):
    def test_questions_keep_bare_strings_and_exact_ids(self):
        self.assertEqual(rows('questions', STATE), [['Q-1', 'open'], ['Q-TIER-B', 'answered'], ['Q-TIER', 'unanswered']])

    def test_inline_flow_list_of_maps(self):
        text = 'open_questions: [{id: Q-OPEN-GATE, status: open}, {id: Q-SORT, status: answered, quote: "a, b"}]\n'
        self.assertEqual(read_items(text, 'open_questions'),
                         [{'id': 'Q-OPEN-GATE', 'status': 'open'}, {'id': 'Q-SORT', 'status': 'answered', 'quote': 'a, b'}])

    def test_flow_item_with_trailing_comment(self):
        text = 'open_questions:   # 必须含待确认\n  - {id: Q-1, class: 战略, status: open}   # 注释\n'
        self.assertEqual(read_items(text, 'open_questions'), [{'id': 'Q-1', 'class': '战略', 'status': 'open'}])

    def test_failed_gates_keep_the_latest_record_per_name_and_stage(self):
        text = ('gates:\n'
                '  - {name: lint, kind: script, stage: define, result: fail}\n'
                '  - {name: lint, kind: script, stage: define, result: pass}\n'
                '  - {name: check-sdlc, kind: script, stage: define, result: fail, exit_code: 1}\n'
                '  - {name: unit, kind: script, result: fail}\n'
                '  - {name: fresh-context, kind: fresh-context, stage: shape, result: fail}\n')
        self.assertEqual(rows('failed-gates', text),
                         [['script', 'check-sdlc', 'define'], ['script', 'unit', ''], ['fresh-context', 'fresh-context', 'shape']])
        cleared = text + '  - {name: unit, kind: script, result: pass}\n'
        self.assertEqual(rows('failed-gates', cleared),
                         [['script', 'check-sdlc', 'define'], ['fresh-context', 'fresh-context', 'shape']])

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

    def test_summary_full_v4(self):
        rc, raw = capture('summary', FULL_V4)
        self.assertEqual(rc, 0)
        self.assertEqual(raw.splitlines(), [
            'feature: billing-export',
            'lane: L2',
            'phase: Rework',
            'sdlc_version: 4',
            'delivery_goal: local_verified',
            'current_hat: implement',
            'hats_done: define, shape',
            '',
            'discovery: status=skipped reopened=none skip_why=已有合同，不再探索',
            '',
            'open_questions:',
            '- Q-1 (open)',
            '- Q-TIER (unanswered)',
            'failed_gates:',
            '- kind=script name=check-sdlc stage=define',
            '- kind=fresh-context name=fresh-context stage=shape',
            'last_fresh: result=fail stage=shape',
            'null_gates:',
            '- e2e',
            '',
            'host_spawn:',
            '- researcher: requested=sdlc-workflow:researcher available=[sdlc-workflow:researcher] fallback=general-purpose reason=宿主没有类型表',
            '',
            'bet: hypothesis=H-2 metric=周活 readout_due=2026-12-01',
            'escape: origin_feature=export origin_release=2026-11-01 should_have_caught_at=verify gate=e2e defect_class=code',
            '',
            'roles_skipped:',
            '- growth: 内部工具，无对外宣称',
            '- designer: none',
        ])
        self.assertNotIn('Q-PRICE', raw)
        self.assertNotIn('evidence_grade', raw)
        self.assertNotIn('无单测配置', raw)

    def test_summary_blocked_state(self):
        rc, raw = capture('summary', BLOCKED)
        self.assertEqual(rc, 0)
        self.assertEqual(raw.splitlines(), [
            'feature: blocked-pay',
            'lane: L3',
            'phase: Rework',
            'sdlc_version: 4',
            'delivery_goal: release_ready',
            'current_hat: verify',
            'hats_done: define, shape, implement',
            '',
            'discovery: status=done reopened=y skip_why=none',
            '',
            'open_questions:',
            '- Q-KEEP (open)',
            '- Q-EXT (external)',
            'failed_gates:',
            '- kind=fresh-context name=fresh-context stage=accept',
            '- kind=script name=e2e stage=verify',
            'last_fresh: result=fail stage=accept',
            'null_gates:',
            '- lint',
        ])
        self.assertNotIn('Q-DONE', raw)
        self.assertNotIn('typecheck', raw)
        self.assertNotIn('kind=fresh-context name=fresh-context stage=verify', raw)
        for absent in ('host_spawn:', 'bet:', 'escape:', 'roles_skipped:'):
            self.assertNotIn(absent, raw)

    def test_summary_minimal_legacy_omits_optional_sections(self):
        rc, raw = capture('summary', MINIMAL)
        self.assertEqual(rc, 0)
        self.assertEqual(raw.splitlines(), [
            'feature: 极简',
            'lane: none',
            'phase: none',
            'sdlc_version: none',
            'delivery_goal: none',
            'current_hat: none',
            'hats_done: none',
            '',
            'discovery: none',
            '',
            'open_questions: none',
            'failed_gates: none',
            'null_gates: none',
        ])
        passed = 'feature: ok\ngates:\n  - {name: fresh-context, kind: fresh-context, stage: define, result: pass}\n'
        rc_pass, raw_pass = capture('summary', passed)
        self.assertEqual(rc_pass, 0)
        self.assertNotIn('last_fresh:', raw_pass)
        self.assertIn('failed_gates: none', raw_pass)
        rc_empty, raw_empty = capture('summary', '')
        self.assertEqual(rc_empty, 0)
        self.assertIn('feature: none', raw_empty)
        template = (Path(__file__).resolve().parents[1] / 'skills/sdlc/templates/state.yaml').read_text(encoding='utf-8')
        rc_template, raw_template = capture('summary', template)
        self.assertEqual(rc_template, 0)
        self.assertIn('feature: <feature-name>', raw_template)
        self.assertIn('discovery: status=pending reopened=none skip_why=none', raw_template)

    def test_tsv_views_unchanged_on_summary_fixtures(self):
        self.assertEqual(rows('questions', FULL_V4), [
            ['Q-1', 'open'], ['Q-PRICE', 'answered'], ['Q-TIER', 'unanswered']])
        self.assertEqual(rows('null-gates', FULL_V4), [['e2e']])
        self.assertEqual(rows('last-fresh', FULL_V4), [['fail', 'shape']])
        self.assertEqual(rows('failed-gates', FULL_V4), [
            ['script', 'check-sdlc', 'define'], ['fresh-context', 'fresh-context', 'shape']])
        self.assertEqual(rows('skips', FULL_V4), [
            ['growth', '内部工具，无对外宣称'], ['designer', '']])
        self.assertEqual(rows('discovery', FULL_V4), [['skipped', '已有合同，不再探索', '']])
        self.assertEqual(rows('escape', FULL_V4), [['1', 'verify', 'code', '', '']])
        self.assertEqual(rows('escape', BLOCKED), [])
        self.assertEqual(rows('questions', BLOCKED), [
            ['Q-KEEP', 'open'], ['Q-DONE', 'answered'], ['Q-EXT', 'external']])
        self.assertEqual(rows('null-gates', BLOCKED), [['lint']])
        self.assertEqual(rows('last-fresh', BLOCKED), [['fail', 'accept']])
        self.assertEqual(rows('failed-gates', BLOCKED), [
            ['fresh-context', 'fresh-context', 'accept'], ['script', 'e2e', 'verify']])
        self.assertEqual(rows('discovery', BLOCKED), [['done', '', 'y']])
        self.assertEqual(rows('skips', BLOCKED), [])
        self.assertTrue(all('\t' not in line for line in capture('summary', STATE)[1].splitlines()))


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
