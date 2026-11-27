# metrics.yaml 指标定义规范

## 为什么指标即代码

指标语义必须有唯一归属；具体规模数字不是适用性论据。`metrics.yaml` 保存定义，或指向项目已有语义层的权威定义。SQL 可以引用同一指标，多处独立维护不同公式才是缺陷。

## 顶层版本与每条指标必填字段（SVOT 单一真相版本）

顶层声明 `version: <int>`；下游分析、看板与实验统一引用 `metric:<id>@v<version>`，破坏性口径变更必须递增版本并写明 `effective_from`，严禁原位静默篡改历史含义。

| 字段 | 必填 | 说明 |
|---|---|---|
| id | ✅ | 全局唯一，snake_case（如 `ticket_avg_resolution_time`） |
| fr_anchor | ✅ | 回溯到 PRD 的哪条 FR/NFR（产品级北极星可为空串 `""`） |
| name | ✅ | 人类可读名称 |
| formula | ✅ | SQL 级精确定义（在目标引擎可复现） |
| granularity | ✅ | 时间粒度（`daily` / `weekly` / `monthly`） |
| time_semantics | ✅ | 时间归属语义：`event_time`（行为发生时间）/ `business_time`（业务生效或结算时间）/ `ingestion_time`（入仓时间），含迟到回溯窗口说明 |
| effective_from | ✅ | 当前口径生效日期（`YYYY-MM-DD`），防止跨期回算混淆新旧口径 |
| dimensions | ✅ | 可钻取的维度列表 |
| exclusions | ✅ | 排除口径（哪些数据被排除、为什么） |
| owner | ✅ | 业务负责人：决定指标的含义与阈值，对「这个数代表什么」负责；计算实现与本文件由 `data-warehouse-engineer` 维护 |

## 常见错误

| 错误 | 后果 | 正确做法 |
|---|---|---|
| 同一指标两处 SQL 定义 | 看板和分析数据不一致，管理层不信数据 | 唯一位置定义，SQL 引用 ID/版本 |
| formula 写"留存率"而不写 SQL | 不同人理解不同 | 精确到 所选引擎中可执行的表达式/查询引用（条件计数需使用该引擎正确语法） |
| 排除口径不写 | "活跃用户"是否含新注册？各说各话 | 显式写 `exclusions: "registered_at > NOW() - 7 days"` |
| 无 owner | 指标出错了没人修 | 每条指标必须有 owner |
| 无 FR 锚点 | 需求变了指标不知道要不要跟着变 | 回溯到 PRD |
