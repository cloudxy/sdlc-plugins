# 覆盖矩阵 · 导出租户审计日志 CSV

上游：`01-define/spec.md`。契约：`02-shape/contract.md`。日期：2026-11-21。

## 1. FR 与 NFR

| FR/NFR | 用例 | 层 | 状态 |
|---|---|---|---|
| FR-1 | tests/test_audit_export.py | 单元 | ✅ pass |
| NFR-1 | tests/test_audit_export.py | 单元 | ✅ pass |
| [SEC-1] | tests/test_audit_export.py | 单元 | ✅ pass |

## 1b. 旅程

本样例没有浏览器。J-1 用 API 级用例从头走到返回的 CSV 或拒绝，层写 e2e，表示这条旅程有端到端断言，不是只测了一个内部分支。

| J-n | 旅程 | 用例 | 层 | 结果 |
|---|---|---|---|---|
| J-1 | 租户管理员导出本租户审计 | tests/test_audit_export.py | e2e | ✅ pass |

## 2. 用例回指

| 用例 | 名称 | 对应 |
|---|---|---|
| test_admin_exports_utc_csv | UTC 列 | FR-1 |
| test_empty_events_return_header_only | 空列表 | FR-1 |
| test_member_is_forbidden | 非管理员 | FR-1 |
| test_cross_tenant_event_is_refused | 跨租户 | FR-1 [SEC-1] |
| test_naive_timestamp_is_rejected | 无时区 | FR-1 |
| test_row_limit | 行上限 | FR-1 NFR-1 |

没有不回指 FR-1 或 NFR-1 的用例。没有空洞。
