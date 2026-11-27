#!/usr/bin/env python3
"""Result records for closed and lightweight SDLC work: quality outcomes and efficiency metrics.

  record      --feature DIR          on phase: Closed, write <project>/.sdlc/_outcomes/<feature>.json and index.json
  record-run  --project-root R --id ID --track TRACK [efficiency/quality flags]
                                     lightweight run record in <project>/.sdlc/_outcomes/runs/<id>.json
                                     (no phase: Closed or state.yaml required)
  readout     --project-root R --feature F --status supported|refuted|inconclusive --evidence PATH [--note TEXT]
                                     close a bet with its readout (the analyst's retro or cycle readout)
  due         --project-root R [--today YYYY-MM-DD]
                                     bets whose readout date has passed without a readout (one line each)
  stats       [--root DIR] [--json]  quality (lanes, rework, intercepts, escapes, bets) + efficiency metrics
                                     with explicit missing-metric reporting (check-sdlc.sh --stats)

A state records its bet as `bet: {hypothesis: H-n, metric, evidence_grade: E0-E4, readout_due}` and a defect fix
records where the defect escaped and how Process QA welded the seam shut as `escape: {origin_feature, origin_release,
should_have_caught_at, gate, defect_class, seam_fix, verified_by}`. Due bets are reported, never enforced: a late
readout must not block unrelated work.
Exit: 0 ok · 2 usage or a feature that is not closed.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1])  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

import argparse
import collections
import datetime as dt
import json
import re
import sys
from pathlib import Path

from gates.state_view import _top, _scalar, read_items, read_map

STATUSES = ('supported', 'refuted', 'inconclusive')
TRACKS = ('fast_track', 'scoped_team', 'scoped', 'full_sdlc', 'clarify_first', 'single_hat')
QUALITY_STATUSES = ('pass', 'fail', 'partial', 'unverified')
EFFICIENCY_FIELDS = (
    'wall_duration_min',
    'spawn_count',
    'model_calls',
    'tool_calls',
    'input_tokens',
    'output_tokens',
    'overhead_ratio',
)


def scalar(text: str, key: str) -> str:
    inline, _ = _top(text, key)
    return _scalar(inline) if inline else ''


def _opt_float(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _opt_int(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _safe_id(raw: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '-', raw.strip()).strip('-.')
    if not cleaned:
        raise ValueError('run id must contain at least one alphanumeric character')
    return cleaned


def project_root(feature: Path) -> Path:
    for d in [feature, *feature.parents]:
        if (d / 'sdlc.config.yaml').is_file():
            return d
    return feature.parent.parent  # <root>/.sdlc/<feature>


def _feature_efficiency(feature: Path, text: str, gates: list[dict]) -> dict:
    """Extract optional efficiency telemetry from a feature directory without fabricating missing values."""
    gate_durations = [
        float(g['duration_min'])
        for g in gates
        if isinstance(g, dict) and _opt_float(g.get('duration_min')) is not None
    ]
    top_duration = _opt_float(scalar(text, 'wall_duration_min') or scalar(text, 'duration_min'))
    wall_duration = top_duration if top_duration is not None else (sum(gate_durations) if gate_durations else None)

    spawn_count = _opt_int(scalar(text, 'spawn_count'))
    if spawn_count is None:
        runs_dir = feature / 'runs'
        packets_dir = feature / 'packets'
        if runs_dir.is_dir():
            manifests = list(runs_dir.glob('*-manifest.json'))
            if manifests:
                spawn_count = len(manifests)
        if spawn_count is None and packets_dir.is_dir():
            packets = [p for p in packets_dir.glob('*.md') if not p.name.startswith('.')]
            if packets:
                spawn_count = len(packets)

    eff = {
        'track': scalar(text, 'track') or None,
        'wall_duration_min': round(wall_duration, 2) if wall_duration is not None else None,
        'spawn_count': spawn_count,
        'model_calls': _opt_int(scalar(text, 'model_calls')),
        'tool_calls': _opt_int(scalar(text, 'tool_calls')),
        'input_tokens': _opt_int(scalar(text, 'input_tokens')),
        'output_tokens': _opt_int(scalar(text, 'output_tokens')),
        'overhead_ratio': _opt_float(scalar(text, 'overhead_ratio')),
    }
    eff['missing_metrics'] = [k for k in EFFICIENCY_FIELDS if eff.get(k) is None]
    return eff


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
            'escape': read_map(text, 'escape') or None,
            'efficiency': _feature_efficiency(feature, text, gates)}


def out_dir(root: Path) -> Path:
    return root / '.sdlc' / '_outcomes'


def runs_dir(root: Path) -> Path:
    return out_dir(root) / 'runs'


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


def cmd_record_run(args) -> int:
    try:
        run_id = _safe_id(args.id)
    except ValueError as exc:
        print(f'outcomes: {exc}', file=sys.stderr)
        return 2
    if args.track not in TRACKS:
        print(f'outcomes: --track must be one of {TRACKS}', file=sys.stderr)
        return 2
    if args.quality_status not in QUALITY_STATUSES:
        print(f'outcomes: --quality-status must be one of {QUALITY_STATUSES}', file=sys.stderr)
        return 2

    digest_data: dict = {}
    if args.session_digest:
        digest_path = args.session_digest.resolve()
        if not digest_path.is_file():
            print(f'outcomes: session digest file not found: {digest_path}', file=sys.stderr)
            return 2
        try:
            digest_data = json.loads(digest_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            print(f'outcomes: invalid JSON in {digest_path}: {exc}', file=sys.stderr)
            return 2

    def _pick_float(cli_val, *digest_keys):
        if cli_val is not None:
            return round(float(cli_val), 3)
        for k in digest_keys:
            v = _opt_float(digest_data.get(k))
            if v is not None:
                return round(v, 3)
        return None

    def _pick_int(cli_val, *digest_keys):
        if cli_val is not None:
            return int(cli_val)
        for k in digest_keys:
            v = _opt_int(digest_data.get(k))
            if v is not None:
                return v
        if 'tool_uses' in digest_keys and isinstance(digest_data.get('tool_uses'), dict):
            return sum(int(v) for v in digest_data['tool_uses'].values() if isinstance(v, int))
        return None

    eff = {
        'track': args.track,
        'wall_duration_min': _pick_float(args.duration_min, 'wall_duration_min', 'duration_min'),
        'spawn_count': _pick_int(args.spawns, 'spawns', 'spawn_count'),
        'model_calls': _pick_int(args.model_calls, 'model_calls'),
        'tool_calls': _pick_int(args.tool_calls, 'tool_calls', 'tool_uses'),
        'input_tokens': _pick_int(args.input_tokens, 'input_tokens'),
        'output_tokens': _pick_int(args.output_tokens, 'output_tokens'),
        'overhead_ratio': _pick_float(args.overhead_ratio, 'overhead_ratio'),
    }
    if eff['overhead_ratio'] is not None and not (0.0 <= eff['overhead_ratio'] <= 1.0):
        print('outcomes: --overhead-ratio must be between 0.0 and 1.0', file=sys.stderr)
        return 2
    eff['missing_metrics'] = [k for k in EFFICIENCY_FIELDS if eff.get(k) is None]

    record = {
        'schema_version': 1,
        'kind': 'lightweight_run',
        'run_id': run_id,
        'track': args.track,
        'domain': args.domain or None,
        'role': args.role or None,
        'quality': {
            'status': args.quality_status,
            'rework_rounds': args.rework_rounds,
        },
        'efficiency': eff,
        'note': args.note or '',
        'recorded_at': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
    }
    root = args.project_root.resolve()
    target = runs_dir(root) / f'{run_id}.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'recorded run {target}')
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


def _aggregate_efficiency(closed_records: list[dict], run_records: list[dict]) -> dict:
    tracks = collections.Counter()
    quality_counts = collections.Counter()
    samples: dict[str, list[float]] = {k: [] for k in EFFICIENCY_FIELDS}
    missing_counts: dict[str, int] = {k: 0 for k in EFFICIENCY_FIELDS}

    all_effs: list[dict] = []
    for rec in closed_records:
        eff = rec.get('efficiency') if isinstance(rec.get('efficiency'), dict) else {}
        if eff.get('track'):
            tracks[str(eff['track'])] += 1
        all_effs.append(eff)

    for rec in run_records:
        eff = rec.get('efficiency') if isinstance(rec.get('efficiency'), dict) else {}
        track = rec.get('track') or eff.get('track')
        if track:
            tracks[str(track)] += 1
        q = rec.get('quality') if isinstance(rec.get('quality'), dict) else {}
        quality_counts[str(q.get('status') or 'unverified')] += 1
        all_effs.append(eff)

    for eff in all_effs:
        for field in EFFICIENCY_FIELDS:
            val = _opt_float(eff.get(field))
            if val is None:
                missing_counts[field] += 1
            else:
                samples[field].append(val)

    total = len(all_effs)
    metrics = {}
    missing_summary = []
    for field in EFFICIENCY_FIELDS:
        vals = samples[field]
        miss = missing_counts[field]
        mean_val = round(sum(vals) / len(vals), 2) if vals else None
        metrics[field] = {'count': len(vals), 'missing': miss, 'mean': mean_val}
        if total > 0 and miss > 0:
            missing_summary.append(f'{field} ({miss}/{total} 缺测)')

    return {
        'records_total': total,
        'closed_outcomes': len(closed_records),
        'lightweight_runs': len(run_records),
        'tracks': dict(sorted(tracks.items())),
        'run_quality': dict(sorted(quality_counts.items())),
        'metrics': metrics,
        'missing_metrics': missing_summary,
    }


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
    seam_closed = seam_open = 0
    grades: dict[str, dict[str, int]] = {}
    proj = root.parent if root.name == '.sdlc' else root
    outcomes_base = out_dir(proj)
    closed_records: list[dict] = []
    outcomes = sorted(outcomes_base.glob('*.json')) if outcomes_base.is_dir() else []
    for p in outcomes:
        if p.name == 'index.json':
            continue
        rec = json.loads(p.read_text(encoding='utf-8'))
        closed_records.append(rec)
        esc = rec.get('escape') or {}
        if esc:
            by_gate[esc.get('gate') or '?'] += 1
            by_stage[esc.get('should_have_caught_at') or '?'] += 1
            by_class[esc.get('defect_class') or '?'] += 1
            if str(esc.get('seam_fix') or '').strip() and str(esc.get('verified_by') or '').strip():
                seam_closed += 1
            else:
                seam_open += 1
        bet = rec.get('bet') or {}
        if bet:
            row = grades.setdefault(bet.get('evidence_grade') or '?', {s: 0 for s in (*STATUSES, 'open')})
            row[(rec.get('readout') or {}).get('status') or 'open'] += 1

    run_records: list[dict] = []
    rdir = runs_dir(proj)
    if rdir.is_dir():
        for p in sorted(rdir.glob('*.json')):
            run_records.append(json.loads(p.read_text(encoding='utf-8')))

    return {'lanes': dict(sorted(lanes.items())), 'features': sum(lanes.values()), 'rework_rounds': rework,
            'intercepts': intercepts, 'mean_duration_min': (sum(durations) // len(durations)) if durations else None,
            'escapes_by_gate': dict(by_gate), 'escapes_by_stage': dict(by_stage),
            'escapes_by_class': dict(by_class), 'escapes_seam_closed': seam_closed, 'escapes_seam_open': seam_open,
            'bets_by_grade': dict(sorted(grades.items())),
            'efficiency': _aggregate_efficiency(closed_records, run_records)}


def cmd_stats(args) -> int:
    root = args.root.resolve()
    s = stats(root)
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return 0
    print(f'SDLC 度量（{root}）')
    print('================================')
    eff = s['efficiency']
    if not s['features'] and not eff['records_total']:
        print('无已记账 feature')
        return 0
    if s['features']:
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
        if s['escapes_seam_closed'] or s['escapes_seam_open']:
            print(f"过程 QA 接缝补漏: 已焊死 {s['escapes_seam_closed']} · 未闭环 {s['escapes_seam_open']}")
        for grade, row in s['bets_by_grade'].items():
            print(f"赌注 {grade}: 成立 {row['supported']} · 推翻 {row['refuted']} · 不确定 {row['inconclusive']} · 待读数 {row['open']}")
        if not s['bets_by_grade']:
            print('赌注: 无记录')

    if eff['records_total']:
        print('--------------------------------')
        print(f"效率度量: 共 {eff['records_total']} 条（关闭特性 {eff['closed_outcomes']} · 轻量运行 {eff['lightweight_runs']}）")
        if eff['tracks']:
            tracks_str = ' '.join(f'{k}={v}' for k, v in eff['tracks'].items())
            print(f'轨道分布: {tracks_str}')
        if eff['run_quality']:
            rq_str = ' '.join(f'{k}={v}' for k, v in eff['run_quality'].items())
            print(f'轻量运行质量: {rq_str}')
        labels = {
            'wall_duration_min': ('端到端耗时', '分钟'),
            'spawn_count': ('子代理派发', '次'),
            'model_calls': ('模型调用', '次'),
            'tool_calls': ('工具调用', '次'),
            'input_tokens': ('输入 Token', ''),
            'output_tokens': ('输出 Token', ''),
            'overhead_ratio': ('流程开销占比', ''),
        }
        for key, (label, unit) in labels.items():
            m = eff['metrics'][key]
            if m['count'] > 0:
                miss_note = f"（{m['missing']} 条缺测）" if m['missing'] else ''
                suffix = f' {unit}' if unit else ''
                print(f"{label}: 均值 {m['mean']}{suffix}（样本 {m['count']}）{miss_note}")
            else:
                print(f"{label}: 缺测（0/{eff['records_total']}）")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    rec = sub.add_parser('record')
    rec.add_argument('--feature', type=Path, required=True)

    run_p = sub.add_parser('record-run')
    run_p.add_argument('--project-root', type=Path, default=Path('.'))
    run_p.add_argument('--id', required=True)
    run_p.add_argument('--track', required=True, choices=TRACKS)
    run_p.add_argument('--domain')
    run_p.add_argument('--role')
    run_p.add_argument('--duration-min', type=float)
    run_p.add_argument('--spawns', type=int)
    run_p.add_argument('--model-calls', type=int)
    run_p.add_argument('--tool-calls', type=int)
    run_p.add_argument('--input-tokens', type=int)
    run_p.add_argument('--output-tokens', type=int)
    run_p.add_argument('--overhead-ratio', type=float)
    run_p.add_argument('--quality-status', default='unverified', choices=QUALITY_STATUSES)
    run_p.add_argument('--rework-rounds', type=int)
    run_p.add_argument('--note')
    run_p.add_argument('--session-digest', type=Path)

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
    return {
        'record': cmd_record,
        'record-run': cmd_record_run,
        'readout': cmd_readout,
        'due': cmd_due,
        'stats': cmd_stats,
    }[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
