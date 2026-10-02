#!/usr/bin/env python3
"""check_packet.py — lint a registered v2 or sealed v3 packet before the manager spawns a hat. Read-only.

Why it exists (2026-09-17 GLM run on a real project):
  * packets told hats "smoke run — no WebSearch/WebFetch needed", made URLs "optional", and told the designer to fall back
    to reading source code when the app was down — research and screenshots quietly disappeared;
  * a bootstrap pm packet listed whole trees as inputs (docs/, .sdlc/ with 443 files, api and pages directories) and the
    run consumed ~38.7M input tokens;
  * parallel hats appended to the same CHANGELOG, and packets passed spawn-role names where stage ids belong.

  python3 check_packet.py <packet.md> [--plugin-root DIR] [--json]
  python3 check_packet.py --self-test

Exit: 0 no errors (warnings allowed) · 1 errors (fix the packet, do not spawn) · 2 usage / no packet found.
Save packets as <feature>/packets/<nn>-<stage>-<hat>.md (features), .sdlc/_product/packets/<n>-<hat>.md (/sdlc-product)
or .sdlc/_product/cycles/<id>/packets/<n>-<hat>.md (/sdlc-product cycle).
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

from workflow import load_registry, resolve_task, artifact_paths, ticket_pattern, task_scope, ROOT_FIELD, find_config

REGISTRY = load_registry()
STAGES = set(REGISTRY["stages"])
FRESH = {name for name, role in REGISTRY["roles"].items() if role["fresh"]}
OWNERS = {name: set(role["product_writes"]) for name, role in REGISTRY["roles"].items()}
PRODUCT_FILES = set().union(*OWNERS.values())  # canonical product files: each has exactly one owning role
MANAGER_ONLY = set(REGISTRY["manager_only"])
REQUIRED = ("hat", "stage", "task", "subagent_type", "PLUGIN_ROOT", "primary_skill", "deliverable_paths", "success_checks", "return")
ABS_SCALARS = ("PLUGIN_ROOT", "feature_dir", "product_root", "project_root", "cycle_dir", "memory_file", "debug_protocol")
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
    return parse_packet_lines(block)[0]


def parse_packet_lines(block: str) -> tuple[dict[str, Any], list[str]]:
    """v2 syntax is `field: value` and indented `- item` lines. Anything else is reported, never dropped:
    a nested mapping would otherwise read as an empty list and a repeated field would silently win."""
    data: dict[str, Any] = {}
    problems: list[str] = []
    current: str | None = None
    ended: str | None = None
    for raw in block.splitlines():
        if not raw.strip():
            continue
        line = _strip_comment(raw)
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$", line)
        if m and not raw.startswith((" ", "\t")):
            key, val = m.group(1), m.group(2).strip()
            if ended is not None:
                problems.append(f"field {key} follows non-packet text {ended!r}; fence the packet or remove the text")
            if key in data:
                problems.append(f"duplicate field {key}")
            if val:
                data[key] = _value(val)
                current = None
            else:
                data[key] = []
                current = key
            continue
        if ended is not None:
            continue
        if not raw.startswith((" ", "\t")):
            if current is not None and line.startswith("-"):
                problems.append(f"list item for {current} must be indented: {line.strip()[:80]}")
            else:
                ended = line.strip()[:60]
                current = None
            continue
        item = re.match(r"^\s+-\s*(.*)$", line)
        if item and current is not None:
            data[current].append(_value(item.group(1)))
        elif item:
            problems.append(f"list item has no list field: {line.strip()[:80]}")
        else:
            problems.append(f"unsupported nested line (v2 has no nested mappings): {line.strip()[:80]}")
    return data, problems


# ----------------------------------------------------------------------------- positive contracts
def _flag(tokens, name):
    return tokens[tokens.index(name) + 1] if name in tokens and tokens.index(name) + 1 < len(tokens) else None


def check_success_checks(p, contract, hat, stage, err):
    """The packet must carry this task's own check-task line (workflow.py contract → success_check), with the
    real roots filled in. A check for another task, another root, or `echo ok` is not a success check (N05)."""
    product_root = os.path.normpath(str(p.get("product_root") or ""))
    want_root = os.path.normpath(str(p.get(ROOT_FIELD[task_scope(contract)]) or ""))
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
        return bool(re.search(r"^ui:\s*(yes|true)\b", Path(st).read_text(encoding="utf-8"), re.M))
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
    if str(p.get('q_security', '')).lower() in ('yes', 'true'):
        return True
    st = os.path.join(str(p.get("feature_dir") or ""), "state.yaml")
    try:
        return bool(re.search(r"^q_security:\s*[\"']?(yes|true)\b", Path(st).read_text(encoding="utf-8"), re.M))
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
    base = os.path.normpath(str(p.get(ROOT_FIELD[task_scope(contract)]) or ""))
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


def check_imagery(p, contract, stage, err):
    """Images the packet asks for must be generated by the tool, land where their kind belongs, and be gated.

    Nothing here is ever required: no feature must generate an image. What is enforced is that a packet which does
    ask for one carries the practice, a deliverable directory and the check that binds the file to its prompt.
    """
    kinds = {im["kind"]: im["when"] for im in contract.get("imagery", [])}
    asked = [str(x).strip() for x in p.get("imagery") or []]
    for kind in asked:
        if kind not in kinds:
            err("IMAGERY", f"imagery lists {kind}; this task may generate only "
                           f"{', '.join(kinds) or 'no images'}")
    asked = [kind for kind in asked if kind in kinds]
    if not asked:
        return
    g = REGISTRY["imagery"]
    base = os.path.normpath(str(p.get(ROOT_FIELD[task_scope(contract)]) or ""))
    outs = [str(o) for o in p.get("deliverable_paths") or []]
    for kind in sorted({g["dirs"][k] for k in asked}):
        if not any(fnmatch.fnmatchcase(o.replace(base + "/", ""), f"{kind}/*") or
                   o.replace(base + "/", "").rstrip("/") == kind for o in outs):
            err("IMAGERY", f"imagery needs a deliverable under {kind}/ (e.g. {kind}/<name>.png)")
    inputs = [str(i.get("path", "")) if isinstance(i, dict) else str(i) for i in p.get("inputs") or []]
    for need in dict.fromkeys((g["guide"], contract["imagery_reference"])):
        if not any(i.endswith(need) for i in inputs):
            err("IMAGERY", f"inputs must include PLUGIN_ROOT/{need}")
    checks = []
    for chk in p.get("success_checks") or []:
        try:
            tok = shlex.split(str(chk))
        except ValueError:
            continue
        if any(x.endswith(g["check"]) for x in tok):
            checks.append(tok)
    if not checks:
        err("IMAGERY", f"success_checks must run python3 PLUGIN_ROOT/{g['check']} --root {base} "
                       "(the contract prints it as image.check)")
    elif not any(os.path.normpath(str(_flag(tok, "--root") or "")) == base for tok in checks):
        err("IMAGERY", f"the imagery check must use --root {base}")


def _compat_hint(name: str) -> str:
    """An old packet naming a compatibility entry gets the migration target, not only a rejection."""
    meta = REGISTRY.get("skills", {}).get(name.strip(), {})
    if meta.get("kind") != "compat":
        return ""
    sunset = f", sunset {meta['sunset']}" if meta.get("sunset") else ""
    return f" — {name.strip()} is a deprecated compatibility entry{sunset}; migrate to sdlc-workflow:{meta.get('replaced_by')}"


def _real(value) -> Path:
    """Resolve symlinks and `..` so every write field is compared on the path that would really be written."""
    return Path(os.path.realpath(str(value)))


def _within(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def _matches(rel: str, patterns) -> bool:
    return any(fnmatch.fnmatchcase(rel, pat) or (pat.endswith("/*") and rel == pat[:-2]) for pat in patterns)


def check_outputs(p, contract, hat, stage, base, err):
    """Classify every deliverable path by what it really is, whichever field names it (C06, C09).

    A path inside product_root is never authorised just because it is inside the root: a canonical product file
    needs its owning role *and* a product_writes entry; anything else there must be an evidence path the task
    contract declares. A manager-persisted report (registry manager_output) is resolved under project_root and
    is only legal for fresh-context judges, whose final message the manager writes to disk.
    Returns the task-root-relative deliverables used to match the task's required artifacts.
    """
    declared = []
    prod_raw = str(p.get("product_root") or "")
    prod = _real(prod_raw) if os.path.isabs(prod_raw) else None
    base_real = _real(base)
    writes = {_real(w) for w in p.get("product_writes") or [] if os.path.isabs(str(w))}
    evidence = list(contract.get("evidence_paths", []))
    if contract.get("visuals") and contract.get("diagram_dir"):
        evidence += [f"{contract['diagram_dir']}/*.svg", f"{contract['diagram_dir']}/shots/*"]
    manager_out = None
    if contract.get("manager_output"):
        proj = str(p.get("project_root") or "")
        if os.path.isabs(proj):
            manager_out = _real(os.path.join(proj, contract["manager_output"]))
    for output in p.get("deliverable_paths") or []:
        raw = str(output)
        if not os.path.isabs(raw) and ".." in Path(raw).parts:
            err("DELIVERABLE", f"deliverable escapes artifact root: {output}")
            continue
        target = _real(raw if os.path.isabs(raw) else base / raw)
        if manager_out is not None and target == manager_out:
            if hat not in FRESH:
                err("DELIVERABLE-SCOPE", f"{output} is the manager's report path ({contract['manager_output']}); "
                                         "only a fresh-context judge returns it for the manager to write")
            continue
        if prod is not None and _within(target, prod):
            rel = target.relative_to(prod).as_posix()
            if rel in PRODUCT_FILES:
                if hat in FRESH or rel not in OWNERS.get(hat, set()):
                    err("UNOWNED", f"{hat} does not own product file {rel} (owners: workflow/registry.json) — "
                                   "raise an open question to the owner instead")
                elif target not in writes:
                    err("UNOWNED", f"{rel} is a product file: list it in product_writes, not only in deliverable_paths")
            elif not _matches(rel, evidence):
                err("DELIVERABLE-SCOPE", f"{output} is inside product_root but is neither an owned product file nor an "
                                         f"evidence path this task declares ({', '.join(evidence) or 'none'})")
            continue
        if target != base_real and _within(target, base_real):
            if task_scope(contract) == 'feature' and any(_within(target, base_real / name) for name in ('work', 'runs', '.task-objects', 'artifacts', 'imports', '.control')):
                err('DELIVERABLE-SCOPE', f'{output} is a manager-owned work/run record')
                continue
            declared.append(target.relative_to(base_real).as_posix().rstrip("/"))
            continue
        if contract.get("manager_output") and manager_out is None and raw.endswith(contract["manager_output"]):
            err("DELIVERABLE-SCOPE", f"{output}: pass project_root so the manager report path "
                                     f"{contract['manager_output']} can be resolved")
            continue
        # Writes outside the artifact root were silently allowed (N04): the hat is told
        # "do not write outside deliverable_paths", so listing a path authorises it.
        err("DELIVERABLE-SCOPE", f"deliverable outside the artifact root {base}: {output}")
    return declared


def check_memory_file(p, hat, scope, err):
    """memory_file is a write too: it must stay in the task's memory folder, never a product or manager file."""
    mf = str(p.get("memory_file") or "").strip()
    if not mf or mf in ("none", "empty") or not os.path.isabs(mf) or hat in FRESH:
        return
    target = _real(mf)
    prod_raw = str(p.get("product_root") or "")
    if os.path.isabs(prod_raw) and _within(target, _real(prod_raw)):
        err("MEMORY", f"memory_file {mf} is inside product_root; product facts go through product_writes")
        return
    if target.name in MANAGER_ONLY:
        err("LOGWRITE", f"memory_file {mf} names a manager-only file")
        return
    home = str(p.get(ROOT_FIELD.get(scope, "")) or "") if scope in ("feature", "cycle") else ""
    if home and os.path.isabs(home) and not _within(target, _real(home) / "memory"):
        err("MEMORY", f"memory_file must live under {home}/memory/")
    elif target.parent.name != "memory" or target.name != f"{hat}.md":
        err("MEMORY", f"memory_file must be memory/{hat}.md (one file per role; others' memory is not yours)")


