#!/usr/bin/env python3
"""sdlc_trace.py — read-only impact query over one project's SDLC artifacts (plan 3.5).

  python3 workflow.py trace FR-01 --feature <feature-dir>
  python3 workflow.py trace metric:<id> --product-root <product-root>
  python3 workflow.py trace SIG-<yyyymm>-<n> --project-root <project-root>
  add --json for machine output

The index is rebuilt from the artifacts on every run and never written: it is a view, not a second source of
requirements, metrics or status. Every relation keeps the file and line it came from. Status comes only from
records (coverage rows with results, implementation evidence files, state.yaml stale_artifacts); a file that merely
mentions an ID never makes it "verified". Short IDs (FR-01, T-1, …) are scoped to a feature: when several features
define one, the query stops and asks to narrow it. Exit: 0 found · 1 not found · 2 ambiguous or usage error.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

FEATURE_KINDS = {"FR", "NFR", "J", "EV", "T", "D"}
SHORT = r"(?:FR|NFR|J|EV|T)-\d+"
ID_RE = re.compile(rf"(?<![A-Za-z0-9_-])({SHORT}|SIG-\d{{6}}-\d+|(?:metric|tag|event):[A-Za-z0-9_.-]*[A-Za-z0-9_-])(?![A-Za-z0-9_-])")
DIRECTION_RE = re.compile(r"^#+\s*(D\d+)\b")
SKIP_PARTS = {"packets", "memory", "evidence", "shots", "screens", "prototypes", "assets"}
DEF_FILES = {
    "FR": ("01-define/spec.md", "01-define/spec-s.md", "spec-s.md"),
    "NFR": ("01-define/spec.md", "01-define/spec-s.md", "spec-s.md"),
    "J": ("01-define/spec.md", "01-define/spec-s.md", "spec-s.md"),
    "EV": ("01-define/tracking.md",),
    "T": ("02-shape/contract.md", "state.yaml"),
    "D": ("02-shape/design-directions.md",),
}
DATA_DEFS = {"metric": ("data/metrics.yaml", "id"), "tag": ("data/tags.yaml", "id"), "event": ("data/tracking-plan.yaml", "event")}
SUPERSEDE_RE = re.compile(r"supersed|取代|替代|废弃")


def kind_of(ident: str) -> str:
    if ":" in ident:
        return ident.split(":", 1)[0]
    if ident.startswith("SIG-"):
        return "SIG"
    if re.fullmatch(r"D\d+", ident):
        return "D"
    return ident.split("-", 1)[0]


@dataclass
class Line:
    container: str      # feature:<name> · cycle:<id> · product · signals
    path: Path          # absolute file
    rel: str            # path relative to its container root
    no: int
    text: str
    ids: list[str]


@dataclass
class Index:
    lines: list[Line] = field(default_factory=list)
    roots: dict[str, Path] = field(default_factory=dict)
    stale: dict[str, set[str]] = field(default_factory=dict)   # container → stale artifact paths from state.yaml
    tickets: dict[str, dict[str, dict]] = field(default_factory=dict)  # container → T-n → state ticket fields


def _files(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in (".md", ".yaml", ".yml"):
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_PARTS for part in rel.parts[:-1]):
            continue
        yield p, rel.as_posix()


def _scan(index: Index, container: str, root: Path, files=None):
    index.roots[container] = root
    for p, rel in (files if files is not None else _files(root)):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for no, line in enumerate(text.splitlines(), 1):
            ids = [m.group(1) for m in ID_RE.finditer(line)]
            d = DIRECTION_RE.match(line)
            if d and rel.endswith("design-directions.md"):
                ids.append(d.group(1))
            if ids:
                index.lines.append(Line(container, p, rel, no, line.strip(), list(dict.fromkeys(ids))))
        if rel == "state.yaml":
            _state_records(index, container, text)


def _state_records(index: Index, container: str, text: str):
    stale, tickets, in_stale, in_tickets, cur = set(), {}, False, False, None
    for raw in text.splitlines():
        if re.match(r"^stale_artifacts:", raw):
            in_stale, in_tickets = True, False
            stale.update(x.strip().strip("'\"") for x in re.findall(r"[\w./-]+\.(?:md|yaml|dbml|json)", raw))
            continue
        if re.match(r"^tickets:", raw):
            in_tickets, in_stale = True, False
            continue
        if re.match(r"^\S", raw):
            in_stale = in_tickets = False
            continue
        if in_stale:
            stale.update(re.findall(r"[\w./-]+\.(?:md|yaml|dbml|json)", raw))
        if in_tickets:
            m = re.search(r"\bid:\s*(T-\d+)", raw)
            if m:
                cur = tickets.setdefault(m.group(1), {})
            if cur is not None:
                for k in ("status", "journey", "evidence", "integration"):
                    km = re.search(rf"\b{k}:\s*([^,}}\s]+)", raw)
                    if km:
                        cur[k] = km.group(1)
    index.stale[container] = stale
    index.tickets[container] = tickets


def _config(project: Path) -> dict:
    cfg = project / "sdlc.config.yaml"
    if not cfg.is_file():
        return {}
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from check_config import parse_yaml  # noqa: PLC0415
    return parse_yaml(cfg.read_text(encoding="utf-8"))


def _find_project(start: Path) -> Path | None:
    d = start.resolve()
    for _ in range(8):
        if (d / "sdlc.config.yaml").is_file():
            return d
        if d.parent == d:
            return None
        d = d.parent
    return None


def build_index(feature: str | None = None, product_root: str | None = None, project_root: str | None = None) -> Index:
    index = Index()
    project = Path(project_root).resolve() if project_root else None
    if feature:
        froot = Path(feature).resolve()
        _scan(index, f"feature:{froot.name}", froot)
        project = project or _find_project(froot)
    if project and not feature:
        cfg = _config(project)
        sdlc = project / str(cfg.get("artifact_root") or ".") / ".sdlc"
        if sdlc.is_dir():
            for d in sorted(sdlc.iterdir()):
                if d.is_dir() and not d.name.startswith("_"):
                    _scan(index, f"feature:{d.name}", d)
            cycles = sdlc / "_product" / "cycles"
            if cycles.is_dir():
                for d in sorted(cycles.iterdir()):
                    if d.is_dir():
                        _scan(index, f"cycle:{d.name}", d)
    if project:
        cfg = _config(project)
        product_root = product_root or str(project / str(cfg.get("product_root") or "docs/product"))
        store = cfg.get("signals_path")
        if isinstance(store, str) and store.strip() and "<" not in store:
            sp = project / store
            if sp.is_dir():
                _scan(index, "signals", sp)
            elif sp.is_file():
                _scan(index, "signals", sp.parent, [(sp, sp.name)])
    if product_root and Path(product_root).is_dir():
        _scan(index, "product", Path(product_root).resolve())
    return index


def _sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except OSError:
        return "?"


def _is_definition(ln: Line, ident: str) -> bool:
    kind = kind_of(ident)
    if kind in DEF_FILES:
        if ln.rel not in DEF_FILES[kind]:
            return False
        if kind == "D":
            return bool(DIRECTION_RE.match(ln.text)) and DIRECTION_RE.match(ln.text).group(1) == ident
        head = re.escape(ident)
        return bool(re.match(rf"^(#+\s.*\b{head}\b|\|\s*\**{head}\b|[-*]?\s*\**{head}\b|-\s*id:\s*{head}\b|id:\s*{head}\b)", ln.text))
    if kind == "SIG":
        return ln.container == "signals" and bool(re.match(rf"^\|\s*{re.escape(ident)}\s*\|", ln.text))
    return False


def _data_definition(index: Index, ident: str):
    kind, name = ident.split(":", 1)
    root = index.roots.get("product")
    if not root:
        return None
    rel, key = DATA_DEFS[kind]
    f = root / rel
    if not f.is_file():
        return None
    lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    for no, line in enumerate(lines, 1):
        if re.match(rf"^\s*-?\s*{key}:\s*[\"']?{re.escape(name)}[\"']?\s*(#.*)?$", line):
            version = None
            for x in lines[no:]:
                if re.match(r"^\s*-\s", x) or re.match(r"^\S", x):
                    break  # next entry: its version is not this one's
                m = re.match(r"^\s+version:\s*(.+?)\s*(#.*)?$", x)
                if m:
                    version = m.group(1).strip("'\"")
                    break
            return {"container": "product", "file": rel, "line": no, "version": version or _sha(f)}
    return None


def _relation(ident: str, other: str, ln: Line) -> tuple[str, str]:
    """(direction, label) of `other` relative to the queried `ident`, from the line's own context."""
    k, o = kind_of(ident), kind_of(other)
    if SUPERSEDE_RE.search(ln.text):
        return "related", "supersession mentioned"
    if ln.rel.endswith("coverage.md"):
        return "downstream", "verified in the same coverage row"
    in_spec = ln.rel in DEF_FILES["FR"]
    if k in ("FR", "NFR") and o == "J" and in_spec:
        return "upstream", "anchored to journey"
    if k == "J" and o in ("FR", "NFR") and in_spec:
        return "downstream", "anchors requirement"
    if o == "T" and k in ("FR", "NFR", "J", "EV"):
        return "downstream", "implemented by ticket"
    if k == "T" and o in ("FR", "NFR", "J", "EV"):
        return "upstream", "implements"
    if k == "EV" and (o == "J" or o == "metric"):
        return "upstream", "measures"
    if k in ("metric", "tag", "event") and o == "EV":
        return "upstream", "fed by event"
    if o == "SIG":
        return "upstream", "from signal"
    if k == "SIG":
        return "downstream", "cited by"
    return "related", "mentioned together"


