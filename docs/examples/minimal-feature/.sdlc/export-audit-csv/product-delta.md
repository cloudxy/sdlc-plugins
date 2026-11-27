# 产品层回写 · export-audit-csv

泳道：L2。审查对照用。本功能改了产品层里的长期事实，没有写「无产品层变更」。

| 帽子 | 产品层文件 | 变更 | 依据 |
|---|---|---|---|
| pm | strategy.md | 写明 H-1 与北极星 | briefing 的赌注 |
| pm | feature-map.md | 「现在」增加导出租户审计 CSV | spec 的 J-1 |
| architect | architecture.md | 导出是 API 进程内的纯函数，不新开服务 | `02-shape/contract.md` |
| 样例作者（dba 已跳过：不改表） | domain-model.md | 导出结果不是存储实体 | 合同第 7 节 |
| 样例作者（dba 已跳过：不改表） | erd.dbml | 只记录 tenant 与 audit_event | 本轮不改表 |
| pm | data/metrics.yaml | 定义 weekly_export_tenants | 策略第 6 节 |

设计系统与增长说明没有建文件，理由在产品层 README。本表不记录它们。
