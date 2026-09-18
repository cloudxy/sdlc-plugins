#!/usr/bin/env python3
"""Diagram gate: source declaration, safety, vendored svg-lint with the exact pass rule, evidence written by the tool.

  python3 scripts/diagram/lint.py --root <feature_dir|product_root> <a.svg> [<b.svg> ...]
  python3 scripts/diagram/lint.py --self-test

Every SVG must carry, right after <svg ...>:
  <metadata id="sdlc">{"type": "er", "owner": "dba", "sources": ["02-shape/schema.dbml"]}</metadata>
Sources resolve against --root, then the project root (the folder with sdlc.config.yaml).

Pass = all of: files exist, are non-empty and inside --root · no scripts, event handlers, foreignObject or
external references · metadata parses with a known type and existing sources · vendor/svg-diagram matches its
lock · svg-lint exit 0 AND JSON parses AND errors == 0 AND warnings == 0 AND files == requested AND the
reported file set == the requested set.
Evidence: <root>/evidence/diagrams/<name>.json per SVG (svg + source digests, vendor commit, node, summary).
Nobody writes these by hand; a stale digest means the diagram or its source changed after the check.

Exit: 0 pass · 1 violations · 2 usage or environment (no node, vendor missing).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vendorlib  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import semantic  # noqa: E402

TYPES = {"flow", "state", "architecture", "sequence", "trust-boundary", "er", "lineage", "other"}
META = re.compile(r"<metadata\s+id=[\"']sdlc[\"']\s*>(.*?)</metadata>", re.S)
UNSAFE = [
    (re.compile(r"<script\b", re.I), "<script>"),
    (re.compile(r"\son[a-z]+\s*=", re.I), "event handler attribute (on...=)"),
    (re.compile(r"<foreignObject\b", re.I), "<foreignObject>"),
    (re.compile(r"(?:xlink:)?href\s*=\s*[\"']\s*(?:https?:|file:|javascript:|data:text)", re.I), "external or script href"),
    (re.compile(r"url\(\s*[\"']?\s*(?:https?:|file:)", re.I), "external url() reference"),
    (re.compile(r"@import", re.I), "CSS @import"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def project_root(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if (d / "sdlc.config.yaml").is_file():
            return d
    return None


def node_bin() -> str | None:
    return os.environ.get("NODE_BIN") or shutil.which("node") or ("/opt/homebrew/bin/node" if os.path.exists("/opt/homebrew/bin/node") else None)


def check(root: Path, files: list[Path], plugin: Path = vendorlib.ROOT, write_evidence: bool = True) -> tuple[int, list[str]]:
    out: list[str] = []

    def bad(tag, msg):
        out.append(f"✗ [DIAGRAM-{tag}] {msg}")

    if not files:
        return 2, ["✗ [DIAGRAM-USAGE] no SVG files given (an empty list is not a pass)"]
    root = root.resolve()
    proj = project_root(root)
    metas: dict[Path, dict] = {}
    for f in files:
        if f.suffix.lower() != ".svg":
            bad("SOURCE", f"{f}: not an .svg file"); continue
        if not f.is_file() or f.stat().st_size == 0:
            bad("SOURCE", f"{f}: missing or empty"); continue
        if not f.resolve().is_relative_to(root):
            bad("SOURCE", f"{f}: outside {root}"); continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for rx, what in UNSAFE:
            if rx.search(text):
                bad("UNSAFE", f"{f}: {what} is not allowed in a technical diagram")
        m = META.search(text)
        if not m:
            bad("SOURCE", f'{f}: missing <metadata id="sdlc">{{"type": …, "owner": …, "sources": [...]}}</metadata>'); continue
        try:
            meta = json.loads(m.group(1))
        except ValueError:
            bad("SOURCE", f"{f}: sdlc metadata is not valid JSON"); continue
        if meta.get("type") not in TYPES:
            bad("SOURCE", f"{f}: metadata type must be one of {', '.join(sorted(TYPES))}")
        srcs = meta.get("sources")
        if not isinstance(srcs, list) or not srcs:
            bad("SOURCE", f"{f}: metadata sources must list the authoritative files this diagram shows"); continue
        resolved = []
        for s in srcs:
            cands = [root / s] + ([proj / s] if proj else [])
            hit = next((c for c in cands if c.is_file()), None)
            if not hit:
                bad("SOURCE", f"{f}: source {s} does not exist (relative to {root}{' or ' + str(proj) if proj else ''})")
            else:
                resolved.append((s, hit))
        metas[f] = {"meta": meta, "sources": resolved}
        if resolved and len(resolved) == len(srcs) and meta.get("type") in TYPES:
            for prob in semantic.check(f, meta["type"], [h for _, h in resolved]):
                bad("SEMANTIC", prob)
    try:
        tool = json.loads((plugin / "workflow/registry.json").read_text())["diagram"]["tool"]  # vendor/<name>/<path>
        _, vname, vrel = tool.split("/", 2)
        bin_ = vendorlib.resolve(vname, vrel, plugin)
    except vendorlib.VendorError as e:
        return 2, out + [f"✗ [DIAGRAM-VENDOR] {e}"]
    node = node_bin()
    if not node:
        return 2, out + ["✗ [DIAGRAM-VENDOR] node not found (set NODE_BIN)"]
    targets = [f for f in files if f.is_file() and f.suffix.lower() == ".svg" and f.stat().st_size > 0]
    req = {str(f.resolve()) for f in targets}
    summary = None
    if targets:
        p = subprocess.run([node, str(bin_), "--json", *[str(f.resolve()) for f in targets]], capture_output=True, text=True, timeout=120)
        try:
            data = json.loads(p.stdout)
            summary = data["summary"]
            got = {str(Path(x["file"]).resolve()) for x in data["files"]}
        except (ValueError, KeyError, TypeError):
            data, got = None, set()
        if p.returncode != 0 and p.returncode != 1:
            bad("LINT", f"svg-lint exit {p.returncode}: {p.stderr.strip()[:200]} (an unreadable file is not a pass)")
        elif data is None:
            bad("LINT", "svg-lint output is not the expected JSON report")
        else:
            if summary.get("files") != len(req) or got != req:
                bad("LINT", f"svg-lint covered {summary.get('files')} of {len(req)} files")
            n = 0
            for fr in data["files"]:
                for fd in fr.get("findings", []):
                    n += 1
                    hint = (fd.get("repair") or {}).get("hint")
                    bad("LINT", f"{fr['file']}:{fd.get('line', '?')}: [{fd.get('severity', '?')}] {fd.get('check', '')}/{fd.get('code', '')} "
                                f"{fd.get('message', '')}" + (f" → {hint}" if hint else ""))
            if (summary.get("errors") or summary.get("warnings")) and not n:
                bad("LINT", f"svg-lint summary errors={summary.get('errors')} warnings={summary.get('warnings')} (warnings fail this gate too)")
    ok = not out
    if write_evidence:
        lk = vendorlib.lock("svg-diagram", plugin) or {}
        nver = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
        ev_dir = root / "evidence" / "diagrams"
        ev_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        for f in targets:
            info = metas.get(f, {})
            own = [l for l in out if str(f) in l or str(f.resolve()) in l]
            rec = {"svg": os.path.relpath(f.resolve(), root), "svg_sha256": sha(f),
                   "type": info.get("meta", {}).get("type"), "owner": info.get("meta", {}).get("owner"),
                   "sources": [{"path": s, "sha256": sha(h)} for s, h in info.get("sources", [])],
                   "svg_diagram_commit": lk.get("commit"), "node": nver, "checked_at": now,
                   "lint_summary": summary, "passed": ok and not own, "violations": own}
            (ev_dir / (f.stem + ".json")).write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
    return (0 if ok else 1), out


def stale(root: Path, evidence: Path) -> list[str]:
    """Which recorded digests no longer match: the diagram or one of its sources changed after the check."""
    rec = json.loads(evidence.read_text())
    proj = project_root(root.resolve())
    changed = []
    svg = root / rec["svg"]
    if not svg.is_file() or sha(svg) != rec["svg_sha256"]:
        changed.append(rec["svg"])
    for s in rec.get("sources", []):
        cands = [root / s["path"]] + ([proj / s["path"]] if proj else [])
        hit = next((c for c in cands if c.is_file()), None)
        if not hit or sha(hit) != s["sha256"]:
            changed.append(s["path"])
    return changed


def self_test() -> int:
    good = vendorlib.ROOT / "vendor/svg-diagram/assets/house-style.svg"
    if not good.is_file():
        print("self-test skipped: vendor/svg-diagram not installed (bash vendor/install.sh svg-diagram)")
        return 0
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "proj/.sdlc/f"
        (root / "02-shape/assets").mkdir(parents=True)
        (Path(td) / "proj/sdlc.config.yaml").write_text("product_root: docs/product\n")
        (root / "02-shape/schema.dbml").write_text("Table orders {\n  id bigint [pk]\n}\n")
        base = good.read_text()
        meta = '<metadata id="sdlc">{"type": "er", "owner": "dba", "sources": ["02-shape/schema.dbml"]}</metadata>'
        withmeta = re.sub(r"(<svg[^>]*>)", r"\1" + meta, base, count=1).replace("</svg>", '<g data-sdlc-id="orders"/></svg>')
        cases = {
            "ok.svg": (withmeta, 0, None),
            "nometa.svg": (base, 1, "DIAGRAM-SOURCE"),
            "badsrc.svg": (withmeta.replace("02-shape/schema.dbml", "02-shape/gone.dbml"), 1, "DIAGRAM-SOURCE"),
            "script.svg": (withmeta.replace("</svg>", "<script>alert(1)</script></svg>"), 1, "DIAGRAM-UNSAFE"),
            "offpalette.svg": (withmeta.replace("#ffffff", "#ff00aa", 1) if "#ffffff" in withmeta else withmeta + "", 1, "DIAGRAM-LINT"),
        }
        for name, (text, want, tag) in cases.items():
            f = root / "02-shape/assets" / name
            f.write_text(text)
            rc, out = check(root, [f], write_evidence=False)
            if rc != want or (tag and not any(tag in l for l in out)):
                print(f"self-test FAILED: {name}: rc={rc} want={want} tag={tag}", out[:4]); return 1
            f.unlink()
        # semantic layer: an ER diagram must draw exactly the DBML's tables and relationships
        (root / "02-shape/schema.dbml").write_text(
            "Table users {\n  id bigint [pk]\n}\nTable orders {\n  id bigint [pk]\n  user_id bigint [ref: > users.id]\n}\n")
        er = withmeta.replace('<g data-sdlc-id="orders"/></svg>', '<g data-sdlc-id="users"/><g data-sdlc-id="orders"/>'
                              '<g data-sdlc-id="orders.user_id->users.id"/></svg>')
        f = root / "02-shape/assets/er.svg"
        f.write_text(er)
        rc, out = check(root, [f], write_evidence=False)
        if rc != 0:
            print("self-test FAILED: ER matching its DBML must pass", out); return 1
        f.write_text(er.replace('<g data-sdlc-id="orders.user_id->users.id"/>', '<g data-sdlc-id="payments"/>'))
        rc, out = check(root, [f], write_evidence=False)
        joined = " ".join(out)
        if rc != 1 or "relationship orders.user_id — users.id is in the DBML but not drawn" not in joined \
                or "table payments is drawn but not in the DBML" not in joined:
            print("self-test FAILED: a missing relationship and an invented table must be DIAGRAM-SEMANTIC", out); return 1
        f.unlink()
        (root / "02-shape/schema.dbml").write_text("Table orders {\n  id bigint [pk]\n}\n")
        rc, out = check(root, [], write_evidence=False)
        if rc != 2:
            print("self-test FAILED: an empty file list must not pass"); return 1
        f = root / "02-shape/assets/ok.svg"; f.write_text(withmeta)
        rc, out = check(root, [f])
        ev = root / "evidence/diagrams/ok.json"
        if rc != 0 or not ev.is_file() or stale(root, ev):
            print("self-test FAILED: passing diagram must write fresh evidence", rc, out); return 1
        (root / "02-shape/schema.dbml").write_text("Table orders {\n  id bigint [pk]\n  total int\n}\n")
        if stale(root, ev) != ["02-shape/schema.dbml"]:
            print("self-test FAILED: a changed source must make the evidence stale", stale(root, ev)); return 1
    print("self-test ok")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--root")
    ap.add_argument("--stale", metavar="EVIDENCE_JSON", help="report whether recorded digests still match")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.root:
        print("usage: lint.py --root <feature_dir|product_root> <a.svg> ...", file=sys.stderr)
        return 2
    if a.stale:
        ch = stale(Path(a.root), Path(a.stale))
        print("fresh" if not ch else "STALE: " + ", ".join(ch))
        return 1 if ch else 0
    rc, out = check(Path(a.root), [Path(f) for f in a.files])
    for line in out:
        print(line)
    print("✓ diagrams pass" if rc == 0 else f"✗ diagrams: {len(out)} problem(s)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
