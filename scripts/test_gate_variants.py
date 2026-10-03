#!/usr/bin/env python3
"""check-sdlc.sh verdicts must not depend on how state.yaml is written, and verbatim templates never pass silently.

Variants of one state are generated (inline comments, quoting, flow vs block lists, blank and comment lines,
numeric ids, a path with a space) and must produce the same tags as the plain form. Templates the gate reads are
copied verbatim and their verdicts pinned. Diagnosis 2026-10-02 (sessions 9a339564 F2, 11e9b105 G2): hand-written
fixtures covered only the forms their authors thought of.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / 'scripts' / 'check-sdlc.sh'


def tags(target: Path, *args) -> tuple[int, list[str]]:
    p = subprocess.run(['bash', str(CHECK), *args, str(target)], text=True, capture_output=True)
    found = sorted(t for t in re.findall(r'\[SDLC-([A-Z][A-Z0-9-]*)\]', p.stdout) if t != 'SUMMARY')
    return p.returncode, found


SPEC = '泳道：L2\n| id | 问题 | 类别 | 状态 |\n|---|---|---|---|\n| {qid} | 定价档位 | 战略 | 待确认 |\n'

STATES = {
    'plain': ('feature: t\nsdlc_version: 4\nlane: L2\nappetite: 4h\ncurrent_hat: implement\nhats_done: [define, shape]\n'
              'open_questions:\n  - {{id: {qid}, class: 战略, status: {status}}}\n'),
    'inline-comments': ('feature: t   # 功能名\nsdlc_version: 4       # v4\nlane: L2              # L0-L4\n'
                        'appetite: 4h          # 时间预算\ncurrent_hat: implement   # 英文主词（define/shape/implement）\n'
                        'hats_done: [define, shape]   # 已完成\n'
                        'open_questions:    # 必须含待确认\n  - {{id: {qid}, class: 战略, status: {status}}}   # 注释\n'),
    'quoted': ('feature: "t"\nsdlc_version: 4\nlane: "L2"\nappetite: \'4h\'\ncurrent_hat: "implement"\n'
               'hats_done: [define, shape]\nopen_questions:\n  - {{id: "{qid}", class: "战略", status: "{status}"}}\n'),
    'block-list': ('feature: t\nsdlc_version: 4\nlane: L2\nappetite: 4h\ncurrent_hat: implement\nhats_done: [define, shape]\n'
                   'open_questions:\n  - id: {qid}\n    class: 战略\n    status: {status}\n'),
    'flow-list': ('feature: t\nsdlc_version: 4\nlane: L2\nappetite: 4h\ncurrent_hat: implement\nhats_done: [define, shape]\n'
                  'open_questions: [{{id: {qid}, class: 战略, status: {status}}}]\n'),
    'blank-and-comment-lines': ('# state\nfeature: t\n\nsdlc_version: 4\n# 泳道\nlane: L2\n\nappetite: 4h\n'
                                'current_hat: implement\n\nhats_done: [define, shape]\n# 待决\nopen_questions:\n\n'
                                '  # 一条\n  - {{id: {qid}, class: 战略, status: {status}}}\n'),
}


class VariantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='gate-variants.'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def feature(self, name: str, state: str, qid: str, status: str, spec_status: str = '待确认') -> Path:
        d = self.tmp / name
        (d / '01-define').mkdir(parents=True)
        (d / '01-define' / 'spec.md').write_text(SPEC.format(qid=qid).replace('待确认', spec_status), encoding='utf-8')
        (d / 'state.yaml').write_text(state.format(qid=qid, status=status), encoding='utf-8')
        return d

    def test_pending_decision_blocks_in_every_form(self):
        for qid in ('Q-PRICE', 'Q-1'):
            expected = None
            for form, state in STATES.items():
                for space in ('', ' with space'):
                    d = self.feature(f'{qid}-{form}{space}', state, qid, 'open')
                    code, found = tags(d, '--require')
                    with self.subTest(qid=qid, form=form, space=bool(space)):
                        self.assertIn('DECISIONPENDING', found)
                        self.assertIn('OPENQOPEN', found)
                        if expected is None:
                            expected = (code, found)
                        self.assertEqual((code, found), expected)

    def test_answered_decision_passes_in_every_form(self):
        for form, state in STATES.items():
            d = self.feature(f'answered-{form}', state, 'Q-PRICE', 'answered', spec_status='已确认 | 「先免费三个月」· 操作者')
            code, found = tags(d, '--require')
            with self.subTest(form=form):
                self.assertEqual((code, found), (0, []))


class VerbatimTemplateTests(unittest.TestCase):
    """A template copied verbatim keeps its sdlc:unfilled marker; the stage gate must not take it as delivered."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='gate-templates.'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lane(self, name: str, extra_state: str = '') -> Path:
        d = self.tmp / name
        (d / '01-define').mkdir(parents=True)
        (d / 'state.yaml').write_text('feature: t\nlane: L2\nappetite: 4h\ncurrent_hat: define\nhats_done: []\n'
                                      + extra_state, encoding='utf-8')
        return d

    def test_spec_templates_are_missing_at_the_define_gate(self):
        for tpl in ('skills/prd-gwt/templates/spec.md', 'skills/sdlc/templates/spec-s.md'):
            d = self.lane(Path(tpl).stem)
            shutil.copy(ROOT / tpl, d / '01-define' / 'spec.md')
            code, found = tags(d, '--hat', 'define')
            with self.subTest(template=tpl):
                self.assertIn('HATMISS', found)
                self.assertGreaterEqual(code, 1)

    def test_briefing_template_is_not_a_done_discovery(self):
        d = self.lane('briefing', 'discovery:\n  status: done\n')
        (d / '01-define' / 'spec.md').write_text('泳道：L2\n', encoding='utf-8')
        (d / '00-discover').mkdir()
        shutil.copy(ROOT / 'skills/discover/templates/briefing.md', d / '00-discover' / 'briefing.md')
        code, found = tags(d, '--require')
        self.assertEqual((code, found), (1, ['NODISCOVER']))

    def test_state_template_is_not_ready_for_define(self):
        d = self.tmp / 'state-template'
        d.mkdir()
        shutil.copy(ROOT / 'skills/sdlc/templates/state.yaml', d / 'state.yaml')
        code, found = tags(d, '--require')
        self.assertEqual((code, found), (1, ['NODISCOVER']))


if __name__ == '__main__':
    unittest.main()
