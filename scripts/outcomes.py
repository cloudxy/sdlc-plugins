#!/usr/bin/env python3
"""Result records for closed work: what was bet, when the readout is due, and what escaped.

  record  --feature DIR              on phase: Closed, write <project>/.sdlc/_outcomes/<feature>.json and index.json
  readout --project-root R --feature F --status supported|refuted|inconclusive --evidence PATH [--note TEXT]
                                     close a bet with its readout (the analyst's retro or cycle readout)
  due     --project-root R [--today YYYY-MM-DD]
                                     bets whose readout date has passed without a readout (one line each)
  stats   [--root DIR] [--json]      lanes, rework, independent-review intercepts, escapes by gate/stage/class and
                                     bet outcomes by the evidence grade they were made on (check-sdlc.sh --stats)

A state records its bet as `bet: {hypothesis: H-n, metric, evidence_grade: E0-E4, readout_due}` and a defect fix
records where the defect escaped as `escape: {origin_feature, origin_release, should_have_caught_at, gate,
defect_class}`. Due bets are reported, never enforced: a late readout must not block unrelated work.
Exit: 0 ok · 2 usage or a feature that is not closed.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import sys
from pathlib import Path

from state_view import _top, _scalar, read_items, read_map

STATUSES = ('supported', 'refuted', 'inconclusive')


def scalar(text: str, key: str) -> str:
    inline, _ = _top(text, key)
    return _scalar(inline) if inline else ''


def project_root(feature: Path) -> Path:
    for d in [feature, *feature.parents]:
        if (d / 'sdlc.config.yaml').is_file():
            return d
    return feature.parent.parent  # <root>/.sdlc/<feature>


def outcome_from_state(feature: Path) -> dict:
    text = (feature / 'state.yaml').read_text(encoding='utf-8')
    gates = [g for g in read_items(text, 'gates') if isinstance(g, dict)]
    intercepts = sum(int(g.get('findings_total') or 0) for g in gates
                     if g.get('kind') == 'fresh-context' and str(g.get('findings_total', '')).isdigit())
    try:
        rework = int(scalar(text, 'rework_rounds') or 0)
    except ValueError:
        rework = 0
    hats = read_items(text, 'hats_done')
    return {'feature': scalar(text, 'feature') or feature.name, 'lane': scalar(text, 'lane'),
            'delivery_goal': scalar(text, 'delivery_goal'), 'phase': scalar(text, 'phase'),
            'hats_done': [h for h in hats if isinstance(h, str)], 'rework_rounds': rework,
            'intercepts': intercepts, 'bet': read_map(text, 'bet') or None,
            'escape': read_map(text, 'escape') or None}


def out_dir(root: Path) -> Path:
    return root / '.sdlc' / '_outcomes'


def write_index(root: Path) -> None:
    rows = []
    for p in sorted(out_dir(root).glob('*.json')):
        if p.name == 'index.json':
            continue
        rec = json.loads(p.read_text(encoding='utf-8'))
        if rec.get('bet'):
            rows.append({'feature': rec['feature'], **rec['bet'],
                         'readout': (rec.get('readout') or {}).get('status')})
    (out_dir(root) / 'index.json').write_text(json.dumps({'bets': rows}, ensure_ascii=False, indent=1) + '\n',
                                              encoding='utf-8')


def cmd_record(args) -> int:
    feature = args.feature.resolve()
    rec = outcome_from_state(feature)
    if rec['phase'] != 'Closed':
        print(f"outcomes: {feature} is not closed (phase: {rec['phase'] or 'missing'})", file=sys.stderr)
        return 2
    root = project_root(feature)
    target = out_dir(root) / f"{rec['feature']}.json"
    previous = json.loads(target.read_text(encoding='utf-8')) if target.is_file() else {}
    rec['readout'] = previous.get('readout')
    rec['recorded_at'] = dt.datetime.now().astimezone().isoformat(timespec='seconds')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    write_index(root)
    print(f'recorded {target}')
    return 0


def cmd_readout(args) -> int:
    root = args.project_root.resolve()
    target = out_dir(root) / f'{args.feature}.json'
    if not target.is_file() or args.status not in STATUSES:
        print(f'outcomes: no result record for {args.feature}, or status not in {STATUSES}', file=sys.stderr)
        return 2
    rec = json.loads(target.read_text(encoding='utf-8'))
    if not rec.get('bet'):
        print(f'outcomes: {args.feature} recorded no bet', file=sys.stderr)
        return 2
    rec['readout'] = {'status': args.status, 'evidence': args.evidence, 'note': args.note or '',
                      'at': dt.date.today().isoformat()}
    target.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    write_index(root)
    print(f"{args.feature}: {rec['bet'].get('hypothesis', 'bet')} {args.status}")
    return 0


def due(root: Path, today: str) -> list[dict]:
    index = out_dir(root) / 'index.json'
    if not index.is_file():
        return []
    bets = json.loads(index.read_text(encoding='utf-8'))['bets']
    return [b for b in bets if not b.get('readout') and b.get('readout_due') and str(b['readout_due']) <= today]


def cmd_due(args) -> int:
    for b in due(args.project_root.resolve(), args.today or dt.date.today().isoformat()):
        print(f"{b['feature']}: {b.get('hypothesis', 'bet')} / {b.get('metric', '?')} readout due {b['readout_due']}, "
              f"evidence grade {b.get('evidence_grade', '?')}")
    return 0


def stats(root: Path) -> dict:
    lanes = collections.Counter()
    rework = intercepts = 0
    durations = []
    for st in sorted(root.rglob('state.yaml')):
        text = st.read_text(encoding='utf-8', errors='replace')
        lane = scalar(text, 'lane')[:2]
        if not lane.startswith('L'):
            continue
        lanes[lane] += 1
        rec = outcome_from_state(st.parent)
        rework += rec['rework_rounds']
        intercepts += rec['intercepts']
        durations += [int(g['duration_min']) for g in read_items(text, 'gates')
                      if isinstance(g, dict) and str(g.get('duration_min', '')).isdigit()]
    by_gate, by_stage, by_class = collections.Counter(), collections.Counter(), collections.Counter()
    grades: dict[str, dict[str, int]] = {}
    outcomes = sorted(out_dir(root.parent if root.name == '.sdlc' else root).glob('*.json'))
    for p in outcomes:
        if p.name == 'index.json':
            continue
        rec = json.loads(p.read_text(encoding='utf-8'))
        esc = rec.get('escape') or {}
        if esc:
            by_gate[esc.get('gate') or '?'] += 1
            by_stage[esc.get('should_have_caught_at') or '?'] += 1
            by_class[esc.get('defect_class') or '?'] += 1
        bet = rec.get('bet') or {}
        if bet:
            row = grades.setdefault(bet.get('evidence_grade') or '?', {s: 0 for s in (*STATUSES, 'open')})
            row[(rec.get('readout') or {}).get('status') or 'open'] += 1
    return {'lanes': dict(sorted(lanes.items())), 'features': sum(lanes.values()), 'rework_rounds': rework,
            'intercepts': intercepts, 'mean_duration_min': (sum(durations) // len(durations)) if durations else None,
            'escapes_by_gate': dict(by_gate), 'escapes_by_stage': dict(by_stage),
            'escapes_by_class': dict(by_class), 'bets_by_grade': dict(sorted(grades.items()))}


def cmd_stats(args) -> int:
    root = args.root.resolve()
    s = stats(root)
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return 0
    print(f'SDLC 度量（{root}）')
    print('================================')
    if not s['features']:
        print('无已记账 feature')
        return 0
    lanes = ' '.join(f"{k}={v}" for k, v in s['lanes'].items())
    print(f"泳道分布: {lanes}（共 {s['features']}）")
    print(f"独立审查拦截: {s['intercepts']} 个自审未发现问题")
    print(f"返工轮次: {s['rework_rounds']}")
    if s['mean_duration_min'] is not None:
        print(f"平均耗时: {s['mean_duration_min']} 分钟/票")
    high = s['lanes'].get('L3', 0) + s['lanes'].get('L4', 0)
    print(f"L3+ 占比: {high * 100 // s['features']}%（>40% 判定过严）")
    gates = ', '.join(f'{k}={v}' for k, v in s['escapes_by_gate'].items()) or '无记录'
    print(f'逃逸缺陷（按本应拦住它的闸门）: {gates}')
    for grade, row in s['bets_by_grade'].items():
        print(f"赌注 {grade}: 成立 {row['supported']} · 推翻 {row['refuted']} · 不确定 {row['inconclusive']} · 待读数 {row['open']}")
    if not s['bets_by_grade']:
        print('赌注: 无记录')
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    rec = sub.add_parser('record')
    rec.add_argument('--feature', type=Path, required=True)
    ro = sub.add_parser('readout')
    ro.add_argument('--project-root', type=Path, required=True)
    ro.add_argument('--feature', required=True)
    ro.add_argument('--status', required=True)
    ro.add_argument('--evidence', required=True)
    ro.add_argument('--note')
    du = sub.add_parser('due')
    du.add_argument('--project-root', type=Path, required=True)
    du.add_argument('--today')
    stt = sub.add_parser('stats')
    stt.add_argument('--root', type=Path, default=Path('.sdlc'))
    stt.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    return {'record': cmd_record, 'readout': cmd_readout, 'due': cmd_due, 'stats': cmd_stats}[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