def _coverage_result(text: str) -> str:
    cells = [c.strip() for c in text.strip("|").split("|")]
    joined = " ".join(cells)
    if re.search(r"❌|\bfail(ed)?\b|\bhole\b|空洞", joined, re.I):
        return "hole" if re.search(r"\bhole\b|空洞", joined, re.I) else "fail"
    if re.search(r"✅|\bpass(ed)?\b", joined, re.I):
        return "pass"
    return "no result"


def query(index: Index, ident: str, feature_scoped_to: str | None = None) -> tuple[int, dict]:
    kind = kind_of(ident)
    if kind not in FEATURE_KINDS | {"SIG", "metric", "tag", "event"}:
        return 2, {"error": f"unsupported id {ident!r}: FR-n, NFR-n, J-n, EV-n, T-n, D<n>, SIG-<yyyymm>-<n>, metric:/tag:/event:<id>"}
    hits = [ln for ln in index.lines if ident in ln.ids]
    defs = [ln for ln in hits if _is_definition(ln, ident)]
    data_def = _data_definition(index, ident) if kind in DATA_DEFS else None
    containers = sorted({ln.container for ln in defs}) or sorted({ln.container for ln in hits if kind in FEATURE_KINDS})
    if kind in FEATURE_KINDS and len(containers) > 1:
        return 2, {"error": f"{ident} is defined in {len(containers)} places ({', '.join(containers)}); "
                            "a short id is scoped to one feature — pass --feature <feature-dir>"}
    if not hits and not data_def:
        return 1, {"id": ident, "found": False, "gaps": [f"{ident} appears nowhere in the scanned artifacts"]}
    home = containers[0] if containers else (hits[0].container if kind in FEATURE_KINDS and hits else None)
    scope_lines = [ln for ln in hits if kind not in FEATURE_KINDS or ln.container == home]
    result: dict = {"id": ident, "found": True, "kind": kind, "container": home or ("product" if data_def else None),
                    "definitions": [], "upstream": [], "downstream": [], "related": [], "mentions": [], "status": [], "gaps": []}
    for ln in defs:
        result["definitions"].append({"container": ln.container, "file": ln.rel, "line": ln.no, "version": _sha(ln.path)})
    if data_def:
        result["definitions"].append(data_def)
    seen = set()
    coverage = []
    for ln in scope_lines:
        if ln in defs:
            for other in ln.ids:
                if other != ident and (other, ln.rel, ln.no) not in seen:
                    seen.add((other, ln.rel, ln.no))
                    direction, label = _relation(ident, other, ln)
                    result[direction].append({"id": other, "relation": label, "file": ln.rel, "line": ln.no, "container": ln.container})
            continue
        if ln.rel.endswith("coverage.md") and ln.text.startswith("|"):
            first = ln.text.strip("|").split("|")[0].strip()
            if ident in first or kind == "J" and "E2E" in ln.text:
                coverage.append((ln, _coverage_result(ln.text)))
        others = [o for o in ln.ids if o != ident]
        if not others:
            result["mentions"].append({"file": ln.rel, "line": ln.no, "container": ln.container})
        for other in others:
            if (other, ln.rel, ln.no) in seen:
                continue
            seen.add((other, ln.rel, ln.no))
            direction, label = _relation(ident, other, ln)
            result[direction].append({"id": other, "relation": label, "file": ln.rel, "line": ln.no, "container": ln.container})
    # status: only from records
    if coverage:
        outcomes = [r for _, r in coverage]
        state = "failing" if "fail" in outcomes else "unverified (matrix hole)" if "hole" in outcomes else \
            "verified by coverage rows" if all(r == "pass" for r in outcomes) else "coverage rows without a result"
        result["status"].append({"status": state, "records": [f"{ln.rel}:{ln.no}" for ln, _ in coverage]})
    elif kind in ("FR", "NFR", "J", "EV"):
        result["status"].append({"status": "no verification record", "records": []})
    if kind == "T" and home:
        root = index.roots.get(home)
        ev = sorted(p.relative_to(root).as_posix() for p in root.glob(f"03-impl/{ident}-*evidence*.md")) if root else []
        ticket = index.tickets.get(home, {}).get(ident, {})
        result["status"].append({"status": "evidence recorded" if ev else "no evidence record", "records": ev})
        if ticket.get("status"):
            result["status"].append({"status": f"state.yaml ticket status: {ticket['status']}", "records": ["state.yaml"]})
    if kind in DATA_DEFS:
        result["status"].append({"status": "defined" if data_def else "undefined", "records": [d["file"] for d in result["definitions"]]})
    if kind == "SIG":
        result["status"].append({"status": "defined in the signal store" if defs else "not in the signal store", "records": []})
    for d in result["definitions"]:
        if d["file"] in index.stale.get(d["container"], set()):
            result["status"].append({"status": "stale (listed in state.yaml stale_artifacts)", "records": ["state.yaml"]})
    # gaps: what the canonical files do not say yet
    if not result["definitions"]:
        result["gaps"].append(f"{ident} is mentioned but not defined in its canonical file")
    if kind in ("FR", "NFR") and not any(u["relation"] == "anchored to journey" for u in result["upstream"]):
        result["gaps"].append("no journey anchor (J-n) on the requirement's own line")
    if kind in ("FR", "NFR", "J", "EV") and not coverage and home and (index.roots[home] / "04-verify/coverage.md").is_file():
        result["gaps"].append("coverage.md exists but has no row for this id")
    if kind == "T" and not result["upstream"]:
        result["gaps"].append("ticket names no FR/J it implements")
    if kind in DATA_DEFS and not data_def:
        result["gaps"].append(f"referenced but not defined in {DATA_DEFS[kind][0]}")
    for key in ("upstream", "downstream", "related"):
        result[key].sort(key=lambda r: (r["id"], r["file"], r["line"]))
    return 0, result


