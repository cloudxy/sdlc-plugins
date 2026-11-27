#!/usr/bin/env python3
"""覆盖矩阵空洞检测器。

- 每条 FR / NFR / [SEC-n] 至少出现在覆盖矩阵中一次（空洞须补用例或标带理由的豁免/N/A）。
- 每条关键用户旅程 J-n 必须出现在**同一行含 E2E** 的矩阵行里（关键旅程要端到端验证，不接受只做单元映射）。
- 每个埋点 EV-n（来自 01-define/tracking.md 或 spec）必须出现在矩阵中（埋点校验）。

- 一行只有在没有标为失败/跳过/未执行/缺口/需真实环境/待修复时才算覆盖；
- 标为「豁免 / exempt」或带非空备注理由的「➖ N/A / 不适用」算显式豁免（由审查者核理由）；裸 N/A 无理由不算覆盖。
- 「no E2E」「未做 E2E」这类否定写法不算 E2E（P11）。
- 行里引用的测试文件（如 tests/test_login.py:12、e2e/login.spec.ts）必须真实存在。

用法：python3 check-matrix.py coverage.md spec.md [tracking.md contract.md ...]
      python3 check-matrix.py --self-test
退出码：0 = 无空洞；非零 = 空洞数（封顶 125）
"""
from __future__ import annotations

import pathlib
import re
import sys
import tempfile

ID_RE = {
    "FR": re.compile(r"\bFR-\d+\b"),
    "NFR": re.compile(r"\bNFR-\d+\b"),
    "J": re.compile(r"\bJ-\d+\b"),
    "EV": re.compile(r"\bEV-\d+\b"),
    "SEC": re.compile(r"\[(SEC-\d+)\]|\b(SEC-\d+)\b"),
}

FAILED = re.compile(
    r"\b(FAIL(ED)?|SKIP(PED)?|TODO|PENDING|BLOCKED|HOLE|N/?A)\b"
    r"|失败|跳过|未执行|未运行|待执行|待补|阻塞|缺口|需真实环境|待修复|❌",
    re.I,
)
NO_E2E = re.compile(
    r"\b(no|without|not|missing|skip(ped)?)\b[^|]{0,20}\be2e\b"
    r"|\be2e\b[^|]{0,20}\b(not|never)\b[^|]{0,12}(run|executed)"
    r"|(无|没有|未做|未跑|缺)[^|]{0,6}e2e|e2e[^|]{0,6}(未执行|未运行|没跑|未做)",
    re.I,
)
EXEMPT = re.compile(r"豁免|exempt", re.I)
NA_TOKEN = re.compile(r"\bN/?A\b|不适用", re.I)
HARD_FAIL_WITH_NA = re.compile(r"\b(FAIL(ED)?|TODO|BLOCKED|HOLE)\b|失败|阻塞|缺口|待修复|❌", re.I)
TEST_REF = re.compile(
    r"(?<![\w/.-])((?:[\w.-]+/)*[\w.-]+\.(?:py|ts|tsx|js|jsx|go|java|kt|rb|rs|cs|php|feature))(?::\d+)?"
)


def _read(path: str) -> str:
    p = pathlib.Path(path)
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def extract_ids(spec_paths: list[str]) -> dict[str, list[str]]:
    ids: dict[str, set[str]] = {k: set() for k in ID_RE}
    for p in spec_paths:
        text = _read(p)
        for kind, rx in ID_RE.items():
            if kind == "SEC":
                for m in rx.finditer(text):
                    tok = m.group(1) or m.group(2)
                    if tok and re.search(r"\d", tok):
                        ids["SEC"].add(tok)
            else:
                ids[kind].update(rx.findall(text))
    return {k: sorted(v, key=lambda s: (len(s), s)) for k, v in ids.items()}


def _reasoned_na(line: str) -> bool:
    """True when a Markdown table row declares N/A / 不适用 AND carries a non-empty justification cell."""
    if not NA_TOKEN.search(line) or HARD_FAIL_WITH_NA.search(line) or "|" not in line:
        return False
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 3:
        return False
    # At least one trailing cell after the N/A status cell must carry real justification text (not empty / dash / placeholder)
    na_indices = [i for i, c in enumerate(cells) if NA_TOKEN.search(c)]
    if not na_indices:
        return False
    idx = na_indices[-1]
    # Justification can be in the cell after N/A, or embedded inside the N/A cell itself (e.g. `N/A（理由）`)
    after = [c for c in cells[idx + 1:] if c and c not in ("—", "-", "N/A", "n/a") and not c.startswith("<")]
    inline = re.sub(r"[\s➖*`()（）:：-]+", "", NA_TOKEN.sub("", cells[idx]))
    return bool(after or len(inline) >= 2)


def _is_covered_line(ln: str) -> bool:
    if EXEMPT.search(ln) or _reasoned_na(ln):
        return True
    return not FAILED.search(ln)


def project_root(start: str) -> pathlib.Path | None:
    d = pathlib.Path(start).resolve().parent
    for p in [d, *d.parents]:
        if (p / "sdlc.config.yaml").is_file():
            return p
    return None


