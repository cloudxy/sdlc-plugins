#!/usr/bin/env python3
"""Shared zero-dependency primitives for sdlc-workflow scripts (SSOT for YAML lite, paths, and project profiles)."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1])  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

import os
import re
import sys
from pathlib import Path
from typing import Any

SKIP_DIRS = frozenset({
    ".sdlc", ".git", ".idea", ".vscode", ".fleet", ".zed", ".cursor",
    "node_modules", "dist", "build", "out", ".next", ".nuxt",
    ".venv", "venv", "__pycache__", ".ruff_cache", ".mypy_cache",
    "test-results", "playwright-report",
    "coverage", ".pytest_cache", ".turbo", ".cache", "target", "vendor", "site-packages",
})
SKIP_FILES = frozenset({".DS_Store", "Thumbs.db"})

UNFILLED_RE = re.compile(r"^[ \t]*(<!--|#|//)[ \t]*sdlc:unfilled", re.M)

VALID_INDUSTRIES = (
    "b2b-saas",
    "fintech-ledger",
    "ecommerce-marketplace",
    "consumer-social",
    "ai-agentic",
    "aigc-workbench",
    "data-crawler",
    "regulated-compliance",
    "client-iot-localfirst",
)
VALID_TRAITS = (
    "multi-tenant", "payments", "ai-enabled", "realtime",
    "offline-first", "regulated", "high-concurrency", "two-sided",
)
VALID_SURFACES = ("web", "api", "native-mobile", "desktop", "miniprogram", "cli-sdk", "stream-batch")
VALID_DB_ENGINES = ("postgresql", "mysql", "sqlite", "clickhouse", "redis", "mongodb", "duckdb", "none")
VALID_ARCH_STYLES = ("modular-monolith", "layered-crud", "hexagonal-ddd", "microservices", "serverless-event")
VALID_COMPLIANCE = ("gdpr-pipl", "pci-dss", "hipaa", "soc2", "financial-audit", "ai-filing")
VALID_EXTRA_GATES = ("layering", "frontend", "explain", "contract")


def strip_comment(line: str) -> str:
    """Strip trailing `# ...` comments only outside single/double quotes."""
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1].isspace()):
            break
        out.append(ch)
    return "".join(out).rstrip()


def parse_scalar(v: str) -> Any:
    v = strip_comment(v).strip()
    if v in ("", "~", "null", "Null", "NULL"):
        return None
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [parse_scalar(x) for x in inner.split(",")] if inner else []
    if v in ("true", "True", "yes"):
        return True
    if v in ("false", "False", "no"):
        return False
    try:
        return int(v)
    except ValueError:
        return v


def parse_yaml(text: str) -> dict[str, Any]:
    rows = []
    for raw in text.splitlines():
        c = strip_comment(raw)
        if c.strip():
            rows.append((len(c) - len(c.lstrip(" ")), c.strip()))
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for i, (ind, c) in enumerate(rows):
        while len(stack) > 1 and ind <= stack[-1][0]:
            stack.pop()
        is_item = c == "-" or c.startswith("- ")
        if not is_item:
            while len(stack) > 1 and isinstance(stack[-1][1], list):
                stack.pop()
        parent = stack[-1][1]
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        if is_item:
            if not isinstance(parent, list):
                continue
            body = c[1:].strip()
            m = re.match(r"^([A-Za-z0-9_.-]+):(\s+.*|)$", body)
            if m:
                item: dict[str, Any] = {m.group(1): parse_scalar(m.group(2)) if m.group(2).strip() else None}
                parent.append(item)
                stack.append((ind, item))
            else:
                parent.append(parse_scalar(body))
            continue
        m = re.match(r"^([^:]+?):(\s+.*|)$", c)
        if not m or not isinstance(parent, dict):
            continue
        key, val = m.group(1).strip().strip("\"'"), m.group(2).strip()
        if val:
            parent[key] = parse_scalar(val)
        elif nxt and (nxt[0] > ind or (nxt[0] == ind and nxt[1].startswith("-"))):
            container: Any = [] if nxt[1].startswith("-") else {}
            parent[key] = container
            stack.append((ind if nxt[0] > ind else ind - 1, container))
        else:
            parent[key] = None
    return root


def is_unfilled_text(text: str, window: int = 65536) -> bool:
    return bool(UNFILLED_RE.search(text[:window]))


def is_unfilled_file(path: str | Path, window: int = 65536) -> bool:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return is_unfilled_text(fh.read(window), window=window)
    except OSError:
        return False


def find_project_root(start: str | Path, max_depth: int | None = None) -> Path | None:
    d = Path(start).resolve()
    if d.is_file():
        d = d.parent
    steps = 0
    while True:
        if (d / "sdlc.config.yaml").is_file():
            return d
        if d.parent == d or (max_depth is not None and steps >= max_depth):
            return None
        d = d.parent
        steps += 1


def self_test() -> int:
    assert strip_comment('url: "http://x#anchor" # real comment') == 'url: "http://x#anchor"'
    assert parse_scalar('"hello # world" # trailing') == "hello # world"
    cfg = parse_yaml(
        "extra_gates: []  # 可选 layering / frontend / explain\n"
        "# layering_root: backend\n"
        "profile:\n"
        "  industry: fintech-ledger\n"
        "  surfaces: [web, api]\n"
    )
    assert cfg["extra_gates"] == [], cfg
    assert "layering_root" not in cfg, cfg
    assert cfg["profile"] == {"industry": "fintech-ledger", "surfaces": ["web", "api"]}, cfg
    assert is_unfilled_text("<!-- sdlc:unfilled — fill me -->\n# Title\n")
    assert not is_unfilled_text("Prose mentioning sdlc:unfilled in the middle of a line.\n")
    print("self-test ok")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    if len(sys.argv) >= 3 and sys.argv[1] == "extra-gates":
        cfg_file = Path(sys.argv[2])
        data = parse_yaml(cfg_file.read_text(encoding="utf-8", errors="replace")) if cfg_file.is_file() else {}
        eg = data.get("extra_gates")
        items = [str(x).strip() for x in eg] if isinstance(eg, list) else []
        lr = str(data.get("layering_root") or "backend").strip()
        fr = str(data.get("frontend_root") or "").strip()
        cs = str(data.get("contract_spec") or "").strip()
        print("\t".join([",".join(items), lr, fr, cs]))
        sys.exit(0)
    print("usage: _sdlc_core.py --self-test | extra-gates <sdlc.config.yaml>", file=sys.stderr)
    sys.exit(2)
