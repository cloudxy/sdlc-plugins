#!/usr/bin/env python3
"""Read-only workflow contracts. registry.json owns mappings; this module owns validation.

Task checks validate an individual return, never advance state or approve a stage.
Stage checks provide path presence to check-sdlc.sh, which owns semantic checks.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Evidence a task must produce; a packet may add to these, never drop them (check_packet EVIDENCE).
EVIDENCE_KINDS = {"web", "screenshots", "running_app", "e2e"}


# schema 2 adds run scopes (cycle) with their own roots and write rules. A runner that only knows schema 1 must
# refuse such a registry instead of treating a cycle task as a feature task.
SUPPORTED_SCHEMAS = {1, 2, 3}
ROOT_PLACEHOLDER = {"feature": "<feature_dir>", "product": "<product_root>", "cycle": "<cycle_dir>"}
ROOT_FIELD = {"feature": "feature_dir", "product": "product_root", "cycle": "cycle_dir"}


def load_registry(root=ROOT):
    from runtime_protocol import load, capabilities
    data = load(Path(root) / "workflow/registry.json")
    if type(data.get("schema_version")) is not int or data.get("schema_version") not in SUPPORTED_SCHEMAS:
        raise ValueError(f"unsupported workflow schema_version {data.get('schema_version')!r} (this runner supports {sorted(SUPPORTED_SCHEMAS)})")
    capabilities(data.get('required_capabilities', []))
    return data


def load_adapter(root=ROOT):
    return json.loads((Path(root) / "adapters/zcode.json").read_text())


def resolve_task(registry, role, stage, task):
    matches = [t for t in registry["tasks"] if t["role"] == role and t["stage"] == stage
               and (task == t["task"] or task in t.get("aliases", [])
                    or (t.get("task_pattern") and re.fullmatch(t["task_pattern"], task)))]
    if len(matches) != 1:
        raise ValueError(f"unregistered or ambiguous task: {role}/{stage}/{task}")
    return matches[0]


SKILL_KINDS = {"manager", "role", "practice", "compat"}
SKILL_TRIGGERS = {"packet", "command", "domain"}


def task_scope(task):
    """The run scope a task executes in: feature, product (or cycle). Old tasks without the field keep the
    stage-derived meaning, so an old registry or packet never changes behaviour silently."""
    scopes = task.get("scopes") or (["product"] if task["stage"] == "product" else ["feature"])
    return scopes[0]


def root_placeholder(task):
    return ROOT_PLACEHOLDER[task_scope(task)]


def _validate_model(registry, root, errors):
    """Batch-B metadata: role functions, task scopes and lifecycle phases, and the skills table."""
    functions = registry.get("functions", {})
    scopes = set(registry.get("scopes", []))
    lifecycle = set(registry.get("lifecycle", []))
    for role, item in registry["roles"].items():
        if item.get("function") not in functions:
            errors.append(f"{role}: function {item.get('function')!r} is not in registry.functions")
    for t in registry["tasks"]:
        key = (t["role"], t["stage"], t["task"])
        ts = t.get("scopes")
        if not ts or any(s not in scopes for s in ts):
            errors.append(f"{key}: scopes {ts!r} must be a non-empty subset of {sorted(scopes)}")
        elif (t["stage"] == "product") != (ts == ["product"]):
            errors.append(f"{key}: stage product and scope product go together")
        elif (t["stage"] == "cycle") != (ts == ["cycle"]):
            errors.append(f"{key}: stage cycle and scope cycle go together")
        store = t.get("store_writes")
        if store is not None:
            meta = registry.get("stores", {}).get(store)
            if meta is None:
                errors.append(f"{key}: store_writes names unknown store {store!r}")
            elif meta.get("owner") != t["role"]:
                errors.append(f"{key}: only the store owner {meta.get('owner')} may write store {store}")
        if any(ph not in lifecycle for ph in t.get("lifecycle_phases", [])):
            errors.append(f"{key}: unknown lifecycle phase in {t.get('lifecycle_phases')}")
    skills = registry.get("skills", {})
    on_disk = {p.parent.name for p in (root / "skills").glob("*/SKILL.md")}
    for name in sorted(on_disk - set(skills)):
        errors.append(f"skills/{name}: missing from registry.skills (kind and trigger)")
    for name in sorted(set(skills) - on_disk):
        errors.append(f"registry.skills.{name}: no skills/{name}/SKILL.md")
    for name, meta in skills.items():
        if meta.get("kind") not in SKILL_KINDS or meta.get("trigger") not in SKILL_TRIGGERS:
            errors.append(f"registry.skills.{name}: kind must be one of {sorted(SKILL_KINDS)}, trigger one of {sorted(SKILL_TRIGGERS)}")
        if meta.get("kind") == "compat":
            if meta.get("replaced_by") not in skills or skills[meta["replaced_by"]].get("kind") == "compat":
                errors.append(f"registry.skills.{name}: a compat entry names a live replacement skill")
            if meta.get("method") and not (root / meta["method"]).is_file():
                errors.append(f"registry.skills.{name}: method {meta['method']} does not exist")
            sunset = meta.get("sunset")
            if sunset is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(sunset)):
                errors.append(f"registry.skills.{name}: sunset must be null or YYYY-MM-DD")
    for t in registry["tasks"]:
        for used in [t["skill"]] + t.get("companions", []):
            if skills.get(used, {}).get("kind") in ("manager", "compat"):
                errors.append(f"{(t['role'], t['stage'], t['task'])}: {used} is a {skills[used]['kind']} skill, not a task method")
    for role, item in registry["roles"].items():
        if skills.get(item["skill"], {}).get("kind") != "role":
            errors.append(f"{role}: default skill {item['skill']} must be kind role")


def validate_registry(registry, root=ROOT):
    from runtime_protocol import input_contract_errors
    errors = input_contract_errors(registry)
    root = Path(root)
    _validate_model(registry, root, errors)
    for role, item in registry["roles"].items():
        if not (root / "skills" / item["skill"] / "SKILL.md").is_file():
            errors.append(f"{role}: missing skill {item['skill']}")
        for name in ("IDENTITY.md", "SOUL.md"):
            if not (root / "agents/profiles" / role / name).is_file():
                errors.append(f"{role}: missing {name}")
        if item["fresh"] and item["product_writes"]:
            errors.append(f"{role}: fresh reviewer cannot own product writes")
    keys = set()
    for t in registry["tasks"]:
        key = (t["role"], t["stage"], t["task"])
        if key in keys:
            errors.append(f"duplicate task {key}")
        keys.add(key)
        if "writes_source" in t and not isinstance(t["writes_source"], bool):
            errors.append(f"{key}: writes_source must be a boolean")
        if "requires_source" in t and not isinstance(t["requires_source"], bool):
            errors.append(f"{key}: requires_source must be a boolean")
        if t.get("requires_source") and not t.get("writes_source"):
            errors.append(f"{key}: requires_source needs writes_source")
        if t.get("writes_source") and registry["roles"].get(t["role"], {}).get("fresh"):
            errors.append(f"{key}: fresh reviewer cannot write source")
        if "partial_stage" in t and not isinstance(t["partial_stage"], bool):
            errors.append(f"{key}: partial_stage must be a boolean")
        if t["role"] not in registry["roles"] or t["stage"] not in registry["stages"]:
            errors.append(f"unknown role/stage {key}")
        if not (root / "skills" / t["skill"] / "SKILL.md").is_file():
            errors.append(f"{key}: missing primary skill")
        for art in t["required"]:
            if art not in registry["artifacts"]:
                errors.append(f"{key}: unknown artifact {art}")
        for v in t.get("visuals", []):
            if v.get("type") not in registry.get("diagram", {}).get("types", []) or v.get("when") not in registry.get("diagram", {}).get("when", {}):
                errors.append(f"{key}: unknown visual {v}")
        if t.get("visuals") and not (root / t.get("diagram_reference", "")).is_file():
            errors.append(f"{key}: diagram_reference {t.get('diagram_reference')} missing")
        for im in t.get("imagery", []):
            if im.get("kind") not in registry.get("imagery", {}).get("kinds", []) or im.get("when") not in registry.get("imagery", {}).get("when", {}):
                errors.append(f"{key}: unknown imagery {im}")
        if t.get("imagery") and not (root / t.get("imagery_reference", "")).is_file():
            errors.append(f"{key}: imagery_reference {t.get('imagery_reference')} missing")
        for rd in t.get("reads", []):
            # vendor files may not be installed yet (bash vendor/install.sh); a lock that lists them is enough
            if not (root / rd).is_file() and not _vendor_lists(root, rd):
                errors.append(f"{key}: reads {rd} is neither in the plugin nor listed in a vendor lock")
        for ev in t.get("evidence", []):
            kind = ev.get("kind") if isinstance(ev, dict) else ev
            if kind not in EVIDENCE_KINDS:
                errors.append(f"{key}: unknown evidence kind {kind}")
        for companion in t.get("companions", []):
            if not (root / "skills" / companion / "SKILL.md").is_file():
                errors.append(f"{key}: unknown companion {companion}")
        for pattern in t.get("evidence_paths", []):
            # Evidence paths are relative to the task root; they never name a canonical product file.
            if Path(pattern).is_absolute() or ".." in Path(pattern).parts or not pattern:
                errors.append(f"{key}: evidence path must stay inside the task root: {pattern}")
            elif pattern in _product_files(registry):
                errors.append(f"{key}: evidence path {pattern} is an owned product file; use product_writes")
        if t.get("manager_output") and (Path(t["manager_output"]).is_absolute() or ".." in Path(t["manager_output"]).parts):
            errors.append(f"{key}: manager_output must be project-relative")
    for name, stage in registry["stages"].items():
        for group in stage["required"]:
            if not group["any"] or any(a not in registry["artifacts"] for a in group["any"]):
                errors.append(f"{name}: unknown/empty required artifacts")
            if group.get("role") and group["role"] not in registry["roles"]:
                errors.append(f"{name}: unknown skip role")
    for name, item in registry["commands"].items():
        if not (root / "skills" / item["skill"] / "SKILL.md").is_file():
            errors.append(f"{name}: missing entry skill")
    for lane, stages in registry["lanes"].items():
        if any(s not in registry["stages"] for s in stages):
            errors.append(f"{lane}: unknown stage")
    for key, item in registry["artifacts"].items():
        for p in item["paths"] + item.get("legacy", []):
            if Path(p).is_absolute() or ".." in Path(p).parts:
                errors.append(f"{key}: path must stay inside artifact root")
    return errors


def _product_files(registry):
    """Canonical product files: every file some role owns under product_root."""
    return {f for role in registry["roles"].values() for f in role["product_writes"]}


def _vendor_lists(root, rel):
    parts = Path(rel).parts
    if len(parts) < 3 or parts[0] != "vendor":
        return False
    try:
        lock = json.loads((Path(root) / "vendor" / f"{parts[1]}.lock.json").read_text())
    except (OSError, ValueError):
        return False
    return any(f.get("path") == "/".join(parts[2:]) for f in lock.get("files", []))


def artifact_paths(registry, ids, legacy=False):
    return [p for key in ids for p in registry["artifacts"][key]["legacy" if legacy else "paths"]]


UNFILLED = re.compile(r"^[ \t]*(<!--|#|//)[ \t]*sdlc:unfilled", re.M)


def deliverable(p):
    """A deliverable is a real file with content: not hidden (.gitkeep), not blank, not an unfilled template."""
    if not p.is_file() or p.name.startswith("."):
        return False
    try:
        head = p.read_bytes()[:65536]
    except OSError:
        return False
    if not head.strip():
        return False
    return not UNFILLED.search(head.decode("utf-8", errors="replace"))


def ticket_pattern(pattern, task=None, role=None):
    """Implementation evidence is per ticket AND per lane: 03-impl/T-<n>-<role>-evidence.md.
    Another ticket's evidence, or another lane's evidence for the same ticket, never satisfies a task (N02)."""
    if task and re.fullmatch(r"T-[1-9][0-9]*", task):
        return pattern.replace("*evidence*", f"{task}-{role}-*evidence*" if role else f"{task}-*evidence*")
    return pattern


def existing(root, patterns, task=None, role=None):
    for pattern in patterns:
        pattern = ticket_pattern(pattern, task, role)
        for p in Path(root).glob(pattern):
            if deliverable(p) and p.resolve().is_relative_to(Path(root).resolve()):
                return p
    return None


def check_groups(registry, root, groups, skipped=(), ui=False, task=None, legacy=True, role=None):
    results = []
    for group in groups:
        if group.get("role") in skipped or (group.get("when") == "ui" and not ui):
            continue
        paths = artifact_paths(registry, group["any"])
        if existing(root, paths, task, role):
            continue
        old = existing(root, artifact_paths(registry, group["any"], True), task) if legacy else None
        if old:
            results.append(("warning", "DEPRECATED", f"{old}: use {' or '.join(paths)}"))
        else:
            present = [p for pat in paths for p in Path(root).glob(pat) if p.is_file() and not p.name.startswith(".")]
            why = (f" ({present[0].relative_to(root)} exists but is empty or still a template with sdlc:unfilled — fill it and delete the marker line)"
                   if present else "")
            results.append(("error", "HATMISS", f"missing {' or '.join(paths)}{why}"))
    return results


def check_task(registry, root, role, stage, task, product_root=None):
    t = resolve_task(registry, role, stage, task)
    results = []
    for a in t["required"]:
        paths = artifact_paths(registry, [a])
        if existing(root, paths, task, role):
            continue
        legacy = [p for p in paths if "*evidence*" in p]
        old = existing(root, [p.replace("*evidence*", f"{task}-evidence") for p in legacy]) if legacy and re.fullmatch(r"T-[1-9][0-9]*", task) else None
        if old:
            results.append(("warning", "DEPRECATED", f"{old}: rename to {task}-{role}-evidence.md (one file per lane)"))
        else:
            results += check_groups(registry, root, [{"any": [a]}], task=task, legacy=False, role=role)
    # Product outputs live under product_root, not under the feature directory (N01).
    if t.get("product_outputs"):
        if not product_root:
            results.append(("error", "USAGE", f"{role}/{stage}/{task} writes product files: pass --product-root <product_root>"))
        else:
            for path in t["product_outputs"]:
                if not existing(product_root, [path]):
                    results.append(("error", "HATMISS", f"missing or unfilled product file {path} under {product_root}"))
    return results


CYCLE_TASK_STATES = {"todo", "doing", "done", "pending-observation", "carried", "rejected", "awaiting-authorization"}
PROPOSAL_STATES = {"accepted", "deferred", "rejected", "pending", "carried"}
SIG_ROW = re.compile(r"^\|\s*(SIG-\d{6}-\d+)\s*\|", re.M)


def find_config(start):
    """sdlc.config.yaml of the project that contains `start` (walks up a few levels)."""
    d = Path(start).resolve()
    for _ in range(8):
        if (d / "sdlc.config.yaml").is_file():
            return d / "sdlc.config.yaml"
        if d.parent == d:
            break
        d = d.parent
    return None


def check_cycle(registry, cycle_dir, today=None):
    """Closure checks for one product cycle (.sdlc/_product/cycles/<id>/cycle.yaml). Mechanical only: it proves
    the cycle's bookkeeping is complete and honest about open windows, never that an analysis is right."""
    import datetime as dt
    from check_config import parse_yaml  # lazy: check_config imports this module lazily as well
    root = Path(cycle_dir)
    results = []

    def bad(code, msg):
        results.append(("error", code, msg))

    state = root / "cycle.yaml"
    if not state.is_file():
        bad("CYCLE", f"missing {state} (start from skills/sdlc/templates/cycle.yaml)")
        return results
    text = state.read_text(encoding="utf-8")
    if UNFILLED.search(text):
        bad("CYCLE", f"{state} is still the template (sdlc:unfilled)")
        return results
    cy = parse_yaml(text)
    if str(cy.get("id") or "") != root.name:
        bad("CYCLE", f"cycle.yaml id {cy.get('id')!r} must equal the directory name {root.name!r}")
    status = cy.get("status")
    if status not in ("open", "closed"):
        bad("CYCLE", f"status {status!r} must be open or closed")

    def day(value, name):
        try:
            return dt.date.fromisoformat(str(value))
        except ValueError:
            bad("CYCLE", f"{name} must be YYYY-MM-DD, got {value!r}")
            return None

    window = cy.get("window") if isinstance(cy.get("window"), dict) else {}
    day(window.get("from"), "window.from")
    w_to = day(window.get("to"), "window.to")
    cutoff = day(cy.get("data_cutoff"), "data_cutoff")
    today = today or dt.date.today()
    tasks = cy.get("selected_tasks") if isinstance(cy.get("selected_tasks"), list) else []
    if not tasks:
        bad("CYCLE", "selected_tasks is empty — a cycle runs only the tasks it selects")
    for i, st in enumerate(tasks):
        if not isinstance(st, dict):
            bad("CYCLE", f"selected_tasks[{i}] must be a mapping")
            continue
        name, run = str(st.get("task")), st.get("status")
        label = f"selected_tasks[{i}] {st.get('role')}/{name}"
        try:
            contract = resolve_task(registry, str(st.get("role")), "cycle", name)
        except ValueError:
            bad("CYCLE", f"{label}: not a registered cycle task")
            continue
        if run not in CYCLE_TASK_STATES:
            bad("CYCLE", f"{label}: status {run!r} is not one of {', '.join(sorted(CYCLE_TASK_STATES))}")
        if run == "done":
            for art in contract["required"]:
                if not existing(root, artifact_paths(registry, [art])):
                    bad("CYCLE", f"{label}: done, but {' or '.join(artifact_paths(registry, [art]))} is missing or unfilled")
            if name == "readout" and st.get("interim") is not True and w_to:
                if w_to >= today:
                    bad("CYCLE-INTERIM", f"{label}: the observation window runs until {w_to}; before then a readout is interim "
                                         "(interim: true) or pending-observation, never a completed result")
                elif cutoff and cutoff < w_to:
                    bad("CYCLE-INTERIM", f"{label}: data_cutoff {cutoff} is before the window end {w_to}; mark the readout interim")
        if run == "carried" and not st.get("carried_to"):
            bad("CYCLE", f"{label}: carried needs carried_to (the cycle or feature that received it)")
        if status == "closed" and run in ("todo", "doing"):
            bad("CYCLE-CLOSE", f"{label}: the cycle is closed but this task is {run} — record done, pending-observation, "
                               "carried, rejected or awaiting-authorization")
    proposals = cy.get("proposals") if isinstance(cy.get("proposals"), list) else []
    for i, pr in enumerate(proposals):
        if not isinstance(pr, dict):
            continue
        ps, label = pr.get("status"), f"proposals[{i}] {pr.get('id')}"
        if ps not in PROPOSAL_STATES:
            bad("CYCLE", f"{label}: status {ps!r} is not one of {', '.join(sorted(PROPOSAL_STATES))}")
        if ps == "carried" and not pr.get("carried_to"):
            bad("CYCLE", f"{label}: carried needs carried_to")
        if ps in ("accepted", "deferred", "rejected") and not (pr.get("decided_in") and existing(root, [str(pr["decided_in"])])):
            bad("CYCLE", f"{label}: {ps} needs decided_in pointing at the filled decision record")
        if status == "closed" and ps == "pending" and not pr.get("reason"):
            bad("CYCLE-CLOSE", f"{label}: still pending at closure — say what it waits for (evidence, authorization)")
    if status == "closed" and not str(cy.get("closure") or "").strip():
        bad("CYCLE-CLOSE", "a closed cycle states where its unfinished items went (closure)")
    config = find_config(root)
    if config:
        store = parse_yaml(config.read_text(encoding="utf-8")).get("signals_path")
        if isinstance(store, str) and store.strip() and "<" not in store:
            path = config.parent / store
            files = [path] if path.is_file() else sorted(path.rglob("*.md")) if path.is_dir() else []
            seen = {}
            for f in files:
                body = f.read_text(encoding="utf-8", errors="replace")
                if UNFILLED.search(body):
                    continue
                for m in SIG_ROW.finditer(body):
                    if m.group(1) in seen:
                        where = f"in {f}" if seen[m.group(1)] == f else f"in {seen[m.group(1)]} and {f}"
                        bad("SIGDUP", f"{m.group(1)} is defined twice {where}; a signal ID is never reused")
                    seen.setdefault(m.group(1), f)
    return results


