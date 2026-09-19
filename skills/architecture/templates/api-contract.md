<!-- sdlc:unfilled — 写入真实内容后删除本行；未填写的模板不算交付 -->
# API 契约 · <功能名>

> canonical 版本：<version>｜状态/授权：<record>｜上游：<spec@revision + FR/NFR IDs>
> 消费方及兼容范围：<backend / frontend / SDK / 外部客户 / QA>

使用项目现有协议与错误规范，引用其版本；以下导出例仅展示契约完整性，不预设项目必须异步。业务批准异步后才采用。

## 通用约定

| 项 | 定义 |
|---|---|
| 地址 / 认证 / 授权 | <协议、路径、主体、租户与对象级校验> |
| 字段 | <required 与 nullable 分开；未知字段与枚举的消费者行为> |
| 时间 | <格式、单位、时区；日期/时刻/当地日程区别> |
| 错误 | <稳定 code、结构、可重试性、trace_id；不泄露内部敏感信息> |
| 限流/预算 | <大小、时限、速率、Retry-After 如适用> |
| 分页（如适用） | <cursor/offset、稳定排序、页大小、total 与并发更新语义> |

## 示例：创建异步导出

`POST /api/v1/exports`；请求字段、约束、权限与上游 FR 逐项映射。

```json
{"filter":{"status":["open"]},"format":"csv"}
```

请求成功返回 **202**（受理而非完成）：

```json
{"export_id":"exp_1","status":"processing","estimated_rows":24800,"created_at":"2026-09-05T14:30:00Z"}
```

幂等键作用域为 `<租户 + 主体 + 操作 + Idempotency-Key>`；定义有效期与规范化请求指纹。示例策略：同键同载荷重放首次受理的 **202 与同一响应体**，不改成 200、不重复创建任务；当前进度通过 GET 获取。同键异载荷返回 409 `IDEMPOTENCY_CONFLICT`。并发请求由原子占位协调；首次事务未提交时重试行为、失败恢复、过期键和任务状态保留期限须在实际契约补全。生产实现必须验证去重记录与任务创建的原子性。

## 示例：查询状态

`GET /api/v1/exports/{export_id}` 返回 **200** 和下列联合类型之一。每次校验对象归属；404/403 的存在性披露政策按项目定义。

| 字段 | required | nullable | 状态条件 / 含义 |
|---|---|---|---|
| export_id, status, created_at | 是 | 否 | 所有状态；status 为 processing/completed/failed |
| estimated_rows | 否 | 否 | processing 可出现；省略表示未知 |
| row_count, file_url, expires_at | completed 时必须，其他状态禁止 | 否 | 完成后的结果与访问期限 |
| error | failed 时必须，其他状态禁止 | 否 | 稳定 code 与可展示 message |

```json
{"export_id":"exp_1","status":"completed","row_count":24800,"file_url":"https://example.invalid/download/exp_1","expires_at":"2026-09-12T14:30:00Z","created_at":"2026-09-05T14:30:00Z"}
```

```json
{"export_id":"exp_1","status":"failed","error":{"code":"SOURCE_QUERY_TIMEOUT","message":"查询超时"},"created_at":"2026-09-05T14:30:00Z"}
```

processing 使用创建响应的同一结构。若项目选择显式 null，须同时修改表与全部示例。下载地址需访问控制与有效期语义；示例 URL 不代表公开文件。

## 失败与重试

| 场景 | 协议状态 / code | 重试/恢复 | 消费者行为 |
|---|---|---|---|
| <输入、鉴权、权限、冲突、限流、依赖/内部失败> | | | |

## 演进与核对

<列出现有消费者及版本、兼容性验证、破坏性变更的 expand-contract 和退出条件。新增字段/枚举也须验证严格客户端。>

- 对齐需求权限、状态机和 GWT；引用数据字典/DBA 的字段语义和显式映射，不要求 API 字段机械等同表字段。
- 表格、schema、成功/失败/重试示例相互一致；已有 OpenAPI/IDL 是权威时本文件只链接，避免双份定义。
- 接口幂等、事件顺序及时间语义的方法只维护在 `references/contract-design.md`。
