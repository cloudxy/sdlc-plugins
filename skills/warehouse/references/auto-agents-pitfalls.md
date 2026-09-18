# auto-agents 数仓坑点（仅实战已验证）

> 写入纪律：只收录本仓库已经发生、且有回归钉可证伪的项。架构推断、未跑过的 ETL、未建的分层表不进本文。

## P-WH-01 MySQL 不支持 `NULLS LAST` / `NULLS FIRST`

- **现象**：资产/技能列表排序在 SQLite 测试绿、生产 MySQL **1064**，接口 500。
- **原因**：SQLAlchemy `col.desc().nullslast()` 编译出 PostgreSQL 方言 `NULLS LAST`。SQLite 接受；MySQL 不接受。MySQL `ORDER BY col DESC` **默认就把 NULL 排在最后**，不必再写。
- **证据**：
  - 修复 commit `0e0aaf8`（`fix(db): 资产目录 500——去除 MySQL 不支持的 NULLS LAST 语法`）
  - 回归钉 `backend/tests/test_t10_fix_regressions.py`：`list_skills` / `list_assets` 的 MySQL 方言编译产物不得含 `NULLS LAST`/`NULLS FIRST`；保真通道断言 NULL 行在 DESC 下排最后
- **对仓的含义**：本仓分析库与 OLTP **同一 MySQL 8**。下一轮凡写 `ods_`/`dwd_`/`dws_`/`ads_` 查询或 ETL SQL，禁止 `NULLS LAST`/`FIRST`，禁止用 SQLite 绿当作方言已过。需要「NULL 在后」时用裸 `DESC`。
- **反例**：在仓 SQL 或 dbt/脚本里写 `ORDER BY completed_at DESC NULLS LAST` → 上线即 1064。