def check_cycle_dir(p, err):
    """A cycle runs in <artifact_root>/.sdlc/_product/cycles/<id>: its own root, separate from product facts."""
    raw = str(p.get("cycle_dir") or "")
    if not raw:
        err("MISSING", "cycle_dir is required for cycle tasks")
        return
    path = _real(raw)
    if not os.path.isabs(raw) or not path.is_dir():
        err("CYCLE-DIR", f"cycle_dir must be an existing absolute directory: {raw}")
    elif path.parent.name != "cycles" or path.parent.parent.name != "_product" or path.parent.parent.parent.name != ".sdlc":
        err("CYCLE-DIR", f"cycle_dir must be .sdlc/_product/cycles/<id>, not {raw}")
    prod = str(p.get("product_root") or "")
    if os.path.isabs(prod) and _within(path, _real(prod)):
        err("CYCLE-DIR", "cycle_dir cannot live inside product_root (cycle records are not product facts)")


def _store_dir(p, store):
    """Resolve a registered store (e.g. signals) from the project's config; None when unset."""
    proj = str(p.get("project_root") or "")
    meta = REGISTRY.get("stores", {}).get(store, {})
    if not os.path.isabs(proj) or not meta:
        return None
    cfg = Path(proj) / "sdlc.config.yaml"
    if not cfg.is_file():
        return None
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from check_config import parse_yaml  # noqa: PLC0415
    value = parse_yaml(cfg.read_text(encoding="utf-8")).get(meta.get("config"))
    if not isinstance(value, str) or not value.strip() or "<" in value:
        return None
    return _real(os.path.join(proj, value))


