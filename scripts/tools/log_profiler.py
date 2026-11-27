#!/usr/bin/env python3
"""Read-only defensive log profiler: line/level/error stats + embedded JSON schema inference with secret redaction.

  python3 scripts/tools/log_profiler.py <log_file> [--max-lines 50000] [--top 10] [--json | --md]

Pure Python stdlib, zero network, strictly read-only. Redacts credentials/tokens before output.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path
from typing import Any

LEVEL_RE = re.compile(r"\b(CRITICAL|FATAL|ERROR|WARN(?:ING)?|INFO|DEBUG)\b")
TS_RE = re.compile(r"\b(20\d{2}[-/]\d{2}[-/]\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\b")
HTTP_STATUS_RE = re.compile(r'(?:"\s+|\bstatus[=:\s]+)([1-5]\d{2})\b', re.I)
SECRET_RES = [
    # 1. Full Authorization header (including quoted JSON or plain header with Bearer/Basic/Token + payload)
    (
        re.compile(
            r"""(?i)(["']?authorization["']?\s*[:=]\s*)(?:"(?:bearer|basic|token)\s+[^"]+"|'(?:bearer|basic|token)\s+[^']+'|(?:bearer|basic|token)\s+[^\s,;}\]]+)"""
        ),
        r"\1[REDACTED]",
    ),
    # 2. Standalone Bearer/Token credential anywhere
    (
        re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._\-+/=]{8,}"),
        r"\1[REDACTED]",
    ),
    # 3. Database / cache URIs with embedded password
    (
        re.compile(r"(?i)((?:mysql|postgres|postgresql|redis|mongodb)(?:\+\w+)?://[^:\s/]+:)([^@\s]+)(@)"),
        r"\1[REDACTED]\3",
    ),
    # 4. Quoted JSON / key-value credentials (skip already-redacted placeholders)
    (
        re.compile(
            r"""(?i)(["']?(?:password|passwd|pwd|secret|access_token|refresh_token|id_token|token|api[_-]?key|authorization|cookie|set-cookie)["']?\s*[:=]\s*)(?!\[REDACTED\])(?:"[^"]*"|'[^']*'|[^\s,;}\]]+)"""
        ),
        r"\1[REDACTED]",
    ),
    # 5. High-confidence token prefixes anywhere on the line
    (
        re.compile(r"\b(?:AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{16,}|xox[baprs]-[A-Za-z0-9-]{10,})\b"),
        "[REDACTED]",
    ),
]
NORM_NUM_RE = re.compile(r"\b(?:0x[0-9a-f]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|\d{4,})\b", re.I)


def redact_text(s: str) -> str:
    out = s
    for pat, repl in SECRET_RES:
        out = pat.sub(repl, out)
    return out


def _extract_json_payloads(line: str) -> list[Any]:
    """Extract whole-line JSON or trailing/embedded JSON objects from a log line."""
    s = line.strip()
    if not s:
        return []
    dec = json.JSONDecoder()
    # Try whole line first
    if s[0] in "{[":
        try:
            obj = json.loads(s)
            if isinstance(obj, (dict, list)):
                return [obj]
        except ValueError:
            pass
    # Scan for first embedded '{'
    idx = s.find("{")
    if idx > 0:
        try:
            obj, _ = dec.raw_decode(s[idx:])
            if isinstance(obj, dict):
                return [obj]
        except ValueError:
            pass
    return []


def _infer_schema(obj: Any, schema: dict[str, dict[str, Any]], prefix: str = "", depth: int = 0, max_depth: int = 6) -> None:
    if depth > max_depth:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            entry = schema.setdefault(path, {"types": set(), "nulls": 0, "count": 0, "max_len": 0})
            entry["count"] += 1
            if v is None:
                entry["nulls"] += 1
                entry["types"].add("null")
            elif isinstance(v, bool):
                entry["types"].add("bool")
            elif isinstance(v, int):
                entry["types"].add("int")
            elif isinstance(v, float):
                entry["types"].add("float")
            elif isinstance(v, str):
                entry["types"].add("str")
                entry["max_len"] = max(entry["max_len"], len(v))
            elif isinstance(v, list):
                entry["types"].add("list")
                if v:
                    sample_items = v[:5]
                    for item in sample_items:
                        if isinstance(item, (dict, list)):
                            _infer_schema(item, schema, f"{path}[]", depth + 1, max_depth)
                        else:
                            it_entry = schema.setdefault(f"{path}[]", {"types": set(), "nulls": 0, "count": 0, "max_len": 0})
                            it_entry["count"] += 1
                            it_entry["types"].add(type(item).__name__ if item is not None else "null")
                            if isinstance(item, str):
                                it_entry["max_len"] = max(it_entry["max_len"], len(item))
            elif isinstance(v, dict):
                entry["types"].add("dict")
                _infer_schema(v, schema, path, depth + 1, max_depth)
    elif isinstance(obj, list):
        for item in obj[:5]:
            _infer_schema(item, schema, f"{prefix}[]" if prefix else "[]", depth + 1, max_depth)


def profile_log(path: str | Path, max_lines: int = 50000, top_n: int = 10) -> dict[str, Any]:
    p = Path(path).resolve()
    if not p.is_file():
        raise ValueError(f"log file not found: {path}")

    levels: collections.Counter[str] = collections.Counter()
    http_statuses: collections.Counter[str] = collections.Counter()
    error_sigs: collections.Counter[str] = collections.Counter()
    schema: dict[str, dict[str, Any]] = {}
    first_ts: str | None = None
    last_ts: str | None = None
    json_records = 0
    total_lines = 0
    truncated = False

    with p.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if total_lines >= max_lines:
                truncated = True
                break
            total_lines += 1
            m_ts = TS_RE.search(line)
            if m_ts:
                ts = m_ts.group(1)
                if first_ts is None or ts < first_ts:
                    first_ts = ts
                if last_ts is None or ts > last_ts:
                    last_ts = ts
            m_lv = LEVEL_RE.search(line)
            if m_lv:
                lv = "WARN" if m_lv.group(1).startswith("WARN") else m_lv.group(1)
                levels[lv] += 1
                if lv in ("ERROR", "CRITICAL", "FATAL"):
                    sig = NORM_NUM_RE.sub("<N>", redact_text(line.strip()))[:160]
                    error_sigs[sig] += 1
            elif "Traceback (most recent call last)" in line or re.search(r"\b\w+Error:\s", line):
                sig = NORM_NUM_RE.sub("<N>", redact_text(line.strip()))[:160]
                error_sigs[sig] += 1
            for m_st in HTTP_STATUS_RE.finditer(line):
                http_statuses[m_st.group(1)] += 1
            for payload in _extract_json_payloads(line):
                json_records += 1
                _infer_schema(payload, schema)

    serialized_schema = {
        k: {
            "types": sorted(v["types"]),
            "count": v["count"],
            "nulls": v["nulls"],
            "max_len": v["max_len"],
        }
        for k, v in sorted(schema.items())
    }
    return {
        "file": str(p),
        "bytes": p.stat().st_size,
        "lines_scanned": total_lines,
        "truncated": truncated,
        "time_range": {"first": first_ts, "last": last_ts},
        "levels": dict(levels.most_common()),
        "http_statuses": dict(http_statuses.most_common(20)),
        "top_errors": [{"signature": sig, "count": cnt} for sig, cnt in error_sigs.most_common(top_n)],
        "json_records_found": json_records,
        "json_field_count": len(serialized_schema),
        "json_schema": serialized_schema,
        "redacted": True,
    }


def render_md(res: dict[str, Any]) -> str:
    lines = [
        f"# Log Profile: `{Path(res['file']).name}`",
        f"- Bytes: `{res['bytes']}` | Lines scanned: `{res['lines_scanned']}` (truncated: `{res['truncated']}`)",
        f"- Time range: `{res['time_range']['first']}` → `{res['time_range']['last']}`",
        f"- Levels: `{res['levels']}` | HTTP statuses: `{res['http_statuses']}`",
        f"- JSON payloads parsed: `{res['json_records_found']}` | Unique JSON paths: `{res['json_field_count']}`",
    ]
    if res["top_errors"]:
        lines.append("\n## Top Error Signatures")
        for item in res["top_errors"]:
            lines.append(f"- ({item['count']}x) `{item['signature']}`")
    if res["json_schema"]:
        lines.append("\n## Inferred JSON Schema (first 40 paths)")
        lines.append("| Path | Types | Count | Nulls | MaxLen |")
        lines.append("|---|---|---:|---:|---:|")
        for path, meta in list(res["json_schema"].items())[:40]:
            lines.append(f"| `{path}` | `{','.join(meta['types'])}` | {meta['count']} | {meta['nulls']} | {meta['max_len']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only log profiler with redacted error clustering and JSON schema inference.")
    ap.add_argument("log_file", help="Path to log file")
    ap.add_argument("--max-lines", type=int, default=50000)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--md", action="store_true", help="Output markdown instead of JSON")
    args = ap.parse_args(argv)
    try:
        res = profile_log(args.log_file, max_lines=args.max_lines, top_n=args.top)
        print(render_md(res) if args.md else json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"log_profiler: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
