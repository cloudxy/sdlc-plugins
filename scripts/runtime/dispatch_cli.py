#!/usr/bin/env python3
"""Unified light/strict dispatch & finish CLI wrappers over existing v2/v3 protocols.

  python3 scripts/workflow.py dispatch --mode light --role <r> --stage <s> --task <t> \
      --feature-root <dir> --project-root <dir> --intent-quote "<q>" [--source-write <p>...] [--input <p>...]
  python3 scripts/workflow.py dispatch --mode strict --role <r> --stage <s> --task <t> \
      --feature-root <dir> --bindings <json> --draft-out <json> [--scope feature]
  python3 scripts/workflow.py finish --mode light --run <light-manifest.json>
  python3 scripts/workflow.py finish --mode strict --run <manifest.json> [--return <file>] \
      [--interrupted <reason>] [--concurrent] [--feature-root <feature-root>] [--task-id <id>]

Compatibility & Write-Audit Guarantees:
- NEVER downgrades `protocol_required` tasks into `--mode light` (neither in dispatch nor finish).
- `dispatch --mode light` binds task, allowed `deliverable_paths`, `memory_file`, `source_writes`,
  `project_root`, and a full content SHA-256 `baseline_snapshot` of the workspace into an immutable
  light manifest (`<feature_root>/runs/light-<run_id>-manifest.json`).
- `finish --mode light` MUST verify against that bound manifest (`--run`), NEVER trusting caller-supplied
  write scopes or omitted project_root. Pre-existing dirty files whose content did not change are preserved
  untouched; re-edits to already-dirty files, new untracked files, deletions, and writes outside bound
  deliverables/memory/`source_writes` are all caught.
- Overlapping concurrent light runs on the same `project_root` or snapshot coverage gaps report explicit
  `write_audit_status: "unknown_concurrent"` / `"unknown"` and fail closed (`ok: false`).
- Underlying `prepare` / `seal` / `record` / `check-tasks` / `continuous` commands remain intact.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1])  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

import argparse
import datetime as dt
import json
import re
import sys
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any
from zoneinfo import ZoneInfo

from runtime.bootstrap_route import HIGH_RISK_RULES
from gates.check_packet import lint as lint_v2_packet
from runtime.runtime_protocol import ProtocolError, changes as snapshot_changes, digest, file_hash, load, snapshot, write_json
from runtime.task_runtime import lint_packet_v3, prepare, record, seal, seal_dispatch_view
from runtime.task_state import check_tasks
from workflow import ROOT, check_task, load_registry, resolve_task, success_check

DEFAULT_LIGHT_SNAPSHOT_LIMIT = 20000


def _strip_dot_slash(raw_posix: str) -> str:
    """Remove only exact leading './' prefixes without corrupting dotfiles (.env, .github/...) or '..'."""
    norm = raw_posix
    while norm.startswith("./"):
        norm = norm[2:]
    return norm


def _matches_declared_artifact(rel_posix: str, pattern_path: str) -> bool:
    """Check whether a normalized relative deliverable path matches a registry artifact path pattern."""
    pat = _strip_dot_slash(pattern_path.replace("\\", "/"))
    if pat.endswith("/"):
        prefix = pat.rstrip("/")
        return rel_posix == prefix or rel_posix.startswith(prefix + "/")
    # Convert placeholders like <n>, <id>, <slug> to single-segment non-slash wildcards
    regex = "^" + re.sub(r"<[^>]+>", r"[^/]+", re.escape(pat).replace(r"\<", "<").replace(r"\>", ">")) + "$"
    return bool(re.fullmatch(regex, rel_posix))


def _allowed_deliverable_patterns(registry: dict[str, Any], task_contract: dict[str, Any]) -> list[str]:
    patterns: list[str] = []
    for key_group in ("required", "optional"):
        for art_key in task_contract.get(key_group, []):
            art = registry.get("artifacts", {}).get(art_key)
            if art:
                patterns.extend(art.get("paths", []))
    return patterns


def _validate_deliverables(
    registry: dict[str, Any],
    task_contract: dict[str, Any],
    deliverables: list[str],
    feature_root: Path,
) -> list[str]:
    froot = feature_root.resolve()
    patterns = _allowed_deliverable_patterns(registry, task_contract)
    out: list[str] = []
    for raw in deliverables:
        s = raw.strip()
        if not s:
            raise ValueError("deliverable path cannot be empty")
        posix = s.replace("\\", "/")
        p_raw = PurePosixPath(posix)
        if p_raw.is_absolute() or posix.startswith("/"):
            raise ValueError(f"deliverable must be relative to feature_root: {raw}")
        if ".." in p_raw.parts:
            raise ValueError(f"deliverable must not traverse parent directories ('..'): {raw}")
        norm = _strip_dot_slash(posix).rstrip("/")
        if s.endswith("/") and norm:
            norm += "/"
        if not norm or norm in (".", "/"):
            raise ValueError(f"deliverable must name a file/dir inside feature_root: {raw}")
        resolved = (froot / norm.rstrip("/")).resolve()
        if resolved == froot or not resolved.is_relative_to(froot):
            raise ValueError(f"deliverable escapes feature_root: {raw}")
        if patterns and not any(_matches_declared_artifact(norm, pat) for pat in patterns):
            raise ValueError(
                f"deliverable {raw!r} is outside task contract allowed outputs ({patterns})"
            )
        out.append(norm)
    return out


def _resolve_output_paths(
    registry: dict[str, Any],
    task_contract: dict[str, Any],
    deliverables: list[str] | None,
    feature_root: Path,
) -> list[str]:
    if deliverables:
        return _validate_deliverables(registry, task_contract, deliverables, feature_root)
    out = []
    for art_key in task_contract.get("required", []):
        paths = registry["artifacts"][art_key]["paths"]
        if paths:
            out.append(paths[0])
    return out


def _render_check_cmd(registry: dict[str, Any], task_contract: dict[str, Any], feature_root: Path) -> str:
    cmd = success_check(task_contract)
    return cmd.replace("<PLUGIN_ROOT>", str(ROOT)).replace("<feature_dir>", str(feature_root))


def _normalize_source_writes(project_root: Path, source_writes: list[str]) -> list[str]:
    """Validate and normalize --source-write paths without corrupting dotfiles or allowing '..' escape."""
    out = []
    proot = project_root.resolve()
    sdlc_root = (proot / ".sdlc").resolve()
    for raw in source_writes:
        s = raw.strip()
        if not s:
            continue
        posix = s.replace("\\", "/")
        p_posix = PurePosixPath(posix)
        if ".." in p_posix.parts:
            raise ValueError(f"source_write must not traverse parent directories ('..'): {raw}")
        p = Path(s)
        if p.is_absolute():
            resolved = p.resolve()
            if resolved == proot or not resolved.is_relative_to(proot):
                raise ValueError(f"source_write escapes or equals project_root: {raw}")
            if resolved == sdlc_root or resolved.is_relative_to(sdlc_root):
                raise ValueError(f"source_write cannot target .sdlc metadata directory: {raw}")
            rel = resolved.relative_to(proot).as_posix()
            if s.endswith("/"):
                rel = rel.rstrip("/") + "/"
            out.append(rel)
        else:
            norm = _strip_dot_slash(posix)
            if not norm or norm in (".", "/"):
                raise ValueError(f"source_write cannot be empty or project root: {raw}")
            # Reject symlinks inside the declared path that point outside project_root
            cand = proot / norm.rstrip("/")
            resolved = cand.resolve()
            if resolved == proot or not resolved.is_relative_to(proot):
                raise ValueError(f"source_write escapes or equals project_root: {raw}")
            if resolved == sdlc_root or resolved.is_relative_to(sdlc_root):
                raise ValueError(f"source_write cannot target .sdlc metadata directory: {raw}")
            if s.endswith("/"):
                norm = norm.rstrip("/") + "/"
            out.append(norm)
    return out


def _light_workspace_snapshot(
    project_root: Path,
    feature_root: Path,
    limit: int = DEFAULT_LIGHT_SNAPSHOT_LIMIT,
) -> dict[str, Any]:
    """Capture content hashes of project_root AND feature_root with explicit limit & timing telemetry.

    On repositories exceeding `limit` files, returns status='unprovable_limit_exceeded' instead of
    crashing silently or falsifying a green audit; finish_light always fails closed as 'unknown'.
    """
    proot = project_root.resolve()
    froot = feature_root.resolve()
    roots = [proot]
    if froot != proot:
        roots.append(froot)
    excludes = [
        froot / "runs",
        froot / "packets",
        proot / ".sdlc" / "_runtime",
        proot / ".sdlc" / "_outcomes",
    ]
    t0 = time.monotonic()
    try:
        snap = snapshot(roots, exclude=excludes, limit=limit)
    except ProtocolError as exc:
        elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
        return {
            "status": "unprovable_limit_exceeded",
            "reason": str(exc),
            "limit": limit,
            "elapsed_ms": elapsed_ms,
            "files": None,
            "files_hashed": None,
            "gaps": [str(exc)],
            "roots": [str(r) for r in roots],
        }
    elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
    snap["status"] = "ok"
    snap["limit"] = limit
    snap["elapsed_ms"] = elapsed_ms
    snap["files_hashed"] = len(snap["files"])
    return snap


def _active_overlapping_light_runs(
    runs_dir: Path,
    project_root: Path,
    exclude_run_id: str | None = None,
    since_created_at: str | None = None,
) -> list[str]:
    """Return IDs of other light runs targeting the same project_root that overlapped this run's window.

    Checks both `<feature_root>/runs` and any `<project_root>/.sdlc/*/runs` so cross-feature overlap
    and runs that started & finished strictly inside our lifespan (`finished_at > since_created_at`)
    are both detected.
    """
    target = str(project_root.resolve())
    search_dirs: list[Path] = []
    if runs_dir.is_dir():
        search_dirs.append(runs_dir.resolve())
    sdlc_root = project_root.resolve() / ".sdlc"
    if sdlc_root.is_dir():
        for cand in sorted(sdlc_root.glob("*/runs")):
            if cand.is_dir():
                rc = cand.resolve()
                if rc not in search_dirs:
                    search_dirs.append(rc)

    overlaps: set[str] = set()
    for sdir in search_dirs:
        for mp in sorted(sdir.glob("light-*-manifest.json")):
            try:
                m = json.loads(mp.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            rid = m.get("run_id")
            if not rid or rid == exclude_run_id:
                continue
            if m.get("project_root") != target:
                continue
            res_file = sdir / f"light-{rid}-result.json"
            if not res_file.is_file():
                overlaps.add(str(rid))
            elif since_created_at:
                try:
                    res = json.loads(res_file.read_text(encoding="utf-8"))
                    fin_at = str(res.get("finished_at") or "")
                    if fin_at and fin_at > since_created_at:
                        overlaps.add(str(rid))
                except (OSError, ValueError):
                    overlaps.add(str(rid))
    return sorted(overlaps)


def _path_is_authorized(
    changed_abs: str,
    project_root: Path,
    feature_root: Path,
    deliverable_paths: list[str],
    memory_file: str,
    source_writes: list[str],
) -> tuple[bool, str]:
    """Determine if an absolute changed path falls strictly inside manifest-bound write permissions."""
    p = Path(changed_abs).resolve()
    froot = feature_root.resolve()
    proot = project_root.resolve()

    # 1. Exact declared deliverable_paths under feature_root
    for rel in deliverable_paths:
        target = (froot / rel).resolve()
        if p == target or (rel.endswith("/") and p.is_relative_to(target)):
            return True, "deliverable"

    # 2. Exact bound memory_file (if non-empty)
    if memory_file:
        mem = Path(memory_file).resolve()
        if p == mem:
            return True, "memory_file"

    # 3. Declared source_writes under project_root (never allowing .sdlc/ bypass)
    sdlc_dir = (proot / ".sdlc").resolve()
    if p.is_relative_to(sdlc_dir):
        return False, "unauthorized_sdlc_write"

    for entry in source_writes:
        is_dir = entry.endswith("/")
        target = (proot / entry.rstrip("/")).resolve()
        if p == target or (is_dir and p.is_relative_to(target)) or (target.is_dir() and p.is_relative_to(target)):
            return True, "source_write"

    return False, "outside_authorized_write_scope"


def dispatch_light(
    role: str,
    stage: str,
    task: str,
    feature_root: str | Path,
    project_root: str | Path,
    intent_quote: str,
    product_root: str | Path | None = None,
    lane: str = "L2",
    inputs: list[str] | None = None,
    source_writes: list[str] | None = None,
    deliverables: list[str] | None = None,
    explore_roots: list[str] | None = None,
    assignment: str = "",
    snapshot_limit: int = DEFAULT_LIGHT_SNAPSHOT_LIMIT,
) -> dict[str, Any]:
    reg = load_registry()
    contract = resolve_task(reg, role, stage, task)
    if contract.get("protocol_required"):
        raise ValueError(
            f"{role}/{stage}/{task} requires strict protocol (protocol_required=1); use --mode strict"
        )
    combined_intent = f"{intent_quote}\n{assignment}"
    risk_hits = [code for code, _desc, pat in HIGH_RISK_RULES if pat.search(combined_intent)]
    if risk_hits:
        raise ValueError(
            f"high-risk trigger(s) {risk_hits} detected in intent/assignment; "
            "cannot downgrade to --mode light (use --mode strict)"
        )
    froot = Path(feature_root).resolve()
    proot = Path(project_root).resolve()
    if not proot.is_dir():
        raise ValueError(f"project_root does not exist: {project_root}")

    sw = _normalize_source_writes(proot, [s for s in (source_writes or []) if s])
    if sw and not contract.get("writes_source"):
        raise ValueError(f"{role}/{stage}/{task} is read-only (writes_source=false); source_writes not allowed: {sw}")
    if contract.get("requires_source") and not sw:
        raise ValueError(f"{role}/{stage}/{task} requires explicit --source-write paths")

    prod_root = Path(product_root).resolve() if product_root else (proot / "docs/product")
    delivs = _resolve_output_paths(reg, contract, deliverables, froot)
    check_cmd = _render_check_cmd(reg, contract, froot)
    evidence = contract.get("evidence", [])
    is_fresh = bool(reg["roles"][role].get("fresh"))
    mem_file = "" if is_fresh else str(froot / "memory" / f"{role}.md")
    in_lines = [f"  - {{path: {Path(p).resolve()}, required: true}}" for p in (inputs or [])]
    for rd in contract.get("reads", []):
        in_lines.append(f"  - {{path: {ROOT / rd}, required: true}}")
    exp_lines = [f"  - {Path(p).resolve()}" for p in (explore_roots or [proot])]
    deliv_lines = [f"  - {d}" for d in delivs]
    sw_block = "source_writes: []" if not sw else "source_writes:\n" + "\n".join(f"  - {s}" for s in sw)
    ev_block = "evidence_required: []" if not evidence else "evidence_required:\n" + "\n".join(f"  - {e}" for e in evidence)
    quote_clean = intent_quote.replace('"', "'").replace("\n", " ").strip()[:200]
    lane_file = contract.get("lane_file") or "none"

    lines = [
        "## SPAWN PACKET v2",
        f"hat: {role}",
        f"stage: {stage}",
        f"task: {task}",
        f"subagent_type: sdlc-workflow:{role}",
        f'intent_quote: "{quote_clean}"',
        f"lane: {lane}",
        f"feature_dir: {froot}",
        f"PLUGIN_ROOT: {ROOT}",
        "constitution: none",
        f"product_root: {prod_root}",
        f"project_root: {proot}",
        sw_block,
        "product_context: []",
        "product_writes: []",
        f"lane_file: {lane_file}",
        f"primary_skill: sdlc-workflow:{contract['skill']}",
        "companion_skills: []",
        "inputs:" if in_lines else "inputs: []",
        *in_lines,
        "explore_roots:",
        *exp_lines,
        "deliverable_paths:",
        *deliv_lines,
        ev_block,
        "visuals: []",
        "imagery: []",
        "forbidden:",
        "  - Do not spawn further subagents (host depth 1).",
        "  - Do not Write outside deliverable_paths, product_writes, source_writes and memory_file.",
        "  - Do not read <feature>/memory/*.md unless it is your own memory_file.",
        f"memory_file: {mem_file}",
        "debug_protocol: ",
        "success_checks:",
        "  - each deliverable_paths exists on disk",
        f"  - {check_cmd}",
        "return: output paths + summary + decisions + open_questions + product-delta + verified lessons",
    ]
    if assignment:
        lines.extend(["", "## Assignment", assignment.strip()])
    packet_text = "\n".join(lines) + "\n"

    froot.mkdir(parents=True, exist_ok=True)
    lint_res = lint_v2_packet(packet_text)
    if lint_res["errors"]:
        msgs = "; ".join(f"{e['code']}: {e['message']}" for e in lint_res["errors"])
        raise ValueError(f"generated v2 packet failed check_packet: {msgs}")

    packets_dir = froot / "packets"
    runs_dir = froot / "runs"
    packets_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    ts = dt.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d-%H%M%S")
    uid = uuid.uuid4().hex[:6]
    run_id = f"{ts}-{stage}-{role}-{uid}"
    safe_task = task.replace("/", "-")
    pkt_path = packets_dir / f"{ts}-{stage}-{role}-{safe_task}-{uid}.md"
    pkt_path.write_text(packet_text, encoding="utf-8")
    pkt_sha = file_hash(pkt_path)

    overlapping = _active_overlapping_light_runs(runs_dir, proot)
    baseline = _light_workspace_snapshot(proot, froot, limit=snapshot_limit)
    write_audit_capable = baseline.get("status") == "ok" and not baseline.get("gaps")

    manifest_path = runs_dir / f"light-{run_id}-manifest.json"
    manifest_core = {
        "schema_version": 1,
        "kind": "light-run-manifest",
        "mode": "light",
        "run_id": run_id,
        "created_at": dt.datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="microseconds"),
        "role": role,
        "stage": stage,
        "task": task,
        "skill": contract["skill"],
        "protocol_required": bool(contract.get("protocol_required")),
        "writes_source": bool(contract.get("writes_source")),
        "requires_source": bool(contract.get("requires_source")),
        "feature_root": str(froot),
        "project_root": str(proot),
        "product_root": str(prod_root),
        "packet": str(pkt_path),
        "packet_sha256": pkt_sha,
        "deliverable_paths": delivs,
        "source_writes": sw,
        "memory_file": mem_file,
        "snapshot_limit": snapshot_limit,
        "write_audit_capable": write_audit_capable,
        "concurrent_at_dispatch": overlapping,
        "baseline_snapshot": baseline,
    }
    manifest_core["manifest_sha256"] = digest(manifest_core)
    write_json(manifest_path, manifest_core)

    warnings = list(lint_res["warnings"])
    if not write_audit_capable:
        warnings.append({
            "code": "LIGHT-SNAPSHOT-UNPROVABLE",
            "message": (
                f"Workspace baseline snapshot could not be completed ({baseline.get('status')}: "
                f"{baseline.get('reason') or baseline.get('gaps')}); finish --mode light will fail closed "
                "with write_audit_status='unknown'. For large repositories (>20000 files), use --mode strict "
                "or an isolated worktree."
            ),
        })

    snippet = (
        f"Read the validated SPAWN PACKET v2 file below (verify sha256 first) and execute it in full:\n"
        f"- packet: {pkt_path} (sha256: {pkt_sha})\n"
        f"- light_manifest: {manifest_path}"
    )
    return {
        "mode": "light",
        "run_id": run_id,
        "manifest": str(manifest_path),
        "packet": str(pkt_path),
        "packet_sha256": pkt_sha,
        "dispatch_snippet": snippet,
        "role": role,
        "stage": stage,
        "task": task,
        "skill": contract["skill"],
        "read_only": not bool(contract.get("writes_source")),
        "source_writes": sw,
        "deliverables": delivs,
        "write_audit_capable": write_audit_capable,
        "snapshot_stats": {
            "status": baseline.get("status"),
            "files_hashed": baseline.get("files_hashed"),
            "elapsed_ms": baseline.get("elapsed_ms"),
            "limit": snapshot_limit,
        },
        "concurrent_at_dispatch": overlapping,
        "baseline_gaps": baseline.get("gaps", []),
        "warnings": warnings,
    }


def dispatch_strict(
    role: str,
    stage: str,
    task: str,
    feature_root: str | Path,
    bindings_path: str | Path,
    draft_out: str | Path,
    scope: str = "feature",
) -> dict[str, Any]:
    req = {"role": role, "stage": stage, "task": task, "scope": scope, "root": str(Path(feature_root).resolve())}
    prep = prepare(req, load(bindings_path), str(draft_out), offline=False)
    if prep["missing"]:
        return {
            "mode": "strict",
            "ready": False,
            "draft": str(Path(draft_out).resolve()),
            "missing": prep["missing"],
        }
    paths = seal(str(draft_out))
    v3_lint = lint_packet_v3(Path(paths["packet"]).read_text(encoding="utf-8"))
    if v3_lint["errors"]:
        raise ValueError("sealed v3 packet failed lint: " + "; ".join(e["message"] for e in v3_lint["errors"]))
    view = seal_dispatch_view(paths)
    return {"mode": "strict", "ready": True, "packet_valid": True, **view}


def finish_light(run_manifest: str | Path) -> dict[str, Any]:
    """Verify a light run strictly against its sealed dispatch manifest and baseline content snapshot."""
    mpath = Path(run_manifest).resolve()
    if not mpath.is_file():
        return {
            "mode": "light",
            "ok": False,
            "write_audit_status": "unknown",
            "errors": [{"level": "error", "code": "MANIFEST-MISSING", "message": f"light manifest not found: {mpath}"}],
            "warnings": [],
        }
    try:
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "mode": "light",
            "ok": False,
            "write_audit_status": "unknown",
            "errors": [{"level": "error", "code": "MANIFEST-INVALID", "message": f"unreadable manifest: {exc}"}],
            "warnings": [],
        }

    # Refuse strict manifests or tampered manifests
    if manifest.get("kind") != "light-run-manifest" or manifest.get("mode") != "light":
        return {
            "mode": "light",
            "ok": False,
            "write_audit_status": "failed",
            "errors": [{
                "level": "error",
                "code": "MODE-MISMATCH",
                "message": "refusing to close a non-light / strict run via finish --mode light; use --mode strict",
            }],
            "warnings": [],
        }

    recorded_sha = manifest.get("manifest_sha256")
    verify_copy = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    if not recorded_sha or digest(verify_copy) != recorded_sha:
        return {
            "mode": "light",
            "ok": False,
            "write_audit_status": "unknown",
            "errors": [{
                "level": "error",
                "code": "MANIFEST-TAMPERED",
                "message": "light manifest integrity check failed (manifest_sha256 mismatch); cannot prove write boundaries",
            }],
            "warnings": [],
        }

    reg = load_registry()
    role = manifest["role"]
    stage = manifest["stage"]
    task = manifest["task"]
    contract = resolve_task(reg, role, stage, task)
    if contract.get("protocol_required"):
        return {
            "mode": "light",
            "ok": False,
            "write_audit_status": "failed",
            "errors": [{
                "level": "error",
                "code": "STRICT-BYPASS",
                "message": f"{role}/{stage}/{task} requires strict protocol (protocol_required=1); cannot close via finish --mode light",
            }],
            "warnings": [],
        }

    froot = Path(manifest["feature_root"]).resolve()
    proot = Path(manifest["project_root"]).resolve()
    prod_root = Path(manifest["product_root"]).resolve()
    if not proot.is_dir():
        return {
            "mode": "light",
            "ok": False,
            "write_audit_status": "unknown",
            "errors": [{"level": "error", "code": "PROJECT-ROOT-MISSING", "message": f"bound project_root missing: {proot}"}],
            "warnings": [],
        }

    pkt_path = Path(manifest["packet"])
    if not pkt_path.is_file() or file_hash(pkt_path) != manifest.get("packet_sha256"):
        return {
            "mode": "light",
            "ok": False,
            "write_audit_status": "unknown",
            "errors": [{"level": "error", "code": "PACKET-DRIFT", "message": "bound packet missing or altered after dispatch"}],
            "warnings": [],
        }

    # Re-validate manifest deliverables against task contract and feature_root
    try:
        validated_delivs = _validate_deliverables(reg, contract, manifest.get("deliverable_paths", []), froot)
    except ValueError as exc:
        return {
            "mode": "light",
            "ok": False,
            "write_audit_status": "failed",
            "errors": [{
                "level": "error",
                "code": "DELIVERABLE-OUT-OF-CONTRACT",
                "message": str(exc),
            }],
            "warnings": [],
        }

    rows = check_task(reg, str(froot), role, stage, task, str(prod_root))
    errors = [{"level": r[0], "code": r[1], "message": r[2]} for r in rows if r[0] == "error"]
    warnings = [{"level": r[0], "code": r[1], "message": r[2]} for r in rows if r[0] != "error"]

    runs_dir = froot / "runs"
    snap_limit = int(manifest.get("snapshot_limit") or DEFAULT_LIGHT_SNAPSHOT_LIMIT)
    baseline = manifest.get("baseline_snapshot")
    if (
        not isinstance(baseline, dict)
        or baseline.get("status", "ok") != "ok"
        or not isinstance(baseline.get("files"), dict)
    ):
        reason = (baseline or {}).get("reason") or (baseline or {}).get("status") or "baseline_snapshot missing"
        result_doc = {
            "schema_version": 1,
            "kind": "light-run-result",
            "mode": "light",
            "run_id": manifest["run_id"],
            "manifest": str(mpath),
            "finished_at": dt.datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="microseconds"),
            "ok": False,
            "write_audit_status": "unknown",
            "missing_audit_reason": str(reason),
            "changed_files": [],
            "authorized_changes": [],
            "unauthorized_changes": [],
            "outside_source_writes": [],
            "snapshot_stats": {
                "baseline_status": (baseline or {}).get("status"),
                "limit": snap_limit,
            },
            "errors": errors + [{
                "level": "error",
                "code": "WRITE-AUDIT-UNPROVABLE",
                "message": f"baseline snapshot unavailable ({reason}); write audit cannot be proven",
            }],
            "warnings": warnings,
        }
        res_path = runs_dir / f"light-{manifest['run_id']}-result.json"
        write_json(res_path, result_doc)
        result_doc["result_file"] = str(res_path)
        return result_doc

    after = _light_workspace_snapshot(proot, froot, limit=snap_limit)
    if after.get("status") != "ok" or not isinstance(after.get("files"), dict):
        reason = after.get("reason") or after.get("status") or "post-run snapshot failed"
        result_doc = {
            "schema_version": 1,
            "kind": "light-run-result",
            "mode": "light",
            "run_id": manifest["run_id"],
            "manifest": str(mpath),
            "finished_at": dt.datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="microseconds"),
            "ok": False,
            "write_audit_status": "unknown",
            "missing_audit_reason": str(reason),
            "changed_files": [],
            "authorized_changes": [],
            "unauthorized_changes": [],
            "outside_source_writes": [],
            "snapshot_stats": {
                "baseline_status": baseline.get("status"),
                "baseline_ms": baseline.get("elapsed_ms"),
                "after_status": after.get("status"),
                "after_ms": after.get("elapsed_ms"),
                "limit": snap_limit,
            },
            "errors": errors + [{
                "level": "error",
                "code": "WRITE-AUDIT-UNPROVABLE",
                "message": f"post-run snapshot unavailable ({reason}); write audit cannot be proven",
            }],
            "warnings": warnings,
        }
        res_path = runs_dir / f"light-{manifest['run_id']}-result.json"
        write_json(res_path, result_doc)
        result_doc["result_file"] = str(res_path)
        return result_doc

    gaps = list(baseline.get("gaps", [])) + list(after.get("gaps", []))
    overlapping = sorted(
        set(manifest.get("concurrent_at_dispatch", []))
        | set(
            _active_overlapping_light_runs(
                runs_dir,
                proot,
                exclude_run_id=manifest["run_id"],
                since_created_at=str(manifest.get("created_at") or ""),
            )
        )
    )

    changed_paths = snapshot_changes(baseline, after)

    authorized: list[dict[str, str]] = []
    unauthorized: list[dict[str, str]] = []
    for abs_path in changed_paths:
        ok_w, reason = _path_is_authorized(
            abs_path,
            proot,
            froot,
            validated_delivs,
            manifest.get("memory_file", ""),
            manifest.get("source_writes", []),
        )
        entry = {"path": abs_path, "reason": reason}
        if ok_w:
            authorized.append(entry)
        else:
            unauthorized.append(entry)

    write_audit_status = "verified"
    if gaps:
        write_audit_status = "unknown"
        errors.append({
            "level": "error",
            "code": "WRITE-AUDIT-GAPS",
            "message": f"workspace snapshot had coverage gaps; write audit unprovable: {gaps[:5]}",
        })
    elif overlapping:
        write_audit_status = "unknown_concurrent"
        errors.append({
            "level": "error",
            "code": "CONCURRENT-LIGHT-RUN",
            "message": f"overlapping active light run(s) on same project_root ({overlapping}); cannot attribute writes safely (use isolated worktree / strict continuous)",
        })
    elif unauthorized:
        write_audit_status = "failed"
        errors.append({
            "level": "error",
            "code": "UNAUTHORIZED-WRITES",
            "message": f"detected {len(unauthorized)} write(s) outside manifest scope",
        })

    ok = (write_audit_status == "verified") and not errors
    result_doc = {
        "schema_version": 1,
        "kind": "light-run-result",
        "mode": "light",
        "run_id": manifest["run_id"],
        "manifest": str(mpath),
        "finished_at": dt.datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="microseconds"),
        "ok": ok,
        "write_audit_status": write_audit_status,
        "changed_files": changed_paths,
        "authorized_changes": authorized,
        "unauthorized_changes": unauthorized,
        "outside_source_writes": [u["path"] for u in unauthorized],
        "concurrent_runs": overlapping,
        "snapshot_gaps": gaps,
        "snapshot_stats": {
            "baseline_files_hashed": baseline.get("files_hashed"),
            "baseline_ms": baseline.get("elapsed_ms"),
            "after_files_hashed": after.get("files_hashed"),
            "after_ms": after.get("elapsed_ms"),
            "limit": snap_limit,
        },
        "errors": errors,
        "warnings": warnings,
    }
    res_path = runs_dir / f"light-{manifest['run_id']}-result.json"
    write_json(res_path, result_doc)
    result_doc["result_file"] = str(res_path)
    return result_doc


def finish_strict(
    run_manifest: str | Path,
    return_path: str | Path | None = None,
    interrupted: str | None = None,
    concurrent: bool = False,
    feature_root: str | Path | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    rec = record(str(run_manifest), str(return_path) if return_path else None, interrupted, concurrent)
    task_check = None
    if feature_root:
        task_check = check_tasks(str(Path(feature_root).resolve()), task_id=task_id)
    ok = bool(rec.get("execution_complete")) and not (task_check and task_check.get("errors"))
    return {
        "mode": "strict",
        "ok": ok,
        "record": rec,
        "task_check": task_check,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unified light/strict dispatch and finish wrappers.")
    sub = parser.add_subparsers(dest="command", required=True)

    pd = sub.add_parser("dispatch")
    pd.add_argument("--mode", choices=("light", "strict"), required=True)
    pd.add_argument("--role", required=True)
    pd.add_argument("--stage", required=True)
    pd.add_argument("--task", required=True)
    pd.add_argument("--feature-root", required=True)
    pd.add_argument("--project-root")
    pd.add_argument("--product-root")
    pd.add_argument("--intent-quote", default="")
    pd.add_argument("--lane", default="L2")
    pd.add_argument("--input", action="append", dest="inputs", default=[])
    pd.add_argument("--source-write", action="append", dest="source_writes", default=[])
    pd.add_argument("--deliverable", action="append", dest="deliverables", default=[])
    pd.add_argument("--explore-root", action="append", dest="explore_roots", default=[])
    pd.add_argument("--assignment", default="")
    pd.add_argument("--snapshot-limit", type=int, default=DEFAULT_LIGHT_SNAPSHOT_LIMIT)
    pd.add_argument("--bindings")
    pd.add_argument("--draft-out")
    pd.add_argument("--scope", default="feature")

    pf = sub.add_parser("finish")
    pf.add_argument("--mode", choices=("light", "strict"), required=True)
    pf.add_argument("--run")
    pf.add_argument("--role")
    pf.add_argument("--stage")
    pf.add_argument("--task")
    pf.add_argument("--feature-root")
    pf.add_argument("--product-root")
    pf.add_argument("--project-root")
    pf.add_argument("--source-write", action="append", dest="source_writes", default=[])
    pf.add_argument("--return", dest="return_path")
    pf.add_argument("--interrupted")
    pf.add_argument("--concurrent", action="store_true")
    pf.add_argument("--task-id")

    args = parser.parse_args(argv)
    try:
        if args.command == "dispatch":
            if args.mode == "light":
                if not args.project_root or not args.intent_quote:
                    raise ValueError("--mode light requires --project-root and --intent-quote")
                res = dispatch_light(
                    role=args.role, stage=args.stage, task=args.task,
                    feature_root=args.feature_root, project_root=args.project_root,
                    intent_quote=args.intent_quote, product_root=args.product_root,
                    lane=args.lane, inputs=args.inputs, source_writes=args.source_writes,
                    deliverables=args.deliverables or None,
                    explore_roots=args.explore_roots or None, assignment=args.assignment,
                    snapshot_limit=args.snapshot_limit,
                )
                print(json.dumps(res, ensure_ascii=False, indent=2))
                return 0
            else:
                if not args.bindings or not args.draft_out:
                    raise ValueError("--mode strict requires --bindings and --draft-out")
                res = dispatch_strict(
                    role=args.role, stage=args.stage, task=args.task,
                    feature_root=args.feature_root, bindings_path=args.bindings,
                    draft_out=args.draft_out, scope=args.scope,
                )
                print(json.dumps(res, ensure_ascii=False, indent=2))
                return 0 if res.get("ready") else 1
        else:
            if args.mode == "light":
                if not args.run:
                    raise ValueError(
                        "--mode light finish requires --run <light-manifest.json> from dispatch --mode light "
                        "(write boundaries and baseline snapshot must come from the sealed manifest, not caller flags)"
                    )
                if args.source_writes or args.project_root:
                    raise ValueError(
                        "finish --mode light forbids overriding --source-write or --project-root; "
                        "pass only --run <light-manifest.json>"
                    )
                res = finish_light(run_manifest=args.run)
            else:
                if not args.run:
                    raise ValueError("--mode strict finish requires --run")
                res = finish_strict(
                    run_manifest=args.run, return_path=args.return_path,
                    interrupted=args.interrupted, concurrent=args.concurrent,
                    feature_root=args.feature_root, task_id=args.task_id,
                )
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return 0 if res.get("ok") else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"workflow {args.command}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
