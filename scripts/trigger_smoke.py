#!/usr/bin/env python3
"""Trigger smoke: does a plain user message make the host load the intended skill, per method tree?

  run    --skills a,b --reps N --arm LABEL [--ref REF] --out DIR --budget-usd X
         For each skills/<s>/evals/triggers.json row {id, prompt, should_trigger}, start the host with this plugin,
         only Read and Skill available and no instruction to load anything, and record which skills it loads
         (Skill tool calls, plus Reads of a skills/<name>/SKILL.md). Arms and trees work as in behavior_smoke.py:
         `current` is the working tree, any other label needs --ref, trees are exported to a content-named cache
         and the evidence keeps only DIR/trees/<id>/manifest.json. An ok record is skipped on rerun.
  score  --out DIR [--json]
         Per skill, prompt and arm: how often the target skill loaded, and accuracy against should_trigger.
         Scoring is mechanical; there is nothing to judge.

Limits: the first turns of one host (default 2: a skill loads in the first action, then the answer is written),
not a whole session; a skill can still be reached later in a real session. The
skill listing the host shows also depends on the host version, which each record notes.
Run arms one after another (see behavior_smoke.py on the shared session quota).
Exit: 0 ok · 2 usage · 3 budget stop · 4 quota stop (as in behavior_smoke.py).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from behavior_smoke import BEIJING, ROOT, ensure_tree, prepare_tree, quota_hit, redact, spent

SKILL_READ = re.compile(r'/skills/([a-z0-9-]+)/SKILL\.md$')


def load_rows(skill: str) -> list[dict]:
    rows = json.loads((ROOT / 'skills' / skill / 'evals' / 'triggers.json').read_text(encoding='utf-8'))['triggers']
    for row in rows:
        if not isinstance(row.get('should_trigger'), bool) or not row.get('prompt'):
            raise SystemExit(f'trigger_smoke: skills/{skill}/evals/triggers.json row {row.get("id")} is malformed')
    return rows


def build_command(tree: Path, prompt: str, per_run_usd: float, max_turns: int) -> list[str]:
    return [os.environ.get('CLAUDE_BIN', 'claude'), '--plugin-dir', str(tree), '--tools', 'Read,Skill',
            '--allowedTools', 'Read,Skill', '--permission-mode', 'dontAsk', '--no-session-persistence',
            '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--settings', '{"disableAllHooks":true}',
            '--output-format', 'stream-json', '--verbose', '--max-turns', str(max_turns),
            '--max-budget-usd', f'{per_run_usd:g}', '-p', prompt]


def parse_stream(stdout: str) -> dict:
    out = {'loaded': [], 'tools': None, 'skills_listed': None}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            out.update(model=event.get('model'), tools=event.get('tools'), skills_listed=event.get('skills'))
        if event.get('type') == 'assistant':
            for item in (event.get('message') or {}).get('content') or []:
                if not isinstance(item, dict) or item.get('type') != 'tool_use':
                    continue
                args = item.get('input') or {}
                if item.get('name') == 'Skill':
                    out['loaded'].append(str(args.get('skill') or args.get('command') or ''))
                elif item.get('name') == 'Read':
                    m = SKILL_READ.search(str(args.get('file_path') or ''))
                    if m:
                        out['loaded'].append(f'read:{m.group(1)}')
        if event.get('type') == 'result':
            out.update(subtype=event.get('subtype'), is_error=event.get('is_error'), reply=event.get('result') or '',
                       cost=event.get('total_cost_usd'), api_error_status=event.get('api_error_status'))
    return out


def loaded_target(loaded: list[str], skill: str) -> bool:
    return any(name.split(':')[-1] == skill for name in loaded)


def run_one(args, arm_dir: Path, tree: Path, manifest: dict, skill: str, row: dict, rep: int, host: str,
            tree_check: str = 'ok') -> dict:
    name = f"{skill}-t{row['id']}-r{rep}"
    target = arm_dir / f'{name}.json'
    now = dt.datetime.now(BEIJING)
    cwd = Path(tempfile.mkdtemp(prefix=f"trigger-{manifest['tree_id']}-"))  # empty: no project files to suggest a skill
    command = build_command(tree, row['prompt'], args.per_run_usd, args.max_turns)
    record = {'at': now.isoformat(timespec='seconds'), 'skill': skill, 'trigger_id': str(row['id']),
              'should_trigger': row['should_trigger'], 'arm': args.arm, 'arm_ref': args.ref, 'rep': rep,
              'tree_id': manifest['tree_id'], 'tree_check': tree_check, 'host_version': host,
              'prompt': row['prompt'], 'command': command,
              'scope': f'first {args.max_turns} turns of one host session with Read and Skill only'}
    started = dt.datetime.now()
    proc = subprocess.Popen(command, cwd=cwd, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGTERM)
        stdout, stderr = proc.communicate()
    parsed = parse_stream(stdout or '')
    # Reaching the turn or per-run budget limit is a normal end here: the load decision is the first action, and only
    # what loaded before the limit is measured (a long answer to a prompt that loads nothing can exhaust the budget).
    finished = (parsed.get('subtype') in ('success', 'error_max_turns', 'error_max_budget_usd')
                and not parsed.get('api_error_status'))
    status = 'timeout' if timed_out else ('ok' if finished and 'session limit' not in parsed.get('reply', '') else
                                          'host_failure')
    record.update(exit_code=proc.returncode, duration_s=round((dt.datetime.now() - started).total_seconds(), 1),
                  status=status, subtype=parsed.get('subtype'), model=parsed.get('model'), cost_usd=parsed.get('cost'),
                  tools=parsed.get('tools'), skills_listed=parsed.get('skills_listed'), loaded=parsed['loaded'],
                  triggered=loaded_target(parsed['loaded'], skill), reply=parsed.get('reply', ''),
                  stderr=(stderr or '')[-2000:])
    if target.exists():
        k = 2
        while (arm_dir / f'{name}.attempt-{k}.json').exists():
            k += 1
        target.rename(arm_dir / f'{name}.attempt-{k}.json')
    target.write_text(redact(json.dumps(record, ensure_ascii=False, indent=1)) + '\n', encoding='utf-8')
    return record


def cmd_run(args) -> int:
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,30}', args.arm) or args.arm in ('trees', 'work'):
        print('trigger_smoke: --arm is a short lowercase label', file=sys.stderr)
        return 2
    if args.arm != 'current' and not args.ref:
        print('trigger_smoke: an arm other than current needs --ref', file=sys.stderr)
        return 2
    args.ref = args.ref or 'WORKTREE'
    plan = [(s.strip(), row) for s in args.skills.split(',') if s.strip() for row in load_rows(s.strip())]
    if args.dry_run:
        for skill, row in plan:
            print(skill, row['id'], row['should_trigger'], ' '.join(build_command(Path('<tree>'), '<prompt>',
                                                                                    args.per_run_usd, args.max_turns)))
        return 0
    args.out = args.out.resolve()
    arm_dir = args.out / args.arm
    arm_dir.mkdir(parents=True, exist_ok=True)
    tree, manifest = prepare_tree(args.out, args.ref)
    host = subprocess.run([os.environ.get('CLAUDE_BIN', 'claude'), '--version'], text=True,
                          capture_output=True).stdout.strip()
    for rep in range(1, args.reps + 1):  # rep-major order: an interruption leaves every prompt equally covered
        for skill, row in plan:
            target = arm_dir / f"{skill}-t{row['id']}-r{rep}.json"
            if target.exists() and json.loads(target.read_text(encoding='utf-8')).get('status') == 'ok':
                continue
            total, n = spent(arm_dir)
            if total + (total / n if n else args.per_run_usd) > args.budget_usd:
                print(f'budget stop: spent {total:.2f} of {args.budget_usd:.2f} before {target.name}')
                return 3
            tree, manifest, check = ensure_tree(args.out, args.ref, tree, manifest)
            rec = run_one(args, arm_dir, tree, manifest, skill, row, rep, host, check)
            print(f"{args.arm} {target.stem}: {rec['status']} loaded={rec['loaded']} "
                  f"${rec.get('cost_usd') or 0:.3f} {rec['duration_s']}s", flush=True)
            if quota_hit(rec):
                print(f"quota stop: {rec['reply'].strip()[:120]}")
                return 4
    total, n = spent(arm_dir)
    print(f'{args.arm}: {n} costed runs, ${total:.2f} of ${args.budget_usd:.2f}')
    return 0


def score(out: Path) -> dict:
    rows: dict[tuple, dict] = {}
    for arm_dir in sorted(p for p in out.iterdir() if p.is_dir() and p.name not in ('trees', 'work')):
        for p in sorted(arm_dir.glob('*.json')):
            if '.attempt-' in p.name:
                continue
            rec = json.loads(p.read_text(encoding='utf-8'))
            if rec.get('status') != 'ok':
                continue
            key = (rec['skill'], rec['trigger_id'], rec['should_trigger'], rec['arm'])
            r = rows.setdefault(key, {'runs': 0, 'triggered': 0, 'correct': 0, 'other': {}})
            r['runs'] += 1
            r['triggered'] += rec['triggered']
            r['correct'] += rec['triggered'] == rec['should_trigger']
            for name in rec['loaded']:
                if name.split(':')[-1] != rec['skill']:
                    r['other'][name] = r['other'].get(name, 0) + 1
    arms: dict[str, dict] = {}
    for (skill, _tid, should, arm), r in rows.items():
        a = arms.setdefault(arm, {'should': [0, 0], 'should_not': [0, 0]})
        bucket = a['should' if should else 'should_not']
        bucket[0] += r['correct']
        bucket[1] += r['runs']
    return {'rows': [dict(skill=k[0], trigger_id=k[1], should_trigger=k[2], arm=k[3], **v)
                     for k, v in sorted(rows.items())], 'arms': arms}


def cmd_score(args) -> int:
    s = score(args.out.resolve())
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return 0
    print('| skill | prompt | should | arm | loaded target | correct | other skills loaded |')
    print('|---|---|---|---|---|---|---|')
    for r in s['rows']:
        other = ', '.join(f'{k}×{v}' for k, v in sorted(r['other'].items())) or '—'
        print(f"| {r['skill']} | {r['trigger_id']} | {'yes' if r['should_trigger'] else 'no'} | {r['arm']} | "
              f"{r['triggered']}/{r['runs']} | {r['correct']}/{r['runs']} | {other} |")
    for arm, a in sorted(s['arms'].items()):
        print(f"{arm}: should trigger {a['should'][0]}/{a['should'][1]} correct, "
              f"should not {a['should_not'][0]}/{a['should_not'][1]} correct")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run')
    run.add_argument('--skills', required=True)
    run.add_argument('--reps', type=int, default=3)
    run.add_argument('--arm', required=True)
    run.add_argument('--ref')
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--budget-usd', type=float, required=True)
    run.add_argument('--per-run-usd', type=float, default=0.5)
    run.add_argument('--max-turns', type=int, default=2)
    run.add_argument('--timeout', type=int, default=300)
    run.add_argument('--dry-run', action='store_true')
    sc = sub.add_parser('score')
    sc.add_argument('--out', type=Path, required=True)
    sc.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    if args.command == 'run':
        if args.reps < 1 or args.budget_usd <= 0 or args.per_run_usd <= 0 or args.max_turns < 1:
            ap.error('reps, budget, per-run cap and max turns must be positive')
        return cmd_run(args)
    return cmd_score(args)


if __name__ == '__main__':
    sys.exit(main())