def check_store_writes(p, contract, hat, err):
    """A store (the product-level signals store) has one owning task and a configured location: a path in the
    config is not a grant; only the registered task may write, and only inside that directory."""
    writes = p.get("store_writes") or []
    if not writes:
        return
    store = contract.get("store_writes")
    if not store:
        err("STORE-SCOPE", f"{hat}/{contract['stage']}/{contract['task']} may not write a store")
        return
    base = _store_dir(p, store)
    if base is None:
        err("STORE-SCOPE", f"store_writes needs project_root and {REGISTRY['stores'][store]['config']} in its sdlc.config.yaml")
        return
    proj = _real(str(p.get("project_root")))
    guarded = [proj / ".sdlc", proj / ".git"] + [_real(str(p[k])) for k in ("product_root", "feature_dir", "cycle_dir") if p.get(k)]
    if base == proj or not _within(base, proj) or any(_within(base, g) or _within(g, base) for g in guarded):
        err("STORE-SCOPE", f"the {store} store {base} must be its own directory inside the project, apart from product, feature and manager files")
        return
    for item in writes:
        value = str(item)
        rel = Path(value)
        target = _real(os.path.join(str(base), value))
        if (not value or rel.is_absolute() or ".." in rel.parts or any(c in value for c in "*?[]")
                or not _within(target, base) or target == base):
            err("STORE-SCOPE", f"store write must be a file or subtree inside the {store} store: {value}")


