# 实现证据 · T-1 后端

票：T-1。锚点：FR-1、J-1、NFR-1。角色：backend。日期：2026-11-21。

## 1. 落位

| 元素 | 落在 | 文件 |
|---|---|---|
| 权限、租户边界、时区、行上限、CSV 列 | 纯函数 | `src/audit_export.py` |
| 用例 | 测试 | `tests/test_audit_export.py` |

没有 Router、ORM 或新表。调用方负责把已读出的事件传进来。

## 2. 改动

| 文件 | 性质 |
|---|---|
| `src/audit_export.py` | 新增 |
| `tests/test_audit_export.py` | 新增 |

## 3. 决策

无事务、无外部调用、无幂等键。重复调用得到同样的文本，因为函数不写库。

## 6. 自测证据

在样例项目根 `docs/examples/minimal-feature` 执行。下面是本次运行的原样输出。

```
$ python3 tests/test_audit_export.py
......
----------------------------------------------------------------------
Ran 6 tests in 0.070s

OK
exit code 0

$ python3 -m py_compile src/audit_export.py tests/test_audit_export.py
exit code 0
```

| 场景 | 测试 | 结果 |
|---|---|---|
| UTC 与列名 | test_admin_exports_utc_csv | 通过 |
| 空列表 | test_empty_events_return_header_only | 通过 |
| 非管理员 | test_member_is_forbidden | 通过 |
| 跨租户 | test_cross_tenant_event_is_refused | 通过 |
| 无时区 | test_naive_timestamp_is_rejected | 通过 |
| 10000 与 10001 | test_row_limit | 通过 |

## 7. NFR

NFR-1：10000 行返回表头加 10000 行；10001 行抛出 `limit`。环境是本机 CPython，2026-11-21 这次运行。
