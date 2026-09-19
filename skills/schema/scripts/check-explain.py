#!/usr/bin/env python3
"""MySQL tabular EXPLAIN hygiene check; not a performance certification.

Requires named columns. Unsupported/empty plans fail explicitly. Scan budget is
configurable; use the engine/project-specific verifier for other plan formats.
"""
import argparse
import re
import sys
from pathlib import Path


def parse(text, max_scan_rows=1000):
    header = None
    plans = []
    for line in text.splitlines():
        if '|' not in line or re.fullmatch(r'[\s+|:-]+', line):
            continue
        cols = [c.strip() for c in line.strip().strip('|').split('|')]
        lowered = [c.lower() for c in cols]
        if {'table', 'type', 'key', 'rows'}.issubset(lowered):
            header = lowered
            continue
        if header is not None and len(cols) == len(header):
            plans.append(dict(zip(header, cols)))
    if not plans:
        return ['UNSUPPORTED: expected a MySQL tabular plan with table/type/key/rows headers; no plan validated']
    issues = []
    for plan in plans:
        table = plan['table']
        try:
            rows = float(plan['rows'])
            if not __import__('math').isfinite(rows) or rows < 0:
                raise ValueError
        except ValueError:
            issues.append(f'UNSUPPORTED row estimate for {table}: {plan["rows"]}')
            continue
        access = plan['type'].upper()
        if access not in {'ALL', 'INDEX', 'RANGE', 'INDEX_MERGE', 'REF', 'REF_OR_NULL', 'EQ_REF', 'CONST', 'SYSTEM', 'FULLTEXT'}:
            issues.append(f'UNSUPPORTED access type for {table}: {access}')
            continue
        if access in ('ALL', 'INDEX') and rows > max_scan_rows:
            issues.append(f'SCAN BUDGET on {table}: type={access}, key={plan["key"]}, rows={rows:g} > {max_scan_rows}')
        if rows > max_scan_rows and any(x in plan.get('extra', '').lower() for x in ('using filesort', 'using temporary')):
            issues.append(f'SORT/TEMP REVIEW on {table}: rows={rows:g} exceeds configured diagnostic budget')
    return issues


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', nargs='?')
    parser.add_argument('--max-scan-rows', type=int, default=1000)
    args = parser.parse_args()
    if args.max_scan_rows < 0:
        parser.error('scan budget must be nonnegative')
    try:
        text = Path(args.file).read_text() if args.file else sys.stdin.read()
        issues = parse(text, args.max_scan_rows)
    except OSError as error:
        issues = [str(error)]
    for issue in issues:
        print(f'✗ [EXPLAIN] {issue}')
    if not issues:
        print('✓ MySQL EXPLAIN structural/budget check passed; runtime performance remains to be verified')
    sys.exit(min(len(issues), 125))