def check_matrix(matrix_path: str, ids: dict[str, list[str]]) -> list[str]:
    content = _read(matrix_path)
    lines = [ln for ln in content.splitlines() if ln.strip().startswith("|")] or content.splitlines()
    holes: list[str] = []
    root = project_root(matrix_path)
    counts = [ln for ln in lines if _is_covered_line(ln)]
    for kind in ("FR", "NFR", "EV", "SEC"):
        for item in ids.get(kind, []):
            rx = re.compile(rf"(?<![\w-]){re.escape(item)}(?![\w-])")
            if not any(rx.search(ln) for ln in lines):
                label = "埋点校验" if kind == "EV" else ("安全控制验证" if kind == "SEC" else "用例")
                holes.append(f"{item} 未出现在覆盖矩阵中（空洞须补{label}或标豁免）")
            elif not any(rx.search(ln) for ln in counts):
                holes.append(f"{item} 只出现在缺口/失败/跳过/未执行/无理由 N/A 的行里（不算已覆盖）")
    for item in ids["J"]:
        rx = re.compile(rf"\b{re.escape(item)}\b")
        rows = [ln for ln in lines if rx.search(ln)]
        if not rows:
            holes.append(f"{item} 关键旅程未出现在覆盖矩阵中（须有 E2E 用例）")
        elif not any(re.search(r"e2e", ln, re.I) and not NO_E2E.search(ln) and ln in counts for ln in rows):
            holes.append(f"{item} 关键旅程没有已执行的 E2E 用例（否定写法、缺口、失败或未执行的行不算）")
    if root:
        for ln in lines:
            for ref in TEST_REF.findall(ln):
                if not (root / ref).exists() and not list(root.glob(f"**/{ref}"))[:1]:
                    holes.append(f"引用的测试不存在: {ref}（矩阵只能指向真实的用例）")
    return holes


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "sdlc.config.yaml").write_text("product_root: docs/product\n", encoding="utf-8")
        (root / "tests").mkdir()
        (root / "tests/test_export.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
        spec = root / "spec.md"
        spec.write_text("FR-01 FR-02 NFR-01 NFR-09 J-1 EV-1 [SEC-1]\n", encoding="utf-8")

        # 1. `❌ 缺口`, `⚠️ 需真实环境`, bare `N/A` without reason, and missing `[SEC-1]` MUST fail
        bad_cov = root / "bad_cov.md"
        bad_cov.write_text(
            "| FR-01 | GWT-01.1 | TC-1 | tests/test_export.py:1 | 集成 | ✅ | |\n"
            "| FR-02 | GWT-02.1 | — | — | — | ❌ **缺口** | 尚未构造 |\n"
            "| NFR-01 | — | TC-2 | — | 专项 | ⚠️ **需真实环境** | 待压测 |\n"
            "| NFR-09 | — | — | — | — | ➖ **N/A** | |\n"
            "| J-1 | 导出旅程 | TC-E2E | tests/test_export.py:1 | E2E | ✅ | |\n"
            "| EV-1 | exported | ✅ | tests/test_export.py:1 | 集成 | ✅ | |\n",
            encoding="utf-8",
        )
        holes = check_matrix(str(bad_cov), extract_ids([str(spec)]))
        for must_catch in ("FR-02", "NFR-01", "NFR-09", "SEC-1"):
            if not any(must_catch in h for h in holes):
                print(f"self-test FAILED: did not catch {must_catch}:", holes)
                return 1

        # 2. Reasoned `➖ **N/A**` and covered `[SEC-1]` MUST pass
        good_cov = root / "good_cov.md"
        good_cov.write_text(
            "| FR-01 | GWT-01.1 | TC-1 | tests/test_export.py:1 | 集成 | ✅ | |\n"
            "| FR-02 | GWT-02.1 | TC-2 | tests/test_export.py:1 | 单元 | ✅ | |\n"
            "| NFR-01 | — | TC-3 | tests/test_export.py:1 | 集成 | ✅ | |\n"
            "| NFR-09 | — | — | — | — | ➖ **N/A** | PRD 已声明本轮单语种 N/A |\n"
            "| [SEC-1] | 租户隔离 | TC-4 | tests/test_export.py:1 | 集成 | ✅ | |\n"
            "| J-1 | 导出旅程 | TC-E2E | tests/test_export.py:1 | E2E | ✅ | |\n"
            "| EV-1 | exported | TC-5 | tests/test_export.py:1 | 集成 | ✅ | |\n",
            encoding="utf-8",
        )
        ok_holes = check_matrix(str(good_cov), extract_ids([str(spec)]))
        if ok_holes:
            print("self-test FAILED: expected 0 holes, got:", ok_holes)
            return 1
    print("self-test ok")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    if len(sys.argv) < 3:
        print("用法: check-matrix.py <coverage.md> <spec.md> [tracking.md contract.md ...]")
        sys.exit(1)
    matrix = sys.argv[1]
    specs = sys.argv[2:]
    ids = extract_ids(specs)
    total = sum(len(v) for v in ids.values())
    if total == 0:
        print("✓ 无 FR/NFR/J/EV/SEC 编号，跳过矩阵检查")
        sys.exit(0)
    holes = check_matrix(matrix, ids)
    if holes:
        for h in holes:
            print(f"✗ [MATRIX] {h}")
        sys.exit(min(len(holes), 125))
    sec_part = f" · SEC {len(ids['SEC'])}" if ids["SEC"] else ""
    print(f"✓ 覆盖矩阵完整：FR {len(ids['FR'])} · NFR {len(ids['NFR'])} · J {len(ids['J'])}（E2E）· EV {len(ids['EV'])}{sec_part}")
    sys.exit(0)