def check_source_writes(p, contract, hat, err):
    writes = p.get("source_writes") or []
    if not isinstance(writes, list):
        err("SOURCE-SCOPE", "source_writes must be a list of project-relative files or trailing-slash subtrees")
        return
    if contract.get("requires_source") and not writes:
        err("SOURCE-SCOPE", "this implementation task requires explicit source_writes")
    if not writes:
        return
    if not contract.get("writes_source") or hat in FRESH:
        err("SOURCE-SCOPE", "this task is not authorized to write project source")
        return
    raw = str(p.get("project_root") or "")
    root = Path(raw).resolve()
    if not Path(raw).is_absolute() or not root.is_dir() or root == Path(root.anchor):
        err("SOURCE-SCOPE", "source_writes requires an existing absolute project_root, not filesystem root")
        return
    protected = [root / ".git", root / ".sdlc", root / ".agents", root / ".codex"]
    for store in REGISTRY.get("stores", {}):
        store_dir = _store_dir(p, store)
        if store_dir is not None:
            protected.append(store_dir)  # owned by its store task; source writes cannot reach it
    for key in ("feature_dir", "product_root", "cycle_dir"):
        if p.get(key):
            protected.append(Path(str(p[key])).resolve())
    for item in writes:
        value = str(item)
        rel = Path(value)
        target = (root / rel).resolve()
        bad = (not value or value in (".", "./") or rel.is_absolute() or ".." in rel.parts
               or any(c in value for c in "*?[]") or "\\" in value
               or not target.is_relative_to(root) or target == root)
        # Neither a protected file nor a parent subtree may bypass product/manager ownership.
        if any(target == q or target.is_relative_to(q) or q.is_relative_to(target) for q in protected):
            bad = True
        if target.name in MANAGER_ONLY:
            bad = True
        if target.is_dir() and not value.endswith("/"):
            bad = True
        if bad:
            err("SOURCE-SCOPE", f"unsafe or unscoped source write: {value}")


