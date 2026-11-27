<!-- sdlc:unfilled — 写入真实内容后删除本行；未填写的模板不算交付 -->
# API 契约 · <功能名>

> canonical 可执行契约文件（Git SSOT）：`<openapi.yaml / *.schema.json / *.proto>@<version>`｜状态/授权：<record>｜上游：<spec@revision + FR/NFR IDs>
> 消费方及兼容范围：<backend / frontend（生成 TS 类型 + Mock）/ CLI / SDK / 外部客户 / qa（注意 N-2 兼容要求）>
> **契约先行纪律（Contract-First）**：先改 Git 内机器可读契约文件 → 重新生成前端 TS 类型/Mock 并跑后端契约测试与 `scripts/check-contract.py`（`extra_gates: [contract]`）→ 再改业务代码；新增向后兼容，删改字段走新版本或 `expand-contract`。本文件仅记录业务语义增量与恢复协议，严禁手抄第二份易漂移的字段表（DIE）。

使用项目现有协议与错误规范并引用其版本；以下异步导出例仅展示契约完整性，业务批准异步后才采用。方法唯一来源：`references/contract-design.md`。

## 通用约定、边界解析与四大返工源锁定（Parse, Don't Validate）

| 项 | 显式锁定定义（零口头猜测） |
|---|---|
| 地址 / 认证 / 授权 | <协议、路径；主体与 `tenant_id` 从服务端鉴权态解析，每次对象级校验> |
| **返工源① 类型与单位** | <时间：`ISO-8601 UTC`（区分日期 `YYYY-MM-DD` 与时刻 `...Z`）或锁死精度 `s/ms` 的 epoch；金额：最小货币整数单位 `分/cents` + `currency` 或精确十进制字符串（严禁 float）；布尔：严守 `true/false`（禁混 `0/1`）；数值带单位后缀> |
| **返工源② 分页与排序默认值** | <显式锁死 `1-based` 还是 `0-based` `page`（或含排序键+唯一 ID 的 `cursor`）；默认与最大 `page_size`；`total` 是否返回；默认排序字段/方向；**传入不存在或未白名单开放的排序字段时确定性返回 `400 INVALID_SORT_FIELD`**> |
| **返工源③ 可区分错误 `code`** | <`400/422` 参数/规则校验失败（带稳定 `code` + 字段级 `field`）vs `401/403` 认证/权限 vs `409` 冲突 vs `429` `Retry-After` vs `5xx`（必带 `trace_id`，零内部堆栈泄露）；严禁前端凭 `message` 分支> |
| **返工源④ 空值与 `DELETE` 幂等** | <集合永返 `[]` 禁返 `null`；严格区分字段省略、`null` 与默认值；可辨识联合消除冲突布尔组合；**`DELETE` 不存在的资源显式锁死为 `200/204` 幂等成功 或 `404`（全接口一致）**> |
| 读写分离（CQS）与窄响应（ISP） | <`GET`/预检/dry-run 零业务写副作用与零计费消耗；按消费者裁剪响应 DTO，不透传 ORM> |
| 有界预算与流式 / CLI-SDK | <请求体上限、超时、AI 步数/token 上限；SSE 事件帧 `delta/error/done` 与断连取消，或 CLI `--json` stdout/stderr 分离与退出码；不适用写 N/A> |

## 示例：创建异步导出（命令端）

`POST /api/v1/exports`（请求字段、限额与上游 FR 逐项同源映射）：

```json
{"filter":{"status":["open"]},"format":"csv"}
```

受理返回 **202**：`{"export_id":"exp_1","status":"processing","estimated_rows":24800,"created_at":"2026-09-05T14:30:00Z"}`。
幂等键作用域 `<tenant_id + actor_id + operation + Idempotency-Key>` + 规范化请求指纹：同键同载荷重放首次 **202 与同一响应体**；同键异载荷返 409 `IDEMPOTENCY_CONFLICT`；写请求读超时进入 **`In-Doubt`**，客户端须重放同一幂等键或查状态接口，严禁换新键盲目重发。

## 示例：查询状态（可辨识联合响应，消除非法组合）

`GET /api/v1/exports/{export_id}` 返回 **200**，按 `status` 区分合法字段组合：

| 字段 | required | nullable | 状态不变量 |
|---|---|---|---|
| export_id, status, created_at | 是 | 否 | `status ∈ {processing, completed, failed}` |
| estimated_rows | 否 | 否 | 仅 `processing` 可选出现 |
| row_count, file_url, expires_at | `completed` 必返，其余禁止 | 否 | 受控签名访问与有效期 |
| error (`code`, `message`) | `failed` 必返，其余禁止 | 否 | 稳定 `code`，不凭 `message` 分支 |

```json
{"export_id":"exp_1","status":"completed","row_count":24800,"file_url":"https://example.invalid/download/exp_1","expires_at":"2026-09-12T14:30:00Z","created_at":"2026-09-05T14:30:00Z"}
```
```json
{"export_id":"exp_1","status":"failed","error":{"code":"SOURCE_QUERY_TIMEOUT","message":"查询超时"},"created_at":"2026-09-05T14:30:00Z"}
```

## 失败、三态恢复与演进核对

| 场景（输入 / 鉴权 / 冲突 / 限流 / 依赖超时 `In-Doubt` / Brownout） | 状态码与 `code` | 服务端恢复 / 对账保证 | 消费方重试或降级行为 |
|---|---|---|---|
| <逐类填写> | | | |

- 破坏性变更走 `expand-contract`（字段并存 + 弃用期或版本路径）；新增响应字段/枚举须核严格解码客户端与 N-2 兼容性。
- 表格、schema 与示例严格一致；已有 OpenAPI/Protobuf 为权威时本文件仅链接增量，严禁维护双份易漂移定义（DIE）。
