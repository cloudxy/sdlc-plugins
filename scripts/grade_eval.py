#!/usr/bin/env python3
"""Mechanical grader for sdlc-eval workspaces. Does not call a model."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from typing import Any


def collect_text(outdir: str) -> str:
    if not os.path.isdir(outdir):
        return ""
    chunks: list[str] = []
    for root, _dirs, files in os.walk(outdir):
        for fn in sorted(files):
            if fn.startswith("."):
                continue
            path = os.path.join(root, fn)
            try:
                chunks.append(open(path, encoding="utf-8", errors="replace").read())
            except OSError:
                continue
    return "\n".join(chunks)


def _has(*needles: str, text: str) -> bool:
    low = text.lower()
    return any(n.lower() in low for n in needles)


_REFUSAL_RE = re.compile(
    r"(do not|don't|doesn't|does not|did not|will not|won't|never|refuse"
    r"|not:\s*|not —|not -|not the (outcome|user outcome)"
    r"|not (a |the )?(valid|sufficient|proof)"
    r"|no [\"'“]"
    r"|不应|不要|禁止|拒绝|不接受|不是证据|不算|并非|不是"
    r"|不写|未写|不产出|不生成|不交|未交|不 spawn)",
    re.I,
)


def _phrase_refused_somewhere(text: str, phrase: str) -> bool:
    """True if at least one mention of phrase sits next to refusal language."""
    low = text.lower()
    p = phrase.lower()
    start = 0
    while True:
        i = low.find(p, start)
        if i < 0:
            return False
        window = low[max(0, i - 160) : i + len(p) + 160]
        if _REFUSAL_RE.search(window):
            return True
        if re.search(
            rf"(?:not|不是|不得|不能|禁止|不写|未写)\s*{re.escape(p)}",
            window,
            re.I,
        ):
            return True
        # "no reviewer" / "without spec.md" — bare no/without, not only no "
        if re.search(rf"\b(?:no|without)\s+{re.escape(p)}\b", window, re.I):
            return True
        start = i + max(len(p), 1)


def _neutralize_contractions(s: str) -> str:
    """it's/don't/architect's: an apostrophe sandwiched between letters is a
    contraction, not a quote delimiter. Rewrite to ’ so quote extraction
    (`'([^']+)'`) cannot capture the span between two contractions as a
    'quoted phrase' (iteration-6 coverage-matrix-2: "…(it's lenient) … doesn't"
    yielded the phantom phrase "s lenient) but MySQL doesn")."""
    return re.sub(r"(?<=[A-Za-z])'(?=[A-Za-z])", "’", s)


def _quoted_in_text(q: str, text: str) -> bool:
    """Quoted-phrase hit. 'rejected' also matches rejection / 否决 (iteration-4 architecture-2)."""
    q = q.replace("’", "'")
    if q.lower() in text.replace("’", "'").lower():
        return True
    if q.lower() == "rejected" and _has("rejection", "reject", "否决", text=text):
        return True
    return False


def _strip_negative_examples(exp: str) -> str:
    """Drop parenthetical 'not just …' so grader does not require the bad example."""
    s = re.sub(r"\([^)]*\bnot just\b[^)]*\)", " ", exp, flags=re.I)
    s = re.sub(r"\([^)]*\bnot\s+'[^']+'[^)]*\)", " ", s, flags=re.I)
    return s


def check_expectation(text: str, exp: str) -> tuple[bool | None, str]:
    """True/False if mechanically decidable; None = too subjective to script."""
    e = exp.strip()
    el = e.lower()
    if not text.strip():
        return False, "outputs/ empty"

    if el.startswith("does not") or el.startswith("does not "):
        quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", _neutralize_contractions(e))
        phrases = [a or b for a, b in quoted]
        if "delivery date" in el or "交付" in e:
            # Mentioning the forbidden act in a refusal is not a commit
            # ("Delivery dates … architect's call", "never commit to a delivery date").
            if re.search(
                r"(never commit|do not commit|don't commit|architect['’]s call|appetite only|gives appetite|scheduling is)"
                r"|delivery dates? for anything",
                text,
                re.I,
            ):
                return True, "explicitly refuses delivery dates"
            hit = _has(
                "ship by",
                "due date",
                "deadline is",
                "交付日期",
                "上线日期",
                "deliver on",
                "ship on",
                text=text,
            ) or bool(re.search(r"delivery dates?\s*:", text, re.I))
            return (not hit), "no delivery-date commitment" if not hit else "found a date commitment"
        if "approve" in el:
            hit = _has("approved as-is", "prd is ready", "lgtm", "可以上线", "验收通过", text=text)
            # "not ready" / "not approve" is fine
            if re.search(r"\bnot (ready|approved)\b", text, re.I):
                return True, "rejects as-is"
            return (not hit) or _has("untestable", "not ready", "not approve", text=text), "approval language"
        if phrases:
            leftover = [p for p in phrases if _quoted_in_text(p, text) and not _phrase_refused_somewhere(text, p)]
            if leftover:
                return False, f"found {leftover[0]!r}"
            return True, "forbidden phrase absent or only in refusal"

    if "gwt" in el or "given/when/then" in el:
        has_gwt = bool(re.search(r"\b(given|when|then|gwt)\b", text, re.I))
        if "empty" in el or "no data" in el:
            return has_gwt and _has("empty", "no data", "zero row", "空", text=text), "GWT empty-result"
        if "unauthorized" in el or "viewer" in el:
            return has_gwt and _has("unauthorized", "unauthorised", "forbidden", "viewer", "权限", "未授权", text=text), "GWT unauthorized"
        if "error" in el:
            return has_gwt and _has("error", "fail", "timeout", "错误", text=text), "GWT error scenario"
        return has_gwt, "GWT present"

    if "instrument" in el or "export usage" in el:
        return _has("instrument", "export_clicked", "tracking", "telemetry", "埋点", "指标", text=text), "instrumentation"

    if "appetite" in el or "time budget" in el:
        return _has("appetite", "time budget", "时间预算", "appetite", text=text), "appetite"

    if "untestable" in el and ("correctly" in el or "friendly" in el):
        leftover = []
        for p in ("correctly", "friendly", "正确地", "友好的"):
            if p.lower() in text.lower() and not _phrase_refused_somewhere(text, p):
                leftover.append(p)
        return (not leftover), "no untestable leftover words" if not leftover else "untestable words present"

    if "6 states" in el or "empty/loading/error" in el:
        en = ["empty", "loading", "error", "boundary", "permission", "offline"]
        zh = ["空", "加载", "错误", "边界", "权限", "离线"]
        n_en = sum(1 for w in en if w in text.lower())
        n_zh = sum(1 for w in zh if w in text)
        ok = n_en >= 5 or n_zh >= 5 or (n_en + n_zh) >= 6
        return ok, "six states present" if ok else "six states missing"

    if "untestable" in el or "gracefully" in el:
        return _has("untestable", "不可测", "gracefully", "user experience", text=text), "flags untestable wording"

    if "rice" in el:
        return _has("rice", text=text), "RICE"

    if "confidence" in el and ("a " in el or el.startswith("confidence for a")):
        return _has("confidence", text=text) and _has(
            "low", "50%", "0.5", "speculative", "no data", "猜测", text=text
        ), "honest confidence on A"

    if "prioritized" in el or "200+" in el or "password" in el:
        return _has("password", "#4523", "4523", "200", text=text), "B/evidence"

    if "parity" in el or "competitor" in el or "automatic priority" in el:
        return _has("parity", "competitor", "竞品", "checkbox", "keep up", text=text), "C as parity"

    if "why" in el and ("qa" in el or "test" in el):
        return _has("qa", "test case", "无法", "can't", "cannot", "why", text=text), "explains why untestable"

    if "v1 is pm-only" in el or "states v1" in el or ("table" in el and "skill" in el):
        return _has(
            "prd-gwt", "table", "pm-only", "harness", "discover", "named skill", "14", "eight",
            text=text,
        ), "harness table scope"
    if "未量化" in e:
        return _has("未量化", "unquantified", "not quantified", "no number", "e1", text=text), "未量化"
    if re.search(r"\bE3\b", e) and (
        el.startswith("does not") or "not grade" in el or "operator" in el or "refuse" in el
    ):
        if re.search(
            r"(not\s+E3|E1\b.{0,40}E3|E3.{0,40}E1|不是\s*E3|不能.{0,12}E3|不得.{0,12}E3|≤E1|<=E1)",
            text,
            re.I,
        ):
            return True, "refuses E3 from operator/un-counted"
        if re.search(r"\bE3\b", text) and not _phrase_refused_somewhere(text, "E3"):
            return False, "claimed E3"
        return True, "no E3 claim"
    if "客服" in e or "第一次成功" in e:
        return _has("客服", "第一次成功", "first success", "cs q", "support q", text=text), "enablement structure"
    if "briefing" in el and ("compress" in el or "paste" in el or "链到" in e):
        paste = bool(re.search(r"(.{200,})", text)) and ("## Market" in text or "## Compete" in text)
        linked = _has("链到", "00-discover/market.md", "00-discover/compete.md", "link", "summary", text=text)
        if "does not paste" in el or "compress" in el:
            return linked or not paste, "briefing compress" if linked or not paste else "pasted survey into briefing"
    if "does not spawn 16" in el:
        spawned16 = bool(re.search(r"16 role|all 16|十六", text, re.I)) and not _has(
            "refuse", "will not", "do not spawn 16", "won't spawn", "拒绝", text=text
        )
        return (not spawned16) or _has("refuse", "拒绝", text=text), "refuses 16-role sweep"
    if "weekly" in el or "cron" in el or "health-check integration" in el:
        return _has("refuse", "not a gate", "non-deterministic", "拒绝", "不进", text=text), "refuses cron/health-check"
    if "root_cause" in el:
        return bool(re.search(r"root_cause\s*:", text, re.I)), "root_cause line"
    if "flaky" in el:
        return _has("flaky", "not fixed", "not a fix", "不稳定", "不是修复", text=text), "flaky not fixed"
    if "characterization" in el:
        return _has("characterization", "表征", text=text), "characterization"
    if "g-script" in el or (el.startswith("refuses") and "ci" in el):
        return _has("g-script", "g script", "not a new gate", "independent reviewer", "拒绝", "refuse", text=text), "CI is G-script"
    if "logic" in el and ("not ui" in el or "chooses" in el):
        return _has("logic", text=text), "LOGIC branch"
    if "fake" in el and ("chooses" in el or "not production" in el):
        return _has("fake", "waitlist", "pricing", "假门", text=text), "FAKE branch"
    if "red" in el and "green" in el:
        if "does not" in el[:24]:
            return check_generic(text, exp)
        return _has("red", "fail", "FAIL", text=text) and _has(
            "green", "pass", "PASS", "exit code 0", text=text
        ), "red then green"

    # ≤6 extra mechanical rules (v3.20): kill verdict, 亲爱的用户, Router layering
    if re.search(r"verdict is ['\"]?kill", el) or (
        "verdict" in el and "kill" in el and "does not" not in el[:24]
    ):
        return _has("kill", "killed", "杀死", text=text), "kill verdict"
    if "亲爱的用户" in e and (
        el.startswith("does not") or "not treat" in el or "deliverable of sre" in el
    ):
        if _phrase_refused_somewhere(text, "亲爱的用户") or _has(
            "ops", "enablement", "产品运营", "refuse", "拒绝", text=text
        ):
            return True, "亲爱的用户 refused or reassigned"
        if "亲爱的用户" in text:
            return False, "sre wrote 亲爱的用户"
        return True, "no 亲爱的用户 copy"
    if ("router" in el and ("service" in el or "orm" in el or "layer" in el)) or "分层" in e:
        return _has("router", "Router", text=text) and _has(
            "service", "Service", "repository", "orm", text=text
        ), "Router/Service layering"
    if "splits coordination" in el or ("协调" in e and "记录" in e):
        coord = _has("coordination", "hot path", "hot-path", "协调", text=text)
        rec = _has("history", "audit", "记录", "终态", "审计", text=text)
        return coord and rec, "split coordination/record"
    if "assumed" in el or "topology" in el or "[ASSUMED]" in e:
        return _has(
            "[ASSUMED]",
            "ASSUMED",
            "already deployed",
            "already part",
            "已有",
            "现网",
            "拓扑",
            text=text,
        ), "topology constraint or ASSUMED"

    return check_generic(text, exp)


def check_generic(text: str, exp: str) -> tuple[bool | None, str]:
    """Keyword / quoted-phrase fallback for non-pm expectations."""
    el = exp.lower()
    quoted = [a or b for a, b in re.findall(r"'([^']+)'|\"([^\"]+)\"", _neutralize_contractions(_strip_negative_examples(exp)))]
    deny = el.startswith("does not") or "does not " in el[:24]

    if quoted:
        if deny:
            leftover = [q for q in quoted if _quoted_in_text(q, text) and not _phrase_refused_somewhere(text, q)]
            if leftover:
                return False, f"found {leftover[0]!r}"
            return True, "forbidden quoted absent or only in refusal"
        missing = [q for q in quoted if not _quoted_in_text(q, text)]
        if missing:
            return False, f"missing {missing[0]!r}"
        return True, "quoted phrases present"

    needles: list[str] = []
    if "adr" in el:
        needles += ["adr", "decision", "alternatives"]
    if "rice" in el:
        needles += ["rice"]
    if "fr-" in el or "fr number" in el or "every fr" in el:
        needles += ["fr-"]
    if "expand-contract" in el or "expand/contract" in el:
        needles += ["expand", "contract"]
    if "ttl" in el:
        needles += ["ttl", "expire"]
    if "ods" in el or "dwd" in el or "4-layer" in el:
        needles += ["ods", "dwd"]
    if "metrics.yaml" in el:
        needles += ["metrics.yaml", "metric"]
    if "react-query" in el or "usequery" in el:
        needles += ["usequery", "react-query", "react query"]
    if "antd" in el:
        needles += ["antd", "table"]
    if "playwright" in el or "splash" in el or "js rendering" in el:
        needles += ["playwright", "splash", "javascript", "js render"]
    if "download_delay" in el or "rate limit" in el:
        needles += ["download_delay", "delay", "1s", "1 s", "rate"]
    if "content_hash" in el:
        needles += ["content_hash", "hash", "dedup"]
    if "soft block" in el or "captcha" in el:
        needles += ["captcha", "200"]
    if "data leakage" in el or "leakage" in el:
        needles += ["leak", "split"]
    if "time-based split" in el:
        needles += ["time", "split"]
    if "pr auc" in el or "lift" in el:
        needles += ["pr auc", "prauc", "lift", "precision"]
    if "rollback" in el and "first" in el:
        needles += ["rollback"]
    if "blameless" in el:
        needles += ["blameless", "postmortem", "post-mortem"]
    if "l0" in el:
        needles += ["l0"]
    if "sdlc-workflow:pm" in el or "qualified" in el:
        needles += ["sdlc-workflow:pm"]
    if "block" in el and ("decision" in el or "matrix" in el or "ship" in el):
        needles += ["block", "not approve", "cannot ship", "不通过", "阻塞"]
    if "hollow" in el:
        needles += ["hollow", "200", "status"]
    if "middleware" in el:
        needles += ["middleware"]
    if "edge state" in el or "6 states" in el:
        needles += ["empty", "loading", "error"]
    if "token" in el and "semantic" in el:
        needles += ["semantic", "token"]
    if "arm vs" in el or "x86" in el:
        needles += ["arm", "x86"]
    if "unique constraint" in el or "idempotency" in el:
        needles += ["unique", "idempot"]
    if "service layer" in el:
        needles += ["service"]
    if "router" in el and "orm" in el:
        needles += ["router"]
    if deny:
        return None, "no mechanical rule"
    if needles:
        ok = _has(*needles, text=text)
        return (ok, "keywords present" if ok else "keywords missing")

    return None, "no mechanical rule"


def grade_arm(outdir: str, expectations: list[str]) -> dict[str, Any]:
    text = collect_text(outdir)
    rows = []
    passed = 0
    failed = 0
    skipped = 0
    for exp in expectations:
        ok, why = check_expectation(text, exp)
        if ok is True:
            passed += 1
            status = "pass"
        elif ok is False:
            failed += 1
            status = "fail"
        else:
            skipped += 1
            status = "skip"
        rows.append({"text": exp, "passed": ok is True, "status": status, "evidence": why})
    return {
        "empty": not text.strip(),
        "chars": len(text),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "expectations": rows,
    }


def load_evals(plugin_root: str, skill: str) -> list[dict[str, Any]]:
    path = os.path.join(plugin_root, "skills", skill, "evals", "evals.json")
    data = json.load(open(path, encoding="utf-8"))
    cases = data.get("evals") or []
    if not isinstance(cases, list):
        raise SystemExit(f"evals.json: evals is not a list ({path})")
    return cases


def list_skills(plugin_root: str) -> list[str]:
    skills_dir = os.path.join(plugin_root, "skills")
    names = []
    for name in sorted(os.listdir(skills_dir)):
        if os.path.isfile(os.path.join(skills_dir, name, "evals", "evals.json")):
            names.append(name)
    return names


def grade_skill(plugin_root: str, itdir: str, skill: str, only_ids: list[str] | None = None) -> dict[str, Any]:
    cases = load_evals(plugin_root, skill)
    if only_ids:
        wanted = {str(x) for x in only_ids}
        cases = [c for c in cases if str(c.get("id")) in wanted]
    report: dict[str, Any] = {"skill": skill, "iteration_dir": itdir, "cases": []}
    listing = os.listdir(itdir) if os.path.isdir(itdir) else []
    for case in cases:
        cid = case.get("id")
        prefix = f"{skill}-{cid}"
        matches = [d for d in listing if d == prefix or d.startswith(prefix + "-")]
        cdir = os.path.join(itdir, matches[0]) if matches else os.path.join(itdir, prefix)
        exps = [str(x) for x in (case.get("expectations") or [])]
        arms = {}
        for arm in ("with_skill", "without_skill"):
            arms[arm] = grade_arm(os.path.join(cdir, arm, "outputs"), exps)
        report["cases"].append({"id": cid, "dir": cdir, "prompt": case.get("prompt"), "arms": arms})
    return report


def grade_iteration(plugin_root: str, workspace: str, iteration: str, skill: str, only_ids: list[str] | None = None) -> dict[str, Any]:
    itdir = os.path.join(workspace, f"iteration-{iteration}" if not str(iteration).startswith("iteration-") else str(iteration))
    if not os.path.isdir(itdir):
        itdir = os.path.join(workspace, str(iteration))
    if skill in ("all", "*"):
        combined: dict[str, Any] = {"skill": "all", "iteration_dir": itdir, "skills": [], "cases": []}
        for name in list_skills(plugin_root):
            one = grade_skill(plugin_root, itdir, name, only_ids)
            combined["skills"].append(name)
            for case in one["cases"]:
                case["skill"] = name
                combined["cases"].append(case)
        return combined
    return grade_skill(plugin_root, itdir, skill, only_ids)


def print_table(report: dict[str, Any]) -> int:
    failed_total = 0
    print(f"skill={report['skill']}  dir={report['iteration_dir']}")
    print(f"{'skill':<28} {'case':<6} {'arm':<16} {'pass':>4} {'fail':>4} {'skip':>4} {'chars':>6}")
    for case in report["cases"]:
        sk = str(case.get("skill") or report["skill"])
        for arm, g in case["arms"].items():
            print(
                f"{sk:<28} {str(case['id']):<6} {arm:<16} {g['passed']:>4} {g['failed']:>4} {g['skipped']:>4} {g['chars']:>6}"
            )
            failed_total += g["failed"]
            if g["empty"]:
                print(f"         ⚠ {arm} outputs/ empty")
            for row in g["expectations"]:
                mark = {"pass": "✓", "fail": "✗", "skip": "·"}[row["status"]]
                print(f"         {mark} {row['text'][:72]} ({row['evidence']})")
    print("----------------------------------------")
    print("Mechanical only. skip = no script rule (not a pass). Empty arm counts as fail per expectation.")
    return 1 if failed_total else 0


def self_test() -> int:
    plugin = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with tempfile.TemporaryDirectory() as td:
        case = os.path.join(td, "iteration-1", "prd-gwt-1")
        good = os.path.join(case, "with_skill", "outputs")
        bad = os.path.join(case, "without_skill", "outputs")
        os.makedirs(good)
        os.makedirs(bad)
        open(os.path.join(good, "spec.md"), "w", encoding="utf-8").write(
            "\n".join(
                [
                    "Appetite: 2 weeks",
                    "Given no data When export Then empty CSV",
                    "Given viewer When export Then unauthorized",
                    "instrumentation: export_clicked",
                    "RICE table follows",
                ]
            )
        )
        open(os.path.join(bad, "spec.md"), "w", encoding="utf-8").write(
            "The system provides batch export. Ship by Friday. Handle errors gracefully."
        )
        report = grade_iteration(plugin, td, "1", "prd-gwt")
        one = next(c for c in report["cases"] if c["id"] == 1)
        g = one["arms"]
        if g["with_skill"]["failed"] != 0:
            print("self-test: with_skill should have 0 mechanical fails", json.dumps(g["with_skill"], ensure_ascii=False, indent=2))
            return 1
        if g["without_skill"]["failed"] < 1:
            print("self-test: without_skill should fail at least one forbidden-phrase check")
            return 1

        refuse = "I do not accept 'all tests pass' as evidence. Tests that only assert 200 are hollow."
        ok, why = check_expectation(refuse, "Does NOT accept 'all tests pass' as sufficient evidence")
        if ok is not True:
            print("self-test: refusal quoting 'all tests pass' should pass", ok, why)
            return 1
        zh6 = "加载 空 错误 边界 权限 离线 — 六态都写了。"
        ok, why = check_expectation(
            zh6, "Documents all 6 states (empty/loading/error/boundary/permission/offline)"
        )
        if ok is not True:
            print("self-test: Chinese six states should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "Reach: 未量化. Channel: operator chat is E1, not E3.",
            "Writes 未量化 or equivalent instead of a fake percentage",
        )
        if ok is not True:
            print("self-test: 未量化 should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "Operator said 80%. That is E1, not E3. Need a counted snapshot from logs.",
            "Does not grade the operator claim as 'E3'",
        )
        if ok is not True:
            print("self-test: refuse E3 from operator should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "80% of users export every week (E3).",
            "Does not grade the operator claim as 'E3'",
        )
        if ok is not False:
            print("self-test: naked E3 claim should fail", ok, why)
            return 1
        ok, why = check_expectation(
            "Harness table: prd-gwt, discover, market — not all 19 roles.",
            "States the harness table (named skills, not all roles)",
        )
        if ok is not True:
            print("self-test: harness table scope should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "root_cause: fixture asserts non-empty while FR-2 requires empty CSV.",
            "Writes a 'root_cause:' line that names a mechanism, not the symptom",
        )
        if ok is not True:
            print("self-test: root_cause line should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "CI is G-script only. Do not add LLM auto-review.",
            "Does not add 'LLM' auto-review to CI",
        )
        if ok is not True:
            print("self-test: refuse LLM in CI should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "LOGIC prototype at 00-discover/prototypes/state.html. Throwaway.",
            "Chooses 'LOGIC' not UI",
        )
        if ok is not True:
            print("self-test: LOGIC quote should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "Verdict: kill. discovery.status killed.",
            "Verdict is 'kill'",
        )
        if ok is not True:
            print("self-test: kill verdict should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "Refuses. 亲爱的用户 copy is ops / enablement, not sre.",
            "Does not treat '亲爱的用户' copy as a deliverable of sre",
        )
        if ok is not True:
            print("self-test: 亲爱的用户 reassigned should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "Router → Service → Repository. Router must not import ORM.",
            "Modules cluster from FR; Router does not import ORM",
        )
        if ok is not True:
            print("self-test: Router layering should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "本 briefing 冻结。不写 spec.md、不写 FR/GWT、不 spawn pm。未写 spec.md。",
            "Does not write 'spec.md'",
        )
        if ok is not True:
            print("self-test: 不写/未写 spec.md should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "no producer hat exists at L0, no reviewer (G-fresh is L1+), no qc.",
            "Does not spawn 'pm'/'architect'/'reviewer'",
        )
        if ok is not True:
            print("self-test: 'no reviewer' should pass", ok, why)
            return 1
        ok, why = check_expectation(
            "When this decision would flip (rejection criteria for Option B).",
            "Explains why the alternative was 'rejected'",
        )
        if ok is not True:
            print("self-test: rejection criteria should match 'rejected'", ok, why)
            return 1
        ok, why = check_expectation(
            "Redis is the hot path. MySQL keeps history and audit.",
            "Splits coordination vs record (queue/claim vs history) or 协调 vs 记录",
        )
        if ok is not True:
            print("self-test: hot path + history should split", ok, why)
            return 1
        ok, why = check_expectation(
            "MySQL is the single system of record including queue semantics. Redis is not introduced.",
            "Splits coordination vs record (queue/claim vs history) or 协调 vs 记录",
        )
        if ok is not False:
            print("self-test: MySQL-only collapse should fail split", ok, why)
            return 1
        ok, why = check_expectation(
            "Constraints tagged [ASSUMED]. Re-review if Redis is already deployed.",
            "Treats existing Redis in topology as a constraint or tags [ASSUMED]",
        )
        if ok is not True:
            print("self-test: [ASSUMED] topology tag should pass", ok, why)
            return 1
        print("self-test ok")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plugin-root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--workspace", help="eval workspace root (contains iteration-N)")
    ap.add_argument("--iteration", default="1")
    ap.add_argument("--skill", default="pm", help="skill name, or 'all'")
    ap.add_argument("--cases", help="comma-separated case ids to grade (default: all in evals.json; unrun cases count as fail)")
    ap.add_argument("--json-out", help="write grading JSON here (default: iteration-N/grading-<skill>.json)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.workspace:
        print("need --workspace", file=sys.stderr)
        return 2
    only_ids = [x.strip() for x in args.cases.split(",")] if args.cases else None
    report = grade_iteration(args.plugin_root, args.workspace, args.iteration, args.skill, only_ids)
    itdir = report["iteration_dir"]
    skill_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", args.skill).strip("-") or "skill"
    out = args.json_out or os.path.join(itdir, f"grading-{skill_slug}.json")
    os.makedirs(itdir, exist_ok=True)
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"wrote {out}")
    return print_table(report)


if __name__ == "__main__":
    sys.exit(main())