# ----------------------------------------------------------------------------- lint
def lint(text: str, plugin_root: str | None = None, *, enforce_protocol: bool = True) -> dict[str, Any]:
    if '## SPAWN PACKET v3' in text:
        from task_runtime import lint_packet_v3
        return lint_packet_v3(text)
    errors: list[dict[str, str]] = []
    warns: list[dict[str, str]] = []

    def err(code: str, msg: str) -> None:
        errors.append({"code": code, "message": msg})

    def warn(code: str, msg: str) -> None:
        warns.append({"code": code, "message": msg})

    block = extract_packet(text)
    if block is None:
        return {"errors": [{"code": "NO-PACKET", "message": "no '## SPAWN PACKET v2' block found"}], "warnings": [], "packet": {}}
    p, problems = parse_packet_lines(block)
    for problem in problems:
        err("PARSE", problem)
    hat = str(p.get("hat", "")).strip()
    stage = str(p.get("stage", "")).strip()

    for k in REQUIRED:
        if p.get(k) in (None, "", []):
            err("MISSING", f"{k} is missing or empty")
    try:
        scope = task_scope(resolve_task(REGISTRY, hat, stage, str(p.get("task", ""))))
    except ValueError:
        scope = "product" if stage == "product" else "feature"
    if stage and scope == "feature":
        for k in ("feature_dir", "lane"):
            if not p.get(k):
                err("MISSING", f"{k} is required for feature stages")
    if scope == "product" and not p.get("product_root"):
        err("MISSING", "product_root is required for stage: product")
    if scope == "cycle":
        check_cycle_dir(p, err)
    if stage and stage not in STAGES:
        err("STAGE", f"stage {stage!r} is not a stage id ({', '.join(sorted(STAGES))})")

    contract = {}
    try:
        contract = resolve_task(REGISTRY, hat, stage, str(p.get("task", "")))
        if enforce_protocol and contract.get('protocol_required'):
            err('PROTOCOL', 'this task requires prepare → seal → SPAWN PACKET v3; v2 cannot downgrade it')
        if p.get("primary_skill") != "sdlc-workflow:" + contract["skill"]:
            err("TASKSKILL", f"{hat}/{stage}/{p.get('task')} requires sdlc-workflow:{contract['skill']}"
                + _compat_hint(str(p.get("primary_skill", "")).split(":", 1)[-1]))
        # run_scope is optional: an old packet keeps the stage-derived scope. A declared one must be a scope the
        # task contract allows — a caller cannot change a task's permissions or evidence by writing another scope.
        declared_scope = str(p.get("run_scope") or "").strip()
        if declared_scope and declared_scope not in (contract.get("scopes") or [task_scope(contract)]):
            err("SCOPE", f"run_scope {declared_scope!r} is not a scope of {hat}/{stage}/{p.get('task')} "
                         f"({', '.join(contract.get('scopes') or [task_scope(contract)])})")
        if contract.get("lane_file") and p.get("lane_file") != contract["lane_file"]:
            err("TASKLANE", f"{hat} implementation requires lane_file: {contract['lane_file']}")
        if stage == "implement" and contract.get('integration_required', True):
            implementers = {t["role"] for t in REGISTRY["tasks"] if t["stage"] == "implement"}
            if p.get("slice_integrator") not in implementers:
                err("INTEGRATOR", "implementation packets must name one implementation role as slice_integrator")
        base = Path(str(p.get(ROOT_FIELD[task_scope(contract)]) or "."))
        declared = check_outputs(p, contract, hat, stage, base, err)
        for key in contract["required"]:
            patterns = [ticket_pattern(s, str(p["task"]), hat) for s in artifact_paths(REGISTRY, [key])]
            if not any(fnmatch.fnmatchcase(path, pattern) or
                       (pattern.endswith("/*") and path == pattern[:-2])
                       for path in declared for pattern in patterns):
                err("DELIVERABLE", f"task requires an output matching {' or '.join(patterns)}")
        allowed = set(contract.get("companions", []))
        if p.get('debug_protocol'):
            # Existing rework routing can enable debug even outside normal companions.
            allowed.add('debug')
        for c in p.get("companion_skills") or []:
            name = str(c).split(":", 1)[-1].strip()
            if name and name not in allowed:
                err("COMPANION", f"companion_skills lists {name}, which {hat}/{stage}/{p.get('task')} does not use"
                    + (" (prototype is throwaway discovery code; design prototypes follow design-contract direction-prototypes.md)" if name == "prototype" else "")
                    + _compat_hint(name))
        check_success_checks(p, contract, hat, stage, err)
        check_evidence(p, contract, stage, err)
        check_visuals(p, contract, stage, err)
        check_imagery(p, contract, stage, err)
        check_source_writes(p, contract, hat, err)
        check_store_writes(p, contract, hat, err)
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

    # write scope: product_writes resolve under product_root on their real path (symlinks, `..`)
    writes = [str(w) for w in p.get("product_writes") or []]
    prod_real = _real(pr) if pr and os.path.isabs(pr) else None
    for w in writes:
        target = _real(w if os.path.isabs(w) or not pr else os.path.join(pr, w))
        inside = prod_real is not None and _within(target, prod_real)
        rel = target.relative_to(prod_real).as_posix() if inside else w.replace("\\", "/")
        if os.path.basename(rel) in MANAGER_ONLY:
            err("LOGWRITE", f"{rel} is written by the manager only; hats return delta rows")
        elif hat in FRESH:
            err("FRESHWRITE", f"{hat} is a fresh-context judge and must not have product_writes ({rel})")
        elif not inside or rel not in OWNERS.get(hat, set()):
            err("UNOWNED", f"{hat} does not own {rel} (owners: workflow/registry.json) — raise an open question to the owner instead")
    for d in p.get("deliverable_paths") or []:
        if os.path.basename(str(d)) in MANAGER_ONLY:
            err("LOGWRITE", f"deliverable_paths names {d}, which only the manager writes")
    if hat in FRESH and str(p.get("memory_file", "")).strip() not in ("", "none", "empty"):
        err("FRESHWRITE", f"{hat} must not have a memory_file")
    check_memory_file(p, hat, scope, err)

    # success checks use stage ids
    for chk in p.get("success_checks") or []:
        m = re.search(r"--hat\s+([A-Za-z-]+)", str(chk))
        if m and m.group(1) not in STAGES:
            err("HATARG", f"success_checks uses --hat {m.group(1)}: pass the stage id, never the spawn role")
        elif m and m.group(1) != stage:
            err("GATESTAGE", f"packet stage {stage} cannot use --hat {m.group(1)}")
        elif m and contract.get("partial_stage"):
            err("EARLYGATE", f"{hat}/{stage}/{p.get('task')} uses workflow.py check-task; run the stage gate only after all participating tasks finish")
    forbidden = " ".join(str(x) for x in p.get("forbidden") or [])
    if "spawn further subagents" not in forbidden:
        warn("FORBIDDEN", "forbidden should include 'Do not spawn further subagents (host depth 1).'")

    demanded = set(str(x) for x in p.get("evidence_required") or [])
    for ev in contract.get("evidence", []):
        if isinstance(ev, str):
            demanded.add(ev)
        elif ev.get("when") != "ui" or _ui_feature(p):
            demanded.add(ev["kind"])
    # Explicit scope omissions are allowed for evidence not applicable to this task.
    categories = {"web": r"web|brows|internet|联网|上网|搜索|来源|出处|URL|网址|链接",
                  "screenshots": r"screenshot|截图", "e2e": r"E2E",
                  "running_app": r"app|source|code|源码|启动"}
    # waivers anywhere in the packet text
    for n, line in enumerate(block.splitlines(), 1):
        for pat in WAIVERS:
            if re.search(pat, line, re.I) and any(re.search(categories.get(k, r"(?!)"), line, re.I) for k in demanded):
                err("WAIVER", f"line {n} waives evidence: {line.strip()[:140]} — scale the deliverable, never the evidence")
                break
    return {"errors": errors, "warnings": warns, "packet": {"hat": hat, "stage": stage}}


