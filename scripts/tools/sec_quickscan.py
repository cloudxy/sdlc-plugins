#!/usr/bin/env python3
"""Strictly defensive local static security clue scanner (read-only, zero network, zero exploitation).

  python3 scripts/tools/sec_quickscan.py <path> [<path>...] [--max-files 2000]

Pure Python stdlib. Respects _sdlc_core.SKIP_DIRS, redacts any matched secret values,
and explicitly labels findings as static clues requiring semantic review by `architect`.
Exit codes: 0 scan completed (check `findings_count`) · 2 usage/input error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime._sdlc_core import SKIP_DIRS

SCAN_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb", ".php",
    ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".conf", ".env", ".sh", ".sql",
}

RULES: list[dict[str, Any]] = [
    {
        "id": "SEC-SECRET-PRIVATE-KEY",
        "severity": "blocker",
        "category": "secret_exposure",
        "pattern": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        "redact": True,
        "note": "Private key material committed in source",
    },
    {
        "id": "SEC-SECRET-TOKEN",
        "severity": "blocker",
        "category": "secret_exposure",
        "pattern": re.compile(r"\b(?:AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})\b"),
        "redact": True,
        "note": "High-confidence cloud/API token literal detected",
    },
    {
        "id": "SEC-SECRET-DB-URI",
        "severity": "major",
        "category": "secret_exposure",
        "pattern": re.compile(r"(?:mysql|postgres|postgresql|redis|mongodb)(?:\+\w+)?://[^:\s/]+:[^@\s$\{]{4,}@(?!localhost\b|127\.0\.0\.1\b)[^\s\"']+"),
        "redact": True,
        "note": "Non-local database/cache URI with embedded password literal",
    },
    {
        "id": "SEC-CODE-EXEC",
        "severity": "major",
        "category": "code_injection",
        "pattern": re.compile(r"\b(?:eval|exec)\s*\(|pickle\.loads\s*\(|yaml\.load\s*\([^)]*\)(?!.*SafeLoader)"),
        "redact": False,
        "note": "Dynamic code execution or unsafe deserialization sink; verify input trust boundary",
    },
    {
        "id": "SEC-SHELL-TRUE",
        "severity": "major",
        "category": "command_injection",
        "pattern": re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True"),
        "redact": False,
        "note": "Subprocess invoked with shell=True; verify inputs are strictly static or switch to argv list",
    },
    {
        "id": "SEC-RAW-SQL-FORMAT",
        "severity": "major",
        "category": "sql_injection",
        "pattern": re.compile(r"\.execute\s*\(\s*(?:f[\"']|[\"'][^\"']*(?:SELECT|INSERT|UPDATE|DELETE)[^\"']*[\"']\s*(?:%|\.format\s*\())", re.I),
        "redact": False,
        "note": "String-interpolated SQL inside execute(); verify parameterization",
    },
    {
        "id": "SEC-TLS-VERIFY-FALSE",
        "severity": "major",
        "category": "transport_security",
        "pattern": re.compile(r"\bverify\s*=\s*False\b|rejectUnauthorized\s*:\s*false"),
        "redact": False,
        "note": "TLS certificate verification disabled",
    },
    {
        "id": "SEC-DOM-XSS-SINK",
        "severity": "minor",
        "category": "xss",
        "pattern": re.compile(r"dangerouslySetInnerHTML|\.innerHTML\s*="),
        "redact": False,
        "note": "Raw HTML sink; verify sanitization of untrusted content",
    },
]

LOCKFILES = ("uv.lock", "poetry.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.lock", "go.sum")


def _redact_line_secrets(line: str) -> str:
    """Redact any secret/credential match on a line so co-occurring non-secret rules never leak raw secrets."""
    out = line
    # 1. Full Authorization header (Bearer/Basic/Token + payload) BEFORE generic key=val
    out = re.sub(
        r"""(?i)(["']?authorization["']?\s*[:=]\s*)(?:"(?:bearer|basic|token)\s+[^"]+"|'(?:bearer|basic|token)\s+[^']+'|(?:bearer|basic|token)\s+[^\s,'";}\]]+)""",
        r"\1[REDACTED_SECRET_MATCH]",
        out,
    )
    # 2. Standalone Bearer token
    out = re.sub(r"(?i)(\bbearer\s+)[A-Za-z0-9._\-+/=]{8,}", r"\1[REDACTED_SECRET_MATCH]", out)
    # 3. Explicit secret rules (private keys, cloud/API tokens, DB URIs)
    for rule in RULES:
        if rule["redact"]:
            out = rule["pattern"].sub("[REDACTED_SECRET_MATCH]", out)
    # 4. Generic quoted/unquoted password/token/api_key/authorization literals (skip already redacted)
    out = re.sub(
        r"""(?i)(["']?(?:authorization|password|passwd|pwd|secret|token|api[_-]?key)["']?\s*[:=]\s*)(?!\[REDACTED_SECRET_MATCH\])(?:"[^"]*"|'[^']*'|[^\s,;}\]]+)""",
        r"\1[REDACTED_SECRET_MATCH]",
        out,
    )
    return out


def scan_paths(targets: list[str], max_files: int = 2000) -> dict[str, Any]:
    files: list[Path] = []
    lockfiles_found: list[str] = []
    files_discovered = 0
    files_skipped_symlink = 0
    files_skipped_size = 0
    files_skipped_unreadable = 0
    truncated = False

    for raw in targets:
        raw_path = Path(raw)
        if not raw_path.exists() and not raw_path.is_symlink():
            raise ValueError(f"path not found: {raw}")
        if raw_path.is_symlink():
            files_skipped_symlink += 1
            continue
        p = raw_path.resolve()
        if p.is_file():
            files_discovered += 1
            if len(files) < max_files:
                files.append(p)
                if p.name in LOCKFILES:
                    lockfiles_found.append(str(p))
            else:
                truncated = True
        else:
            for dp, dns, fns in os.walk(p, followlinks=False):
                kept_dirs = []
                for d in sorted(dns):
                    if d in SKIP_DIRS:
                        continue
                    dpath = Path(dp) / d
                    if dpath.is_symlink():
                        files_skipped_symlink += 1
                        continue
                    kept_dirs.append(d)
                dns[:] = kept_dirs
                for fn in sorted(fns):
                    fp = Path(dp) / fn
                    if fp.is_symlink():
                        files_skipped_symlink += 1
                        continue
                    try:
                        resolved_fp = fp.resolve()
                        resolved_fp.relative_to(p)
                    except (OSError, ValueError):
                        files_skipped_symlink += 1
                        continue
                    if fn in LOCKFILES:
                        lockfiles_found.append(str(resolved_fp))
                    if fp.suffix.lower() in SCAN_EXTS or fn == ".env":
                        files_discovered += 1
                        if len(files) < max_files:
                            files.append(resolved_fp)
                        else:
                            truncated = True

    findings: list[dict[str, Any]] = []
    files_scanned = 0
    for fp in files:
        try:
            if fp.stat().st_size > 1_000_000:
                files_skipped_size += 1
                continue
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            files_skipped_unreadable += 1
            continue
        files_scanned += 1
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                continue
            matched_rules = [rule for rule in RULES if rule["pattern"].search(line)]
            if not matched_rules:
                continue
            line_has_secret = any(r["redact"] for r in matched_rules)
            safe_snippet = _redact_line_secrets(stripped)[:140]
            for rule in matched_rules:
                snippet = "[REDACTED_SECRET_MATCH]" if (rule["redact"] or line_has_secret) else safe_snippet
                findings.append({
                    "rule_id": rule["id"],
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "file": str(fp),
                    "line": lineno,
                    "snippet": snippet,
                    "note": rule["note"],
                })

    by_sev: dict[str, int] = {}
    for f in findings:
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1

    return {
        "scope": "defensive_static_clues_only",
        "active_probing": False,
        "requires_semantic_review": True,
        "files_discovered": files_discovered,
        "files_scanned": files_scanned,
        "files_skipped_size": files_skipped_size,
        "files_skipped_symlink": files_skipped_symlink,
        "files_skipped_unreadable": files_skipped_unreadable,
        "truncated": truncated,
        "lockfiles_found": sorted(set(lockfiles_found)),
        "findings_count": len(findings),
        "counts_by_severity": by_sev,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Defensive static security clue scanner (read-only, no active probing).")
    ap.add_argument("paths", nargs="+", help="Files or directories to scan")
    ap.add_argument("--max-files", type=int, default=2000)
    args = ap.parse_args(argv)
    try:
        res = scan_paths(args.paths, max_files=args.max_files)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"sec_quickscan: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
