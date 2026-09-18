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


def load_registry(root=ROOT):
    data = json.loads((Path(root) / "workflow/registry.json").read_text())
    if data.get("schema_version") != 1:
        raise ValueError("unsupported workflow schema_version")
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


def validate_registry(registry, root=ROOT):
    errors = []
    root = Path(root)
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
        if t["role"] not in registry["roles"] or t["stage"] not in registry["stages"]:
            errors.append(f"unknown role/stage {key}")
        if not (root / "skills" / t["skill"] / "SKILL.md").is_file():
            errors.append(f"{key}: missing primary skill")
        for art in t["required"]:
            if art not in registry["artifacts"]:
                errors.append(f"{key}: unknown artifact {art}")
        for companion in t.get("companions", []):
            if not (root / "skills" / companion / "SKILL.md").is_file():
                errors.append(f"{key}: unknown companion {companion}")
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


def existing(root, patterns, task=None):
    for pattern in patterns:
        # One ticket's evidence cannot satisfy a different ticket's task check.
        if task and re.fullmatch(r"T-[1-9][0-9]*", task):
            pattern = pattern.replace("*evidence*", task + "-*evidence*")
        for p in Path(root).glob(pattern):
            if deliverable(p) and p.resolve().is_relative_to(Path(root).resolve()):
                return p
    return None


def check_groups(registry, root, groups, skipped=(), ui=False, task=None, legacy=True):
    results = []
    for group in groups:
        if group.get("role") in skipped or (group.get("when") == "ui" and not ui):
            continue
        paths = artifact_paths(registry, group["any"])
        if existing(root, paths, task):
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


def check_task(registry, root, role, stage, task):
    t = resolve_task(registry, role, stage, task)
    results = check_groups(registry, root, [{"any": [a]} for a in t["required"]], task=task, legacy=False)
    # Product tasks use product_root. Reviewer output is persisted by the manager separately.
    for path in t.get("product_outputs", []):
        if not existing(root, [path]):
            results.append(("error", "HATMISS", f"missing product file {path}"))
    return results


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
             "", "| Role | Stage | Task | Skill | Required artifacts |", "|---|---|---|---|---|"]
    for t in registry["tasks"]:
        paths = [" / ".join(registry["artifacts"][a]["paths"]) for a in t["required"]]
        paths += ["product:" + p for p in t.get("product_outputs", [])]
        if t.get("manager_output"):
            paths.append("manager: " + t["manager_output"])
        lines.append(f"| {t['role']} | {t['stage']} | {t['task']} | {t['skill']} | {'; '.join(paths)} |")
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


def generated_files(registry):
    yield from render_commands(registry)
    yield "skills/sdlc/references/stage-map.md", render_stage_map(registry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sub.add_parser("stages")
    sub.add_parser("roles")
    sub.add_parser("artifact-paths")
    rank = sub.add_parser("rank"); rank.add_argument("stage")
    path = sub.add_parser("paths"); path.add_argument("artifact"); path.add_argument("--legacy", action="store_true")
    render = sub.add_parser("render"); render.add_argument("--check", action="store_true")
    for command in ("contract", "check-task"):
        p = sub.add_parser(command)
        for field in ("role", "stage", "task"):
            p.add_argument("--" + field, required=True)
        if command == "check-task":
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
        if args.command == "rank":
            print(r["stages"].get(args.stage, {}).get("rank", 0)); return 0
        if args.command == "paths":
            print("\n".join(artifact_paths(r, [args.artifact], args.legacy))); return 0
        if args.command == "contract":
            task = dict(resolve_task(r, args.role, args.stage, args.task))
            task["artifacts"] = {key: r["artifacts"][key] for key in task["required"]}
            print(json.dumps(task, ensure_ascii=False, indent=2)); return 0
        if not Path(args.root).is_dir():
            raise ValueError(f"artifact root does not exist: {args.root}")
        if args.command == "check-task":
            results = check_task(r, args.root, args.role, args.stage, args.task)
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
