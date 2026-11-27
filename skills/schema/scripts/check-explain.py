#!/usr/bin/env python3
"""Multi-engine EXPLAIN hygiene & scan-budget verifier (PostgreSQL, MySQL, SQLite); not a latency certification.

Supported formats:
  1. MySQL tabular EXPLAIN (`| table | type | key | rows | ... |`)
  2. PostgreSQL text EXPLAIN / EXPLAIN ANALYZE (`Seq Scan on <table> ... (cost=... rows=<N> width=...)`)
  3. PostgreSQL JSON EXPLAIN (`[{"Plan": {"Node Type": ..., "Plan Rows": ...}}]`)
  4. SQLite EXPLAIN QUERY PLAN (`SCAN <table>` / `SEARCH <table> USING INDEX ...`)

Unsupported or empty plans fail explicitly so a configured gate never silently passes.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

PG_NODE_RE = re.compile(
    r"^\s*(?:->\s*)?(Seq Scan|Index Only Scan|Index Scan|Bitmap Heap Scan|Bitmap Index Scan)\s+(?:using\s+\S+\s+)?on\s+([\w.\"]+)\b.*?\(cost=[\d.]+\.\.[\d.]+\s+rows=(\d+)\s+width=\d+\)",
    re.I,
)
PG_DISK_SORT_RE = re.compile(r"Sort Method:\s*external\s+(?:merge|sort)\s+Disk:", re.I)
SQLITE_EQP_HEAD_RE = re.compile(r"^\s*(?:QUERY PLAN\b|`?--|\|--|\d+\|\d+\|\d+\|)", re.I | re.M)
SQLITE_SCAN_RE = re.compile(r"(?:^|\|\s*|--\s*)(SCAN|SEARCH)\s+(?:TABLE\s+)?([\w.\"]+)(.*)$", re.I)


def _parse_mysql_tabular(text: str, max_scan_rows: int) -> tuple[bool, list[str]]:
    header = None
    plans = []
    for line in text.splitlines():
        if "|" not in line or re.fullmatch(r"[\s+|:-]+", line):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        lowered = [c.lower() for c in cols]
        if {"table", "type", "key", "rows"}.issubset(lowered):
            header = lowered
            continue
        if header is not None and len(cols) == len(header):
            plans.append(dict(zip(header, cols)))
    if not plans:
        return False, []
    issues = []
    for plan in plans:
        table = plan["table"]
        try:
            rows = float(plan["rows"])
            if not math.isfinite(rows) or rows < 0:
                raise ValueError
        except ValueError:
            issues.append(f'UNSUPPORTED row estimate for {table}: {plan["rows"]}')
            continue
        access = plan["type"].upper()
        if access not in {"ALL", "INDEX", "RANGE", "INDEX_MERGE", "REF", "REF_OR_NULL", "EQ_REF", "CONST", "SYSTEM", "FULLTEXT"}:
            issues.append(f"UNSUPPORTED access type for {table}: {access}")
            continue
        if access in ("ALL", "INDEX") and rows > max_scan_rows:
            issues.append(f'SCAN BUDGET on {table}: type={access}, key={plan["key"]}, rows={rows:g} > {max_scan_rows}')
        if rows > max_scan_rows and any(x in plan.get("extra", "").lower() for x in ("using filesort", "using temporary")):
            issues.append(f"SORT/TEMP REVIEW on {table}: rows={rows:g} exceeds configured diagnostic budget")
    return True, issues


def _parse_pg_json(text: str, max_scan_rows: int) -> tuple[bool, list[str]]:
    # Locate JSON array/object containing PostgreSQL "Plan"
    for m in re.finditer(r"(\[\s*\{\s*\"Plan\"|\{\s*\"Plan\")", text):
        snippet = text[m.start():]
        try:
            data = json.loads(snippet)
        except ValueError:
            # Try fenced block extraction if embedded in markdown
            continue
        roots = data if isinstance(data, list) else [data]
        if not roots or not all(isinstance(r, dict) and isinstance(r.get("Plan"), dict) for r in roots):
            continue
        issues: list[str] = []

        def walk(node: dict) -> None:
            ntype = str(node.get("Node Type", ""))
            rel = str(node.get("Relation Name") or node.get("Alias") or "<subquery>")
            rows = float(node.get("Plan Rows", 0) or 0)
            if ntype == "Seq Scan" and rows > max_scan_rows:
                issues.append(f"SCAN BUDGET on {rel} (PostgreSQL JSON): Seq Scan Plan Rows={rows:g} > {max_scan_rows}")
            if node.get("Sort Space Type") == "Disk" and rows > max_scan_rows:
                issues.append(f"SORT/TEMP REVIEW on {rel} (PostgreSQL JSON): external disk sort rows={rows:g}")
            for child in node.get("Plans") or []:
                if isinstance(child, dict):
                    walk(child)

        for r in roots:
            walk(r["Plan"])
        return True, issues
    return False, []


def _parse_pg_text(text: str, max_scan_rows: int) -> tuple[bool, list[str]]:
    matches = [PG_NODE_RE.match(ln) for ln in text.splitlines()]
    nodes = [m for m in matches if m is not None]
    if not nodes:
        return False, []
    issues: list[str] = []
    for m in nodes:
        node_type, table, rows_s = m.group(1), m.group(2).strip('"'), int(m.group(3))
        if node_type.lower() == "seq scan" and rows_s > max_scan_rows:
            issues.append(f"SCAN BUDGET on {table} (PostgreSQL): Seq Scan rows={rows_s} > {max_scan_rows}")
    if PG_DISK_SORT_RE.search(text):
        issues.append("SORT/TEMP REVIEW (PostgreSQL): external disk sort detected; verify work_mem or supporting index")
    return True, issues


def _parse_sqlite_eqp(text: str, _max_scan_rows: int) -> tuple[bool, list[str]]:
    lines = text.splitlines()
    ops = []
    for ln in lines:
        m = SQLITE_SCAN_RE.search(ln)
        if m:
            ops.append((m.group(1).upper(), m.group(2).strip('"'), m.group(3) or ""))
    if not ops and not SQLITE_EQP_HEAD_RE.search(text):
        return False, []
    if not ops:
        return False, []
    issues: list[str] = []
    for verb, table, tail in ops:
        if verb == "SCAN" and not re.search(r"USING\s+(?:COVERING\s+)?INDEX|PRIMARY\s+KEY", tail, re.I):
            if not table.startswith("sqlite_"):
                issues.append(f"FULL TABLE SCAN on {table} (SQLite EQP): SCAN without index{tail.rstrip()}")
    if re.search(r"USE\s+TEMP\s+B-TREE\s+FOR\s+(?:ORDER\s+BY|GROUP\s+BY|DISTINCT)", text, re.I):
        issues.append("SORT/TEMP REVIEW (SQLite EQP): USE TEMP B-TREE detected; verify composite index order")
    return True, issues


def parse(text: str, max_scan_rows: int = 1000) -> list[str]:
    for parser_fn in (_parse_mysql_tabular, _parse_pg_json, _parse_pg_text, _parse_sqlite_eqp):
        matched, issues = parser_fn(text, max_scan_rows)
        if matched:
            return issues
    return [
        "UNSUPPORTED: expected MySQL tabular EXPLAIN, PostgreSQL EXPLAIN (text or FORMAT JSON), "
        "or SQLite EXPLAIN QUERY PLAN; no valid execution plan found"
    ]


def self_test() -> int:
    mysql_ok = "| id | table | type | key | rows | Extra |\n| 1 | orders | ref | idx_tenant | 42 | Using where |\n"
    mysql_bad = "| id | table | type | key | rows | Extra |\n| 1 | orders | ALL | NULL | 5000 | Using filesort |\n"
    pg_ok = "Index Scan using idx_orders_tenant on orders  (cost=0.42..8.44 rows=12 width=64)\n"
    pg_bad = "Seq Scan on audit_logs  (cost=0.00..1850.00 rows=25000 width=120)\n  Sort Method: external merge  Disk: 4096kB\n"
    pg_json_bad = '[{"Plan": {"Node Type": "Seq Scan", "Relation Name": "invoices", "Plan Rows": 9000}}]'
    sqlite_ok = "QUERY PLAN\n|--SEARCH orders USING INDEX idx_orders_user (user_id=?)\n"
    sqlite_bad = "QUERY PLAN\n|--SCAN orders\n`--USE TEMP B-TREE FOR ORDER BY\n"

    assert parse(mysql_ok) == [], parse(mysql_ok)
    assert len(parse(mysql_bad)) == 2, parse(mysql_bad)
    assert parse(pg_ok) == [], parse(pg_ok)
    assert len(parse(pg_bad)) == 2, parse(pg_bad)
    assert len(parse(pg_json_bad)) == 1 and "invoices" in parse(pg_json_bad)[0], parse(pg_json_bad)
    assert parse(sqlite_ok) == [], parse(sqlite_ok)
    assert len(parse(sqlite_bad)) == 2, parse(sqlite_bad)
    assert any("UNSUPPORTED" in x for x in parse("just prose without any plan")), parse("just prose")
    print("self-test ok")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?")
    parser.add_argument("--max-scan-rows", type=int, default=1000)
    args = parser.parse_args()
    if args.max_scan_rows < 0:
        parser.error("scan budget must be nonnegative")
    try:
        text = Path(args.file).read_text(encoding="utf-8", errors="replace") if args.file else sys.stdin.read()
        issues = parse(text, args.max_scan_rows)
    except OSError as error:
        issues = [str(error)]
    for issue in issues:
        print(f"✗ [EXPLAIN] {issue}")
    if not issues:
        print("✓ EXPLAIN structural/budget check passed (MySQL/PostgreSQL/SQLite); runtime latency remains to be verified")
    sys.exit(min(len(issues), 125))