# ----------------------------------------------------------------------------- self-test
def self_test() -> int:
    def legacy_lint(text):
        return lint(text, enforce_protocol=False)

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
        pm_reads = resolve_task(REGISTRY, 'pm', 'define', 'spec').get('reads', [])
        for rel in pm_reads:
            method = Path(plugin) / rel
            method.parent.mkdir(parents=True, exist_ok=True)
            method.write_text('Method fixture for authority validation\n')

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
                      *[f"  - {{path: {plugin}/{rel}, required: true}}" for rel in pm_reads],
                      "explore_roots:", f"  - {proj}/backend",
                      "deliverable_paths:", "  - 01-define/spec.md",
                      "forbidden:", "  - Do not spawn further subagents (host depth 1).",
                      "success_checks:", f"  - bash {plugin}/scripts/check-sdlc.sh --require --hat define {feat}",
                      f"  - python3 {plugin}/scripts/workflow.py check-task --role {fields['hat']} --stage {fields['stage']} --task {fields['task']} --root {feat}",
                      "return: output paths + summary"]
            return "\n".join(lines) + "\n"

        good = legacy_lint(packet())
        if good["errors"]:
            return fail("a valid packet must pass", good["errors"])
        # A nested mapping used to read as an empty list; a repeated field used to win silently (plan §1.2).
        for extra in ("evidence_inputs:\n  build_revision: git:abc\n  verification_records: [run.json]\n",
                      "lane: L3\n", "memory_file: x\n  - stray\n", "inputs:\n- orphan\n"):
            parsed = legacy_lint(packet() + extra)
            if "PARSE" not in {e["code"] for e in parsed["errors"]}:
                return fail("unsupported v2 syntax must be a PARSE error", extra, parsed["errors"])
        if legacy_lint(packet() + "Notes for the manager, not packet fields.\n  - a markdown bullet\n")["errors"]:
            return fail("trailing prose after an unfenced packet is not a packet field")
        if "PARSE" not in {e["code"] for e in legacy_lint(packet() + "Stray text.\nlane: L3\n")["errors"]}:
            return fail("a field after non-packet text must be a PARSE error")
        bad_text = packet().replace(f"  - {{path: {brief}, required: true}}",
                                    f"  - {{path: {brief}, required: true}}\n  - {{path: {proj}/backend/api, required: false}}")
        bad_text = bad_text.replace("  - 01-define/spec.md", "  - 01-define/spec.md\n  - 冒烟规模约定：这是 smoke run，不需要 WebSearch/WebFetch")
        bad_text = bad_text.replace(f"  - {prod}/feature-map.md\ninputs:", f"  - {prod}/feature-map.md\n  - {prod}/CHANGELOG.md\ninputs:")
        bad_text = bad_text.replace("--hat define", "--hat pm")
        codes = {e["code"] for e in legacy_lint(bad_text)["errors"]}
        if not {"DIRINPUT", "LOGWRITE", "HATARG"} <= codes:
            return fail("dir input, waiver, log write and role --hat must all be errors", codes)
        codes = {e["code"] for e in legacy_lint(packet(hat="designer", subagent_type="sdlc-workflow:designer", primary_skill="sdlc-workflow:design-contract"))["errors"]}
        if "UNOWNED" not in codes:
            return fail("designer writing strategy.md must be UNOWNED", codes)
        rv = packet(hat="reviewer", subagent_type="sdlc-workflow:reviewer", primary_skill="sdlc-workflow:findings", stage="review")
        codes = {e["code"] for e in legacy_lint(rv)["errors"]}
        if "FRESHWRITE" not in codes:
            return fail("reviewer with product_writes / memory must be FRESHWRITE", codes)
        text = packet().replace(f"  - {prod}/strategy.md\n  - {prod}/feature-map.md\nproduct_writes:",
                                f"  - {prod}/strategy.md\n  - {prod}/missing.md\nproduct_writes:")
        if "MISSING-FILE" not in {e["code"] for e in legacy_lint(text)["errors"]}:
            return fail("a missing product_context file must be an error")
        text = packet().replace("return: output paths + summary",
                                                      "return: output paths + summary\nnotes: 本机无运行 UI 时按 packet 约定走源码考古")
        if "WAIVER" not in {e["code"] for e in legacy_lint(text + "\nevidence_required: [web, running_app]\n")["errors"]}:
            return fail("'走源码考古' must be a waiver")
        with open(os.path.join(prod, "big.md"), "w") as f:
            f.write("x" * 450_000)
        text = packet().replace(f"  - {prod}/feature-map.md\nproduct_writes:", f"  - {prod}/feature-map.md\n  - {prod}/big.md\nproduct_writes:")
        if "BUDGET" not in {e["code"] for e in legacy_lint(text)["errors"]}:
            return fail("an oversized product_context must be BUDGET")
        # N04: a deliverable outside the feature directory is an unauthorised write
        text = packet().replace("  - 01-define/spec.md", "  - 01-define/spec.md\n  - /etc/hosts")
        if "DELIVERABLE-SCOPE" not in {e["code"] for e in legacy_lint(text)["errors"]}:
            return fail("an absolute deliverable outside feature_dir must be DELIVERABLE-SCOPE")
        # N05: a check-task for another task, or no check-task at all
        text = packet().replace("--role pm --stage define --task spec", "--role designer --stage designer --task explore")
        if "CHECKMISMATCH" not in {e["code"] for e in legacy_lint(text)["errors"]}:
            return fail("a check-task for another task must be CHECKMISMATCH")
        text = "\n".join(l for l in packet().splitlines() if "check-task" not in l) + "\n"
        if "MISSING-CHECK" not in {e["code"] for e in legacy_lint(text)["errors"]}:
            return fail("a packet without this task's check-task must be MISSING-CHECK")
        # N06: evidence the registry requires cannot be dropped, however the waiver is worded
        os.makedirs(os.path.join(plugin, "skills", "market"), exist_ok=True)
        open(os.path.join(plugin, "skills", "market", "SKILL.md"), "w").close()
        open(os.path.join(plugin, "agents", "researcher.md"), "w").close()
        rs = packet(hat="researcher", stage="market", task="survey", subagent_type="sdlc-workflow:researcher",
                    primary_skill="sdlc-workflow:market").replace("  - 01-define/spec.md", "  - 00-discover/market.md")
        rs = rs.replace(f"  - {prod}/strategy.md\n  - {prod}/feature-map.md\ninputs:", "inputs:")
        codes = {e["code"] for e in legacy_lint(rs + "notes: 这轮 WebSearch 非必需\n")["errors"]}
        if "EVIDENCE" in codes:
            return fail("internal research must not require web evidence", codes)
        codes = {e["code"] for e in legacy_lint(rs.replace("forbidden:", "evidence_required:\n  - web\nforbidden:"))["errors"]}
        if "EVIDENCE" in codes:
            return fail("evidence_required listing web must satisfy the research contract", codes)
        if legacy_lint("no packet here")["errors"][0]["code"] != "NO-PACKET":
            return fail("text without a packet must be NO-PACKET")
    print("self-test ok")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint a registered v2 or sealed v3 packet (read-only).")
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
