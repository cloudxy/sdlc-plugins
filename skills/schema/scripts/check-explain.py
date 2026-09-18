#!/usr/bin/env python3
"""EXPLAIN 输出解析器——检查是否达到索引命中标准。

用法：cat explain_output.txt | python check-explain.py
     python check-explain.py explain_output.txt
退出码：0 = 通过，违规数 = 非零
"""
import sys, re

def parse(text):
    """解析 MySQL EXPLAIN 表格输出。"""
    violations = []
    lines = [l for l in text.split("\n") if l.strip()]
    for line in lines:
        # 匹配表格数据行
        if "|" not in line or "select_type" in line or "---" in line:
            continue
        cols = [c.strip() for c in line.split("|") if c.strip()]
        if len(cols) < 7:
            continue
        try:
            # 列序：| id | select_type | table | type | possible_keys | key | key_len | rows | filtered | Extra |
            # 实际 MySQL EXPLAIN 可能 9-10 列，用关键词定位更稳
            table = cols[2] if len(cols) > 2 else ""
            etype = ""
            key = ""
            rows = "0"
            extra = ""
            for i, c in enumerate(cols):
                if c in ("ALL", "ref", "eq_ref", "const", "range", "index", "system"):
                    etype = c
                    # key 通常在 type 后 1-2 列（possible_keys 和 key）
                    for j in range(i+1, min(i+3, len(cols))):
                        if cols[j] != "NULL" and cols[j] != "":
                            key = cols[j]
                            break
                    # rows 在 key 后 1-2 列
                    for j in range(i+2, min(i+4, len(cols))):
                        if cols[j].isdigit():
                            rows = cols[j]
                            break
                    # Extra 在最后
                    extra = cols[-1] if len(cols) > i+2 else ""
                    break
        except (IndexError, ValueError):
            continue
        row_count = int(rows) if rows.isdigit() else 0

        if etype == "ALL":
            violations.append(f"FULL TABLE SCAN on {table} (type=ALL, rows={row_count})")
        elif etype == "index" and row_count > 100:
            violations.append(f"FULL INDEX SCAN on {table} (type=index, rows={row_count})")

        if key == "NULL" and etype not in ("const", "system"):
            violations.append(f"NO INDEX USED on {table} (key=NULL)")

        if "Using filesort" in extra and row_count > 100:
            violations.append(f"FILESORT on {table} (rows={row_count}) — sort column not in index")
        if "Using temporary" in extra:
            violations.append(f"TEMPORARY TABLE on {table} — consider index optimization")

    return violations

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = open(sys.argv[1]).read()
    else:
        text = sys.stdin.read()
    v = parse(text)
    if v:
        for x in v:
            print(f"✗ [EXPLAIN] {x}")
        sys.exit(len(v))
    else:
        print("✓ EXPLAIN check passed")
        sys.exit(0)
