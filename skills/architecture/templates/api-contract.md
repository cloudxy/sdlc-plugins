# API 契约 · <功能名>

> 上游：PRD FR-<n>｜作者：/architect｜版本：v1｜日期：<YYYY-MM-DD>
> 消费方：`/backend`（实现）· `/frontend`（调用）· `/qa`（用例）
> **契约先行**：本文件定稿后 `/backend` 与 `/frontend` 可并行开工。

## 通用约定

| 项 | 约定 |
|---|---|
| Base path | `/api/v1` |
| 认证 | `Authorization: Bearer <token>` |
| 时间格式 | ISO 8601 UTC（`2026-09-05T14:30:00Z`）；纯日期用 `2026-09-05` |
| 字符编码 | UTF-8 |
| 集合类字段 | **永不返回 null**，用 `[]` / `{}` |
| 未知字段 | 客户端必须容忍（服务端可新增字段） |
| trace_id | 5xx 响应必带，用于关联日志 |

## 错误码清单

> 业务判断用稳定的 `code` 字符串。**`message` 是给人看的，前端不许用它做逻辑判断。**

| HTTP | code | 语义 | 前端处理建议 |
|---|---|---|---|
| 400 | `INVALID_PARAM` | 参数校验失败，含 `field` | 高亮对应字段 |
| 401 | `UNAUTHENTICATED` | 未登录或 token 过期 | 跳登录 |
| 403 | `FORBIDDEN_SCOPE` | 权限不足 | 提示无权限 |
| 404 | `NOT_FOUND` | 资源不存在 | 提示不存在 |
| 409 | `EXPORT_IN_PROGRESS` | 已有任务进行中 | 提示并展示进行中的任务 |
| 422 | `ROW_LIMIT_EXCEEDED` | 超出行数上限，含 `detail.limit` | 提示缩小筛选范围 |
| 429 | `RATE_LIMITED` | 限流，响应头 `Retry-After` | 按 Retry-After 退避重试 |
| 500 | `INTERNAL_ERROR` | 服务端错误，含 `trace_id` | 提示稍后重试 + 上报 |
| 503 | `DEPENDENCY_DOWN` | 依赖不可用，含 `detail.service` | 提示服务暂不可用 |

错误响应统一结构：

```json
{
  "code": "ROW_LIMIT_EXCEEDED",
  "message": "单次最多导出 10000 条，请缩小筛选范围",
  "field": null,
  "detail": { "limit": 10000, "actual": 10001 },
  "trace_id": "abc123"
}
```

## 分页约定

| 项 | 值 |
|---|---|
| 方式 | cursor / offset |
| 参数 | `cursor` + `limit` ／ `page` + `page_size` |
| 默认页大小 | 20 |
| 最大页大小 | 100 |
| 返回 total | 否（大表 count 昂贵）／ 是 |

## 幂等约定

| 操作 | 幂等 | 保证方式 |
|---|---|---|
| `GET` | 天然 | — |
| `POST /exports` | **需要** | 客户端传 `Idempotency-Key` 头（UUID），有效期 24h；重复请求返回**首次结果**（200，非 409） |

---

## 接口：创建导出任务

```
POST /api/v1/exports
```

**实现**：FR-01, FR-04, FR-06, FR-07

### 请求

| 头 | 必填 | 说明 |
|---|---|---|
| `Idempotency-Key` | 是 | UUID，24h 内重复请求返回首次结果 |

```json
{
  "filter": {
    "status": ["open", "pending"],
    "created_from": "2026-09-01",
    "created_to": "2026-09-07",
    "assignee_ids": [42, 43]
  },
  "format": "csv",
  "columns": ["ticket_no", "title", "created_at", "assignee_name"]
}
```

| 字段 | 类型 | 必填 | 校验 | 说明 |
|---|---|---|---|---|
| `filter.status` | string[] | 否 | 枚举 `open`/`pending`/`resolved`/`closed` | 不传 = 全部状态 |
| `filter.created_from` | date | 否 | ISO 日期 | 含当日 |
| `filter.created_to` | date | 否 | ≥ from，区间 ≤ 90 天 | 含当日 |
| `filter.assignee_ids` | int[] | 否 | 最多 50 个 | **权限校验：客服只能填自己的 ID（FR-04）** |
| `format` | string | 是 | 枚举 `csv` | 本轮只支持 csv |
| `columns` | string[] | 是 | 白名单校验，1–20 个 | 顺序即列顺序 |

