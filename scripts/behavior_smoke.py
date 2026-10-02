#!/usr/bin/env python3
"""Repeated read-only behavior smoke runs of this plugin's own eval cases, one method tree per arm.

  run    --skill S --cases 1,3 --reps N --arm current|baseline [--baseline-ref REF] --out DIR --budget-usd X
         One record per (case, rep) under DIR/<arm>/. Case text and fixtures come from the current repository
         (they are the test); only the method tree varies by arm. Both arms run from exported copies under
         DIR/trees/<tree-id>/ so later edits cannot leak into a run and the path does not name the arm.
         An existing ok record is skipped, so an interrupted run resumes; host failures are retried.
  judge  --out DIR --file judgments.json
         judgments.json maps each record's path (relative to DIR) to {verdict: pass|fail|deviation, quote}.
         Every ok record needs one, and its quote must occur verbatim in that run's reply.

This is a next-turn smoke with Read only: it shows current behaviour and its spread across repetitions. It is not
a blind rubric comparison (blind_eval.py), a whole workflow or a human trial.

Run arms one after another. Each run spends the operator's own subscription session quota, which the operator's
interactive session shares: on 2026-10-02 four parallel processes hit "You've hit your session limit" within ten
minutes and stopped that session too. Those runs are recorded as host failures and retried on the next invocation.
Exit: 0 ok · 1 missing/invalid judgments · 2 usage · 3 budget stop.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEIJING = dt.timezone(dt.timedelta(hours=8))
SECRETS = [
    (re.compile(r'(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}'), '<REDACTED>'),  # not 'task-notification'
    (re.compile(r'(?i)(Bearer\s+)[A-Za-z0-9._~+/-]{15,}'), r'\1<REDACTED>'),
    (re.compile(r'(?i)("?(?:authorization|api[_-]?key|access[_-]?token|secret)"?\s*[:=]\s*"?)[^\s",]{12,}'), r'\1<REDACTED>'),
]
METHOD_DIRS = ('skills', 'agents', 'agent-sources', 'workflow', 'commands', 'adapters')


def redact(text: str) -> str:
    for pattern, repl in SECRETS:
        text = pattern.sub(repl, text)
    return text


def git(*args: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True, **kw)


def export_tree(ref: str, staging: Path) -> Path:
    """The plugin as of `ref` (a git ref, or WORKTREE for tracked plus untracked files), with vendor/ added."""
    staging.mkdir(parents=True)
    if ref == 'WORKTREE':
        names = git('ls-files', '-co', '--exclude-standard', '-z', capture_output=True).stdout.decode().split('\0')
        for name in filter(None, names):
            src = ROOT / name
            if src.is_file():
                dst = staging / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
    else:
        archive = git('archive', '--format=tar', ref, capture_output=True).stdout
        with tempfile.NamedTemporaryFile(suffix='.tar') as fh:
            fh.write(archive)
            fh.flush()
            with tarfile.open(fh.name) as tar:
                tar.extractall(staging)
    vendor = ROOT / 'vendor'  # upstream originals are git-ignored and identical for both arms
    for child in (vendor.iterdir() if vendor.is_dir() else []):
        if child.is_dir() and not (staging / 'vendor' / child.name).exists():
            shutil.copytree(child, staging / 'vendor' / child.name)
    return staging


def tree_manifest(tree: Path) -> dict:
    files = {}
    for top in METHOD_DIRS:
        for p in sorted((tree / top).rglob('*')) if (tree / top).is_dir() else []:
            if p.is_file() and '/evals/files/' not in p.as_posix():
                files[p.relative_to(tree).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    digest = hashlib.sha256(''.join(f'{k}\0{v}\n' for k, v in files.items()).encode()).hexdigest()
    return {'tree_id': digest[:12], 'method_hashes': files}


def prepare_tree(out: Path, ref: str) -> tuple[Path, dict]:
    staging = out / 'trees' / f'.staging-{os.getpid()}'
    if staging.exists():
        shutil.rmtree(staging)
    export_tree(ref, staging / 'sdlc-workflow')
    manifest = tree_manifest(staging / 'sdlc-workflow')
    final = out / 'trees' / manifest['tree_id']
    if final.exists():
        shutil.rmtree(staging)
    else:
        staging.rename(final)
        (final / 'manifest.json').write_text(json.dumps(dict(manifest, ref=ref), ensure_ascii=False, indent=1))
    return final / 'sdlc-workflow', manifest


def load_case(skill: str, case_id: str) -> dict:
    cases = json.loads((ROOT / 'skills' / skill / 'evals' / 'evals.json').read_text(encoding='utf-8'))['evals']
    for case in cases:
        if str(case['id']) == case_id:
            return case
    raise SystemExit(f'behavior_smoke: no case {skill}/{case_id}')


def copy_fixtures(skill: str, case: dict, cwd: Path) -> dict:
    fixtures = {}
    for f in case.get('files') or []:
        rel = Path(f)
        if rel.parts[:2] != ('evals', 'files') or len(rel.parts) < 4:
            raise SystemExit(f'behavior_smoke: fixture outside evals/files/<case>/: {f}')
        src = ROOT / 'skills' / skill / rel
        dst = cwd.joinpath(*rel.parts[3:])
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        fixtures[dst.relative_to(cwd).as_posix()] = hashlib.sha256(src.read_bytes()).hexdigest()
    return fixtures


def build_prompt(tree: Path, skill: str, case: dict) -> str:
    return (f'You are handling the next turn of an isolated dialogue scenario. '
            f'Read and follow {tree}/skills/{skill}/SKILL.md, and read its relevant references as needed. '
            'Only file reads are available in this test; do not write files, delegate or claim to have performed '
            'unavailable actions. Respond in Chinese to the user with the next useful response. Do not simulate '
            'future user answers. This is a dialogue smoke test, not a completed workflow or build.\n\n'
            'User and supplied conversation context:\n' + case['prompt'])


def build_command(tree: Path, prompt: str, per_run_usd: float) -> list[str]:
    return [os.environ.get('CLAUDE_BIN', 'claude'), '--plugin-dir', str(tree), '--tools', 'Read',
            '--allowedTools', 'Read', '--add-dir', str(tree), '--permission-mode', 'dontAsk',
            '--no-session-persistence', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
            '--settings', '{"disableAllHooks":true}', '--output-format', 'stream-json', '--verbose',
            '--max-turns', '8', '--max-budget-usd', f'{per_run_usd:g}', '-p', prompt]


def parse_stream(stdout: str) -> dict:
    result = {}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get('type') == 'system' and event.get('subtype') == 'init':
            result['model'] = event.get('model')
        if isinstance(event, dict) and event.get('type') == 'result':
            result.update(subtype=event.get('subtype'), is_error=event.get('is_error'),
                          reply=event.get('result') or '', cost=event.get('total_cost_usd'))
    return result


def spent(arm_dir: Path) -> tuple[float, int]:
    total, n = 0.0, 0
    for p in arm_dir.glob('*.json'):
        rec = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(rec.get('cost_usd'), (int, float)):
            total += rec['cost_usd']
            n += 1
    return total, n


def run_one(args, arm_dir: Path, tree: Path, manifest: dict, case: dict, rep: int, host: str) -> dict:
    name = f"{args.skill}-{case['id']}-r{rep}"
    target = arm_dir / f'{name}.json'
    now = dt.datetime.now(BEIJING)
    cwd = args.out / 'work' / f"{manifest['tree_id']}-{name}-{now:%H%M%S%f}"
    cwd.mkdir(parents=True)
    fixtures = copy_fixtures(args.skill, case, cwd)
    prompt = build_prompt(tree, args.skill, case)
    command = build_command(tree, prompt, args.per_run_usd)
    record = {'at': now.isoformat(timespec='seconds'), 'skill': args.skill, 'case_id': str(case['id']),
              'arm': args.arm, 'arm_ref': args.ref, 'rep': rep, 'tree_id': manifest['tree_id'],
              'tree_path': str(tree), 'host_version': host, 'cwd': str(cwd), 'fixtures': fixtures,
              'scope': 'one next-turn read-only smoke; not a blind comparison, whole workflow or human trial',
              'prompt': prompt, 'command': command}
    started = dt.datetime.now()
    proc = subprocess.Popen(command, cwd=cwd, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate()
    parsed = parse_stream(stdout or '')
    ok = (not timed_out and proc.returncode == 0 and parsed.get('subtype') == 'success'
          and not parsed.get('is_error'))
    record.update(exit_code=proc.returncode, duration_s=round((dt.datetime.now() - started).total_seconds(), 1),
                  status='timeout' if timed_out else ('ok' if ok else 'host_failure'),
                  model=parsed.get('model'), cost_usd=parsed.get('cost'), reply=parsed.get('reply', ''),
                  stdout=stdout or '', stderr=(stderr or '')[-4000:])
    if target.exists():  # keep the earlier non-ok attempt as evidence
        k = 2
        while (arm_dir / f'{name}.attempt-{k}.json').exists():
            k += 1
        target.rename(arm_dir / f'{name}.attempt-{k}.json')
    target.write_text(redact(json.dumps(record, ensure_ascii=False, indent=1)) + '\n', encoding='utf-8')
    return record


def cmd_run(args) -> int:
    if args.arm == 'baseline' and not args.baseline_ref:
        print('behavior_smoke: --arm baseline needs --baseline-ref', file=sys.stderr)
        return 2
    args.ref = args.baseline_ref if args.arm == 'baseline' else 'WORKTREE'
    cases = [load_case(args.skill, c.strip()) for c in args.cases.split(',') if c.strip()]
    if args.dry_run:
        for case in cases:
            print(' '.join(build_command(Path('<tree>'), f"<prompt for {args.skill}/{case['id']}>", args.per_run_usd)))
        return 0
    args.out = args.out.resolve()
    arm_dir = args.out / args.arm
    arm_dir.mkdir(parents=True, exist_ok=True)
    tree, manifest = prepare_tree(args.out, args.ref)
    host = subprocess.run([os.environ.get('CLAUDE_BIN', 'claude'), '--version'], text=True,
                          capture_output=True).stdout.strip()
    for case in cases:
        for rep in range(1, args.reps + 1):
            target = arm_dir / f"{args.skill}-{case['id']}-r{rep}.json"
            if target.exists() and json.loads(target.read_text(encoding='utf-8')).get('status') == 'ok':
                continue
            total, n = spent(arm_dir)
            expected = total / n if n else args.per_run_usd
            if total + expected > args.budget_usd:
                target.write_text(json.dumps({'skill': args.skill, 'case_id': str(case['id']), 'arm': args.arm,
                                              'rep': rep, 'status': 'budget_stop', 'cost_usd': None,
                                              'spent_usd': round(total, 4), 'budget_usd': args.budget_usd},
                                             ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
                print(f'budget stop: spent {total:.2f} of {args.budget_usd:.2f} before {target.name}')
                return 3
            rec = run_one(args, arm_dir, tree, manifest, case, rep, host)
            print(f"{args.arm} {target.stem}: {rec['status']} ${rec.get('cost_usd') or 0:.3f} {rec['duration_s']}s")
    total, n = spent(arm_dir)
    print(f'{args.arm}: {n} costed runs, ${total:.2f} of ${args.budget_usd:.2f}')
    return 0


def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def cmd_judge(args) -> int:
    out = args.out.resolve()
    judgments = json.loads(Path(args.file).read_text(encoding='utf-8'))
    problems, table = [], {}
    for arm_dir in sorted(p for p in out.iterdir() if p.is_dir() and p.name in ('current', 'baseline')):
        for rec_path in sorted(arm_dir.glob('*.json')):
            if '.attempt-' in rec_path.name:
                continue
            rec = json.loads(rec_path.read_text(encoding='utf-8'))
            key = rec_path.relative_to(out).as_posix()
            row = table.setdefault((rec['skill'], rec['case_id'], rec['arm']),
                                   {'pass': 0, 'fail': 0, 'deviation': 0, 'not_judged': 0, 'host': 0})
            if rec.get('status') != 'ok':
                row['host'] += 1
                continue
            j = judgments.get(key)
            if not j:
                problems.append(f'{key}: no judgment')
                row['not_judged'] += 1
                continue
            if j.get('verdict') not in ('pass', 'fail', 'deviation'):
                problems.append(f'{key}: verdict must be pass|fail|deviation')
                continue
            quote = normalize(j.get('quote') or '')
            if not quote or quote not in normalize(rec.get('reply', '')):
                problems.append(f'{key}: quote not found in this run\'s reply')
                continue
            row[j['verdict']] += 1
    print('| skill | case | arm | pass | deviation | fail | not judged | host/budget |')
    print('|---|---|---|---|---|---|---|---|')
    for (skill, case, arm), r in sorted(table.items()):
        print(f"| {skill} | {case} | {arm} | {r['pass']} | {r['deviation']} | {r['fail']} | {r['not_judged']} | {r['host']} |")
    for p in problems:
        print('✗', p)
    return 1 if problems else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run')
    run.add_argument('--skill', required=True)
    run.add_argument('--cases', required=True)
    run.add_argument('--reps', type=int, default=5)
    run.add_argument('--arm', choices=['current', 'baseline'], required=True)
    run.add_argument('--baseline-ref')
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--budget-usd', type=float, required=True)
    run.add_argument('--per-run-usd', type=float, default=1.0)
    run.add_argument('--timeout', type=int, default=150)
    run.add_argument('--dry-run', action='store_true')
    judge = sub.add_parser('judge')
    judge.add_argument('--out', type=Path, required=True)
    judge.add_argument('--file', required=True)
    args = ap.parse_args(argv)
    if args.command == 'run':
        if args.reps < 1 or args.budget_usd <= 0 or args.per_run_usd <= 0:
            ap.error('reps, budget and per-run cap must be positive')
        return cmd_run(args)
    return cmd_judge(args)


if __name__ == '__main__':
    sys.exit(main())