def success_check(task):
    """The one check-task command a packet must carry for this task (check_packet compares against it)."""
    cmd = (f"python3 <PLUGIN_ROOT>/scripts/workflow.py check-task --role {task['role']} --stage {task['stage']} "
           f"--task {task['task'] if not task.get('task_pattern') else '<T-n>'} "
           f"--root {root_placeholder(task)}")
    if task.get("product_outputs"):
        cmd += " --product-root <product_root>"
    return cmd


def render_commands(registry):
    for name, item in registry["commands"].items():
        yield f"commands/{name}.md", (
            "---\n" + f"description: {json.dumps(item['description'], ensure_ascii=False)}\n"
            + f"argument-hint: {json.dumps(item['argument_hint'], ensure_ascii=False)}\n"
            + f"skills: {item['skill']}\n---\n\n"
            + "<!-- GENERATED from workflow/registry.json by scripts/workflow.py render. -->\n\n"
            + f"Follow `sdlc-workflow:{item['skill']}` in **mode: {item['mode']}**. "
            + "Preserve this mode while interpreting the arguments.\n\n$ARGUMENTS\n")


def render_stage_map(registry):
    lines = ["# Stage map (generated)", "", "<!-- GENERATED by scripts/workflow.py render. Edit workflow/registry.json. -->", "",
             "Authoritative mappings: `workflow/registry.json`. Scheduling, inputs and participation: [stage-procedure.md](stage-procedure.md).",
             "", "`hat` is the role; `stage` is the gate ID; `task` selects the contract; `primary_skill` is the method.",
             "Query one contract: `python3 PLUGIN_ROOT/scripts/workflow.py contract --role designer --stage designer --task explore`.",
             "Task presence checks do not advance state. Use `check-sdlc.sh --hat <stage>` only after that stage's participating tasks finish.",
             "", "| Role | Stage | Task | Scope · lifecycle | Skill | Required artifacts |", "|---|---|---|---|---|---|"]
    for t in registry["tasks"]:
        lines.append(f"| {t['role']} | {t['stage']} | {t['task']} | {_scope_life(t)} | {t['skill']} | {'; '.join(_outputs(registry, t))} |")
    lines += ["", "## Progress and rank", "", "| Stage | Progress word | Rank |", "|---|---|---|"]
    for name, s in registry["stages"].items():
        lines.append(f"| {name} | {s['progress'] or '—'} | {s['rank']} |")
    lines += ["", "## Lane completion vocabulary", "", "These are aggregate stage requirements; skipping one role never removes an entire stage. L4 adds retro when analyst is invited. Legacy v3 omits accept.", ""]
    for lane, stages in registry["lanes"].items():
        lines.append(f"- {lane}: {', '.join(stages) or 'none'}")
    lines += ["", "## Product write ownership", "", "Packet product_writes may narrow this scope. Manager-only files: " + ", ".join(registry["manager_only"]), ""]
    for role, item in registry["roles"].items():
        if item["product_writes"]:
            lines.append(f"- {role}: {', '.join(item['product_writes'])}")
    return "\n".join(lines) + "\n"


