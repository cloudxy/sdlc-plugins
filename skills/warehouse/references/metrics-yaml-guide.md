# metrics.yaml 指标定义规范

## 为什么指标即代码

Airbnb Minerva 用 12000+ 指标验证：口径分散是数据不可信的第一来源。同一指标在两处 SQL 中定义，随时间推移必然漂移——最终看板和分析使用不同的"留存率"，管理层做出错误决策。

**metrics.yaml 是唯一事实源。** 分析师、挖掘师、看板一律引用，不另写 SQL。

## 每条指标的字段

| 字段 | 必填 | 说明 |
|---|---|---|
| id | ✅ | 全局唯一，snake_case（如 `ticket_avg_resolution_time`） |
| fr_anchor | ✅ | 回溯到 PRD 的哪条 FR（保证指标与需求对齐） |
| name | ✅ | 人类可读名称 |
| formula | ✅ | SQL 级定义（精确到可复现） |
| granularity | ✅ | 时间粒度（daily/weekly/monthly） |
| dimensions | ✅ | 可钻取的维度列表 |
| exclusions | ✅ | 排除口径（哪些数据被排除、为什么） |
| owner | ✅ | 谁负责这个指标的正确性 |

## 常见错误

| 错误 | 后果 | 正确做法 |
|---|---|---|
| 同一指标两处 SQL 定义 | 看板和分析数据不一致，管理层不信数据 | 只在 metrics.yaml 定义，SQL 引用 ID |
| formula 写"留存率"而不写 SQL | 不同人理解不同 | 精确到 `COUNT(DISTINCT user_id WHERE ...)` |
| 排除口径不写 | "活跃用户"是否含新注册？各说各话 | 显式写 `exclusions: "registered_at > NOW() - 7 days"` |
| 无 owner | 指标出错了没人修 | 每条指标必须有 owner |
| 无 FR 锚点 | 需求变了指标不知道要不要跟着变 | 回溯到 PRD |