### 响应

**202 Accepted**（行数超阈值，转异步）

```json
{
  "export_id": "exp_01H8X...",
  "status": "processing",
  "estimated_rows": 24800,
  "created_at": "2026-09-05T14:30:00Z"
}
```

**200 OK**（行数在阈值内，同步完成）

```json
{
  "export_id": "exp_01H8X...",
  "status": "completed",
  "row_count": 30,
  "file_url": "https://.../exp_01H8X.csv",
  "expires_at": "2026-09-12T14:30:00Z",
  "created_at": "2026-09-05T14:30:00Z"
}
```

| 字段 | 类型 | 可空 | 说明 |
|---|---|---|---|
| `export_id` | string | 否 | |
| `status` | string | 否 | `processing` / `completed` / `failed` |
| `row_count` | int | **是** | `processing` 时为 null |
| `file_url` | string | **是** | 仅 `completed` 时有值；有效期见 `expires_at` |
| `expires_at` | string | **是** | 文件过期时刻（NFR：保留 7 天） |
| `estimated_rows` | int | **是** | 仅 `processing` 时有值 |

### 错误

| 场景 | HTTP | code |
|---|---|---|
| `columns` 含非白名单列 | 400 | `INVALID_PARAM`（`field: "columns"`） |
| 客服尝试导出他人工单 | 403 | `FORBIDDEN_SCOPE` |
| 已有进行中的任务 | 409 | `EXPORT_IN_PROGRESS` |
| 预估行数 > 10000 且不支持异步 | 422 | `ROW_LIMIT_EXCEEDED` |
| 时间区间 > 90 天 | 400 | `INVALID_PARAM`（`field: "filter.created_to"`） |

---

## 接口：查询导出任务

```
GET /api/v1/exports/{export_id}
```

**实现**：FR-06（进度可见）

### 响应

**200 OK** —— 结构同上（创建接口的 200 响应）

`status: failed` 时：

```json
{
  "export_id": "exp_01H8X...",
  "status": "failed",
  "error": { "code": "SOURCE_QUERY_TIMEOUT", "message": "数据查询超时，请缩小范围重试" },
  "created_at": "2026-09-05T14:30:00Z"
}
```

### 错误

| 场景 | HTTP | code |
|---|---|---|
| 任务不存在 | 404 | `NOT_FOUND` |
| 查询他人的任务 | 403 | `FORBIDDEN_SCOPE` |

---

## 接口：导出历史列表

```
GET /api/v1/exports?cursor=<c>&limit=20
```

### 响应

```json
{
  "items": [ { "export_id": "...", "status": "completed", "row_count": 30, "created_at": "..." } ],
  "next_cursor": "eyJpZCI6MTAwMX0",
  "has_more": true
}
```

`items` 为空时返回 `[]`（不是 null），`next_cursor` 为 null 表示到底。

---

## 版本策略

| 变更类型 | 处理 |
|---|---|
| 新增可选请求字段 / 响应字段 / 错误码 | 直接加（前端须容忍未知字段、有 default 分支） |
| 删除或重命名字段 | **字段并存**：新旧同时返回 → 客户端迁移 → 标 Deprecated 并给下线日期 → 删除 |
| 改字段类型 / 收紧校验 / 改默认值 | 破坏性，同上走并存或新版本路径 |

## 对齐核对（/architect 整合时检查）

- [ ] 字段名与 `/dba` 的 DBML 一致（或明确了映射关系）
- [ ] 状态枚举值与 PRD 流转图、`db-spec` 第 2.1 节、`/qa` 用例一致
- [ ] 错误码与 `/frontend` 的处理分支一一对应
- [ ] 权限规则与 PRD 权限矩阵一致
- [ ] 时间字段语义与 `db-spec` 第 2.2 节一致（记录时间 vs 业务时间）