def _outputs(registry, t):
    paths = [" / ".join(registry["artifacts"][a]["paths"]) for a in t["required"]]
    paths += ["product:" + p for p in t.get("product_outputs", [])]
    paths += ["evidence:" + p for p in t.get("evidence_paths", [])]
    if t.get("manager_output"):
        paths.append("manager: " + t["manager_output"])
    return paths


def _scope_life(t):
    phases = ", ".join(t.get("lifecycle_phases", [])) or "—"
    return f"{task_scope(t)} · {phases}"


def render_function_map(registry):
    """A view for people: which roles and tasks each function covers. Not a second source of truth."""
    lines = ["# Function map (generated)", "", "<!-- GENERATED by scripts/workflow.py render. Edit workflow/registry.json. -->", "",
             "Which roles and tasks belong to each function — a view for people, not a new source. Mappings come from "
             "`workflow/registry.json`. What a task reads, when it runs and who must decide live in "
             "[stage-procedure.md](stage-procedure.md) (scheduling and required inputs), [product-layer.md](product-layer.md) "
             "(decisions: who decides what) and the manager's human decision points (`skills/sdlc/SKILL.md` Step 4).",
             "", "`function` groups roles for display only: it grants no product writes, tool access or waiver authority, "
             "and a team may organise differently (an analyst may sit with product or with a data team).", ""]
    by_fn = {}
    for role, item in registry["roles"].items():
        by_fn.setdefault(item["function"], []).append(role)
    for fn, meta in registry["functions"].items():
        roles = by_fn.get(fn, [])
        lines += [f"## {meta['name']} (`{fn}`)", "", "Roles: " + ", ".join(f"`{r}`" for r in roles), "",
                  "| Role | Stage / task | Scope · lifecycle | Primary skill | Companions | Outputs | Source writes |",
                  "|---|---|---|---|---|---|---|"]
        for t in registry["tasks"]:
            if t["role"] not in roles:
                continue
            source = "required" if t.get("requires_source") else "optional" if t.get("writes_source") else "—"
            lines.append(f"| {t['role']} | {t['stage']} / {t['task']} | {_scope_life(t)} | {t['skill']} | "
                         f"{', '.join(t.get('companions', [])) or '—'} | {'; '.join(_outputs(registry, t)) or '—'} | {source} |")
        owned = [f"{r}: {', '.join(registry['roles'][r]['product_writes'])}" for r in roles if registry["roles"][r]["product_writes"]]
        reads = sorted({rd for t in registry["tasks"] if t["role"] in roles for rd in t.get("reads", [])})
        lines += ["", "Product files owned: " + ("; ".join(owned) if owned else "none") + ".",
                  "Required plugin reading: " + (", ".join(f"`{rd}`" for rd in reads) if reads else "none") + ".", ""]
    return "\n".join(lines)


