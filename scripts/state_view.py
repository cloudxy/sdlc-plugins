#!/usr/bin/env python3
"""Read-only views of a feature state.yaml for check-sdlc.sh.

The gate used to grep these fields line by line, so inline comments, flow vs block YAML and ID prefixes changed
its verdict. Each command prints TAB-separated rows; the shell decides what is a violation.

  questions  <state>   id, status for each open_questions entry (a bare string is an open question)
  null-gates <state>   name of each gates[] record with result null and no reason
  last-fresh <state>   result, stage of the last fresh-context gate record (no row when there is none)
  failed-gates <state> kind, name, stage of each staged gate (fresh-context or script) whose latest record for that
                       name and stage is a fail; a later pass clears it, records without a stage are not listed
  skips      <state>   role, reason for each roles_skipped token (reason empty when roles_skipped_why lacks it)
  discovery  <state>   status, skip_why, reopened (y or empty)

Exit: 0 ok · 2 usage or unreadable file. Never edits state.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _strip_comment(s: str) -> str:
    """Drop a trailing ` # comment` that is outside quotes."""
    quote = None
    for i, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or s[i - 1].isspace()):
            return s[:i]
    return s


def _scalar(v: str) -> str:
    v = _strip_comment(v).strip()
    return v[1:-1] if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0] else v


def _flow_map(body: str) -> dict:
    """{a: b, c: "d"} → dict. Splits only before `key:` so commas inside values survive."""
    out = {}
    for part in re.split(r",\s*(?=[\w-]+\s*:)", body.strip()[1:-1]):
        if ":" in part:
            k, _, v = part.partition(":")
            out[k.strip()] = _scalar(v)
    return out


def _top(text: str, key: str):
    """(inline value, indented child lines) of a top-level key, or (None, []) when absent."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^{re.escape(key)}:(.*)$", line)
        if not m:
            continue
        inline = _strip_comment(m.group(1)).strip()
        child = []
        for nxt in lines[i + 1:]:
            if nxt.strip() == "" or nxt.lstrip().startswith("#"):
                continue
            if re.match(r"^\S", nxt):
                break
            child.append(nxt)
        return inline, child
    return None, []


def _split_flow(body: str) -> list[str]:
    """Top-level comma split of a flow list body; commas inside {…}, […] or quotes stay."""
    parts, depth, quote, cur = [], 0, None, ""
    for ch in body:
        if quote:
            quote = None if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(cur); cur = ""
            continue
        cur += ch
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def read_items(text: str, key: str) -> list:
    """Items of a top-level list: dict for block or flow mappings, str for bare scalars."""
    inline, child = _top(text, key)
    if inline:
        if inline.startswith("[") and inline.endswith("]"):
            return [_flow_map(x) if x.startswith("{") and x.endswith("}") else _scalar(x)
                    for x in _split_flow(inline[1:-1])]
        return []
    items: list = []
    for line in child:
        im = re.match(r"^\s*-\s*(.*)$", line)
        if im:
            body = _strip_comment(im.group(1)).strip()
            if body.startswith("{") and body.endswith("}"):
                items.append(_flow_map(body))
                continue
            km = re.match(r"^([\w-]+)\s*:\s*(.*)$", body)
            if km:
                items.append({km.group(1): _scalar(km.group(2))})
            else:
                items.append(_scalar(body))
            continue
        km = re.match(r"^\s+([\w-]+)\s*:\s*(.*)$", line)
        if km and items and isinstance(items[-1], dict):
            items[-1][km.group(1)] = _scalar(km.group(2))
    return items


def read_map(text: str, key: str) -> dict:
    """A top-level mapping written as a flow map on the key line or as indented `k: v` lines (one level)."""
    inline, child = _top(text, key)
    if inline:
        return _flow_map(inline) if inline.startswith("{") and inline.endswith("}") else {}
    out = {}
    indent = None
    for line in child:
        km = re.match(r"^(\s+)([\w-]+)\s*:\s*(.*)$", line)
        if not km:
            continue
        if indent is None:
            indent = len(km.group(1))
        if len(km.group(1)) == indent:
            out[km.group(2)] = _scalar(km.group(3))
    return out


def skipped_roles(text: str) -> list[str]:
    """Same contract as check-sdlc.sh role_skipped: a one-line flow list; block style does not count."""
    m = re.search(r"^roles_skipped:(.*)$", text, re.M)
    if not m:
        return []
    raw = re.sub(r"#.*$", "", m.group(1)).replace("[", "").replace("]", "")
    return [t.strip() for t in raw.split(",") if t.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("view", choices=["questions", "null-gates", "last-fresh", "failed-gates", "skips", "discovery"])
    ap.add_argument("state")
    args = ap.parse_args(argv)
    try:
        text = Path(args.state).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"state_view: {e}", file=sys.stderr)
        return 2
    rows: list[tuple] = []
    if args.view == "questions":
        for q in read_items(text, "open_questions"):
            if isinstance(q, dict):
                if q.get("id"):
                    rows.append((q["id"], q.get("status", "open") or "open"))
            elif q:
                rows.append((q, "open"))
    elif args.view == "null-gates":
        for g in read_items(text, "gates"):
            if isinstance(g, dict) and g.get("result", "") in ("null", "~", "") and "result" in g \
                    and not str(g.get("reason", "")).strip():
                rows.append((g.get("name") or "<unnamed>",))
    elif args.view == "last-fresh":
        fresh = [g for g in read_items(text, "gates") if isinstance(g, dict) and g.get("kind") == "fresh-context"
                 and g.get("result") in ("pass", "fail")]
        if fresh:
            rows.append((fresh[-1]["result"], fresh[-1].get("stage", "")))
    elif args.view == "failed-gates":
        latest = {}
        for g in read_items(text, "gates"):
            if isinstance(g, dict) and g.get("kind") in ("fresh-context", "script") and g.get("stage") \
                    and g.get("result") in ("pass", "fail"):
                key = (g["kind"], g.get("name") or g["kind"], g["stage"])
                latest.pop(key, None)  # keep insertion order of the latest record
                latest[key] = g["result"]
        rows = [key for key, result in latest.items() if result == "fail"]
    elif args.view == "skips":
        why = read_map(text, "roles_skipped_why")
        rows = [(r, why.get(r, "").strip()) for r in skipped_roles(text)]
    elif args.view == "discovery":
        d = read_map(text, "discovery")
        _, child = _top(text, "discovery")
        reopened = "y" if any(re.match(r"^\s+reopened:", c) for c in child) else ""
        if d or child:
            rows.append((d.get("status", ""), d.get("skip_why", "").strip(), reopened))
    for row in rows:
        print("\t".join(str(c).replace("\t", " ") for c in row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
