# backend return · be-export-filter · 2026-10-02

Status: blocked (not implemented)

现在的 `GET /api/v1/orders/export` 只收 `date_from` / `date_to`。列表的筛选条件（状态、渠道、门店、关键词）要传进来，得把导出改成 `POST /api/v1/orders/export`，请求体带 `filters` 对象，原来的 GET 参数去掉。

调用方（按 nginx 访问日志 2026-09）：管理后台、移动端 App 3.2+、开放平台的两家合作方（按 API 文档对外承诺过参数）。

我可以直接改：后端改 POST，管理后台一起改，大概半天。移动端和合作方那边我没法改。