def generated_files(registry):
    yield from render_commands(registry)
    yield "skills/sdlc/references/stage-map.md", render_stage_map(registry)
    yield "skills/sdlc/references/function-map.md", render_function_map(registry)
    rows = ['# Task inputs (generated)', '', '<!-- GENERATED by scripts/workflow.py render. Edit workflow/registry.json. -->', '',
            'Only protocol-1 pilot contracts are encoded here. Scheduling and other tasks remain in [stage-procedure.md](stage-procedure.md).', '',
            '| Role / stage / task | Input | Source | Condition | Access | Acceptance |', '|---|---|---|---|---|---|']
    for t in registry['tasks']:
        for i in t.get('inputs', []):
            rows.append(f"| {t['role']} / {t['stage']} / {t['task']} | {i['id']} | {i['source']}: {i.get('ref','explicit binding')} | {i['when']} | {i['access']} | {i.get('requires_acceptance',False)} |")
    yield 'skills/sdlc/references/task-inputs.md', '\n'.join(rows) + '\n'


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('prepare', 'seal', 'record', 'check-tasks', 'migrate-tasks', 'eval-prepare', 'eval-audit', 'eval-blind'):
        from task_runtime import main as runtime_main
        return runtime_main(sys.argv[1:])
    if len(sys.argv) > 1 and sys.argv[1] == "trace":
        # Read-only impact query; the index is rebuilt from artifacts on every run (sdlc_trace.py).
        from sdlc_trace import main as trace_main
        return trace_main(sys.argv[2:])
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sub.add_parser("stages")
    sub.add_parser("roles")
    sub.add_parser("artifact-paths")
    rank = sub.add_parser("rank"); rank.add_argument("stage")
    lane = sub.add_parser("lane"); lane.add_argument("lane"); lane.add_argument("--short", action="store_true")
    path = sub.add_parser("paths"); path.add_argument("artifact"); path.add_argument("--legacy", action="store_true")
    render = sub.add_parser("render"); render.add_argument("--check", action="store_true")
    for command in ("contract", "check-task"):
        p = sub.add_parser(command)
        for field in ("role", "stage", "task"):
            p.add_argument("--" + field, required=True)
        if command == "check-task":
            p.add_argument("--root", required=True)
            p.add_argument("--product-root")
    p = sub.add_parser("check-cycle")
    p.add_argument("--root", required=True)
    p = sub.add_parser("check-stage")
    p.add_argument("--stage", required=True); p.add_argument("--root", required=True)
    p.add_argument("--skip", action="append", default=[]); p.add_argument("--ui", action="store_true")
    args = parser.parse_args()
    try:
        r = load_registry()
        if args.command == "validate":
            errors = validate_registry(r)
            print("\n".join(errors) if errors else "workflow registry: valid")
            return int(bool(errors))
        if args.command == "render":
            errors = validate_registry(r)
            if errors:
                raise ValueError("; ".join(errors))
            drift = []
            for path, text in generated_files(r):
                p = ROOT / path
                if args.check:
                    if not p.is_file() or p.read_text() != text:
                        drift.append(path)
                else:
                    p.write_text(text)
            if drift:
                print("generated drift: " + ", ".join(drift))
            return int(bool(drift))
        if args.command == "stages":
            print(" ".join(r["stages"])); return 0
        if args.command == "roles":
            print(" ".join(r["roles"])); return 0
        if args.command == "artifact-paths":
            for key, item in r["artifacts"].items():
                if not re.fullmatch(r"[a-z][a-z0-9-]*", key):
                    raise ValueError(f"invalid artifact id: {key}")
                print(key.replace("-", "_") + "\t" + item["paths"][0])
            return 0
        if args.command == "lane":
            key = args.lane if args.lane in r["lanes"] else (f"{args.lane}-short" if args.short else f"{args.lane}-default")
            if key not in r["lanes"]:
                raise ValueError(f"unknown lane {args.lane}")
            print(" ".join(r["lanes"][key])); return 0
        if args.command == "rank":
            print(r["stages"].get(args.stage, {}).get("rank", 0)); return 0
        if args.command == "paths":
            print("\n".join(artifact_paths(r, [args.artifact], args.legacy))); return 0
        if args.command == "contract":
            task = dict(resolve_task(r, args.role, args.stage, args.task))
            task["artifacts"] = {key: r["artifacts"][key] for key in task["required"]}
            task["success_check"] = success_check(task)
            if task.get("reads"):
                task["reads"] = [f"<PLUGIN_ROOT>/{rd}" for rd in task["reads"]]  # add each to packet inputs
            if task.get("visuals"):
                d = r["diagram"]
                base = root_placeholder(task)
                task["diagram"] = {
                    "when": {v["type"]: d["when"][v["when"]] for v in task["visuals"]},
                    "enforced": [v["type"] for v in task["visuals"] if v["when"] in d["enforced_when"]],
                    "inputs": [f"<PLUGIN_ROOT>/{d['guide']}", f"<PLUGIN_ROOT>/{task['diagram_reference']}"],
                    "deliverable": f"{task['diagram_dir']}/<name>.svg",
                    "check": f"python3 <PLUGIN_ROOT>/{d['lint']} --root {base} {base}/{task['diagram_dir']}/<name>.svg",
                    "render": f"bash <PLUGIN_ROOT>/{d['render']} {base}/{task['diagram_dir']}/shots {base}/{task['diagram_dir']}/<name>.svg",
                }
            if task.get("imagery"):
                g = r["imagery"]
                base = root_placeholder(task)
                dirs = sorted({g["dirs"][im["kind"]] for im in task["imagery"]})
                task["image"] = {
                    "when": {im["kind"]: g["when"][im["when"]] for im in task["imagery"]},
                    "kinds": [im["kind"] for im in task["imagery"]],
                    "inputs": list(dict.fromkeys([f"<PLUGIN_ROOT>/{g['guide']}",
                                                  f"<PLUGIN_ROOT>/{task['imagery_reference']}"])),
                    "deliverable": [f"{d}/<name>.png" for d in dirs],
                    "generate": (f"python3 <PLUGIN_ROOT>/{g['generate']} --root {base} --kind <kind> --name <name>"
                                 " --purpose <one line> --declared-in <artifact> --prompt-file <file>"),
                    "check": f"python3 <PLUGIN_ROOT>/{g['check']} --root {base}",
                    "authorize": f"python3 <PLUGIN_ROOT>/{g['auth']} status (the human runs login, never a hat)",
                    "not_evidence": g["not_evidence"],
                }
            task.setdefault("evidence", [])
            print(json.dumps(task, ensure_ascii=False, indent=2)); return 0
        if not Path(args.root).is_dir():
            raise ValueError(f"artifact root does not exist: {args.root}")
        if args.command == "check-task":
            results = check_task(r, args.root, args.role, args.stage, args.task, args.product_root)
        elif args.command == "check-cycle":
            results = check_cycle(r, args.root)
        else:
            results = check_groups(r, args.root, r["stages"][args.stage]["required"], args.skip, args.ui)
        for result in results:
            print("\t".join(result))
        return int(any(row[0] == "error" for row in results))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"workflow: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
