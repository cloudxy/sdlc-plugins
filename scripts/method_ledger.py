#!/usr/bin/env python3
"""Method change ledger: every edit to a method source file carries a change record.

Method sources are what a model reads as instructions: skills/** text (not evals/, skill scripts or files with a
GENERATED header), agent-sources/**, workflow/registry.json, adapters/*.json and adapters/*/HOST.md. Generated
outputs (agents/, host agent files, commands/, generated references) are checked by `render --check` instead.

  seed    --reason R                 first baseline plus a seed record (refuses to overwrite)
  check                              METHODCHANGE (error) for an edit not in the baseline, or a baseline entry no
                                     record vouches for; METHODPENDING (warning) for behavioral records awaiting a verdict
  record  --id ID --kind behavioral|editorial --reason R [--failure-form F] [--verdict V] [--evidence P …] [--files P …]
          [--unchecked-evidence REASON]
                                     records the unregistered changes (all, or only --files) and moves the baseline to them;
                                     a verdict other than pending needs the same evidence as `verdict`
  verdict --id ID --verdict V --evidence P … [--unchecked-evidence REASON]
                                     appends the outcome to an existing behavioral record. Evidence that is a
                                     behavior_smoke.py directory must contain a run whose tree carries exactly the
                                     recorded file digests (no verdict from text edited afterwards); a verdict without
                                     such run evidence needs --unchecked-evidence with the reason

failure_form follows writing-skills "match the form to the failure": discipline (knows the rule, skips it),
shape (output has the wrong form), omission (a required element is missing), conditional (depends on a condition).
Editorial records are for edits that change no behaviour (typos, links, layout); method reviews sample them.
Exit: 0 ok · 1 violations · 2 usage.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.pdf', '.zip', '.gz'}
KINDS = ('behavioral', 'editorial')
FORMS = ('discipline', 'shape', 'omission', 'conditional')
VERDICTS = ('pending', 'improved', 'no_change', 'regressed')


def _generated(path: Path) -> bool:
    try:
        head = path.read_bytes()[:400].decode('utf-8', 'ignore')
    except OSError:
        return False
    return 'GENERATED' in head


def method_files(root: Path) -> dict[str, str]:
    paths = []
    for top in ('skills', 'agent-sources'):
        base = root / top
        if base.is_dir():
            paths += [p for p in base.rglob('*') if p.is_file()]
    paths += [p for p in [root / 'workflow' / 'registry.json'] if p.is_file()]
    paths += sorted((root / 'adapters').glob('*.json')) + sorted((root / 'adapters').glob('*/HOST.md'))
    out = {}
    for p in paths:
        rel = p.relative_to(root).as_posix()
        parts = rel.split('/')
        if (p.suffix.lower() in BINARY or '__pycache__' in parts or 'evals' in parts
                or (parts[0] == 'skills' and len(parts) > 2 and parts[2] == 'scripts') or _generated(p)):
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(sorted(out.items()))


def _paths(root: Path):
    m = root / 'maintainers'
    return m / 'method-baseline.json', m / 'method-changes'


def _load_records(changes: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted(changes.glob('*.json'))] if changes.is_dir() else []


def check(root: Path) -> tuple[list[str], list[str]]:
    baseline_path, changes = _paths(root)
    if not baseline_path.is_file():
        return [f'[METHODCHANGE] {baseline_path.relative_to(root)} missing: run method_ledger.py seed'], []
    baseline = json.loads(baseline_path.read_text(encoding='utf-8'))['files']
    current = method_files(root)
    errors, warnings = [], []
    for rel in sorted(set(baseline) | set(current)):
        if baseline.get(rel) != current.get(rel):
            what = 'new file' if rel not in baseline else ('deleted' if rel not in current else 'edited')
            errors.append(f'[METHODCHANGE] {rel}: {what} without a change record '
                          f'(python3 scripts/method_ledger.py record --id … --kind behavioral|editorial --reason …)')
    vouched: dict[str, set] = {}
    records = _load_records(changes)
    for rec in records:
        for rel, digest in rec.get('files', {}).items():
            vouched.setdefault(rel, set()).add(digest)
        if rec.get('kind') == 'behavioral' and rec.get('verdict') == 'pending':
            warnings.append(f"[METHODPENDING] {rec['id']}: behavioral change awaiting evidence "
                            f"({len(rec.get('files', {}))} files)")
    for rel, digest in baseline.items():
        if digest not in vouched.get(rel, set()):
            errors.append(f'[METHODCHANGE] {rel}: baseline entry has no change record (baseline edited by hand?)')
    return errors, warnings


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))


def _write_record(changes: Path, rec: dict) -> Path:
    changes.mkdir(parents=True, exist_ok=True)
    target = changes / f"{_now():%Y-%m-%d}-{rec['id']}.json"
    if target.exists() or any(p.name.endswith(f"-{rec['id']}.json") for p in changes.glob('*.json')):
        raise SystemExit(f"method_ledger: record id {rec['id']} already exists")
    target.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return target


def cmd_seed(root: Path, args) -> int:
    baseline_path, changes = _paths(root)
    if baseline_path.exists():
        print('method_ledger: baseline exists; use record', file=sys.stderr)
        return 2
    files = method_files(root)
    _write_record(changes, {'id': 'seed', 'at': _now().isoformat(timespec='seconds'), 'kind': 'editorial',
                            'failure_form': 'n/a', 'verdict': 'n/a', 'reason': args.reason, 'evidence': [],
                            'decided_by': args.decided_by, 'files': files})
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps({'version': 1, 'files': files}, ensure_ascii=False, indent=1) + '\n',
                             encoding='utf-8')
    print(f'seeded {len(files)} method files')
    return 0


def cmd_record(root: Path, args) -> int:
    baseline_path, changes = _paths(root)
    if args.kind == 'behavioral' and (args.failure_form not in FORMS or args.verdict not in VERDICTS):
        print(f'method_ledger: behavioral records need --failure-form {FORMS} and --verdict {VERDICTS}', file=sys.stderr)
        return 2
    baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
    current = method_files(root)
    changed = {rel: current.get(rel) for rel in sorted(set(baseline['files']) | set(current))
               if baseline['files'].get(rel) != current.get(rel)}
    if args.files:
        unknown = sorted(set(args.files) - set(changed))
        if unknown:
            print(f'method_ledger: not unregistered method changes: {", ".join(unknown)}', file=sys.stderr)
            return 2
        changed = {k: v for k, v in changed.items() if k in set(args.files)}
    if not changed:
        print('method_ledger: nothing to record', file=sys.stderr)
        return 2
    if args.kind == 'behavioral':  # a verdict given at record time needs the same evidence as `verdict`
        problem = evidence_problem(args.id, {k: v for k, v in changed.items() if v is not None}, args.verdict,
                                   args.evidence, args.unchecked_evidence)
        if problem:
            print(f'method_ledger: {problem}', file=sys.stderr)
            return 2
    rec = {'id': args.id, 'at': _now().isoformat(timespec='seconds'), 'kind': args.kind,
           'failure_form': args.failure_form if args.kind == 'behavioral' else 'n/a',
           'verdict': args.verdict if args.kind == 'behavioral' else 'n/a', 'reason': args.reason,
           'evidence': args.evidence or [], 'decided_by': args.decided_by,
           'files': {k: v for k, v in changed.items() if v is not None},
           'deleted': sorted(k for k, v in changed.items() if v is None)}
    if args.unchecked_evidence:
        rec['unchecked_evidence'] = args.unchecked_evidence
    target = _write_record(changes, rec)
    for rel, digest in changed.items():
        if digest is None:
            baseline['files'].pop(rel, None)
        else:
            baseline['files'][rel] = digest
    baseline['files'] = dict(sorted(baseline['files'].items()))
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'recorded {len(changed)} files in {target.relative_to(root)}')
    return 0


def _evidence_path(entry: str) -> Path:
    return Path(entry.split(' (', 1)[0].strip()).expanduser()


def evidence_matches(files: dict, evidence: list) -> tuple[bool, bool]:
    """(has run evidence, some run tree carries exactly these file digests)."""
    manifests = []
    for entry in evidence or []:
        trees = _evidence_path(entry) / 'trees'
        if trees.is_dir():
            manifests += [json.loads(m.read_text(encoding='utf-8')) for m in sorted(trees.glob('*/manifest.json'))]
    if not manifests:
        return False, False
    return True, any(all(m.get('method_hashes', {}).get(rel) == digest for rel, digest in files.items())
                     for m in manifests)


def evidence_problem(change_id: str, files: dict, verdict: str, evidence: list, unchecked: str) -> str:
    """Why a non-pending verdict may not be recorded with this evidence ('' when it may)."""
    if verdict == 'pending':
        return ''
    has_runs, matches = evidence_matches(files, evidence)
    if has_runs and not matches:
        return (f'evidence was not produced on the recorded text of {change_id} '
                '(no run tree carries the recorded file digests); rerun on the current text')
    if not has_runs and not unchecked:
        return 'no behavior_smoke run evidence; pass --unchecked-evidence with the reason'
    return ''


def cmd_verdict(root: Path, args) -> int:
    _, changes = _paths(root)
    hits = [p for p in changes.glob('*.json') if p.name.endswith(f'-{args.id}.json')]
    if len(hits) != 1 or args.verdict not in VERDICTS:
        print('method_ledger: one existing record id and a valid --verdict are required', file=sys.stderr)
        return 2
    rec = json.loads(hits[0].read_text(encoding='utf-8'))
    if rec.get('kind') != 'behavioral':
        print('method_ledger: only behavioral records carry a verdict', file=sys.stderr)
        return 2
    problem = evidence_problem(args.id, rec.get('files', {}), args.verdict, args.evidence, args.unchecked_evidence)
    if problem:
        print(f'method_ledger: {problem}', file=sys.stderr)
        return 2
    rec.setdefault('history', []).append({'at': _now().isoformat(timespec='seconds'), 'from': rec['verdict'],
                                          'to': args.verdict, 'evidence': args.evidence or [],
                                          'unchecked_evidence': args.unchecked_evidence or ''})
    rec['verdict'] = args.verdict
    rec['evidence'] = list(dict.fromkeys(rec.get('evidence', []) + (args.evidence or [])))
    hits[0].write_text(json.dumps(rec, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{args.id}: {rec["history"][-1]["from"]} → {args.verdict}')
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', type=Path, default=ROOT)
    sub = ap.add_subparsers(dest='command', required=True)
    seed = sub.add_parser('seed')
    seed.add_argument('--reason', required=True)
    seed.add_argument('--decided-by', default='maintainer')
    sub.add_parser('check')
    rec = sub.add_parser('record')
    rec.add_argument('--id', required=True)
    rec.add_argument('--kind', choices=KINDS, required=True)
    rec.add_argument('--reason', required=True)
    rec.add_argument('--failure-form', default='n/a')
    rec.add_argument('--verdict', default='n/a')
    rec.add_argument('--evidence', nargs='*')
    rec.add_argument('--decided-by', default='maintainer')
    rec.add_argument('--files', nargs='*')
    rec.add_argument('--unchecked-evidence')
    ver = sub.add_parser('verdict')
    ver.add_argument('--id', required=True)
    ver.add_argument('--verdict', required=True)
    ver.add_argument('--evidence', nargs='*')
    ver.add_argument('--unchecked-evidence')
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if args.command == 'seed':
        return cmd_seed(root, args)
    if args.command == 'record':
        return cmd_record(root, args)
    if args.command == 'verdict':
        return cmd_verdict(root, args)
    errors, warnings = check(root)
    for line in errors:
        print('✗ ' + line)
    for line in warnings:
        print('⚠ ' + line)
    if not errors:
        print(f'✓ method ledger: {len(method_files(root))} method files registered')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
