#!/usr/bin/env python3
"""Plugin health gate. Exit code = violation count. Warnings print but do not fail."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from workflow import load_registry, validate_registry, generated_files
import vendorlib

RED, YEL, GRN, NC = "\033[0;31m", "\033[0;33m", "\033[0;32m", "\033[0m"


def _vendor_tree(root: str) -> tuple[str, dict[str, str]]:
    return vendorlib.tree(root)


def check_vendor(root: str, err, warn, ok) -> None:
    """vendor/ 只收纳上游原件（不进 git，按锁文件由 plugin-updater 或 vendor/install.sh 下载）；插件通过引用使用，不复制、不手改。"""
    if os.path.isdir(os.path.join(root, "references")):
        err("VENDOR", "根目录 references/ 已退役：上游原件在 vendor/，由 plugin-updater 收纳（不要再手工拷入）")
    vroot = os.path.join(root, "vendor")
    if not os.path.isdir(vroot):
        warn("VENDOR", "vendor/ 不存在：运行 plugin-updater 的 update-plugins.sh 收纳上游原件")
        return
    locks = [os.path.join(vroot, f) for f in sorted(os.listdir(vroot)) if f.endswith(".lock.json")]
    if not os.path.isfile(os.path.join(vroot, "install.sh")):
        err("VENDOR", "vendor/install.sh 缺失：使用者无法按锁文件下载上游原件")
    texts = {}
    for sub in ("skills", "agents", "commands", "workflow"):
        for dp, _dn, fn in os.walk(os.path.join(root, sub)):
            for f in fn:
                if f.endswith((".md", ".json")):
                    p = os.path.join(dp, f)
                    texts[os.path.relpath(p, root)] = open(p, encoding="utf-8", errors="replace").read()
    copies = {}
    for rel, _ in texts.items():
        p = os.path.join(root, rel)
        if os.path.getsize(p) > 200:
            copies.setdefault(hashlib.sha256(open(p, "rb").read()).hexdigest(), []).append(rel)
    n_files = 0
    for lk in locks:
        try:
            lock = json.load(open(lk, encoding="utf-8"))
        except (OSError, ValueError):
            err("VENDOR", f"{os.path.relpath(lk, root)} 无法解析")
            continue
        target = lk[: -len(".lock.json")]
        vrel = os.path.relpath(target, root).replace(os.sep, "/")
        restricted = (lock.get("license") or "unknown") not in vendorlib.FREE_LICENSES
        runtime = [f["path"] for f in lock.get("files", []) if f.get("purpose") == "runtime"]
        if restricted and runtime:
            err("VENDOR", f"{vrel} 许可证为「{lock.get('license')}」，使用者默认不下载，不能有 runtime 文件: {', '.join(runtime[:3])}")
        if not os.path.isdir(target):
            (warn if restricted or not runtime else err)(
                "VENDOR", f"{vrel} 未安装：运行 bash vendor/install.sh {os.path.basename(vrel)}"
                + ("（许可证受限，需 --accept-restricted）" if restricted else ""))
            continue
        digest, files = _vendor_tree(target)
        if digest != lock.get("tree_digest"):
            recorded = {f["path"]: f["sha256"] for f in lock.get("files", [])}
            changed = sorted(p for p in set(recorded) | set(files) if recorded.get(p) != files.get(p))
            err("VENDOR", f"{vrel} 与锁文件不一致（被本地改动？）: {', '.join(changed[:8])}")
        for f in lock.get("files", []):
            n_files += 1
            ref = f"{vrel}/{f['path']}"
            users = [r for r, t in texts.items() if ref in t]
            if f.get("purpose") == "runtime" and not users:
                err("VENDOR", f"{ref} 标为 runtime，但没有任何技能/角色/registry 引用它")
            elif f.get("purpose") != "runtime" and users:
                err("VENDOR", f"{ref} 是维护者参考（maintainer），不得进入技能/角色/registry: {', '.join(users[:3])}")
            dup = [r for r in copies.get(f["sha256"], [])]
            if dup:
                err("VENDOR", f"{ref} 在插件内存在逐字节副本: {', '.join(dup[:3])}（改为引用 vendor 原件）")
    try:
        st = subprocess.run(["git", "-C", root, "status", "--porcelain", "--", "vendor"], capture_output=True, text=True, timeout=10)
        if st.returncode == 0 and st.stdout.strip():
            warn("VENDOR", "vendor/ 的锁文件或安装脚本有未提交的变化（plugin-updater 更新锁文件后由维护者提交）: "
                 + ", ".join(l[3:] for l in st.stdout.splitlines())[:200])
    except (OSError, subprocess.SubprocessError):
        pass
    ok(f"vendor 来源 {len(locks)} 个、{n_files} 个文件与锁文件一致，引用规则通过" if locks else "vendor 无来源")


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    V = 0
    warns: list[str] = []
    errs: list[str] = []

    def err(tag: str, msg: str) -> None:
        nonlocal V
        errs.append(f"{RED}✗ [{tag}]{NC} {msg}")
        V += 1

    def warn(tag: str, msg: str) -> None:
        warns.append(f"{YEL}⚠ [{tag}]{NC} {msg}")

    def ok(msg: str) -> None:
        print(f"{GRN}✓ {msg}{NC}")

    print("sdlc-workflow 健康检查")
    print("========================================")

    manifest = os.path.join(root, ".zcode-plugin", "plugin.json")
    if os.path.isfile(manifest):
        try:
            json.load(open(manifest, encoding="utf-8"))
            ok("plugin.json JSON 合法")
        except Exception:
            err("MANIFEST", "plugin.json JSON 解析失败")
    else:
        err("MANIFEST", ".zcode-plugin/plugin.json 不存在")

    if os.path.isfile(os.path.join(root, "commands", "sdlc.md")):
        ok("commands/sdlc.md 存在")
    else:
        err("COMMAND", "commands/sdlc.md 缺失（ZCode 工作流入口）")
    if os.path.isfile(os.path.join(root, "commands", "sdlc-review.md")):
        ok("commands/sdlc-review.md 存在")
    else:
        err("COMMAND", "commands/sdlc-review.md 缺失（独立 G-fresh 入口）")
    if os.path.isfile(os.path.join(root, "commands", "sdlc-discover.md")):
        ok("commands/sdlc-discover.md 存在")
    else:
        err("COMMAND", "commands/sdlc-discover.md 缺失（发现带 HITL 入口）")
    if os.path.isfile(os.path.join(root, "commands", "sdlc-research.md")):
        ok("commands/sdlc-research.md 存在")
    else:
        err("COMMAND", "commands/sdlc-research.md 缺失（AFK 调研入口）")
    if os.path.isfile(os.path.join(root, "commands", "sdlc-eval.md")):
        ok("commands/sdlc-eval.md 存在")
    else:
        err("COMMAND", "commands/sdlc-eval.md 缺失（人触发评测入口）")
    try:
        registry = load_registry(root)
        for problem in validate_registry(registry, root):
            err("CONTRACT", problem)
        for relative, expected in generated_files(registry):
            from pathlib import Path
            path = Path(root) / relative
            if not path.is_file() or path.read_text() != expected:
                err("CONTRACT", f"{relative}: generated drift; run scripts/workflow.py render")
    except (OSError, ValueError, KeyError, TypeError) as error:
        err("CONTRACT", str(error))
        registry = {"roles": {}}

    def fm(text: str) -> str:
        m = re.match(r"^---\n(.*?)\n---", text, re.S)
        return m.group(1) if m else ""

    def fm_field(front: str, key: str) -> str:
        m = re.search(rf"^{re.escape(key)}:\s*(.*?)(?:\n[A-Za-z][\w-]*:|\Z)", front, re.S | re.M)
        if not m:
            return ""
        val = m.group(1).strip().strip('"').strip("'")
        if val[:1] in ">|":
            val = val[1:].strip()
        return val

    skills_dir = os.path.join(root, "skills")
    excerpt_total = 0
    name_total = 0
    # ZCode shouldWalkSkillDirectoryEntry (zcode.cjs OFe): folder names skipped
    # like node_modules. A skill directory named coverage is never discovered.
    HOST_WALK_SKIP = {
        "node_modules", "dist", "build", "out", "target", "vendor",
        "coverage", ".cache", ".next", ".turbo", ".venv", "__pycache__",
    }
    for name in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, name)
        sk = os.path.join(d, "SKILL.md")
        if not os.path.isdir(d) or not os.path.isfile(sk):
            continue
        if name in HOST_WALK_SKIP:
            err(
                "SKILL",
                f"skills/{name}/ 目录名在 ZCode shouldWalkSkillDirectoryEntry 跳过集合里，"
                "discoverSkills 不会收录（v3.20.4：coverage → coverage-matrix）",
            )
        text = open(sk, encoding="utf-8").read()
        front = fm(text)
        fm_name = fm_field(front, "name")
        if fm_name and fm_name != name:
            err("SKILL", f"{name}: frontmatter name {fm_name!r} ≠ directory")
        desc = fm_field(front, "description")
        if not desc:
            err("DESC", f"{name}: frontmatter description 缺失（质量要求：空描述仍会被 discoverSkills 收录，但永不触发；运行时只 drop 缺 name 或 length>1024）")
        elif len(desc) > 1024:
            err("DESC", f"{name}: description {len(desc)} > 1024")
        elif len(desc) < 50:
            warn("DESC", f"{name}: description 过短（{len(desc)}）")
        if desc and not re.search(r"Use this skill|Use when|/sdlc", desc, re.I):
            err("DESC", f"{name}: description 缺触发语（Use this skill when / Use when）")
        if desc and not re.search(r"Do NOT", desc, re.I):
            warn("DESC", f"{name}: description 缺 Do NOT 排除项")
        SATELLITES = {
            "sdlc-eval", "signals", "schema", "design-contract", "release-gate",
            "deliver", "retro", "warehouse", "collect", "growth",
            "debug", "tdd", "refactor", "cicd",
            "market", "compete", "prototype", "enablement",
        }
        if name in SATELLITES and desc and not re.match(
            r"Use this skill when (the user says /sdlc-eval|the spawn packet)", desc
        ):
            warn("DESC", f"{name}: 卫星 skill description 应以 spawn-packet/hat 触发语开头（前 250 字不放领域名词，PR10）")
        wtu = fm_field(front, "when_to_use")
        if not wtu:
            warn("WTU", f"{name}: 缺 when_to_use（字段保留作前向兼容；当前 build asar 0 命中该键，host 不读。触发面 = name + description，上限 1024）")
        elif "Do NOT" not in wtu:
            warn("WTU", f"{name}: when_to_use 缺 Do NOT（前向兼容；当前 host 不读该键）")

        lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        if desc:
            # ZCode 每轮注入 name + description 前 250 字；预算门防 PR4/PR10 静默回胀
            excerpt_total += min(len(desc), 250)
            name_total += len(name)
        if lines > 500:
            err("SIZE", f"{name}: SKILL.md {lines} 行（>500）")
        if (len(text) // 4) > 5000:
            err("SIZE", f"{name}: SKILL.md ~{len(text)//4} tokens（>5000）")
        if not re.search(r"gotcha|footgun|踩坑|陷阱", text, re.I):
            if name == "sdlc" and "orchestrator-gates.md" in text:
                pass  # F17: 编排 skill 的 Gotchas 下沉到 references/orchestrator-gates.md
            else:
                err("GOTCHA", f"{name}: SKILL.md 缺 Gotchas")
        slash_roles = re.findall(
            r'(?<![\w./])/(?:pm|dba|qa|ops|miner|algo|architect|backend|frontend|designer|sre|qc|reviewer|analyst|data-collector|data-warehouse-engineer|prd-gwt|schema|coverage-matrix|coverage|findings|release-gate|impl-evidence|architecture|design-contract|signals|deliver|retro|warehouse|collect)(?![\w-])',
            text,
        )
        if slash_roles:
            warn("SLASH", f"{name}: 角色引用带前导 /（{', '.join(sorted(set(slash_roles)))}）；skill 按 name 调用，仅 /sdlc 是 command")

        ev = os.path.join(d, "evals", "evals.json")
        if not os.path.isfile(ev):
            err("EVALS", f"{name}: 缺 evals/evals.json")
        else:
            try:
                data = json.load(open(ev, encoding="utf-8"))
            except Exception:
                err("EVALS", f"{name}: evals.json 无法解析")
                data = {}
            cases = data.get("evals") or []
            if not isinstance(cases, list):
                err("EVALS", f"{name}: evals 不是数组")
                cases = []
            n = len(cases)
            if n < 2:
                warn("EVALS", f"{name}: evals 仅 {n} 个（建议 ≥2）")
            for i, case in enumerate(cases, 1):
                if not isinstance(case, dict):
                    err("EVALS", f"{name}: evals[{i}] 不是对象")
                    continue
                if not (case.get("prompt") or "").strip():
                    err("EVALS", f"{name}: evals[{i}] 缺 prompt")
                if not (case.get("expected_output") or case.get("expectations")):
                    err("EVALS", f"{name}: evals[{i}] 缺 expected_output/expectations（质量证明文档，不是 runner）")
                rub = case.get("rubric")
                if rub is not None:
                    if not isinstance(rub, list) or not rub:
                        err("RUBRIC", f"{name}: evals[{i}] rubric 须为非空数组")
                    else:
                        rids = [r.get("id") for r in rub if isinstance(r, dict)]
                        if len(rids) != len(rub) or len(set(rids)) != len(rids) or not all(rids):
                            err("RUBRIC", f"{name}: evals[{i}] rubric 每项须有唯一 id")
                        for r in rub:
                            if isinstance(r, dict) and (not r.get("criterion") or not isinstance(r.get("weight", 1), (int, float)) or r.get("weight", 1) <= 0):
                                err("RUBRIC", f"{name}: evals[{i}] rubric {r.get('id')} 须有 criterion 且 weight > 0")

        routed_refs = set(re.findall(r"references/([A-Za-z0-9_.-]+\.md)", text))
        disk_refs = set()
        rd = os.path.join(d, "references")
        if os.path.isdir(rd):
            disk_refs = {f for f in os.listdir(rd) if f.endswith(".md")}
        for f in sorted(routed_refs - disk_refs):
            err("REF", f"{name}: 引用 references/{f} 但不存在")
        for f in sorted(disk_refs - routed_refs):
            if f.endswith("-pitfalls.md"):
                continue
            err("REF", f"{name}: 孤儿 references/{f}（SKILL.md 未路由）")

        routed_tpl = set(re.findall(r"templates/([A-Za-z0-9_.-]+)", text))
        disk_tpl: set[str] = set()
        td = os.path.join(d, "templates")
        if os.path.isdir(td):
            for _dirpath, _dirnames, files in os.walk(td):
                for f in files:
                    if not f.startswith("."):
                        disk_tpl.add(f)
        for f in sorted(disk_tpl - routed_tpl):
            if name == "sdlc" and f == "README.md" and ("templates/m" in text or "m/README" in text):
                continue
            err("TPL", f"{name}: 孤儿 templates/{f}（SKILL.md 未路由）")

    sdlc_path = os.path.join(skills_dir, "sdlc", "SKILL.md")
    sdlc = open(sdlc_path, encoding="utf-8").read() if os.path.isfile(sdlc_path) else ""
    if "sdlc-workflow:<role>" not in sdlc:
        err("DISPATCH", "skills/sdlc/SKILL.md 未把 sdlc-workflow:<role> 作为唯一 spawn type（ZCode 原生执行 plugin agents）")
    if "check-sdlc.sh" in sdlc and "--require" not in sdlc:
        err("DISPATCH", "skills/sdlc/SKILL.md 帽子后 G-script 须 check-sdlc.sh --require（默认 skip≠pass）")
    if re.search(r"does not execute plugin|not executed on ZCode|Recorded but not executed", sdlc, re.I):
        err("DISPATCH", "skills/sdlc/SKILL.md 仍断言 plugin agents 不执行（与 host/实测相反）")
    if re.search(r"Methodology is preloaded|skills:` preload|skills: preload", sdlc, re.I):
        err("DISPATCH", "skills/sdlc/SKILL.md 仍断言 skills: 预加载（应写 Skill 工具 + Read 回退）")
    if "sdlc-workflow:" not in sdlc or "Skill" not in sdlc:
        err("DISPATCH", "skills/sdlc/SKILL.md 须写明帽子 invoke 限定名 sdlc-workflow:<role>（Skill 工具）")
    if not re.search(r"agents as tools|manager", sdlc, re.I):
        err("DISPATCH", "skills/sdlc/SKILL.md 须写明本窗口是经理（OpenAI agents-as-tools），禁止 handoff")
    if re.search(r"\bhandoff\b", sdlc, re.I) is None:
        err("DISPATCH", "skills/sdlc/SKILL.md 须明确禁止 handoff（子代理不得接管面向用户的回复）")
    if "skills/coverage-matrix/scripts/check-matrix.py" not in sdlc:
        err("DISPATCH", "skills/sdlc/SKILL.md qc 脚本路径须为 skills/coverage-matrix/scripts/check-matrix.py")
    if "prd-gwt" not in sdlc:
        err("DISPATCH", "skills/sdlc/SKILL.md 须把做法池（prd-gwt 等）与帽子名分开")

    ad = os.path.join(root, "agents")
    renderer = os.path.join(root, "scripts", "render-role-agents.py")
    if os.path.isfile(renderer):
        import subprocess

        drift = subprocess.run(
            [sys.executable, renderer, "--check"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if drift.returncode:
            err("AGENT", "agents/*.md 与 profiles/_lib 漂移（编译期引入失同步）。改源文件后跑 python3 scripts/render-role-agents.py")
            for line in (drift.stdout or drift.stderr or "").splitlines():
                if line.strip():
                    err("AGENT", line.strip())
        else:
            ok("agents/*.md 与 profiles/_lib 一致（编译期引入）")
    lib = os.path.join(ad, "_lib")
    for lib_name in (
        "LOOP.md",
        "TOOLS.md",
        "SKILLS.md",
        "SKILLS-reviewer.md",
        "MEMORY-writer.md",
        "MEMORY-reviewer.md",
        "CONTRACT.md",
    ):
        if not os.path.isfile(os.path.join(lib, lib_name)):
            err("AGENT", f"agents/_lib/{lib_name} 缺失（共享 prompt 源）")
    AGENT_PROC = {name: role["skill"] for name, role in registry["roles"].items()}
    ALIASES = {"pm": "prd-gwt", "dba": "schema", "qa": "coverage-matrix"}
    ORCH = {"sdlc", "sdlc-eval", "discover"}
    NO_HAT_PROCS = {"debug", "tdd", "refactor", "cicd", "falsify", "prototype"}
    SECOND_HAT_PROCS = {"enablement"}  # ops 第二做法（教/开/告），主做法仍是 signals
    skill_dirs = {
        n for n in os.listdir(skills_dir)
        if os.path.isdir(os.path.join(skills_dir, n)) and os.path.isfile(os.path.join(skills_dir, n, "SKILL.md"))
    }
    agent_roles = {
        os.path.splitext(f)[0]
        for f in os.listdir(ad)
        if f.endswith(".md") and f != "README.md"
    } if os.path.isdir(ad) else set()
    for role, proc in AGENT_PROC.items():
        if role not in agent_roles:
            err("AGENT", f"agents/{role}.md 缺失")
        if proc not in skill_dirs:
            err("AGENT", f"hats {role} 的做法 skill skills/{proc}/ 缺失")
    for extra in sorted(agent_roles - set(AGENT_PROC)):
        warn("AGENT", f"agents/{extra}.md 不在 AGENT_PROC 表")
    import datetime as _dt
    _alias_deadline = _dt.date(2026, 10, 9)
    _today = _dt.date.today()
    for alias, target in ALIASES.items():
        ap = os.path.join(skills_dir, alias, "SKILL.md")
        if not os.path.isfile(ap):
            if _today >= _alias_deadline:
                ok(f"${alias} 已按期删除（PR4b）")
            else:
                ok(f"${alias} 已提前删除（PR4b 加速于 7A 补齐；主入口 ${target}）")
        elif _today >= _alias_deadline:
            err("ALIAS", f"skills/{alias}/ 逾期未删（2026-10-09 后不得存在；主入口 ${target}）")
        else:
            at = open(ap, encoding="utf-8").read()
            if f"sdlc-workflow:{target}" not in at:
                err("ALIAS", f"skills/{alias}/SKILL.md 须跳转到 sdlc-workflow:{target}")
            if at.count("\n") > 40:
                warn("ALIAS", f"skills/{alias}/SKILL.md 过长（薄跳转应 <40 行）")
            warn("ALIAS", f"${alias} deprecated，删除期限 2026-10-09（主入口 ${target}）")
    for name in sorted(skill_dirs - ORCH - set(ALIASES) - set(AGENT_PROC.values()) - NO_HAT_PROCS - SECOND_HAT_PROCS):
        warn("SKILL", f"skills/{name}/ 不在做法池/别名/编排器/同伴做法表")

    # 发现面预算：excerpt 截断到 250（ZCode 注入形态），超固定预算会退化成只剩名字
    budget = excerpt_total + name_total
    if budget > 4200:
        err("BUDGET", f"skill metadata 预算超限：excerpt(capped 250)+names = {budget}（>4200；宿主固定预算会退化成只剩名字）")
    elif budget > 3500:
        warn("BUDGET", f"skill metadata 偏高：excerpt(capped 250)+names = {budget}（warn>3500 / error>4200）")
    else:
        ok(f"skill metadata 预算 {budget}/4200（excerpt capped 250 + names）")

    for f in sorted(agent_roles):
        path = os.path.join(ad, f + ".md")
        text = open(path, encoding="utf-8").read()
        front = fm(text)
        if not front:
            err("AGENT", f"agents/{f}.md 缺 YAML frontmatter")
            continue
        if not fm_field(front, "name"):
            err("AGENT", f"agents/{f}.md 缺 name")
        desc = fm_field(front, "description")
        if not desc:
            err("AGENT", f"agents/{f}.md 缺 description")
        elif not re.search(r"Use this agent|Do NOT", desc, re.I):
            warn("AGENT", f"agents/{f}.md description 缺触发/排除语")
        tools = fm_field(front, "tools")
        inherit_all = tools.strip() in ("*", "")
        proc = AGENT_PROC.get(f, f)
        if f in ("reviewer", "qc"):
            if inherit_all:
                err("AGENT", f"agents/{f}.md 审查角色不得 tools: *（会继承 Write/Bash）")
            if re.search(r"\bWrite\b", tools):
                err("AGENT", f"agents/{f}.md 审查角色不得声明 Write")
            if not re.search(r"\bSkill\b", tools, re.I):
                err("AGENT", f"agents/{f}.md 审查角色须显式列出 Skill（ZCode Skill 页：自定义名单无 Skill 则无法 invoke）")
            disallow = fm_field(front, "disallowedTools")
            if not re.search(r"\bWrite\b", disallow):
                err("AGENT", f"agents/{f}.md 审查角色须 disallowedTools 含 Write（Anthropic/ZCode 双闸）")
            if not fm_field(front, "maxTurns"):
                warn("AGENT", f"agents/{f}.md 审查角色建议 maxTurns（防 reviewer shopping）")
            if "skill allowlist" not in text and "Skills are a pool" not in text:
                warn("AGENT", f"agents/{f}.md 审查角色应写明：G-fresh=隔离，不是 skill 白名单")
            if f == "reviewer" and "Use proactively" in desc:
                warn("AGENT", "agents/reviewer.md 不应 Use proactively（仅 packet / 用户点名，与 qc 相同）")
            if f in ("reviewer", "qc") and re.search(r"do not self-select", text, re.I):
                warn("AGENT", f"agents/{f}.md 审查者不应写 do not self-select（做法池在 SKILLS-reviewer.md）")
        else:
            if inherit_all:
                err("AGENT", f"agents/{f}.md 写作者不得 tools: */省略（继承全部 MCP 与 Agent；四档 profile 用穷尽名单，PR8b 工厂 allowlist 才可升格）")
            if re.search(r"\bAgent\b", tools):
                err("AGENT", f"agents/{f}.md 写作者名单不得含 Agent（depth 1 不可 spawn，徒增 schema）")
            if not re.search(r"\bSkill\b", tools, re.I):
                err("AGENT", f"agents/{f}.md 写作者须列出 Skill（ZCode Skill 页：自定义名单无 Skill 则无法 invoke）")
        skills_field = fm_field(front, "skills")
        if skills_field:
            err("AGENT", f"agents/{f}.md 不得发射 skills:（ZCode 非空列表=FilteredSkillPort allowlist，挡伴生做法与 reviewer 池；省略该键）")
        if re.search(r"ZCode ignores the field|ZCode ignores skills:", text):
            err("AGENT", f"agents/{f}.md 仍断言 ZCode ignores skills:（2026-09-09 起宿主执行该字段为 allowlist）")
        if re.search(r"preloaded via|Methodology is preloaded", text, re.I):
            err("AGENT", f"agents/{f}.md 仍断言 skills: 预加载（应写 Skill 工具 + Read 回退）")
        if re.search(r"/Users/|~/\.zcode/local-plugins", text):
            err("AGENT", f"agents/{f}.md 硬编码本机路径")
        # Grok 1.0.13 plugin-agent frontmatter is deny-unknown (parse fail → skip).
        if re.search(r"^(prompt_mode|agents_md|permission_mode):", front, re.M):
            err("AGENT", f"agents/{f}.md 含 Grok 不认识的 snake_case 字段（prompt_mode/agents_md/permission_mode 会导致 skip；用 permissionMode）")
        if not fm_field(front, "permissionMode"):
            err("AGENT", f"agents/{f}.md 缺 permissionMode（Grok camelCase）")
        for sec in ("## SOUL", "## IDENTITY", "## Loop", "## Tools", "## Skills", "## Memory", "## Contract"):
            if sec not in text:
                err("AGENT", f"agents/{f}.md 缺 {sec}（Hermes 式 prompt stack；源文件在 profiles/_lib）")
        ident_src = os.path.join(ad, "profiles", f, "IDENTITY.md")
        soul_src = os.path.join(ad, "profiles", f, "SOUL.md")
        if not os.path.isfile(ident_src):
            err("AGENT", f"agents/profiles/{f}/IDENTITY.md 缺失（分身源文件）")
        if not os.path.isfile(soul_src):
            err("AGENT", f"agents/profiles/{f}/SOUL.md 缺失（SOUL 源文件）")
        if f"sdlc-workflow:{f}" not in text:
            err("AGENT", f"agents/{f}.md 正文未声明 spawn type sdlc-workflow:{f}")
        if f in ("reviewer", "qc"):
            if re.search(r"\bWrite\b", tools):
                err("AGENT", f"agents/{f}.md 审查角色不得拥有 Write")
            if f == "reviewer" and re.search(r"\bBash\b", tools):
                err("AGENT", f"agents/{f}.md 审查角色不得拥有 Bash（可绕过无 Write）")
            if "Do not Write" not in text and "不修改" not in text:
                warn("AGENT", f"agents/{f}.md 未在正文禁止写文件")
            if "<feature>/memory/" in text and "do **not** read" not in text.lower() and "do not read" not in text.lower():
                warn("AGENT", f"agents/{f}.md 审查角色不得把 producer memory 当输入")

    # 运营 ≠ 运维：spawn 名 ops 会被英文读成 SRE。身份和 description 必须把人/机器拆开。
    def _read_if(p: str) -> str:
        return open(p, encoding="utf-8").read() if os.path.isfile(p) else ""

    ops_id = _read_if(os.path.join(ad, "profiles", "ops", "IDENTITY.md"))
    sre_id = _read_if(os.path.join(ad, "profiles", "sre", "IDENTITY.md"))
    ops_ag = _read_if(os.path.join(ad, "ops.md"))
    sre_ag = _read_if(os.path.join(ad, "sre.md"))
    ops_desc = fm_field(fm(ops_ag), "description")
    sre_desc = fm_field(fm(sre_ag), "description")
    if not re.search(r"产品运营|product operations", ops_id, re.I):
        err("OPSRE", "agents/profiles/ops/IDENTITY.md 必须标明 产品运营 / product operations（ops ≠ 运维）")
    if re.search(r"^Title: operations specialist\s*$", ops_id, re.M):
        err("OPSRE", "ops IDENTITY Title 不得只写 operations specialist（英文会读成运维）")
    if not re.search(r"deploy|rollback|incident|SRE|运维", ops_id, re.I):
        err("OPSRE", "ops IDENTITY Refuse/Red 必须把 deploy/rollback/incident/sre 排除给运维")
    if not re.search(r"Do NOT use for.*\b(deploy|rollback|incident)", ops_desc, re.I):
        err("OPSRE", "agents/ops.md description 必须 Do NOT use for deploy/rollback/incidents（自动委派面）")
    if not re.search(r"产品运营|product operations", ops_desc, re.I):
        err("OPSRE", "agents/ops.md description 必须含 product operations / 产品运营")
    if not re.search(r"运维", sre_id):
        err("OPSRE", "agents/profiles/sre/IDENTITY.md 必须标明 运维")
    if not re.search(r"ops|产品运营|user-facing|release notes|signal", sre_id, re.I):
        err("OPSRE", "sre IDENTITY Refuse 必须把用户公告/信号归纳排除给产品运营 ops")
    if not re.search(r"Do NOT use for.*(user-facing|support|signal|产品运营)", sre_desc, re.I):
        err("OPSRE", "agents/sre.md description 必须 Do NOT use for user-facing copy / signals（ops）")
    # ops≠sre 防线在模型侧：上方 ops/sre 的 IDENTITY 与 description 断言 + 下方经理窗口必读 ops-vs-sre.md。README 是项目描述，不承载模型行为矫正。
    if not os.path.isfile(os.path.join(root, "skills", "sdlc", "references", "ops-vs-sre.md")):
        err("OPSRE", "skills/sdlc/references/ops-vs-sre.md 缺失（防会话把 ops 读成运维）")

    # v4：角色提示不得回流宿主管道说明；产品层与阶段表必须存在；截图脚本存在
    HOST_PLUMBING = ("FilteredSkillPort", "shouldWalkSkillDirectoryEntry", "RespondToCoordinator", "PR8b", "ZCode Subagents page")
    for f in sorted(agent_roles):
        body = open(os.path.join(ad, f + ".md"), encoding="utf-8").read()
        leaked = [w for w in HOST_PLUMBING if w in body]
        if leaked:
            err("PLUMBING", f"agents/{f}.md 含宿主管道说明（{', '.join(leaked)}）；移到 adapters/HOST-NOTES.md")
        ident = _read_if(os.path.join(ad, "profiles", f, "IDENTITY.md"))
        if "Excellent looks like" in ident or re.search(r"^Method:", ident, re.M):
            err("LAYER", f"agents/profiles/{f}/IDENTITY.md embeds procedure; move it to its skill")
        proc = AGENT_PROC.get(f)
        if proc and not os.path.isfile(os.path.join(skills_dir, proc, "references", "role-quality.md")):
            err("EXCELLENCE", f"{proc}: missing shared professional criteria")
    for ref in ("stage-map.md", "product-layer.md"):
        if not os.path.isfile(os.path.join(skills_dir, "sdlc", "references", ref)):
            err("V4", f"skills/sdlc/references/{ref} 缺失（v4 阶段表 / 产品层规则）")
    for script, why in (("ui-evidence.sh", "UI 截图取证"), ("check_config.py", "v4 配置检查 / 应用可达探测"), ("blind_eval.py", "盲评与真实回归"), ("check_packet.py", "spawn 包体检")):
        if not os.path.isfile(os.path.join(root, "scripts", script)):
            err("V4", f"scripts/{script} 缺失（{why}）")
    if not os.path.isfile(os.path.join(root, "commands", "sdlc-product.md")):
        err("COMMAND", "commands/sdlc-product.md 缺失（产品层构建入口）")
    extra_tools = os.path.join(root, "adapters", "extra-tools.json")
    if os.path.isfile(extra_tools):
        try:
            json.load(open(extra_tools, encoding="utf-8"))
        except Exception:
            err("AGENT", "adapters/extra-tools.json 无法解析")
    reg_dir = os.path.join(skills_dir, "sdlc-eval", "regressions")
    if os.path.isdir(reg_dir):
        for fn in sorted(os.listdir(reg_dir)):
            if not fn.endswith(".json"):
                continue
            try:
                rc = json.load(open(os.path.join(reg_dir, fn), encoding="utf-8"))
            except Exception:
                err("REGRESSION", f"regressions/{fn} 无法解析")
                continue
            for key in ("id", "skill", "hat", "stage", "task", "inputs", "baseline", "deliverables", "rubric"):
                if not rc.get(key):
                    err("REGRESSION", f"regressions/{fn} 缺 {key}")
            if rc.get("artifacts_ref") is not None and not re.fullmatch(r"[0-9a-f]{7,40}", str(rc["artifacts_ref"])):
                err("REGRESSION", f"regressions/{fn} artifacts_ref 须是提交 sha（7–40 位十六进制）")
            if not (rc.get("baseline_before") or rc.get("baseline_commit")):
                err("REGRESSION", f"regressions/{fn} 缺 baseline_before / baseline_commit（v2：回归必须在基线提交的快照里跑，不能在 HEAD 上跑）")
            if rc.get("skill") and rc["skill"] not in skill_dirs:
                err("REGRESSION", f"regressions/{fn} skill {rc['skill']} 不存在")
            if rc.get("hat") and rc["hat"] not in agent_roles:
                err("REGRESSION", f"regressions/{fn} hat {rc['hat']} 不存在")
            paths = list(rc.get("inputs") or []) + list(rc.get("exclude_paths") or []) + list(rc.get("hindsight_paths") or [])
            paths += list(rc.get("deliverables") or []) + ([rc["product_root"]] if rc.get("product_root") else [])
            for b in rc.get("baseline") or []:
                if isinstance(b, dict):
                    if not b.get("from"):
                        err("REGRESSION", f"regressions/{fn} baseline 条目缺 from")
                    paths += [b.get("from", ""), b.get("as", "")]
                else:
                    paths.append(b)
            for pth in paths:
                if str(pth).startswith("/") or str(pth).startswith("~") or ".." in str(pth).split("/"):
                    err("REGRESSION", f"regressions/{fn} 路径须相对项目根 / 交付根：{pth}")
            rubric_ids = [r.get("id") for r in rc.get("rubric") or [] if isinstance(r, dict)]
            if len(rubric_ids) != len(set(rubric_ids)) or not all(rubric_ids):
                err("REGRESSION", f"regressions/{fn} rubric id 缺失或重复")
    for f in ("growth", "ops", "sre"):
        if f not in agent_roles:
            err("OPSRE", f"agents/{f}.md 缺失（用户运营 / 增长运营 / 运维 三分）")

    for dirpath, _, files in os.walk(root):
        if "/.git/" in dirpath.replace("\\", "/"):
            continue
        for fn in files:
            path = os.path.join(dirpath, fn)
            if not (fn.endswith(".sh") or fn.endswith(".py")):
                continue
            try:
                body = open(path, encoding="utf-8").read()
            except Exception:
                continue
            if re.search(r"(password|secret|api_key)\s*=\s*['\"][^'\"]{8,}", body, re.I):
                err("SECURITY", f"{os.path.relpath(path, root)}: 疑似硬编码密钥")
            if re.search(r"^\s*eval\s", body, re.M):
                err("SECURITY", f"{os.path.relpath(path, root)}: 使用 eval")
            if fn.endswith(".sh"):
                head = "\n".join(body.splitlines()[:20])
                if "set -u" not in head:
                    warn("SCRIPT", f"{os.path.relpath(path, root)}: 前 20 行缺 set -u")

    for name in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, name)
        if os.path.isdir(d) and not os.path.isfile(os.path.join(d, "SKILL.md")):
            err("SKILL", f"skills/{name}/ 没有 SKILL.md：技能目录必须是一个技能（空壳目录删掉；上游原件放 vendor/）")
    check_vendor(root, err, warn, ok)

    for line in errs:
        print(line)
    for line in warns:
        print(line)
    print("----------------------------------------")
    if V == 0:
        ok("健康检查全部通过")
    else:
        print(f"{RED}共 {V} 处违规{NC}")
    return V


if __name__ == "__main__":
    sys.exit(main())