def _where(r: dict, home: str | None) -> str:
    prefix = "" if r.get("container") in (None, home) else f"{r['container']} "
    return f"{prefix}{r['file']}:{r['line']}"


def render(result: dict) -> str:
    if "error" in result:
        return f"trace: {result['error']}"
    if not result.get("found"):
        return f"{result['id']}: not found — " + "; ".join(result["gaps"])
    out = [f"{result['id']} · {result['container']}"]
    for d in result["definitions"]:
        out.append(f"  defined in {d['file']}:{d['line']} (version {d['version']})")
    for s in result["status"]:
        out.append(f"  status: {s['status']}" + (f" — {', '.join(s['records'])}" if s["records"] else ""))
    for key, title in (("upstream", "upstream"), ("downstream", "downstream"), ("related", "related")):
        if result[key]:
            out.append(f"  {title}:")
            out += [f"    {r['relation']} {r['id']} ({_where(r, result['container'])})" for r in result[key]]
    if result["mentions"]:
        out.append("  mentioned in: " + ", ".join(_where(m, result["container"]) for m in result["mentions"]))
    out.append("  gaps: " + ("; ".join(result["gaps"]) if result["gaps"] else "none"))
    out.append("  (read-only view rebuilt from the artifacts; re-verify through the owning task before changing state)")
    return "\n".join(out)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Read-only trace of one id across a project's SDLC artifacts.")
    ap.add_argument("id")
    ap.add_argument("--feature")
    ap.add_argument("--product-root")
    ap.add_argument("--project-root")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not (args.feature or args.product_root or args.project_root):
        print("trace: pass --feature, --product-root or --project-root", file=sys.stderr)
        return 2
    for value in (args.feature, args.product_root, args.project_root):
        if value and not Path(value).is_dir():
            print(f"trace: {value} is not a directory", file=sys.stderr)
            return 2
    index = build_index(args.feature, args.product_root, args.project_root)
    code, result = query(index, args.id)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
