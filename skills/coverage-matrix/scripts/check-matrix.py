#!/usr/bin/env python3
"""覆盖矩阵空洞检测器。

- 每条 FR / NFR 至少出现在覆盖矩阵中一次（空洞须补用例或标豁免）。
- 每条关键用户旅程 J-n 必须出现在**同一行含 E2E** 的矩阵行里（关键旅程要端到端验证，不接受只做单元映射）。
- 每个埋点 EV-n（来自 01-define/tracking.md 或 spec）必须出现在矩阵中（埋点校验）。

- 一行只有在没有标为失败/跳过/未执行时才算覆盖；「no E2E」「未做 E2E」这类否定写法不算 E2E（P11）。
- 行里引用的测试文件（如 tests/test_login.py:12、e2e/login.spec.ts）必须真实存在。

用法：python check-matrix.py coverage.md spec.md [tracking.md ...]
退出码：0 = 无空洞；非零 = 空洞数
"""
import pathlib
import re
import sys

ID_RE = {
    "FR": re.compile(r"\bFR-\d+\b"),
    "NFR": re.compile(r"\bNFR-\d+\b"),
    "J": re.compile(r"\bJ-\d+\b"),
    "EV": re.compile(r"\bEV-\d+\b"),
}


def _read(path: str) -> str:
    p = pathlib.Path(path)
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def extract_ids(spec_paths):
    ids = {k: set() for k in ID_RE}
    for p in spec_paths:
        text = _read(p)
        for kind, rx in ID_RE.items():
            ids[kind].update(rx.findall(text))
    return {k: sorted(v, key=lambda s: (len(s), s)) for k, v in ids.items()}


FAILED = re.compile(r"\b(FAIL(ED)?|SKIP(PED)?|TODO|PENDING|BLOCKED|N/?A)\b|失败|跳过|未执行|未运行|待执行|待补|阻塞", re.I)
NO_E2E = re.compile(r"\b(no|without|not|missing|skip(ped)?)\b[^|]{0,20}\be2e\b|\be2e\b[^|]{0,20}\b(not|never)\b[^|]{0,12}(run|executed)|(无|没有|未做|未跑|缺)[^|]{0,6}e2e|e2e[^|]{0,6}(未执行|未运行|没跑|未做)", re.I)
EXEMPT = re.compile(r"豁免|exempt", re.I)
TEST_REF = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w.-]+\.(?:py|ts|tsx|js|jsx|go|java|kt|rb|rs|cs|php|feature))(?::\d+)?")


def project_root(start):
    d = pathlib.Path(start).resolve().parent
    for p in [d, *d.parents]:
        if (p / "sdlc.config.yaml").is_file():
            return p
    return None


def check_matrix(matrix_path, ids):
    content = _read(matrix_path)
    lines = [ln for ln in content.splitlines() if ln.strip().startswith("|")] or content.splitlines()
    holes = []
    root = project_root(matrix_path)
    # 行是否算覆盖：失败/跳过/未执行的行不算，豁免行算（豁免要写理由，由评审判断）
    counts = [ln for ln in lines if EXEMPT.search(ln) or not FAILED.search(ln)]
    for kind in ("FR", "NFR", "EV"):
        for item in ids[kind]:
            rx = re.compile(rf"\b{re.escape(item)}\b")
            if not any(rx.search(ln) for ln in lines):
                label = "埋点校验" if kind == "EV" else "用例"
                holes.append(f"{item} 未出现在覆盖矩阵中（空洞须补{label}或标豁免）")
            elif not any(rx.search(ln) for ln in counts):
                holes.append(f"{item} 只出现在失败/跳过/未执行的行里（不算已覆盖）")
    for item in ids["J"]:
        rx = re.compile(rf"\b{re.escape(item)}\b")
        rows = [ln for ln in lines if rx.search(ln)]
        if not rows:
            holes.append(f"{item} 关键旅程未出现在覆盖矩阵中（须有 E2E 用例）")
        elif not any(re.search(r"e2e", ln, re.I) and not NO_E2E.search(ln) and ln in counts for ln in rows):
            holes.append(f"{item} 关键旅程没有已执行的 E2E 用例（否定写法、失败或未执行的行不算）")
    if root:
        for ln in lines:
            for ref in TEST_REF.findall(ln):
                if not (root / ref).exists() and not list(root.glob(f"**/{ref}"))[:1]:
                    holes.append(f"引用的测试不存在: {ref}（矩阵只能指向真实的用例）")
    return holes


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: check-matrix.py <coverage.md> <spec.md> [tracking.md ...]")
        sys.exit(1)
    matrix = sys.argv[1]
    specs = sys.argv[2:]
    ids = extract_ids(specs)
    total = sum(len(v) for v in ids.values())
    if total == 0:
        print("✓ 无 FR/NFR/J/EV 编号，跳过矩阵检查")
        sys.exit(0)
    holes = check_matrix(matrix, ids)
    if holes:
        for h in holes:
            print(f"✗ [MATRIX] {h}")
        sys.exit(min(len(holes), 125))
    print(f"✓ 覆盖矩阵完整：FR {len(ids['FR'])} · NFR {len(ids['NFR'])} · J {len(ids['J'])}（E2E）· EV {len(ids['EV'])}")
    sys.exit(0)
