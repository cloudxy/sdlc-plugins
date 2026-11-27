#!/usr/bin/env python3
"""Read-only views of a feature state.yaml for check-sdlc.sh.

The gate used to grep these fields line by line, so inline comments, flow vs block YAML and ID prefixes changed
its verdict. Each command prints TAB-separated rows; the shell decides what is a violation.

  questions  <state>   id, status for each open_questions entry (a bare string is an open question)
  null-gates <state>   name of each gates[] record with result null and no reason
  last-fresh <state>   result, stage of the last fresh-context gate record (no row when there is none)
  failed-gates <state> kind, name, stage of each fresh-context or script gate whose latest record for that
                       name and stage is a fail; a later pass clears it. Fresh-context records without a stage are
                       not listed (last-fresh covers them). Script records without a stage are listed with an empty
                       stage so a v4 check can see them; a later pass with the same empty stage clears that row
  skips      <state>   role, reason for each roles_skipped token (reason empty when roles_skipped_why lacks it)
  discovery  <state>   status, skip_why, reopened (y or empty)
  summary    <state>   human-readable operator panel (not TSV). Optional sections that are absent are omitted;
                       present-but-empty values render as none. Does not change the TSV views above.

Exit: 0 ok · 2 usage or unreadable file. Never edits state.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1])  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

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


def question_rows(text: str) -> list[tuple]:
    rows: list[tuple] = []
    for q in read_items(text, "open_questions"):
        if isinstance(q, dict):
            if q.get("id"):
                rows.append((q["id"], q.get("status", "open") or "open"))
        elif q:
            rows.append((q, "open"))
    return rows


def null_gate_rows(text: str) -> list[tuple]:
    rows: list[tuple] = []
    for g in read_items(text, "gates"):
        if isinstance(g, dict) and g.get("result", "") in ("null", "~", "") and "result" in g \
                and not str(g.get("reason", "")).strip():
            rows.append((g.get("name") or "<unnamed>",))
    return rows


def last_fresh_row(text: str) -> tuple | None:
    fresh = [g for g in read_items(text, "gates") if isinstance(g, dict) and g.get("kind") == "fresh-context"
             and g.get("result") in ("pass", "fail")]
    if not fresh:
        return None
    return (fresh[-1]["result"], fresh[-1].get("stage", ""))


def failed_gate_rows(text: str) -> list[tuple]:
    latest = {}
    for g in read_items(text, "gates"):
        if not isinstance(g, dict) or g.get("kind") not in ("fresh-context", "script"):
            continue
        if g.get("result") not in ("pass", "fail"):
            continue
        stage = g.get("stage") or ""
        # Unstaged fresh-context stays on last-fresh. Unstaged script fails are listed with an
        # empty stage: v4 HATADVANCE treats that as a missing stage, and a later pass of the same
        # kind and name with an empty stage clears it. A pass that names a stage does not.
        if g.get("kind") == "fresh-context" and not stage:
            continue
        key = (g["kind"], g.get("name") or g["kind"], stage)
        latest.pop(key, None)  # keep insertion order of the latest record
        latest[key] = g["result"]
    return [key for key, result in latest.items() if result == "fail"]


def skip_rows(text: str) -> list[tuple]:
    why = read_map(text, "roles_skipped_why")
    return [(r, why.get(r, "").strip()) for r in skipped_roles(text)]


def discovery_row(text: str) -> tuple | None:
    d = read_map(text, "discovery")
    _, child = _top(text, "discovery")
    reopened = "y" if any(re.match(r"^\s+reopened:", c) for c in child) else ""
    if d or child:
        return (d.get("status", ""), d.get("skip_why", "").strip(), reopened)
    return None


def escape_row(text: str) -> tuple | None:
    if not _section_present(text, "escape"):
        return None
    e = read_map(text, "escape")
    return (
        "1",
        e.get("should_have_caught_at", "").strip(),
        e.get("defect_class", "").strip(),
        e.get("seam_fix", "").strip(),
        e.get("verified_by", "").strip(),
    )


def _show(value: str | None) -> str:
    text = (value or "").strip()
    return text if text else "none"


def _top_scalar(text: str, key: str) -> str:
    inline, _child = _top(text, key)
    if not inline:
        return ""
    return _scalar(inline)


def _list_tokens(text: str, key: str) -> list[str]:
    inline, child = _top(text, key)
    if inline is None and not child:
        return []
    names: list[str] = []
    for item in read_items(text, key):
        if isinstance(item, str):
            if item.strip():
                names.append(item.strip())
        elif isinstance(item, dict):
            token = str(item.get("id") or item.get("name") or "").strip()
            if token:
                names.append(token)
    if not names and inline and inline not in ("[]", "{}"):
        scalar = _scalar(inline)
        if scalar and scalar not in ("[]", "{}"):
            names.append(scalar)
    return names


def _section_present(text: str, key: str) -> bool:
    inline, child = _top(text, key)
    return not (inline is None and not child)


def _grouped(text: str, key: str) -> dict | None:
    """None when `key` is absent. `_flat` holds a one-level map; otherwise each child is a map."""
    inline, child = _top(text, key)
    if inline is None and not child:
        return None
    if inline.startswith("{") and inline.endswith("}"):
        return {"_flat": _flow_map(inline)}
    if inline and inline != "{}":
        return {"_flat": {"_value": _scalar(inline)}}
    keyed = []
    for line in child:
        match = re.match(r"^(\s+)([\w.-]+)\s*:\s*(.*)$", line)
        if match:
            keyed.append((len(match.group(1)), match.group(2), _scalar(match.group(3))))
    if not keyed:
        return {}
    base = min(indent for indent, _name, _value in keyed)
    if not any(indent > base for indent, _name, _value in keyed):
        return {"_flat": {name: value for indent, name, value in keyed if indent == base and value}}
    groups: dict[str, dict] = {}
    current = None
    for indent, name, value in keyed:
        if indent <= base:
            current = name
            groups[current] = {}
            if value:
                groups[current]["_value"] = value
        elif current is not None:
            groups[current][name] = value
    return groups


def _pair_line(label: str, data: dict, fields: tuple[str, ...]) -> str:
    parts = [f"{field}={str(data.get(field, '')).strip()}" for field in fields if str(data.get(field, "")).strip()]
    return f"{label}: " + (" ".join(parts) if parts else "none")


def _discovery_summary(text: str) -> str | None:
    if not _section_present(text, "discovery"):
        return None
    data = read_map(text, "discovery")
    _inline, child = _top(text, "discovery")
    raw = str(data.get("reopened", "")).strip()
    present = bool(raw) or any(re.match(r"^\s+reopened:", line) for line in child)
    if not present:
        reopened = "none"
    elif not raw or raw.startswith("{"):
        reopened = "y"
    else:
        reopened = raw
    return f"discovery: status={_show(data.get('status', ''))} reopened={reopened} skip_why={_show(data.get('skip_why', ''))}"


def _spawn_lines(groups: dict) -> list[str]:
    if not groups:
        return []
    flat = groups.get("_flat")
    if flat is not None and len(groups) == 1:
        return [_pair_line("host_spawn", flat, tuple(k for k in flat if k != "_value") or ("_value",))]
    lines = ["host_spawn:"]
    preferred = ("requested", "available", "fallback", "reason")
    for name, fields in groups.items():
        if name == "_flat":
            continue
        ordered = [f"{key}={str(fields.get(key, '')).strip()}" for key in preferred if str(fields.get(key, "")).strip()]
        for key, value in fields.items():
            if key in preferred or key == "_value" or not str(value).strip():
                continue
            ordered.append(f"{key}={str(value).strip()}")
        if not ordered and str(fields.get("_value", "")).strip():
            ordered.append(str(fields["_value"]).strip())
        lines.append(f"- {name}: " + (" ".join(ordered) if ordered else "none"))
    return lines if len(lines) > 1 else []


def render_summary(text: str) -> str:
    """Operator panel. Tolerates missing keys, Chinese scalars and minimal legacy files."""
    lines = [f"{key}: {_show(_top_scalar(text, key))}" for key in (
        "feature", "lane", "phase", "sdlc_version", "delivery_goal", "current_hat")]
    hats = _list_tokens(text, "hats_done")
    lines.append("hats_done: " + (", ".join(hats) if hats else "none"))
    lines.append("")
    lines.append(_discovery_summary(text) or "discovery: none")
    lines.append("")
    pending = [row for row in question_rows(text) if row[1] != "answered"]
    if pending:
        lines.append("open_questions:")
        lines.extend(f"- {qid} ({status})" for qid, status in pending)
    else:
        lines.append("open_questions: none")
    failed = failed_gate_rows(text)
    if failed:
        lines.append("failed_gates:")
        for kind, name, stage in failed:
            lines.append(f"- kind={kind} name={name} stage={_show(stage)}")
    else:
        lines.append("failed_gates: none")
    fresh = last_fresh_row(text)
    if fresh and fresh[0] == "fail":
        lines.append(f"last_fresh: result=fail stage={_show(fresh[1])}")
    nulls = null_gate_rows(text)
    if nulls:
        lines.append("null_gates:")
        lines.extend(f"- {name}" for (name,) in nulls)
    else:
        lines.append("null_gates: none")
    spawn = _grouped(text, "host_spawn")
    if spawn:
        extra = _spawn_lines(spawn)
        if extra:
            lines.append("")
            lines.extend(extra)
    notes = []
    for label, fields in (
        ("bet", ("hypothesis", "metric", "readout_due")),
        ("escape", ("origin_feature", "origin_release", "should_have_caught_at", "gate", "defect_class")),
    ):
        if _section_present(text, label):
            notes.append(_pair_line(label, read_map(text, label), fields))
    if notes:
        lines.append("")
        lines.extend(notes)
    skipped = skip_rows(text)
    if skipped:
        lines.append("")
        lines.append("roles_skipped:")
        lines.extend(f"- {role}: {_show(reason)}" for role, reason in skipped)
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("view", choices=[
        "questions", "null-gates", "last-fresh", "failed-gates", "skips", "discovery", "escape", "summary"])
    ap.add_argument("state")
    args = ap.parse_args(argv)
    try:
        text = Path(args.state).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"state_view: {e}", file=sys.stderr)
        return 2
    if args.view == "summary":
        sys.stdout.write(render_summary(text))
        return 0
    rows: list[tuple] = []
    if args.view == "questions":
        rows = question_rows(text)
    elif args.view == "null-gates":
        rows = null_gate_rows(text)
    elif args.view == "last-fresh":
        fresh = last_fresh_row(text)
        rows = [fresh] if fresh else []
    elif args.view == "failed-gates":
        rows = failed_gate_rows(text)
    elif args.view == "skips":
        rows = skip_rows(text)
    elif args.view == "discovery":
        found = discovery_row(text)
        rows = [found] if found else []
    elif args.view == "escape":
        esc = escape_row(text)
        rows = [esc] if esc else []
    for row in rows:
        print("\t".join(str(c).replace("\t", " ") for c in row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
