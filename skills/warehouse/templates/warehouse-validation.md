<!-- sdlc:unfilled — 写入真实内容后删除本行；未填写的模板不算交付 -->
# 数仓与指标验证报告 · <功能名>

> 阶段：`warehouse/validate`（`04-verify/warehouse-validation.md`）｜作者：`data-warehouse-engineer`｜日期：<YYYY-MM-DD>
> SVOT 版本：`data/metrics.yaml@v<n>` · `data/tags.yaml@v<n>`｜数据快照与引擎：`<分区/窗口>` · `<MySQL 8 / PostgreSQL / ClickHouse / DuckDB>`
> **铁律：调度绿灯不等于数据正确；必须提供源端对账、双跑幂等零差异与边界（迟到/退款负值/删除）实测证据。**

## 1. 源端对账（Source-to-Target Reconciliation）

| 目标表 / 指标 (`metric:<id>@v<n>`) | 对比窗口与 `time_semantics` | 上游源端计数 / 总额 | 数仓目标端计数 / 总额 | 差异与原因说明（如已声明 `exclusions`） | 结果 |
|---|---|---|---|---|---|
| `<dwd_orders / fct_orders>` | `2026-09-01..07` (`business_time`) | 12,480 行 · 净额 `942,100.00` | 12,450 行 · 净额 `942,100.00` | 差 30 行为测试租户（符合 `exclusions`，有效净额 `0` 误差） | ✅ |
| `metric:first_report_view_rate@v1` | `2026-09-07` (`event_time`) | 分子 312 / 分母 800 (`39.0%`) | `39.0%` | 与明细手工复算完全一致 | ✅ |

## 2. 幂等重放与变更边界验证（Replay, Late Arrivals, Refunds & Deletes）

| 验证项 | 操作与输入样本 | 期望结果 | 实测命令与输出摘要 | 结果 |
|---|---|---|---|---|
| 同分区双跑幂等 | 对窗口 `<dt>` 连续执行 2 次管线并比对快照 | 行数、主键集合与汇总值 `diff` 为空 | `<命令 + diff exit: 0>` | ✅ |
| 负值退款 / 冲正守恒 | 含全额退款、跨日部分退款与红冲记录 | 负值正常入仓未被误拦；`实收净额 == 正向收款 + 负向退款` | `<SQL 对账输出>` | ✅ |
| 迟到事件与 CDC 删除 | 回放回溯窗内迟到事件及源端硬删除 tombstone | 迟到事件归入正确 `event_time` 分区；已删主键在目标层更新/剔除 | `<SQL 输出>` | ✅ |
| 生产 SQL 方言保真 | 在 `<生产同款引擎>` 执行全部转换与指标 SQL | `0` 方言报错（无 SQLite 放行 `NULLS LAST` 类隐患） | `<命令 + exit: 0>` | ✅ |

## 3. 最小可行数据产品九要素契约与隔离合规核验（①–⑨ 缺一不可准出）

| 要素 | 核验内容与证据锚点 | 状态 |
|---|---|---|
| **① 负责人（Owner）** | 业务口径负责人：`<pm>` · 数仓维护负责人：`data-warehouse-engineer` | ✅ / ❌ |
| **② 上下游数据契约** | Schema、时间语义（含 `event_time` 与入库可用 `availability_time`）、新鲜度 SLA（`<如每日 ≤ 05:00>`）、体量与安全边界已锁定 | ✅ / ❌ |
| **③ 可执行质量断言** | 主键唯一、非空、正负号守恒、源端对账与波动率脚本自动执行且非 0 阻断发布（`<命令 + exit: 0>`） | ✅ / ❌ |
| **④ 运行日志（Run Logs）** | 结构化落盘 `run_id`、分区窗口、输入/输出行数、耗时与状态（`<日志表或路径>`） | ✅ / ❌ |
| **⑤ 血缘（Lineage）** | 源表/埋点 → 分层表 → `metric:<id>@v<n>` / `tag:<id>@v<n>` 血缘已登记并校验一致 | ✅ / ❌ |
| **⑥ 语义文档（SVOT）** | `data/metrics.yaml@v<n>` 与 `data/tags.yaml@v<n>` 已登记公式、`time_semantics`、`effective_from` 与 `exclusions` | ✅ / ❌ |
| **⑦ 显式消费者清单** | 已登记下游消费方：`<analyst / growth / miner / ops / 看板或 API 名>` | ✅ / ❌ |
| **⑧ 权限与隐私边界** | ☐ 只读源账号（零未授权 OLTP 回写） ☐ 多租户隔离或批准系统上下文（跨租户抽查 `0` 串租） ☐ PII 进明细/服务层前已脱敏 ☐ `growth` 仅消费 `public`/`operational` 标签且模型标签满足 `(entity, availability_time <= decision_time)` | ✅ / ❌ |
| **⑨ 破坏性变更通知机制** | 口径/Schema 破坏性调整走升版 + `effective_from` + expand-contract 并存窗口，已配置向 ⑦ 全体消费者的变更通知路径：`<机制说明>` | ✅ / ❌ |

## 4. 残余假设与生产监控移交

| 未在当前数据量验证的假设 | 风险 | 上线后质量断言 / 告警（移交 `sre` / 调度） |
|---|---|---|
| <例：单日千万级事件倾斜尚未在预发压测> | <大租户 JOIN 慢查询> | <每次任务后跑四类断言；耗时 > 15m 或日环比行数波动 > 30% 告警> |
