#!/usr/bin/env python3
"""Gate catalog: each gate tag, the fixture that asserts it, where it came from and when to review it.

  check [--strict]                   GATECATALOG warnings: tags without a fixture or origin, origins of tags
                                     that no longer exist, reviews that are due. --strict exits 1 on any.
  report [--project-root R]          the catalog as a table, plus escapes recorded in R/.sdlc/_outcomes/
  seed-origins                       record origins of uncatalogued tags from git history (added = first commit
                                     whose diff introduces the tag; review_by = added + 182 days)

Tags come from scripts/check-sdlc.sh (`red TAG`, tags handed to need_images) and scripts/workflow.py
(`bad("TAG"`, `("error", "TAG"`). Fixtures are `assert_tag TAG` in scripts/test-check-sdlc.sh and assert lines
naming the tag in scripts/test_workflow.py. Origins live in maintainers/gate-provenance.json.

A tag is a retirement candidate only when all hold: its review is due, no escape is linked to it during the
observation window, it has a stated cost, and removing it lowers no security, data-correctness or release
obligation. Zero intercepts alone never qualify. The maintainer decides (maintainers/README.md).
Exit: 0 ok · 1 strict findings · 2 usage.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'scripts/check-sdlc.sh': [r'\bred\s+([A-Z][A-Z0-9-]+)\b', r'need_images\s+"[^"]*"\s+([A-Z][A-Z0-9-]+)'],
    'scripts/workflow.py': [r'\bbad\(\s*["\']([A-Z][A-Z0-9-]+)["\']', r'\(\s*["\']error["\']\s*,\s*["\']([A-Z][A-Z0-9-]+)["\']'],
}
IGNORED = {'SUMMARY', 'USAGE'}  # the violation count and argument errors, not gates


def _read(root: Path, rel: str) -> str:
    p = root / rel
    return p.read_text(encoding='utf-8') if p.is_file() else ''


def gate_tags(root: Path) -> dict[str, str]:
    tags = {}
    for rel, patterns in SOURCES.items():
        text = _read(root, rel)
        for pat in patterns:
            for m in re.finditer(pat, text):
                if m.group(1) not in IGNORED:
                    tags.setdefault(m.group(1), rel)
    return dict(sorted(tags.items()))


def fixture_tags(root: Path) -> set[str]:
    found = {re.sub(r'^SDLC-', '', t.strip('\'"'))
             for t in re.findall(r'assert_tag\s+(\S+)', _read(root, 'scripts/test-check-sdlc.sh'))}
    for line in _read(root, 'scripts/test_workflow.py').splitlines():
        if 'assert' in line:
            found |= set(re.findall(r'["\']([A-Z][A-Z0-9-]{2,})["\']', line))
    return found


def provenance(root: Path) -> dict:
    p = root / 'maintainers' / 'gate-provenance.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else {}


def escapes(project_root: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in sorted((project_root / '.sdlc' / '_outcomes').glob('*.json')):
        try:
            rec = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        gate = (rec.get('escape') or {}).get('gate') if isinstance(rec, dict) else None
        if gate:
            out.setdefault(gate, []).append(rec.get('feature') or p.stem)
    return out


def catalog(root: Path, today: str | None = None) -> dict:
    tags = gate_tags(root)
    fixtures = fixture_tags(root)
    origin = provenance(root)
    today = today or dt.date.today().isoformat()
    return {
        'tags': tags,
        'without_fixture': sorted(t for t in tags if t not in fixtures),
        'without_origin': sorted(t for t in tags if t not in origin),
        'stale_origin': sorted(t for t in origin if t not in tags),
        'review_due': sorted(t for t in tags if t in origin and str(origin[t].get('review_by', '9999')) <= today),
        'origin': origin,
    }


def _first_commit(root: Path, tag: str, rel: str) -> tuple[str, str]:
    out = subprocess.run(['git', '-C', str(root), 'log', '--reverse', '--format=%h|%cs|%s', '-S', tag, '--', rel],
                         capture_output=True, text=True).stdout.splitlines()
    if not out:
        return '', ''
    h, date, subject = out[0].split('|', 2)
    return date, f'{h} {subject}'


def cmd_seed(root: Path) -> int:
    path = root / 'maintainers' / 'gate-provenance.json'
    data = provenance(root)
    added = 0
    for tag, rel in gate_tags(root).items():
        if tag in data:
            continue
        date, origin = _first_commit(root, tag, rel)
        date = date or dt.date.today().isoformat()
        review = (dt.date.fromisoformat(date) + dt.timedelta(days=182)).isoformat()
        data[tag] = {'source': rel, 'added': date, 'origin': origin or 'not in git history',
                     'review_by': review, 'cost': '', 'note': ''}
        added += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(data.items())), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'recorded origins for {added} tags')
    return 0


def findings(cat: dict) -> list[str]:
    lines = [f'[GATECATALOG] {t}: no fixture asserts this tag' for t in cat['without_fixture']]
    lines += [f'[GATECATALOG] {t}: no recorded origin (gate_catalog.py seed-origins)' for t in cat['without_origin']]
    lines += [f'[GATECATALOG] {t}: origin recorded for a tag that no longer exists' for t in cat['stale_origin']]
    lines += [f"[GATECATALOG] {t}: review due since {cat['origin'][t].get('review_by')}" for t in cat['review_due']]
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', type=Path, default=ROOT)
    sub = ap.add_subparsers(dest='command', required=True)
    chk = sub.add_parser('check')
    chk.add_argument('--strict', action='store_true')
    rep = sub.add_parser('report')
    rep.add_argument('--project-root', type=Path)
    sub.add_parser('seed-origins')
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if args.command == 'seed-origins':
        return cmd_seed(root)
    cat = catalog(root)
    if args.command == 'check':
        lines = findings(cat)
        for line in lines:
            print('⚠ ' + line)
        if not lines:
            print(f"✓ gate catalog: {len(cat['tags'])} tags, each with a fixture and a recorded origin")
        return 1 if (args.strict and lines) else 0
    esc = escapes(args.project_root.resolve()) if args.project_root else {}
    print('| tag | source | fixture | added | review by | escapes |')
    print('|---|---|---|---|---|---|')
    for tag, rel in cat['tags'].items():
        o = cat['origin'].get(tag, {})
        print(f"| {tag} | {rel} | {'no' if tag in cat['without_fixture'] else 'yes'} | {o.get('added', '')} | "
              f"{o.get('review_by', '')} | {len(esc.get(tag, []))} |")
    return 0


if __name__ == '__main__':
    sys.exit(main())
