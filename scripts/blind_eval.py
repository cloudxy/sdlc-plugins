#!/usr/bin/env python3
"""Blind rubric judging for /sdlc-eval (v2.1). Deterministic file operations only — it never calls a model.

The keyword grader (grade_eval.py) checks hygiene. This script sets up blind, rubric-based comparisons that fresh
judge subagents score, then validates, unblinds and aggregates the judgments.

Hardening after the 2026-09-17 GLM run, whose regression result was not valid evidence:
  hindsight  Arms ran in the live repository after the baseline design had been implemented and reviewed.
             regression-prepare exports the project at the baseline commit (git archive, read-only) and fingerprints
             the hindsight corpus (the baseline artifact, later reviews and docs, lines added to the repo later).
             prepare scans the new outputs: a verbatim hindsight line, a later commit id or a later numbered
             migration makes the case INVALID; a later distinctive file name is a suspect the user clears (REVIEW).
  blinding   Old sides held .sdlc/<feature>/… (hidden from a plain `ls`), new sides held memory/, product-delta.md…
             Blind copies are normalized (the .sdlc/<feature>/ prefix is dropped) and limited to the deliverables;
             memory/ and product-delta.md never reach a judge.
  swaps      A judge credited side A with side B's spec. Every score's "why" must quote its own side verbatim (「…」)
             or cite an image on its own side, the inventory must list the side's documents, and a verified defect
             caps that criterion at 3. `validate` checks this; a quote found only on the other side is a suspected swap.
  verdicts   aggregate prints PASS / FAIL / SPLIT / REVIEW / INVALID per case and summarizes counted cases only.

  python3 scripts/blind_eval.py prepare   --workspace W --iteration N --skill design-contract [--cases 1,2] [--seed 7]
  python3 scripts/blind_eval.py regression-prepare --workspace W --iteration N --case <case.json> --project-root <repo>
  python3 scripts/blind_eval.py prepare   --workspace W --iteration N --regression <case.json>
  python3 scripts/blind_eval.py validate  --folder <…/blind>
  python3 scripts/blind_eval.py leak-review --workspace W --iteration N --case <id> --decision clear|reject --reason "…"
  python3 scripts/blind_eval.py aggregate --workspace W --iteration N --skill <skill|regression>
  python3 scripts/blind_eval.py --self-test
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
from typing import Any, Iterable

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.abspath(__file__)
AB = ("A", "B")
VARIANTS = ("blind", "blind-swap")
SCALE = {
    "1": "missing or wrong",
    "2": "superficial: the words are there, the substance is not",
    "3": "adequate: meets the bar with visible gaps (also the cap for a criterion with a verified defect)",
    "4": "strong: specific, evidenced, few gaps",
    "5": "excellent: a senior practitioner would ship it as-is",
}
JUDGMENT_SCHEMA = {
    "inventory": {"A": ["<every document on side A, path relative to A/>"], "B": ["<every document on side B>"]},
    "defects": {
        "A": [{"criterion": "<criterion_id>", "file": "<path on side A>", "defect": "<the verified defect>"}],
        "B": [],
    },
    "scores": {
        "A": {"<criterion_id>": {"score": 1, "why": "<one line with a verbatim 「quote」 from side A, or A/<image path>>"}},
        "B": {"<criterion_id>": {"score": 1, "why": "<one line with a verbatim 「quote」 from side B, or B/<image path>>"}},
    },
    "preference": "A | B | tie",
    "rationale": "<2-3 sentences on the decisive differences in substance>",
}
TEXT_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".dbml", ".sql", ".csv", ".html", ".css", ".py", ".ts", ".tsx", ".js", ".jsx"}
CODE_EXT = TEXT_EXT | {".sh", ".toml", ".ini", ".cfg", ".xml", ".vue", ".scss", ".less", ".mjs", ".cjs", ".go", ".java", ".kt", ".rs", ".rb", ".php"}
READ_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".dbml", ".sql", ".csv"}  # a judge must list these in its inventory
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
SKILL_EXCLUDE = ["memory/", "product-delta.md"]
FEATURE_PREFIX = re.compile(r"^\.sdlc/[^/]+/")
QUOTE_RE = re.compile(r"「([^」]+)」")
PATH_RE = re.compile(r"(?<![\w/.-])([AB])/([^\s,;:()（）「」“”\"'`，。；：、]+)")
HEX_RE = re.compile(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])")
MIGRATION_RE = re.compile(r"^\d{3,}[_-]")
SUSPECT_ESCALATE = 3  # this many distinct later file names, none derivable from snapshot or inputs, is not a coincidence
MIN_LINE_WEIGHT = 50  # hindsight line fingerprint: CJK characters count 2
MIN_QUOTE = 6
MAX_TEXT_FILE = 1_000_000
GENERIC_BASENAMES = {
    "__init__.py", "index.ts", "index.tsx", "index.js", "index.html", "README.md", "package.json", "package-lock.json",
    "constants.ts", "conftest.py", "settings.py", "services.ts", "components.ts", "migration.py",
}


# ----------------------------------------------------------------------------- helpers
def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _itdir(workspace: str, iteration: str) -> str:
    it = str(iteration)
    return os.path.join(workspace, it if it.startswith("iteration-") else f"iteration-{it}")


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _dump_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _norm_rel(rel: str) -> str:
    rel = rel.replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    return FEATURE_PREFIX.sub("", rel)


def _walk_files(root: str) -> list[str]:
    out: list[str] = []
    if not os.path.isdir(root):
        return out
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for fn in files:
            if not fn.startswith("."):
                out.append(os.path.relpath(os.path.join(dirpath, fn), root).replace("\\", "/"))
    return sorted(out)


def _under(rel: str, paths: Iterable[str]) -> bool:
    """rel equals or lies inside one of the project-relative paths."""
    for p in paths:
        p = str(p).strip().rstrip("/")
        if p and (rel == p or rel.startswith(p + "/")):
            return True
    return False


def _matches(rel: str, patterns: Iterable[str]) -> bool:
    """Deliverable globs: 'dir/' or 'dir/**' match a subtree, anything else is an fnmatch pattern."""
    for p in patterns:
        p = str(p).strip()
        if not p:
            continue
        if p.endswith("/") or p.endswith("/**"):
            if _under(rel, [p[:-3] if p.endswith("/**") else p[:-1]]):
                return True
        elif fnmatch.fnmatch(rel, p):
            return True
    return False


def _read_text(path: str) -> str:
    try:
        if os.path.getsize(path) > MAX_TEXT_FILE:
            return ""
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _tree_text(root: str, exts: set[str]) -> Iterable[tuple[str, str]]:
    for rel in _walk_files(root):
        if os.path.splitext(rel)[1].lower() in exts:
            yield rel, _read_text(os.path.join(root, rel))


def _squash(s: str) -> str:
    return re.sub(r"[\s`*_#>|~]+", "", unicodedata.normalize("NFKC", s).lower())


def _line_key(line: str) -> str | None:
    s = unicodedata.normalize("NFKC", line)
    s = re.sub(r"^\s*(?:[-+]|\d+[.)])\s+", "", s)
    s = re.sub(r"[`*_#>|~]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    if sum(2 if ord(ch) >= 0x2E80 else 1 for ch in s) < MIN_LINE_WEIGHT:
        return None
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:20]


def _validate_rubric(rubric: Any, where: str) -> list[dict[str, Any]]:
    if not isinstance(rubric, list) or not rubric:
        raise SystemExit(f"{where}: rubric must be a non-empty list")
    seen = set()
    out = []
    for c in rubric:
        if not isinstance(c, dict) or not c.get("id") or not c.get("criterion"):
            raise SystemExit(f"{where}: each rubric item needs id and criterion")
        if c["id"] in seen:
            raise SystemExit(f"{where}: duplicate rubric id {c['id']}")
        seen.add(c["id"])
        w = c.get("weight", 1)
        if not isinstance(w, (int, float)) or w <= 0:
            raise SystemExit(f"{where}: rubric {c['id']} weight must be > 0")
        out.append({"id": str(c["id"]), "criterion": str(c["criterion"]), "weight": float(w)})
    return out


# ----------------------------------------------------------------------------- prepare
def _select(src_root: str, include: list[str] | None, exclude: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: dict[str, str] = {}
    for rel in _walk_files(src_root):
        nrel = _norm_rel(rel)
        if (exclude and _matches(nrel, exclude)) or (include is not None and not _matches(nrel, include)):
            continue
        if nrel in seen:
            print(f"⚠ {src_root}: {rel} and {seen[nrel]} normalize to the same path {nrel}; keeping {rel}", file=sys.stderr)
            pairs = [p for p in pairs if p[1] != nrel]
        seen[nrel] = rel
        pairs.append((rel, nrel))
    return pairs


def _prepare_case(casedir: str, arms: tuple[str, str], case_key: str, task_prompt: str, notes: str,
                  rubric: list[dict[str, Any]], rng: random.Random, skill: str,
                  include: list[str] | None, exclude: list[str]) -> dict[str, dict[str, str]]:
    selected = {}
    for arm in arms:
        src = os.path.join(casedir, arm, "outputs")
        if not os.path.isdir(src):
            raise SystemExit(f"{casedir}: missing {arm}/outputs — run the arms first")
        selected[arm] = _select(src, include, exclude)
        if not selected[arm]:
            print(f"⚠ {casedir}: arm {arm} has no files matching the deliverables — its side will be empty", file=sys.stderr)
    first, second = (arms[0], arms[1]) if rng.random() < 0.5 else (arms[1], arms[0])
    mapping = {"blind": {"A": first, "B": second}, "blind-swap": {"A": second, "B": first}}
    manifest: dict[str, Any] = {"include": include, "exclude": exclude, "arms": {}}
    for arm in arms:
        kept = [n for _, n in selected[arm]]
        dropped = [_norm_rel(r) for r in _walk_files(os.path.join(casedir, arm, "outputs")) if _norm_rel(r) not in kept]
        manifest["arms"][arm] = {"kept": kept, "dropped": dropped}
    for variant in VARIANTS:
        vdir = os.path.join(casedir, variant)
        for label in AB:
            arm = mapping[variant][label]
            dst_root = os.path.join(vdir, label)
            if os.path.isdir(dst_root):
                shutil.rmtree(dst_root)
            os.makedirs(dst_root, exist_ok=True)
            for rel, nrel in selected[arm]:
                dst = os.path.join(dst_root, nrel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(os.path.join(casedir, arm, "outputs", rel), dst)
        judgment = os.path.join(vdir, "judgment.json")
        if os.path.exists(judgment):
            os.remove(judgment)
        _dump_json(os.path.join(vdir, "rubric.json"), {
            "skill": skill,
            "case": case_key,
            "task_prompt": task_prompt,
            "reference_notes": notes,
            "criteria": rubric,
            "scale": SCALE,
            "judgment_file": judgment,
            "judgment_schema": JUDGMENT_SCHEMA,
            "validate_command": f"python3 {SCRIPT} validate --folder {vdir}",
        })
    _dump_json(os.path.join(casedir, "blind-manifest.json"), manifest)
    return mapping


def cmd_prepare(args: argparse.Namespace) -> int:
    itdir = _itdir(args.workspace, args.iteration)
    rng = random.Random(args.seed)
    packets: list[str] = []
    if args.regression:
        case = _load_json(args.regression)
        cid = str(case["id"])
        rubric = _validate_rubric(case.get("rubric"), args.regression)
        if not case.get("deliverables"):
            print(f"{args.regression}: regression cases need a 'deliverables' list (v2)", file=sys.stderr)
            return 2
        casedir = os.path.join(itdir, f"regression-{cid}")
        if not os.path.exists(os.path.join(casedir, "leak-markers.json")):
            print(f"{casedir}: no leak-markers.json — run regression-prepare (v2) before the arm, then re-run the arm", file=sys.stderr)
            return 2
        if not _walk_files(os.path.join(casedir, "new", "outputs")):
            print(f"{casedir}: new/outputs is empty — spawn the hat with task.md first", file=sys.stderr)
            return 2
        leak = _leak_scan(casedir)
        if leak["strong"]:
            for variant in VARIANTS:
                shutil.rmtree(os.path.join(casedir, variant), ignore_errors=True)
            print(f"✗ INVALID (leak) {cid}: the new outputs contain {len(leak['strong'])} hindsight marker(s). Do not judge.")
            for h in leak["strong"][:10]:
                print(f"   {h['file']}:{h['line']} [{h['kind']}] {h.get('marker') or h.get('source')} :: {h['text'][:90]}")
            print("   Re-run the arm in a fresh session whose working directory is not the live project, then prepare again.")
            return 4
        if leak["snapshot_writes"]:
            print(f"⚠ {cid}: the arm wrote {len(leak['snapshot_writes'])} file(s) into the snapshot (scanned): {', '.join(leak['snapshot_writes'][:5])}")
        if leak["suspect"]:
            names = sorted({h["marker"] for h in leak["suspect"]})
            print(f"⚠ REVIEW {cid}: new outputs name {len(names)} file(s) that only exist after the baseline: {', '.join(names[:8])}")
            print("   Judging can proceed; the verdict stays REVIEW until the user decides (leak-review). Hits: leak.json")
        mapping = {cid: _prepare_case(casedir, ("old", "new"), cid, case.get("task", ""),
                                      case.get("what_good_looks_like", ""), rubric, rng, case.get("skill", ""),
                                      [str(d) for d in case["deliverables"]], [])}
        skill_key = "regression"
        packets += [os.path.join(casedir, v) for v in VARIANTS]
    else:
        if not args.skill:
            print("prepare needs --skill or --regression", file=sys.stderr)
            return 2
        skill_key = args.skill
        evals = _load_json(os.path.join(args.plugin_root, "skills", args.skill, "evals", "evals.json"))
        wanted = {x.strip() for x in args.cases.split(",")} if args.cases else None
        mapping = {}
        for case in evals.get("evals") or []:
            cid = str(case.get("id"))
            if (wanted and cid not in wanted) or not case.get("rubric"):
                continue
            rubric = _validate_rubric(case["rubric"], f"{args.skill} case {cid}")
            casedir = os.path.join(itdir, f"{args.skill}-{cid}")
            mapping[cid] = _prepare_case(casedir, ("with_skill", "without_skill"), cid, case.get("prompt", ""),
                                         case.get("expected_output", ""), rubric, rng, args.skill,
                                         case.get("deliverables"), list(SKILL_EXCLUDE))
            packets += [os.path.join(casedir, v) for v in VARIANTS]
        if not mapping:
            print(f"no rubric cases for {args.skill} (add a 'rubric' list to evals.json cases)", file=sys.stderr)
            return 2
    map_path = os.path.join(itdir, f".blind-map-{skill_key}.json")
    existing = _load_json(map_path) if os.path.exists(map_path) else {}
    existing.update(mapping)
    _dump_json(map_path, existing)
    print(f"wrote {map_path} (unblinding map — never show it to judges)")
    print("spawn one fresh judge per folder (general-purpose, judge packet v2), all in one turn:")
    for p in packets:
        print(f"  {p}")
    return 0


# ----------------------------------------------------------------------------- judgments
def _score_of(entry: Any) -> float | None:
    if isinstance(entry, dict):
        entry = entry.get("score")
    if isinstance(entry, bool):
        return None
    try:
        v = float(entry)
    except (TypeError, ValueError):
        return None
    return v if 1 <= v <= 5 else None


def _side_rel(raw: Any, vdir: str) -> tuple[str, str | None]:
    """(path relative to its side, side letter named in the path or None)."""
    rel = str(raw.get("path") if isinstance(raw, dict) else raw).strip().replace("\\", "/")
    for side in AB:
        prefix = os.path.join(vdir, side).replace("\\", "/") + "/"
        if rel.startswith(prefix):
            return rel[len(prefix):], side
    m = re.match(r"^(?:\./)?([AB])/(.+)$", rel)
    if m:
        return m.group(2), m.group(1)
    return rel, None


def _evidence_problem(why: str, label: str, vdir: str, squashed: dict[str, str]) -> str:
    other = "B" if label == "A" else "A"
    quotes = [q for q in (_squash(x) for x in QUOTE_RE.findall(why)) if len(q) >= MIN_QUOTE]
    if any(q in squashed[label] for q in quotes):
        return ""
    images = [(side, rel.rstrip(".。,，;；)）]】")) for side, rel in PATH_RE.findall(why)]
    images = [(side, rel) for side, rel in images if os.path.splitext(rel)[1].lower() in IMAGE_EXT]
    if any(side == label and os.path.isfile(os.path.join(vdir, label, rel)) for side, rel in images):
        return ""
    if any(q in squashed[other] for q in quotes) or any(
            side == other and os.path.isfile(os.path.join(vdir, other, rel)) for side, rel in images):
        return f"its evidence is on side {other}, not {label} — suspected A/B swap; re-read both sides and re-score"
    if quotes:
        return "the 「quote」 is not verbatim in any file on its own side"
    return "no verbatim 「quote」 (≥6 characters) from its own side and no image path on its own side"


def _read_judgment(vdir: str, rubric: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[str]]:
    path = os.path.join(vdir, "judgment.json")
    if not os.path.exists(path):
        return None, ["missing judgment.json"]
    try:
        j = _load_json(path)
    except Exception as e:  # noqa: BLE001
        return None, [f"unparseable judgment.json: {e}"]
    if not isinstance(j, dict):
        return None, ["judgment.json must be a JSON object"]
    problems: list[str] = []
    ids = [c["id"] for c in rubric]
    sides = {label: os.path.join(vdir, label) for label in AB}

    inventory = j.get("inventory") if isinstance(j.get("inventory"), dict) else {}
    for label in AB:
        listed = set()
        for raw in inventory.get(label) or []:
            rel, named = _side_rel(raw, vdir)
            if named and named != label:
                problems.append(f"inventory.{label} lists {named}/{rel}, a file of side {named}")
            elif not os.path.isfile(os.path.join(sides[label], rel)):
                problems.append(f"inventory.{label} lists {rel!r}, which is not on side {label}")
            else:
                listed.add(rel)
        missing = [r for r in _walk_files(sides[label]) if os.path.splitext(r)[1].lower() in READ_EXT and r not in listed]
        if missing:
            problems.append(f"inventory.{label} misses {len(missing)} document(s): {', '.join(missing[:6])}")

    squashed = {label: _squash("\n".join(t for _, t in _tree_text(sides[label], TEXT_EXT))) for label in AB}
    scores = j.get("scores") if isinstance(j.get("scores"), dict) else {}
    out: dict[str, dict[str, float]] = {}
    for label in AB:
        per = scores.get(label) if isinstance(scores.get(label), dict) else {}
        row = {}
        for cid in ids:
            entry = per.get(cid)
            s = _score_of(entry)
            if s is None:
                problems.append(f"scores.{label}.{cid} missing or not 1-5")
                continue
            issue = _evidence_problem(str(entry.get("why", "")) if isinstance(entry, dict) else "", label, vdir, squashed)
            if issue:
                problems.append(f"scores.{label}.{cid}: {issue}")
            row[cid] = s
        out[label] = row

    defects = j.get("defects") if isinstance(j.get("defects"), dict) else {}
    for label in AB:
        for d in defects.get(label) or []:
            if not isinstance(d, dict):
                problems.append(f"defects.{label}: each entry must be an object with criterion, file, defect")
                continue
            cid = str(d.get("criterion", ""))
            if cid not in ids:
                problems.append(f"defects.{label}: unknown criterion {cid!r}")
                continue
            rel, named = _side_rel(d.get("file", ""), vdir)
            if (named and named != label) or not os.path.isfile(os.path.join(sides[label], rel)):
                problems.append(f"defects.{label}.{cid}: file {d.get('file')!r} is not on side {label}")
            if out.get(label, {}).get(cid, 0) > 3:
                problems.append(f"scores.{label}.{cid} is {out[label][cid]:g}, but a verified defect caps it at 3")

    pref = str(j.get("preference", "")).strip()
    if pref not in ("A", "B", "tie"):
        problems.append("preference must be A, B or tie")
    if problems:
        return None, problems
    return {"scores": out, "preference": pref, "rationale": str(j.get("rationale", "")), "defects": defects}, []


def cmd_validate(args: argparse.Namespace) -> int:
    vdir = os.path.abspath(args.folder)
    rubric = _load_json(os.path.join(vdir, "rubric.json"))["criteria"]
    _j, problems = _read_judgment(vdir, rubric)
    if problems:
        for p in problems:
            print(f"✗ {p}")
        print("Fix judgment.json and run validate again. Copy quotes from the files; never move a quote between sides to pass.")
        return 3
    print(f"✓ judgment valid: {len(rubric)} criteria × 2 sides, every score backed by own-side evidence")
    return 0


# ----------------------------------------------------------------------------- leak detection
def _leak_scan(casedir: str) -> dict[str, Any]:
    markers = _load_json(os.path.join(casedir, "leak-markers.json"))
    commits = [c.lower() for c in markers.get("commits") or []]
    lines = markers.get("lines") or {}
    names = markers.get("names") or []
    suspects = markers.get("suspects") or []
    strong: list[dict[str, Any]] = []
    weak: list[dict[str, Any]] = []
    texts = [(rel, text) for rel, text in _tree_text(os.path.join(casedir, "new", "outputs"), CODE_EXT)]
    snapshot = os.path.join(casedir, "snapshot")
    extracted_at = markers.get("snapshot_extracted_at") or 0
    written = [rel for rel in _walk_files(snapshot) if os.path.getmtime(os.path.join(snapshot, rel)) >= extracted_at] if extracted_at else []
    texts += [(f"snapshot/{rel}", _read_text(os.path.join(snapshot, rel))) for rel in written
              if os.path.splitext(rel)[1].lower() in CODE_EXT]
    for rel, text in texts:
        for i, line in enumerate(text.splitlines(), 1):
            hit = {"file": rel, "line": i, "text": line.strip()[:200]}
            k = _line_key(line)
            if k and k in lines:
                strong.append({**hit, "kind": "hindsight-line", "source": lines[k]})
            for tok in HEX_RE.findall(line.lower()):
                if re.search(r"[a-f]", tok) and any(c.startswith(tok) for c in commits):
                    strong.append({**hit, "kind": "later-commit", "marker": tok})
            strong += [{**hit, "kind": "later-file", "marker": n} for n in names if n in line]
            weak += [{**hit, "kind": "later-file-name", "marker": n} for n in suspects if n in line]
    distinct = sorted({h["marker"] for h in weak})
    if len(distinct) >= SUSPECT_ESCALATE:
        first = weak[0]
        strong.append({"file": first["file"], "line": first["line"], "text": ", ".join(distinct)[:200],
                       "kind": "later-file-names", "marker": f"{len(distinct)} distinct later file names"})
    result = {"scanned": _now(), "snapshot_writes": written, "strong": strong, "suspect": weak}
    _dump_json(os.path.join(casedir, "leak.json"), result)
    review = os.path.join(casedir, "leak-review.json")
    if os.path.exists(review):
        os.remove(review)  # a new scan needs a new decision
    return result


def cmd_leak_review(args: argparse.Namespace) -> int:
    casedir = os.path.join(_itdir(args.workspace, args.iteration), f"regression-{args.case}")
    leak_path = os.path.join(casedir, "leak.json")
    if not os.path.exists(leak_path):
        print(f"{leak_path} missing — run prepare --regression first", file=sys.stderr)
        return 2
    leak = _load_json(leak_path)
    if leak.get("strong"):
        print("strong leak hits cannot be cleared; re-run the arm", file=sys.stderr)
        return 2
    if not args.reason.strip():
        print("--reason is required (record the user's words)", file=sys.stderr)
        return 2
    _dump_json(os.path.join(casedir, "leak-review.json"), {
        "decision": args.decision, "reason": args.reason.strip(), "suspects": len(leak.get("suspect") or []), "recorded": _now()})
    print(f"recorded {args.decision} for {args.case}")
    return 0


def _git_out(project: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", project, *args], capture_output=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args[:2])} failed in {project}: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode("utf-8", "replace")


def _project_bytes(project: str, rel: str, ref: str | None) -> bytes | None:
    """A project file from the working tree, else from git at `ref` (projects may delete their .sdlc outputs)."""
    full = os.path.join(project, rel)
    if os.path.isfile(full):
        with open(full, "rb") as f:
            return f.read()
    if ref:
        r = subprocess.run(["git", "-C", project, "show", f"{ref}:{rel}"], capture_output=True)
        if r.returncode == 0:
            return r.stdout
    return None


def _resolve_baseline(project: str, case: dict[str, Any]) -> tuple[str, str]:
    if case.get("baseline_commit"):
        ref = str(case["baseline_commit"])
    elif case.get("baseline_before"):
        ref = _git_out(project, "rev-list", "-n1", f"--before={case['baseline_before']}", "HEAD").strip()
        if not ref:
            raise SystemExit(f"no commit before {case['baseline_before']} in {project}")
    else:
        raise SystemExit("regression case needs baseline_before (when the old artifact was started) or baseline_commit")
    sha, date = _git_out(project, "log", "-1", "--format=%H %cI", ref).split()
    return sha, date


def _extract_snapshot(project: str, sha: str, dest: str, exclude: list[str]) -> int:
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    dest_real = os.path.realpath(dest)
    proc = subprocess.Popen(["git", "-C", project, "archive", "--format=tar", sha], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    n = 0
    with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
        for m in tar:
            name = m.name.rstrip("/")
            if not (m.isfile() or m.isdir()) or name.startswith("/") or ".." in name.split("/"):
                continue
            if exclude and _under(name, exclude):
                continue
            target = os.path.realpath(os.path.join(dest, name))
            if target != dest_real and not target.startswith(dest_real + os.sep):
                continue
            tar.extract(m, dest)
            n += 1 if m.isfile() else 0
    err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
    if proc.wait() != 0:
        raise SystemExit(f"git archive failed: {err.strip()}")
    return n


def _build_leak_markers(project: str, sha: str, date: str, case: dict[str, Any], baseline_entries: list[tuple[str, str]],
                        snapshot: str, inputs_dir: str, ref: str | None = None) -> dict[str, Any]:
    targets = ["HEAD"] + ([ref] if ref else [])  # the artifacts commit may be older than a HEAD that deleted them
    exclude = [str(p) for p in case.get("exclude_paths") or []]
    hindsight = exclude + [str(p) for p in case.get("hindsight_paths") or []]
    input_paths = [str(p) for p in case.get("inputs") or []]

    known_keys: set[str] = set()
    known_parts: list[str] = []
    for root in (snapshot, inputs_dir):
        for _rel, text in _tree_text(root, CODE_EXT):
            known_parts.append(text)
            known_keys.update(k for k in map(_line_key, text.splitlines()) if k)
    for dirpath, _dirs, files in os.walk(os.path.join(PLUGIN_ROOT, "skills")):
        for fn in files:
            if fn.endswith((".md", ".yaml", ".yml", ".json", ".dbml")):
                known_keys.update(k for k in map(_line_key, _read_text(os.path.join(dirpath, fn)).splitlines()) if k)
    known_text = "\n".join(known_parts)

    corpus: dict[str, str] = {}

    def add(text: str, source: str) -> None:
        for line in text.splitlines():
            k = _line_key(line)
            if k and k not in known_keys and k not in corpus:
                corpus[k] = source

    for src, _as in baseline_entries:
        add((_project_bytes(project, src, ref) or b"").decode("utf-8", "replace"), src)
    for hp in hindsight:
        full = os.path.join(project, hp)
        if os.path.isfile(full) and hp not in input_paths:
            add(_read_text(full), hp)
        elif os.path.isdir(full):
            for rel, text in _tree_text(full, CODE_EXT):
                prel = f"{hp.rstrip('/')}/{rel}"
                if prel not in input_paths:
                    add(text, prel)
        elif ref:
            listed = subprocess.run(["git", "-C", project, "ls-tree", "-r", "--name-only", ref, "--", hp], capture_output=True)
            for prel in listed.stdout.decode("utf-8", "replace").splitlines():
                if prel not in input_paths and os.path.splitext(prel)[1].lower() in CODE_EXT:
                    add((_project_bytes(project, prel, ref) or b"").decode("utf-8", "replace"), prel)
    for target in targets:
        current = None
        for line in _git_out(project, "diff", "-U0", "--no-color", "--no-ext-diff", sha, target).splitlines():
            if line.startswith("+++ "):
                current = line[6:] if line.startswith("+++ b/") else None
            elif line.startswith("+") and current and not _under(current, input_paths) \
                    and os.path.splitext(current)[1].lower() in CODE_EXT:
                add(line[1:], f"{current} (added after the baseline)")

    names: list[str] = []
    for m in case.get("leak_markers") or []:
        m = str(m).strip()
        if m and m in known_text:
            print(f"⚠ leak marker {m!r} already appears in the snapshot or inputs — ignored", file=sys.stderr)
        elif m:
            names.append(m)
    suspects: list[str] = []
    added = {p for t in targets for p in _git_out(project, "diff", "--name-only", "--diff-filter=A", sha, t).splitlines()}
    for path in sorted(added):
        if path.startswith(".sdlc/") or _under(path, hindsight):
            continue  # documents: covered by line fingerprints
        base = os.path.basename(path)
        if base in GENERIC_BASENAMES or base in known_text:
            continue
        if MIGRATION_RE.match(base):
            names.append(base)
        elif len(os.path.splitext(base)[0]) >= 8:
            suspects.append(base)
    return {
        "baseline_commit": sha,
        "baseline_date": date,
        "commits": sorted({c for t in targets for c in _git_out(project, "rev-list", f"{sha}..{t}").split()}),
        "names": sorted(set(names)),
        "suspects": sorted(set(suspects)),
        "lines": corpus,
    }


def cmd_regression_prepare(args: argparse.Namespace) -> int:
    case = _load_json(args.case)
    cid = str(case["id"])
    _validate_rubric(case.get("rubric"), args.case)
    if not case.get("deliverables"):
        print(f"{args.case}: regression cases need a 'deliverables' list (v2)", file=sys.stderr)
        return 2
    project = os.path.abspath(os.path.expanduser(args.project_root))
    itdir = os.path.abspath(_itdir(args.workspace, args.iteration))
    casedir = os.path.join(itdir, f"regression-{cid}")
    new_out = os.path.join(casedir, "new", "outputs")
    if _walk_files(new_out) and not args.force:
        print(f"{new_out} already has files — pass --force to discard them and prepare again", file=sys.stderr)
        return 2
    baseline_entries: list[tuple[str, str]] = []
    for entry in case.get("baseline") or []:
        if isinstance(entry, dict):
            baseline_entries.append((str(entry["from"]), str(entry.get("as") or _norm_rel(entry["from"]))))
        else:
            baseline_entries.append((str(entry), _norm_rel(str(entry))))
    ref = str(case["artifacts_ref"]) if case.get("artifacts_ref") else None
    missing = [p for p, _ in baseline_entries if _project_bytes(project, p, ref) is None]
    missing += [p for p in case.get("inputs") or [] if _project_bytes(project, p, ref) is None]
    if missing:
        for m in missing:
            print(f"missing in the working tree{f' and at artifacts_ref {ref}' if ref else ''}: {m}", file=sys.stderr)
        return 2
    sha, date = _resolve_baseline(project, case)

    old_out = os.path.join(casedir, "old", "outputs")
    inputs_dir = os.path.join(casedir, "inputs")
    for d in (old_out, new_out, inputs_dir):
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
    for variant in VARIANTS:
        shutil.rmtree(os.path.join(casedir, variant), ignore_errors=True)
    for stale in ("leak.json", "leak-review.json", "blind-manifest.json"):
        if os.path.exists(os.path.join(casedir, stale)):
            os.remove(os.path.join(casedir, stale))
    for src, rel in baseline_entries:
        dst = os.path.join(old_out, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(_project_bytes(project, src, ref) or b"")
    input_list = []
    for rel in case.get("inputs") or []:
        dst = os.path.join(inputs_dir, _norm_rel(rel))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(_project_bytes(project, rel, ref) or b"")
        input_list.append(dst)

    exclude = [str(p) for p in case.get("exclude_paths") or []]
    snapshot = os.path.join(casedir, "snapshot")
    nfiles = _extract_snapshot(project, sha, snapshot, exclude)
    extracted_at = _dt.datetime.now().timestamp()  # extracted files carry the commit time; later writes are newer
    markers = _build_leak_markers(project, sha, date, case, baseline_entries, snapshot, inputs_dir, ref)
    markers["snapshot_extracted_at"] = extracted_at
    _dump_json(os.path.join(casedir, "leak-markers.json"), markers)

    product_root = case.get("product_root")
    if product_root:
        os.makedirs(os.path.join(new_out, product_root), exist_ok=True)
    lines = [
        f"# Regression {cid} · {case.get('title', '')}",
        "",
        f"subagent_type: sdlc-workflow:{case.get('hat', '')}",
        f"stage: {case.get('stage', '')}",
        f"primary_skill: sdlc-workflow:{case.get('skill', '')}",
        f"PLUGIN_ROOT: {PLUGIN_ROOT}",
        f"project_root: {snapshot}",
        f"deliverable_root: {new_out}",
        f"product_root: {os.path.join(new_out, product_root) if product_root else 'none'}",
        "",
        "## Where you work",
        "",
        f"- The project as it was at the baseline (commit {sha[:10]}, {date}) is the read-only snapshot {snapshot}.",
        "  Treat it as the project root: give every Read / Grep / Glob an absolute path under it and run shell commands",
        f"  as `cd {snapshot} && …`. It has no git history.",
        "- Your session's working directory may be a newer copy of this project. Do not read, search or run git there.",
        "  Code, reviews and product documents written after the baseline are hindsight; a leak scan fingerprints them",
        "  and a hit makes this case INVALID.",
        f"- Allowed reads: the snapshot, the inputs below, PLUGIN_ROOT, and the web. Never open {casedir}/old or other cases.",
        "",
        "## Task",
        "",
        str(case.get("task", "")),
        "",
        "## Inputs (read-only copies)",
        "",
    ]
    lines += [f"- {p}" for p in input_list]
    lines += ["", "## Product layer", ""]
    if product_root:
        lines.append(f"product_root {os.path.join(new_out, product_root)} starts empty: this project had no product layer at the "
                     "baseline. Write product files there when your procedure calls for them.")
    else:
        lines.append("There is no product layer for this regression. Do not create product files; mark inferences [推断].")
    lines += [
        "",
        "## Deliverables (only these are judged)",
        "",
        f"Write under {new_out}/ with exactly these relative paths (globs as shown):",
    ]
    lines += [f"- {d}" for d in case["deliverables"]]
    lines += [
        "",
        "Do not write memory files or product-delta.md for this regression. Do not spawn subagents.",
        "Return the list of files you wrote.",
        "",
    ]
    with open(os.path.join(casedir, "task.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"prepared {casedir}")
    print(f"  snapshot: {nfiles} files at {sha[:10]} ({date}); excluded: {', '.join(exclude) or 'nothing'}")
    print(f"  hindsight fingerprints: {len(markers['lines'])} lines · {len(markers['commits'])} later commits · "
          f"{len(markers['names'])} strong names · {len(markers['suspects'])} suspect names")
    print(f"  old baseline (normalized): {old_out}")
    print(f"  spawn sdlc-workflow:{case.get('hat', '')} with the prompt in {os.path.join(casedir, 'task.md')}")
    return 0


# ----------------------------------------------------------------------------- aggregate
def _verdict(casedir: str, valid: list[dict[str, Any]], new_arm: str, old_arm: str, regression: bool) -> str:
    if regression:
        leak_path = os.path.join(casedir, "leak.json")
        if not os.path.exists(leak_path):
            return "INVALID (no leak scan)"
        leak = _load_json(leak_path)
        if leak.get("strong"):
            return "INVALID (leak)"
        if leak.get("suspect"):
            review_path = os.path.join(casedir, "leak-review.json")
            if not os.path.exists(review_path):
                return "REVIEW (leak suspects)"
            if _load_json(review_path).get("decision") != "clear":
                return "INVALID (leak)"
    if len(valid) < len(VARIANTS):
        return "INVALID (judgments)"
    prefs = [v["preference"] for v in valid]
    if all(p == new_arm for p in prefs):
        crit = valid[0]["arms"][new_arm]["criteria"].keys()
        drops = [k for k in crit if sum(v["arms"][new_arm]["criteria"][k] for v in valid)
                 < sum(v["arms"][old_arm]["criteria"][k] for v in valid)]
        return f"FAIL (drops: {', '.join(drops)})" if drops else "PASS"
    if all(p == old_arm for p in prefs):
        return "FAIL"
    return "SPLIT"


def _counted(verdict: str) -> bool:
    return verdict in ("PASS", "SPLIT") or verdict.startswith("FAIL")


def cmd_aggregate(args: argparse.Namespace) -> int:
    itdir = _itdir(args.workspace, args.iteration)
    map_path = os.path.join(itdir, f".blind-map-{args.skill}.json")
    if not os.path.exists(map_path):
        print(f"missing {map_path} — run prepare first", file=sys.stderr)
        return 2
    mapping = _load_json(map_path)
    regression = args.skill == "regression"
    new_arm, old_arm = ("new", "old") if regression else ("with_skill", "without_skill")
    report: dict[str, Any] = {"skill": args.skill, "iteration_dir": itdir, "cases": [], "problems": []}
    arm_scores: dict[str, list[float]] = {}
    arm_criteria: dict[str, dict[str, list[float]]] = {}
    wins: dict[str, float] = {}
    verdicts: dict[str, str] = {}
    for cid, variants in mapping.items():
        casedir = os.path.join(itdir, f"regression-{cid}" if regression else f"{args.skill}-{cid}")
        row: dict[str, Any] = {"id": cid, "variants": [], "invalid_variants": []}
        valid: list[dict[str, Any]] = []
        for variant, labels in variants.items():
            vdir = os.path.join(casedir, variant)
            if not os.path.exists(os.path.join(vdir, "rubric.json")):
                row["invalid_variants"].append({"variant": variant, "problems": ["blind folder missing"]})
                continue
            rubric = _load_json(os.path.join(vdir, "rubric.json"))["criteria"]
            weights = {c["id"]: c["weight"] for c in rubric}
            j, problems = _read_judgment(vdir, rubric)
            if j is None:
                report["problems"] += [f"{cid}/{variant}: {p}" for p in problems]
                row["invalid_variants"].append({"variant": variant, "problems": problems})
                continue
            vrow: dict[str, Any] = {"variant": variant, "arms": {}, "rationale": j["rationale"], "defects": j["defects"]}
            for label, arm in labels.items():
                sc = j["scores"][label]
                vrow["arms"][arm] = {"weighted": round(sum(sc[k] * weights[k] for k in sc) / sum(weights.values()), 3), "criteria": sc}
            vrow["preference"] = "tie" if j["preference"] == "tie" else labels[j["preference"]]
            row["variants"].append(vrow)
            valid.append(vrow)
        verdict = _verdict(casedir, valid, new_arm, old_arm, regression)
        row["verdict"] = verdict
        verdicts[cid] = verdict
        if regression and os.path.exists(os.path.join(casedir, "leak.json")):
            leak = _load_json(os.path.join(casedir, "leak.json"))
            row["leak"] = {"strong": len(leak.get("strong") or []), "suspect": sorted({h["marker"] for h in leak.get("suspect") or []})}
        if valid:
            row["mean_weighted"] = {arm: round(sum(v["arms"][arm]["weighted"] for v in valid) / len(valid), 3) for arm in (new_arm, old_arm)}
            row["criterion_delta"] = {k: round(sum(v["arms"][new_arm]["criteria"][k] - v["arms"][old_arm]["criteria"][k] for v in valid) / len(valid), 2)
                                      for k in valid[0]["arms"][new_arm]["criteria"]}
        if _counted(verdict):
            for arm in (new_arm, old_arm):
                arm_scores.setdefault(arm, []).append(row["mean_weighted"][arm])
                for v in valid:
                    for k, s in v["arms"][arm]["criteria"].items():
                        arm_criteria.setdefault(arm, {}).setdefault(k, []).append(s)
            for v in valid:
                if v["preference"] == "tie":
                    for arm in (new_arm, old_arm):
                        wins[arm] = wins.get(arm, 0) + 0.5 / len(valid)
                else:
                    wins[v["preference"]] = wins.get(v["preference"], 0) + 1 / len(valid)
        report["cases"].append(row)
    counted = [c for c, v in verdicts.items() if _counted(v)]
    report["summary"] = {
        "verdicts": verdicts,
        "cases_counted": len(counted),
        "cases_not_counted": [c for c in verdicts if c not in counted],
        "mean_weighted": {arm: round(sum(v) / len(v), 3) for arm, v in arm_scores.items()},
        "win_rate": {arm: round(w / len(counted), 3) for arm, w in wins.items()} if counted else {},
        "criteria_means": {arm: {k: round(sum(v) / len(v), 2) for k, v in crit.items()} for arm, crit in arm_criteria.items()},
    }
    out = args.json_out or os.path.join(itdir, f"rubric-{args.skill}.json")
    _dump_json(out, report)
    print(f"wrote {out}")
    print(f"{'case':<32} {'verdict':<24} {new_arm:>10} {old_arm:>13}")
    for c in report["cases"]:
        mw = c.get("mean_weighted") or {}
        cells = [f"{mw[a]:.2f}" if a in mw else "-" for a in (new_arm, old_arm)]
        print(f"{c['id']:<32} {c['verdict']:<24} {cells[0]:>10} {cells[1]:>13}")
    s = report["summary"]
    print("----------------------------------------")
    print(f"counted cases: {s['cases_counted']} · not counted: {', '.join(s['cases_not_counted']) or 'none'}")
    for arm, w in sorted(s["mean_weighted"].items()):
        print(f"  {arm:<14} mean weighted {w:.2f} · win rate {s['win_rate'].get(arm, 0):.2f}")
    for p in report["problems"]:
        print(f"⚠ {p}")
    print("REVIEW and INVALID cases are not counted. A judge rationale is a lead, not a finding: open the cited file on the "
          "cited side before repeating any claim from it.")
    return 3 if report["problems"] else 0


# ----------------------------------------------------------------------------- self-test
def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _judge(vdir: str, labels: dict[str, str], strong_arm: str, strong_quotes: tuple[str, str], weak_quotes: tuple[str, str],
           files: list[str], swap: bool = False, defects: dict[str, Any] | None = None) -> None:
    strong = [lab for lab, arm in labels.items() if arm == strong_arm][0]
    weak = "B" if strong == "A" else "A"
    if swap:
        strong_quotes, weak_quotes = weak_quotes, strong_quotes
    _dump_json(os.path.join(vdir, "judgment.json"), {
        "inventory": {"A": files, "B": files},
        "defects": defects or {"A": [], "B": []},
        "scores": {
            strong: {"value": {"score": 5, "why": f"names it: 「{strong_quotes[0]}」"}, "evidence": {"score": 4, "why": f"「{strong_quotes[1]}」"}},
            weak: {"value": {"score": 2, "why": f"only 「{weak_quotes[0]}」"}, "evidence": {"score": 1, "why": f"「{weak_quotes[1]}」"}},
        },
        "preference": strong, "rationale": "r"})


def self_test() -> int:  # noqa: C901
    def fail(msg: str, *extra: Any) -> int:
        print("self-test FAILED:", msg, *extra)
        return 1

    with tempfile.TemporaryDirectory() as td:
        # ---- skill mode: normalization, memory exclusion, evidence validation, swap, inventory, defect cap
        plugin = os.path.join(td, "plugin")
        _dump_json(os.path.join(plugin, "skills", "demo", "evals", "evals.json"), {"evals": [
            {"id": 1, "prompt": "p", "expected_output": "good", "rubric": [
                {"id": "value", "criterion": "finds the value", "weight": 3},
                {"id": "evidence", "criterion": "cites evidence", "weight": 1}]},
            {"id": 2, "prompt": "no rubric case", "expected_output": "x"},
        ]})
        ws = os.path.join(td, "ws")
        it = os.path.join(ws, "iteration-1")
        _write(os.path.join(it, "demo-1", "with_skill", "outputs", "out.md"), "strong answer: the Aha moment is the first report\n")
        _write(os.path.join(it, "demo-1", "with_skill", "outputs", "memory", "pm.md"), "self praise\n")
        _write(os.path.join(it, "demo-1", "with_skill", "outputs", "product-delta.md"), "| row |\n")
        _write(os.path.join(it, "demo-1", "without_skill", "outputs", ".sdlc", "f", "out.md"), "weak answer: lists features only\n")
        ns = argparse.Namespace(workspace=ws, iteration="1", skill="demo", cases=None, seed=3, regression=None, plugin_root=plugin)
        if cmd_prepare(ns) != 0:
            return fail("prepare failed")
        mapping = _load_json(os.path.join(it, ".blind-map-demo.json"))
        if set(mapping) != {"1"}:
            return fail("only rubric cases should be prepared", mapping)
        for variant in VARIANTS:
            for label in AB:
                if _walk_files(os.path.join(it, "demo-1", variant, label)) != ["out.md"]:
                    return fail("blind sides must be normalized and exclude memory/ and product-delta.md", variant, label)
        good = ("the Aha moment is the first report", "strong answer")
        bad = ("lists features only", "weak answer")
        for variant, labels in mapping["1"].items():
            _judge(os.path.join(it, "demo-1", variant), labels, "with_skill", good, bad, ["out.md"])
        agg = argparse.Namespace(workspace=ws, iteration="1", skill="demo", json_out=None)
        if cmd_aggregate(agg) != 0:
            return fail("aggregate reported problems for valid judgments")
        s = _load_json(os.path.join(it, "rubric-demo.json"))["summary"]
        if s["win_rate"].get("with_skill") != 1.0 or abs(s["mean_weighted"]["with_skill"] - 4.75) > 1e-6 or s["verdicts"]["1"] != "PASS":
            return fail("unexpected summary", s)
        vdir = os.path.join(it, "demo-1", "blind")
        labels = mapping["1"]["blind"]
        crit = _load_json(os.path.join(vdir, "rubric.json"))["criteria"]
        _judge(vdir, labels, "with_skill", good, bad, ["out.md"], swap=True)
        _j, problems = _read_judgment(vdir, crit)
        if not any("suspected A/B swap" in p for p in problems):
            return fail("A/B swap should be detected", problems)
        if cmd_aggregate(agg) != 3 or _load_json(os.path.join(it, "rubric-demo.json"))["summary"]["verdicts"]["1"] != "INVALID (judgments)":
            return fail("a swapped judgment must make the case INVALID (judgments)")
        _judge(vdir, labels, "with_skill", good, bad, [])
        _j, problems = _read_judgment(vdir, crit)
        if not any("misses 1 document" in p for p in problems):
            return fail("an inventory that skips documents must be rejected", problems)
        strong_label = [lab for lab, arm in labels.items() if arm == "with_skill"][0]
        _judge(vdir, labels, "with_skill", good, bad, ["out.md"],
               defects={strong_label: [{"criterion": "value", "file": f"{strong_label}/out.md", "defect": "contradiction"}]})
        _j, problems = _read_judgment(vdir, crit)
        if not any("caps it at 3" in p for p in problems):
            return fail("a defect must cap its criterion at 3", problems)
        _judge(vdir, labels, "with_skill", ("invented paraphrase of the value", "strong answer"), bad, ["out.md"])
        _j, problems = _read_judgment(vdir, crit)
        if not any("not verbatim" in p for p in problems):
            return fail("a paraphrased quote must be rejected", problems)

        # ---- regression mode: baseline snapshot, hindsight fingerprints, deliverables, verdicts
        project = os.path.join(td, "proj")
        os.makedirs(project)
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
                   GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

        def git(*a: str, date: str | None = None) -> None:
            e = dict(env)
            if date:
                e["GIT_AUTHOR_DATE"] = e["GIT_COMMITTER_DATE"] = date
            subprocess.run(["git", "-C", project, *a], check=True, capture_output=True, env=e)

        review_line = "The featured shelf ranks assets by curator weight first and falls back to install recency second."
        git("init", "-q")
        _write(os.path.join(project, "app", "service_core.py"), "base\n")
        _write(os.path.join(project, ".sdlc", "f", "00-discover", "briefing.md"), "brief: operators need a curated shelf\n")
        git("add", "-A")
        git("commit", "-qm", "base", date="2026-09-14T10:00:00+08:00")
        _write(os.path.join(project, ".sdlc", "f", "01-define", "spec.md"), "old spec\n")
        _write(os.path.join(project, ".sdlc", "f", "05-review", "findings.md"), review_line + "\n")
        _write(os.path.join(project, "app", "migrations", "050_featured_examples.py"), "post baseline\n")
        _write(os.path.join(project, "app", "featured_projection.py"), "def project(): pass\n")
        git("add", "-A")
        git("commit", "-qm", "impl", date="2026-09-16T10:00:00+08:00")
        later_sha = _git_out(project, "rev-parse", "HEAD").strip()
        git("rm", "-r", "-q", ".sdlc/f")  # the project later deletes its workflow outputs; the case reads them from history
        git("commit", "-qm", "cleanup", date="2026-09-18T10:00:00+08:00")
        case_path = os.path.join(td, "R9.json")
        _dump_json(case_path, {"id": "R9", "skill": "prd-gwt", "hat": "pm", "stage": "define", "task": "write spec",
                               "baseline_before": "2026-09-15T00:00:00+08:00", "artifacts_ref": later_sha, "exclude_paths": [".sdlc/f"],
                               "inputs": [".sdlc/f/00-discover/briefing.md"],
                               "baseline": [{"from": ".sdlc/f/01-define/spec.md", "as": "01-define/spec.md"}],
                               "deliverables": ["01-define/spec.md", "product/"], "product_root": "product",
                               "rubric": [{"id": "value", "criterion": "c", "weight": 1}]})
        rp = argparse.Namespace(workspace=ws, iteration="1", case=case_path, project_root=project, force=False)
        if cmd_regression_prepare(rp) != 0:
            return fail("regression-prepare failed")
        cdir = os.path.join(it, "regression-R9")
        if _read_text(os.path.join(cdir, "old", "outputs", "01-define", "spec.md")) != "old spec\n" \
                or not _walk_files(os.path.join(cdir, "inputs")):
            return fail("inputs and baseline deleted from the working tree must be read from artifacts_ref")
        snap = _walk_files(os.path.join(cdir, "snapshot"))
        if snap != ["app/service_core.py"]:
            return fail("snapshot must be the baseline commit minus exclude_paths", snap)
        markers = _load_json(os.path.join(cdir, "leak-markers.json"))
        if "050_featured_examples.py" not in markers["names"] or "featured_projection.py" not in markers["suspects"]:
            return fail("later migration must be a strong name and later module a suspect", markers["names"], markers["suspects"])
        if _line_key(review_line) not in markers["lines"]:
            return fail("later review lines must be fingerprinted")
        if "product_root:" not in _read_text(os.path.join(cdir, "task.md")):
            return fail("task.md must name the product root")
        pr = argparse.Namespace(workspace=ws, iteration="1", skill=None, cases=None, seed=1, regression=case_path, plugin_root=plugin)
        new_spec = os.path.join(cdir, "new", "outputs", ".sdlc", "f", "01-define", "spec.md")
        _write(new_spec, "new spec\n" + review_line + "\n")
        if cmd_prepare(pr) != 4 or os.path.isdir(os.path.join(cdir, "blind")):
            return fail("a verbatim hindsight line must stop prepare (INVALID) without blind folders")
        _write(new_spec, f"new spec, see commit {later_sha[:9]}\n")
        if cmd_prepare(pr) != 4:
            return fail("a later commit id must stop prepare")
        _write(new_spec, "new spec adds app/featured_projection.py for the shelf\n")
        _write(os.path.join(cdir, "new", "outputs", "product", "strategy.md"), "new strategy\n")
        _write(os.path.join(cdir, "new", "outputs", "memory", "pm.md"), "mem\n")
        if cmd_prepare(pr) != 0:
            return fail("suspects alone must not stop prepare")
        for variant in VARIANTS:
            sides = [_walk_files(os.path.join(cdir, variant, label)) for label in AB]
            if sorted(map(tuple, sides)) != [("01-define/spec.md",), ("01-define/spec.md", "product/strategy.md")]:
                return fail("regression blind sides must hold only normalized deliverables", sides)
        if cmd_regression_prepare(rp) != 2:
            return fail("regression-prepare must refuse to wipe an arm's outputs without --force")
        markers_path = os.path.join(cdir, "leak-markers.json")
        saved = _load_json(markers_path)
        tampered = dict(saved, suspects=saved["suspects"] + ["featured_sorting.py", "hub_curation.py"])
        _dump_json(markers_path, tampered)
        _write(os.path.join(cdir, "snapshot", "app", "notes.md"), "arm scribble: featured_sorting.py and hub_curation.py\n")
        if cmd_prepare(pr) != 4 or "app/notes.md" not in _load_json(os.path.join(cdir, "leak.json"))["snapshot_writes"]:
            return fail("three distinct later file names (incl. ones written into the snapshot) must escalate to INVALID")
        os.remove(os.path.join(cdir, "snapshot", "app", "notes.md"))
        _dump_json(markers_path, saved)
        if cmd_prepare(pr) != 0:
            return fail("prepare should succeed again after the escalation fixture is removed")
        rmap = _load_json(os.path.join(it, ".blind-map-regression.json"))["R9"]
        for variant, labels in rmap.items():
            new_label = [lab for lab, arm in labels.items() if arm == "new"][0]
            old_label = "B" if new_label == "A" else "A"
            inv = {new_label: ["01-define/spec.md", "product/strategy.md"], old_label: ["01-define/spec.md"]}
            _dump_json(os.path.join(cdir, variant, "judgment.json"), {
                "inventory": inv,
                "scores": {new_label: {"value": {"score": 5, "why": "「adds app/featured_projection.py」"}},
                           old_label: {"value": {"score": 2, "why": "「old spec」 only"}}},
                "preference": new_label, "rationale": "r"})
        ra = argparse.Namespace(workspace=ws, iteration="1", skill="regression", json_out=None)
        cmd_aggregate(ra)
        if _load_json(os.path.join(it, "rubric-regression.json"))["summary"]["verdicts"]["R9"] != "REVIEW (leak suspects)":
            return fail("suspect hits must hold the verdict at REVIEW")
        lr = argparse.Namespace(workspace=ws, iteration="1", case="R9", decision="clear", reason="user: name follows the task wording")
        if cmd_leak_review(lr) != 0 or cmd_aggregate(ra) != 0:
            return fail("leak-review clear should let aggregate pass")
        if _load_json(os.path.join(it, "rubric-regression.json"))["summary"]["verdicts"]["R9"] != "PASS":
            return fail("cleared suspects with two agreeing valid judges must PASS")
    print("self-test ok")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Blind rubric judging for sdlc-eval (no model calls).")
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("prepare")
    p.add_argument("--workspace", required=True)
    p.add_argument("--iteration", default="1")
    p.add_argument("--skill")
    p.add_argument("--cases")
    p.add_argument("--regression", help="regression case JSON (arms old/new)")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--plugin-root", default=PLUGIN_ROOT)
    a = sub.add_parser("aggregate")
    a.add_argument("--workspace", required=True)
    a.add_argument("--iteration", default="1")
    a.add_argument("--skill", required=True, help="skill name, or 'regression'")
    a.add_argument("--json-out")
    v = sub.add_parser("validate")
    v.add_argument("--folder", required=True)
    r = sub.add_parser("regression-prepare")
    r.add_argument("--workspace", required=True)
    r.add_argument("--iteration", default="1")
    r.add_argument("--case", required=True)
    r.add_argument("--project-root", required=True)
    r.add_argument("--force", action="store_true", help="discard existing new/outputs")
    lr = sub.add_parser("leak-review")
    lr.add_argument("--workspace", required=True)
    lr.add_argument("--iteration", default="1")
    lr.add_argument("--case", required=True)
    lr.add_argument("--decision", required=True, choices=["clear", "reject"])
    lr.add_argument("--reason", required=True)
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    handlers = {"prepare": cmd_prepare, "aggregate": cmd_aggregate, "validate": cmd_validate,
                "regression-prepare": cmd_regression_prepare, "leak-review": cmd_leak_review}
    if args.cmd in handlers:
        return handlers[args.cmd](args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
