# 样例产品层

租户控制台的一个脱敏切片：租户管理员导出本租户的审计日志 CSV。这里只放跨功能仍然成立的事实。功能工件在 `.sdlc/export-audit-csv/`。

没有 `design-system.md`：本样例没有用户界面。
没有 `growth.md`：内部管理能力，没有对外增长宣称。
没有 `data/tracking-plan.yaml` 和 `data/tags.yaml`：本切片不新增埋点。
有 `data/metrics.yaml`：复盘指标 id 是 `weekly_export_tenants`（`metric:weekly_export_tenants`）。
