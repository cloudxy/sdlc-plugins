#!/usr/bin/env python3
"""check_packet.py — lint a SPAWN PACKET v2 before the manager spawns a hat. Read-only.

Why it exists (2026-09-17 GLM run on a real project):
  * packets told hats "smoke run — no WebSearch/WebFetch needed", made URLs "optional", and told the designer to fall back
    to reading source code when the app was down — research and screenshots quietly disappeared;
  * a bootstrap pm packet listed whole trees as inputs (docs/, .sdlc/ with 443 files, api and pages directories) and the
    run consumed ~38.7M input tokens;
  * parallel hats appended to the same CHANGELOG, and packets passed spawn-role names where stage ids belong.

  python3 check_packet.py <packet.md> [--plugin-root DIR] [--json]
  python3 check_packet.py --self-test

Exit: 0 no errors (warnings allowed) · 1 errors (fix the packet, do not spawn) · 2 usage / no packet found.
Save packets as <feature>/packets/<nn>-<stage>-<hat>.md (features) or .sdlc/_product/packets/<n>-<hat>.md (/sdlc-product).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import fnmatch
from pathlib import Path
from typing import Any

import shlex

from workflow import load_registry, resolve_task, artifact_paths, ticket_pattern

REGISTRY = load_registry()
STAGES = set(REGISTRY["stages"])
FRESH = {name for name, role in REGISTRY["roles"].items() if role["fresh"]}
OWNERS = {name: set(role["product_writes"]) for name, role in REGISTRY["roles"].items()}
MANAGER_ONLY = set(REGISTRY["manager_only"])
REQUIRED = ("hat", "stage", "task", "subagent_type", "PLUGIN_ROOT", "primary_skill", "deliverable_paths", "success_checks", "return")
ABS_SCALARS = ("PLUGIN_ROOT", "feature_dir", "product_root", "memory_file", "debug_protocol")
WAIVERS = [
    r"不需要\s*(WebSearch|WebFetch|联网|上网|网络检索|网络搜索|搜索|截图|启动应用|E2E)",
    r"(无需|不用|不必|不要|别)\s*(联网|上网|WebSearch|WebFetch|网络检索|网络搜索|截图|启动应用|启动服务|跑\s*E2E|E2E)",
    r"(URL|网址|链接|来源|出处)[^\n]{0,16}可(以)?省略",
    r"可(以)?省略[^\n]{0,16}(URL|网址|链接|来源|出处)",
    r"源码考古",
    r"(按|走)[^\n]{0,6}源码[^\n]{0,6}(反推|代替|替代)",
    r"\b(no|skip|without|don't|do not|never)\s+(web\s*search|webfetch|web\s*fetch|browsing|browse|the\s+web|internet|screenshots?|e2e)\b",
    r"\bfall\s*back\s+to\s+(reading\s+)?(the\s+)?(source|code)",
    r"\binstead\s+of\s+(starting|running)\s+the\s+app\b",
]
CONTEXT_WARN = 200_000
CONTEXT_ERROR = 400_000
INPUTS_WARN = 25


# ----------------------------------------------------------------------------- parsing
def _strip_comment(line: str) -> str:
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


def _value(v: str) -> Any:
    v = v.strip()
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        return v[1:-1]
    if v.startswith("{") and v.endswith("}"):
        d: dict[str, Any] = {}
        for part in re.split(r",\s*(?=[A-Za-z_]+\s*:)", v[1:-1].strip()):
            if ":" in part:
                k, _, val = part.partition(":")
                d[k.strip()] = _value(val)
        return d
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [_value(x) for x in inner.split(",")] if inner else []
    if v in ("true", "false"):
        return v == "true"
    return v


def extract_packet(text: str) -> str | None:
    m = re.search(r"^##\s*SPAWN PACKET v2\s*$", text, re.M)
    if not m:
        return None
    body = text[m.end():]
    fence = re.search(r"^```", body, re.M)
    return body[:fence.start()] if fence else body


def parse_packet(block: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current: str | None = None
    for raw in block.splitlines():
        if not raw.strip():
            continue
        line = _strip_comment(raw)
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$", line)
        if m and not raw.startswith((" ", "\t")):
            key, val = m.group(1), m.group(2).strip()
            if val:
                data[key] = _value(val)
                current = None
            else:
                data[key] = []
                current = key
            continue
        item = re.match(r"^\s+-\s*(.*)$", line)
        if item and current is not None:
            data[current].append(_value(item.group(1)))
    return data


# ----------------------------------------------------------------------------- positive contracts
def _flag(tokens, name):
    return tokens[tokens.index(name) + 1] if name in tokens and tokens.index(name) + 1 < len(tokens) else None


def check_success_checks(p, contract, hat, stage, err):
    """The packet must carry this task's own check-task line (workflow.py contract → success_check), with the
    real roots filled in. A check for another task, another root, or `echo ok` is not a success check (N05)."""
    feature_dir = os.path.normpath(str(p.get("feature_dir") or ""))
    product_root = os.path.normpath(str(p.get("product_root") or ""))
    want_root = product_root if stage == "product" else feature_dir
    found = []
    for chk in p.get("success_checks") or []:
        try:
            tok = shlex.split(str(chk))
        except ValueError:
            continue
        if "check-task" not in tok or not any(x.endswith("workflow.py") for x in tok):
            continue
        found.append(tok)
        got = (_flag(tok, "--role"), _flag(tok, "--stage"), _flag(tok, "--task"))
        if got != (hat, stage, str(p.get("task"))):
            err("CHECKMISMATCH", f"success_checks runs check-task for {'/'.join(map(str, got))}, not {hat}/{stage}/{p.get('task')}")
        if os.path.normpath(str(_flag(tok, "--root") or "")) != want_root:
            err("CHECKMISMATCH", f"success_checks check-task --root must be {want_root}")
        if contract.get("product_outputs") and os.path.normpath(str(_flag(tok, "--product-root") or "")) != product_root:
            err("CHECKMISMATCH", f"success_checks check-task --product-root must be {product_root}")
    if not found:
        err("MISSING-CHECK", "success_checks must include this task's check: "
            "python3 <PLUGIN_ROOT>/scripts/workflow.py contract … prints it as success_check (fill in the real paths)")


def _ui_feature(p):
    if str(p.get("ui", "")).lower() in ("yes", "true"):
        return True
    st = os.path.join(str(p.get("feature_dir") or ""), "state.yaml")
    try:
        return bool(re.search(r"^ui:\s*(yes|true)\b", open(st, encoding="utf-8").read(), re.M))
    except OSError:
        return False


def check_evidence(p, contract, stage, err):
    """Evidence the registry requires for this task must be listed under evidence_required. A packet can add
    evidence, never drop it: rewording a waiver cannot lower what the gate later verifies (N06)."""
    need = set()
    for ev in contract.get("evidence", []):
        if isinstance(ev, dict):
            if ev.get("when") == "ui" and not _ui_feature(p):
                continue
            need.add(ev["kind"])
        else:
            need.add(ev)
    have = {str(x).strip() for x in p.get("evidence_required") or []}
    missing = sorted(need - have)
    if missing:
        err("EVIDENCE", f"evidence_required must list {', '.join(missing)} (registry contract for this task; a packet may add, never drop)")


def _security_feature(p):
    st = os.path.join(str(p.get("feature_dir") or ""), "state.yaml")
    try:
        return bool(re.search(r"^q_security:\s*yes\b", open(st, encoding="utf-8").read(), re.M))
    except OSError:
        return False


def check_visuals(p, contract, stage, err):
    """Diagrams the packet asks for must be drawn with the vendored conventions and checked by the diagram gate."""
    kinds = {v["type"]: v["when"] for v in contract.get("visuals", [])}
    asked = [str(x).strip() for x in p.get("visuals") or []]
    for v in asked:
        if v not in kinds:
            err("VISUALS", f"visuals lists {v}; this task draws only {', '.join(kinds) or 'no diagrams'}")
    for v, when in kinds.items():
        if when in REGISTRY["diagram"]["enforced_when"] and when == "security" and _security_feature(p) and v not in asked:
            err("VISUALS", f"q_security: yes — visuals must include {v}")
    if not [v for v in asked if v in kinds]:
        return
    d = REGISTRY["diagram"]
    base = os.path.normpath(str((p.get("product_root") if stage == "product" else p.get("feature_dir")) or ""))
    outs = [str(o) for o in p.get("deliverable_paths") or []]
    if not any(fnmatch.fnmatchcase(o.replace(base + "/", ""), f"{contract['diagram_dir']}/*.svg") for o in outs):
        err("DIAGRAM", f"visuals need an SVG deliverable under {contract['diagram_dir']}/ (e.g. {contract['diagram_dir']}/<name>.svg)")
    inputs = [str(i.get("path", "")) if isinstance(i, dict) else str(i) for i in p.get("inputs") or []]
    for need in (d["guide"], contract["diagram_reference"]):
        if not any(i.endswith(need) for i in inputs):
            err("DIAGRAM", f"inputs must include PLUGIN_ROOT/{need}")
    checks = []
    for chk in p.get("success_checks") or []:
        try:
            tok = shlex.split(str(chk))
        except ValueError:
            continue
        if any(x.endswith(d["lint"]) for x in tok):
            checks.append(tok)
    if not checks:
        err("DIAGRAM", f"success_checks must run python3 PLUGIN_ROOT/{d['lint']} --root {base} <svg> (the contract prints it as diagram.check)")
    elif not any(os.path.normpath(str(_flag(tok, "--root") or "")) == base for tok in checks):
        err("DIAGRAM", f"the diagram check must use --root {base}")


# ----------------------------------------------------------------------------- lint
def lint(text: str, plugin_root: str | None = None) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warns: list[dict[str, str]] = []

    def err(code: str, msg: str) -> None:
        errors.append({"code": code, "message": msg})

    def warn(code: str, msg: str) -> None:
        warns.append({"code": code, "message": msg})

    block = extract_packet(text)
    if block is None:
        return {"errors": [{"code": "NO-PACKET", "message": "no '## SPAWN PACKET v2' block found"}], "warnings": [], "packet": {}}
    p = parse_packet(block)
    hat = str(p.get("hat", "")).strip()
    stage = str(p.get("stage", "")).strip()

    for k in REQUIRED:
        if p.get(k) in (None, "", []):
            err("MISSING", f"{k} is missing or empty")
    if stage and stage != "product":
        for k in ("feature_dir", "lane"):
            if not p.get(k):
                err("MISSING", f"{k} is required for feature stages")
    if stage == "product" and not p.get("product_root"):
        err("MISSING", "product_root is required for stage: product")
    if stage and stage not in STAGES:
        err("STAGE", f"stage {stage!r} is not a stage id ({', '.join(sorted(STAGES))})")

    try:
        contract = resolve_task(REGISTRY, hat, stage, str(p.get("task", "")))
        if p.get("primary_skill") != "sdlc-workflow:" + contract["skill"]:
            err("TASKSKILL", f"{hat}/{stage}/{p.get('task')} requires sdlc-workflow:{contract['skill']}")
        if contract.get("lane_file") and p.get("lane_file") != contract["lane_file"]:
            err("TASKLANE", f"{hat} implementation requires lane_file: {contract['lane_file']}")
        if stage == "implement":
            implementers = {t["role"] for t in REGISTRY["tasks"] if t["stage"] == "implement"}
            if p.get("slice_integrator") not in implementers:
                err("INTEGRATOR", "implementation packets must name one implementation role as slice_integrator")
        declared = []
        base_raw = p.get("product_root") if stage == "product" else p.get("feature_dir")
        base = Path(str(base_raw or "."))
        owned = {os.path.normpath(str(w)) for w in p.get("product_writes") or []}
        for output in p.get("deliverable_paths") or []:
            path = Path(str(output))
            if path.is_absolute():
                if os.path.normpath(str(path)) in owned:
                    continue  # a product file this hat owns, checked with product_writes below
                try:
                    path = Path(os.path.normpath(str(path))).relative_to(os.path.normpath(str(base)))
                except ValueError:
                    # Writes outside the artifact root were silently allowed (N04): the hat is told
                    # "do not write outside deliverable_paths", so listing a path authorises it.
                    err("DELIVERABLE-SCOPE", f"deliverable outside the artifact root {base}: {output}")
                    continue
            if ".." in path.parts:
                err("DELIVERABLE", f"deliverable escapes artifact root: {output}")
            declared.append(path.as_posix().rstrip("/"))
        for key in contract["required"]:
            patterns = [ticket_pattern(s, str(p["task"]), hat) for s in artifact_paths(REGISTRY, [key])]
            if not any(fnmatch.fnmatchcase(path, pattern) or
                       (pattern.endswith("/*") and path == pattern[:-2])
                       for path in declared for pattern in patterns):
                err("DELIVERABLE", f"task requires an output matching {' or '.join(patterns)}")
        allowed = set(contract.get("companions", []))
        for c in p.get("companion_skills") or []:
            name = str(c).split(":", 1)[-1].strip()
            if name and name not in allowed:
                err("COMPANION", f"companion_skills lists {name}, which {hat}/{stage}/{p.get('task')} does not use"
                    + (" (prototype is throwaway discovery code; design prototypes follow design-contract direction-prototypes.md)" if name == "prototype" else ""))
        check_success_checks(p, contract, hat, stage, err)
        check_evidence(p, contract, stage, err)
        check_visuals(p, contract, stage, err)
        inputs = [str(i.get("path", "")) if isinstance(i, dict) else str(i) for i in p.get("inputs") or []]
        for rd in contract.get("reads", []):
            if not any(i.endswith(rd) for i in inputs):
                err("READS", f"inputs must include PLUGIN_ROOT/{rd} (required reading for {hat}/{stage}/{p.get('task')})")
    except ValueError as error:
        err("TASK", str(error))

    root = plugin_root or (p.get("PLUGIN_ROOT") if isinstance(p.get("PLUGIN_ROOT"), str) else None)
    if root and os.path.isdir(root):
        if hat and not os.path.isfile(os.path.join(root, "agents", f"{hat}.md")):
            err("HAT", f"hat {hat!r} has no agents/{hat}.md")
        ps = str(p.get("primary_skill", ""))
        m = re.match(r"^sdlc-workflow:([a-z0-9-]+)$", ps)
        if ps and not m:
            err("SKILL", f"primary_skill {ps!r} must be sdlc-workflow:<proc>")
        elif m and not os.path.isfile(os.path.join(root, "skills", m.group(1), "SKILL.md")):
            err("SKILL", f"primary_skill {ps!r} has no skills/{m.group(1)}/SKILL.md")
    elif p.get("PLUGIN_ROOT"):
        err("PATH", f"PLUGIN_ROOT {p.get('PLUGIN_ROOT')!r} is not a directory")

    st = str(p.get("subagent_type", ""))
    if hat and st and st != f"sdlc-workflow:{hat}":
        if st == "general-purpose":
            warn("FALLBACK", f"general-purpose fallback: the packet must tell it to Read agents/{hat}.md and the primary SKILL.md, and state.yaml records host_spawn")
        else:
            err("SUBAGENT", f"subagent_type {st!r} must be sdlc-workflow:{hat}")

    for k in ABS_SCALARS:
        v = p.get(k)
        if isinstance(v, str) and v and v not in ("none", "empty") and not os.path.isabs(v):
            err("PATH", f"{k} must be absolute: {v}")
    fd = p.get("feature_dir")
    if isinstance(fd, str) and os.path.isabs(fd) and not os.path.isdir(fd):
        err("PATH", f"feature_dir does not exist: {fd}")
    pr = p.get("product_root") if isinstance(p.get("product_root"), str) else ""

    # product_context and inputs: files only, within budget
    budget = 0
    for f in p.get("product_context") or []:
        f = str(f)
        if not os.path.isabs(f):
            err("PATH", f"product_context entries must be absolute: {f}")
        elif os.path.isdir(f):
            err("DIRINPUT", f"product_context lists a directory: {f}")
        elif not os.path.isfile(f):
            err("MISSING-FILE", f"product_context file does not exist: {f}")
        else:
            budget += os.path.getsize(f)
            with open(f, encoding="utf-8", errors="replace") as fh:
                head = fh.read(4000)
            if re.search(r"^[ \t]*(<!--|#|//)[ \t]*sdlc:unfilled", head, re.M):
                warn("UNFILLED-CONTEXT", f"{f} is still a template — fill it first or drop it from product_context")
    inputs = p.get("inputs") or []
    if len(inputs) > INPUTS_WARN:
        warn("INPUTS", f"{len(inputs)} inputs — name the files the hat must read; put search areas in explore_roots")
    for item in inputs:
        path = str(item.get("path", "")) if isinstance(item, dict) else str(item)
        required = bool(item.get("required", True)) if isinstance(item, dict) else True
        if not os.path.isabs(path):
            err("PATH", f"inputs path must be absolute: {path}")
        elif os.path.isdir(path):
            err("DIRINPUT", f"inputs lists a directory: {path} — list files; directories to search go in explore_roots")
        elif not os.path.isfile(path):
            (err if required else warn)("MISSING-FILE", f"inputs file does not exist: {path}")
        elif required:
            budget += os.path.getsize(path)
    for d in p.get("explore_roots") or []:
        d = str(d)
        if not os.path.isabs(d) or not os.path.isdir(d):
            err("EXPLORE", f"explore_roots entries must be existing absolute directories: {d}")
    if budget > CONTEXT_ERROR:
        err("BUDGET", f"product_context + required inputs = {budget // 1000} KB (> {CONTEXT_ERROR // 1000} KB) — every spawn reads all of it; trim to what this task needs")
    elif budget > CONTEXT_WARN:
        warn("BUDGET", f"product_context + required inputs = {budget // 1000} KB (> {CONTEXT_WARN // 1000} KB)")

    # write scope
    writes = [str(w) for w in p.get("product_writes") or []]
    for w in writes:
        rel = os.path.relpath(w, pr) if pr and os.path.isabs(w) else w
        rel = rel.replace("\\", "/")
        if os.path.basename(rel) in MANAGER_ONLY:
            err("LOGWRITE", f"{rel} is written by the manager only; hats return delta rows")
        elif hat in FRESH:
            err("FRESHWRITE", f"{hat} is a fresh-context judge and must not have product_writes ({rel})")
        elif rel not in OWNERS.get(hat, set()):
            err("UNOWNED", f"{hat} does not own {rel} (owners: workflow/registry.json) — raise an open question to the owner instead")
    for d in p.get("deliverable_paths") or []:
        if os.path.basename(str(d)) in MANAGER_ONLY:
            err("LOGWRITE", f"deliverable_paths names {d}, which only the manager writes")
    if hat in FRESH and str(p.get("memory_file", "")).strip() not in ("", "none", "empty"):
        err("FRESHWRITE", f"{hat} must not have a memory_file")

    # success checks use stage ids
    for chk in p.get("success_checks") or []:
        m = re.search(r"--hat\s+([A-Za-z-]+)", str(chk))
        if m and m.group(1) not in STAGES:
            err("HATARG", f"success_checks uses --hat {m.group(1)}: pass the stage id, never the spawn role")
        elif m and m.group(1) != stage:
            err("GATESTAGE", f"packet stage {stage} cannot use --hat {m.group(1)}")
        elif m and stage == "designer" and p.get("task") == "explore":
            err("EARLYGATE", "explore uses workflow.py check-task; the designer stage gate runs after specify")
    forbidden = " ".join(str(x) for x in p.get("forbidden") or [])
    if "spawn further subagents" not in forbidden:
        warn("FORBIDDEN", "forbidden should include 'Do not spawn further subagents (host depth 1).'")

    # waivers anywhere in the packet text
    for n, line in enumerate(block.splitlines(), 1):
        for pat in WAIVERS:
            if re.search(pat, line, re.I):
                err("WAIVER", f"line {n} waives evidence: {line.strip()[:140]} — scale the deliverable, never the evidence")
                break
    return {"errors": errors, "warnings": warns, "packet": {"hat": hat, "stage": stage}}


# ----------------------------------------------------------------------------- self-test
def self_test() -> int:
    def fail(msg: str, *extra: Any) -> int:
        print("self-test FAILED:", msg, *extra)
        return 1

    with tempfile.TemporaryDirectory() as td:
        plugin = os.path.join(td, "plugin")
        for a in ("pm", "reviewer", "designer"):
            os.makedirs(os.path.join(plugin, "agents"), exist_ok=True)
            open(os.path.join(plugin, "agents", f"{a}.md"), "w").close()
        for s in ("prd-gwt", "findings", "design-contract"):
            os.makedirs(os.path.join(plugin, "skills", s), exist_ok=True)
            open(os.path.join(plugin, "skills", s, "SKILL.md"), "w").close()
        proj = os.path.join(td, "proj")
        prod = os.path.join(proj, "docs", "product")
        feat = os.path.join(proj, ".sdlc", "f")
        os.makedirs(os.path.join(feat, "00-discover"))
        os.makedirs(prod)
        os.makedirs(os.path.join(proj, "backend", "api"))
        for name, body in (("strategy.md", "# s\n"), ("feature-map.md", "# f\n")):
            with open(os.path.join(prod, name), "w") as f:
                f.write(body)
        brief = os.path.join(feat, "00-discover", "briefing.md")
        with open(brief, "w") as f:
            f.write("brief\n")

        def packet(**over: str) -> str:
            fields = {
                "hat": "pm", "stage": "define", "task": "spec", "subagent_type": "sdlc-workflow:pm", "lane": "L2",
                "feature_dir": feat, "PLUGIN_ROOT": plugin, "product_root": prod, "primary_skill": "sdlc-workflow:prd-gwt",
                "memory_file": os.path.join(feat, "memory", "pm.md"), "debug_protocol": "",
            }
            fields.update(over)
            lines = ["## SPAWN PACKET v2"] + [f"{k}: {v}" for k, v in fields.items()]
            lines += ["product_context:", f"  - {prod}/strategy.md", f"  - {prod}/feature-map.md",
                      "product_writes:", f"  - {prod}/strategy.md", f"  - {prod}/feature-map.md",
                      "inputs:", f"  - {{path: {brief}, required: true}}",
                      "explore_roots:", f"  - {proj}/backend",
                      "deliverable_paths:", "  - 01-define/spec.md",
                      "forbidden:", "  - Do not spawn further subagents (host depth 1).",
                      "success_checks:", f"  - bash {plugin}/scripts/check-sdlc.sh --require --hat define {feat}",
                      f"  - python3 {plugin}/scripts/workflow.py check-task --role {fields['hat']} --stage {fields['stage']} --task {fields['task']} --root {feat}",
                      "return: output paths + summary"]
            return "\n".join(lines) + "\n"

        good = lint(packet())
        if good["errors"]:
            return fail("a valid packet must pass", good["errors"])
        bad_text = packet().replace(f"  - {{path: {brief}, required: true}}",
                                    f"  - {{path: {brief}, required: true}}\n  - {{path: {proj}/backend/api, required: false}}")
        bad_text = bad_text.replace("  - 01-define/spec.md", "  - 01-define/spec.md\n  - 冒烟规模约定：这是 smoke run，不需要 WebSearch/WebFetch")
        bad_text = bad_text.replace(f"  - {prod}/feature-map.md\ninputs:", f"  - {prod}/feature-map.md\n  - {prod}/CHANGELOG.md\ninputs:")
        bad_text = bad_text.replace("--hat define", "--hat pm")
        codes = {e["code"] for e in lint(bad_text)["errors"]}
        if not {"DIRINPUT", "WAIVER", "LOGWRITE", "HATARG"} <= codes:
            return fail("dir input, waiver, log write and role --hat must all be errors", codes)
        codes = {e["code"] for e in lint(packet(hat="designer", subagent_type="sdlc-workflow:designer", primary_skill="sdlc-workflow:design-contract"))["errors"]}
        if "UNOWNED" not in codes:
            return fail("designer writing strategy.md must be UNOWNED", codes)
        rv = packet(hat="reviewer", subagent_type="sdlc-workflow:reviewer", primary_skill="sdlc-workflow:findings", stage="review")
        codes = {e["code"] for e in lint(rv)["errors"]}
        if "FRESHWRITE" not in codes:
            return fail("reviewer with product_writes / memory must be FRESHWRITE", codes)
        text = packet().replace(f"  - {prod}/strategy.md\n  - {prod}/feature-map.md\nproduct_writes:",
                                f"  - {prod}/strategy.md\n  - {prod}/missing.md\nproduct_writes:")
        if "MISSING-FILE" not in {e["code"] for e in lint(text)["errors"]}:
            return fail("a missing product_context file must be an error")
        text = packet().replace("return: output paths + summary",
                                                      "return: output paths + summary\nnotes: 本机无运行 UI 时按 packet 约定走源码考古")
        if "WAIVER" not in {e["code"] for e in lint(text)["errors"]}:
            return fail("'走源码考古' must be a waiver")
        with open(os.path.join(prod, "big.md"), "w") as f:
            f.write("x" * 450_000)
        text = packet().replace(f"  - {prod}/feature-map.md\nproduct_writes:", f"  - {prod}/feature-map.md\n  - {prod}/big.md\nproduct_writes:")
        if "BUDGET" not in {e["code"] for e in lint(text)["errors"]}:
            return fail("an oversized product_context must be BUDGET")
        # N04: a deliverable outside the feature directory is an unauthorised write
        text = packet().replace("  - 01-define/spec.md", "  - 01-define/spec.md\n  - /etc/hosts")
        if "DELIVERABLE-SCOPE" not in {e["code"] for e in lint(text)["errors"]}:
            return fail("an absolute deliverable outside feature_dir must be DELIVERABLE-SCOPE")
        # N05: a check-task for another task, or no check-task at all
        text = packet().replace("--role pm --stage define --task spec", "--role designer --stage designer --task explore")
        if "CHECKMISMATCH" not in {e["code"] for e in lint(text)["errors"]}:
            return fail("a check-task for another task must be CHECKMISMATCH")
        text = "\n".join(l for l in packet().splitlines() if "check-task" not in l) + "\n"
        if "MISSING-CHECK" not in {e["code"] for e in lint(text)["errors"]}:
            return fail("a packet without this task's check-task must be MISSING-CHECK")
        # N06: evidence the registry requires cannot be dropped, however the waiver is worded
        os.makedirs(os.path.join(plugin, "skills", "market"), exist_ok=True)
        open(os.path.join(plugin, "skills", "market", "SKILL.md"), "w").close()
        open(os.path.join(plugin, "agents", "researcher.md"), "w").close()
        rs = packet(hat="researcher", stage="market", task="survey", subagent_type="sdlc-workflow:researcher",
                    primary_skill="sdlc-workflow:market").replace("  - 01-define/spec.md", "  - 00-discover/market.md")
        rs = rs.replace(f"  - {prod}/strategy.md\n  - {prod}/feature-map.md\ninputs:", "inputs:")
        codes = {e["code"] for e in lint(rs + "notes: 这轮 WebSearch 非必需\n")["errors"]}
        if "EVIDENCE" not in codes:
            return fail("a research packet without evidence_required: web must be EVIDENCE", codes)
        codes = {e["code"] for e in lint(rs.replace("forbidden:", "evidence_required:\n  - web\nforbidden:"))["errors"]}
        if "EVIDENCE" in codes:
            return fail("evidence_required listing web must satisfy the research contract", codes)
        if lint("no packet here")["errors"][0]["code"] != "NO-PACKET":
            return fail("text without a packet must be NO-PACKET")
    print("self-test ok")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint a SPAWN PACKET v2 (read-only).")
    ap.add_argument("packet", nargs="?")
    ap.add_argument("--plugin-root")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.packet or not os.path.isfile(args.packet):
        print("usage: check_packet.py <packet.md> [--plugin-root DIR] [--json]", file=sys.stderr)
        return 2
    with open(args.packet, encoding="utf-8", errors="replace") as f:
        result = lint(f.read(), args.plugin_root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"check_packet: {args.packet} (hat={result['packet'].get('hat')}, stage={result['packet'].get('stage')})")
        for e in result["errors"]:
            print(f"✗ [{e['code']}] {e['message']}")
        for w in result["warnings"]:
            print(f"⚠ [{w['code']}] {w['message']}")
        print("✗ fix the packet before spawning" if result["errors"] else "✓ packet ok")
    if any(e["code"] == "NO-PACKET" for e in result["errors"]):
        return 2
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
