#!/usr/bin/env python3
"""覆盖矩阵空洞检测器。

- 每条 FR / NFR 至少出现在覆盖矩阵中一次（空洞须补用例或标豁免）。
- 每条关键用户旅程 J-n 必须出现在**同一行含 E2E** 的矩阵行里（关键旅程要端到端验证，不接受只做单元映射）。
- 每个埋点 EV-n（来自 01-define/tracking.md 或 spec）必须出现在矩阵中（埋点校验）。

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


def check_matrix(matrix_path, ids):
    content = _read(matrix_path)
    lines = content.splitlines()
    holes = []
    for kind in ("FR", "NFR", "EV"):
        for item in ids[kind]:
            if not re.search(rf"\b{re.escape(item)}\b", content):
                label = "埋点校验" if kind == "EV" else "用例"
                holes.append(f"{item} 未出现在覆盖矩阵中（空洞须补{label}或标豁免）")
    for item in ids["J"]:
        rx = re.compile(rf"\b{re.escape(item)}\b")
        rows = [ln for ln in lines if rx.search(ln)]
        if not rows:
            holes.append(f"{item} 关键旅程未出现在覆盖矩阵中（须有 E2E 用例）")
        elif not any(re.search(r"e2e", ln, re.I) for ln in rows):
            holes.append(f"{item} 关键旅程无 E2E 用例（矩阵行须标 E2E 层）")
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
