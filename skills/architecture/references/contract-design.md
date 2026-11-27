# 契约设计

契约是「工件即消息」的核心载体。**契约定了，`backend` 与 `frontend` 才能并行开工**；契约含糊，联调时必然返工。

## 可执行契约锁定（Executable Contract Lock）与契约先行纪律

手写 Markdown 表格容易与代码静默漂移；跨前后端/跨服务协作必须把**提交进 Git 的机器可读契约文件（`OpenAPI` `openapi.yaml` / `JSON Schema` `*.schema.json` / `Protobuf` `*.proto`）升格为可执行唯一事实源（Executable SSOT）**：

1. **同源双轨并行**：契约文件锁定入库后，`frontend` 直接生成 TypeScript 类型与契约 Mock 并行开发界面，`backend` 跑契约一致性测试（Contract Test）验证真实 Handler 输出；Markdown 文档（`api-contract.md`）仅补充业务语义、三态恢复与演进策略，严禁手抄第二份字段表（DIE）。
2. **契约先行修改纪律（Contract-First Edit Discipline）**：**先改契约文件 → 重新生成类型与跑契约测试 → 再改业务代码；新增向后兼容，删改字段走新版本或 expand-contract**。严禁开发私自改接口字段后再倒补文档。
3. **门禁校验**：通过 `skills/architecture/scripts/check-contract.py`（项目在 `sdlc.config.yaml` 开启 `extra_gates: [contract]` 与 `contract_spec`）在阶段门禁与 CI 自动拦截契约语法缺陷、悬空引用与未走版本演进的破坏性变更。

## 核心原则：边界解析、消除非法状态与读写分离

- **边界解析而非散落校验（Parse, Don't Validate）**：所有不可信输入（HTTP 请求体/查询参数、Webhook、CLI 参数、IPC 消息、LLM 输出）在信任边界**一次性解析**为窄类型领域对象、具名枚举、精确最小货币单位与强区分标识（如区分 `TenantId`、`UserId`、`ProjectId`，避免长整型位置传参错位）；禁止把裸 `dict` 或未归一化字符串直接塞进 `Service` 反复 `if` 判断。
- **让非法状态不可表示（Make Illegal States Unrepresentable）**：用按状态区分的可辨识联合（Discriminated Union，如 `status: "processing" | "completed" | "failed"` 各自绑定专属字段）替代互相矛盾的布尔标记与可空字段组合（如 `is_completed=true` 却 `error != null` 且 `file_url == null`）。
- **接口隔离（ISP）与命令查询分离（CQS）**：按消费者实际需求定义窄响应 DTO（严禁直接序列化 ORM 实体）；`GET` / `HEAD` / 预览 / 能力探针 / `--dry-run` 必须严格零业务状态修改、零计费额度扣减；写命令通过显式幂等键与状态守卫变更数据。

## 四大联调返工源必锁核对表 + 版本策略（按接口适用性裁剪）

写明本次适用项；不分页的接口无需编造分页方案。复用项目既有规范时引用其版本。以下四类模糊点占前后端联调返工的绝大多数，出站前必须逐项锁死：

### ① 返工源三：可区分错误码清单（`400/422` 字段级 vs `401/403` 鉴权 vs `5xx` `trace_id`）

只写成功响应的契约等于没写——失败语义也是消费者依赖的契约。

```
200  成功
400  参数校验失败      { code: "INVALID_PARAM", field: "row_limit", message: "..." }
401  未认证
403  无权限            { code: "FORBIDDEN_SCOPE", message: "只能导出自己负责的工单" }
404  资源不存在
409  冲突              { code: "EXPORT_IN_PROGRESS", message: "已有导出任务进行中" }
422  业务规则不满足    { code: "ROW_LIMIT_EXCEEDED", detail: { limit: 10000, actual: 10001 } }
429  限流              响应头 Retry-After
500  服务端错误        { code: "INTERNAL_ERROR", trace_id: "..." }
503  依赖不可用        { code: "DEPENDENCY_DOWN", detail: { service: "storage" } }
```

纪律：

- **业务错误用稳定的 `code` 字符串，不用 HTTP 状态码区分**。HTTP 码粒度太粗，前端需要区分「行数超限」和「已有任务在跑」
- `message` 是给人看的，**前端不许用它做逻辑判断**（文案会改、会国际化）
- 校验失败要指出**哪个字段**
- 5xx 要带 `trace_id`，否则排查时无法关联日志

### ② 返工源二：分页与排序默认值（`0/1-based`、页大小、`INVALID_SORT_FIELD`）

| 方式 | 参数 | 适用 | 注意 |
|---|---|---|---|
| offset | `page`（**显式锁死 `1-based` 还是 `0-based`**）/ `page_size` | 需要跳页 | 深分页性能差（见 `dba` 的 explain-reading） |
| cursor | `cursor` / `limit` | 无限滚动、大数据集 | 不能跳页；游标须含排序键 + 唯一打破平局键（如 `created_at + id`） |

必须写明：
- **页码起始基准（`0-based` vs `1-based`）**、**默认 `page_size`**、**最大 `page_size`**（超限截断还是返 `400` 须锁死）、**`total` 返回策略**（大表 count 昂贵，不需要就不返）；
- **默认排序字段与方向**（如默认 `created_at desc, id desc`）及允许排序字段白名单；
- **非法排序字段确定性报错**：当客户端传入不存在或未加入白名单的 `sort` 字段时，**确定性返回 `400 INVALID_SORT_FIELD`（带 `field: "sort"`）**，严禁静默退回默认排序掩盖客户端拼写 bug，更严禁拼接 SQL 抛 `500`。

### ③ 写幂等与 `DELETE` 不存在资源的锁定语义

写操作必须回答：**重复请求会怎样？删除已不存在的资源返回什么？**

| 操作 | 幂等 | 保证方式 |
|---|---|---|
| `GET` `PUT` | HTTP 定义的预期效果具有幂等语义 | 实现必须遵守；检查实际业务副作用与失败窗口 |
| `DELETE` | **必须显式二选一锁死** | 删除不存在/已删除资源时，契约必须明确锁死返回 **`200/204` 幂等成功** 还是 **`404 NOT_FOUND`**（同一 API 表面内严禁各接口各自为政） |
| `POST` 创建 | **需要显式设计** | 客户端传 `Idempotency-Key` 头，服务端唯一约束去重 |
| `POST` 触发动作 | 需要显式设计 | 业务键去重（如「同一用户同一分钟只能触发一次导出」） |

仅靠未受保护的「先查后插」会竞态。使用适用的唯一约束、条件写或事务/锁机制，并覆盖**提交成功但响应丢失（`In-Doubt` 三态）**的情况：客户端读超时后必须沿用同一幂等键重放或查询状态接口，去重记录与外部副作用之间还需对账/恢复协议。

契约写清键来源和作用域（租户/调用者/操作）、请求指纹、有效期、并发处理、同键不同载荷的冲突、进行中/已完成/失败后的重试语义，以及去重记录与副作用的原子性/恢复。参考 [RFC 9110 §9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)。

### ④ 返工源四：空值语义（`[]` 禁 `null`；省略 vs `null` vs 默认值）

每个字段分别标记 **required（键必须出现）** 与 **nullable（值可取 `null`）**。**省略字段（`undefined`/omitted）、显式传 `null`（清空/未设置）与使用服务端默认值**是三种截然不同的语义（尤其在 `PATCH` 更新中），schema 与所有响应/请求示例必须严格一致：

```
{
  "id": 1001,                    // required: true, nullable: false
  "assignee": {                  // required: true, nullable: true —— null 表示工单未分配
    "id": 42, "name": "张三"
  },
  "resolved_at": null,           // null —— 未解决（不是「未知」，也不是空字符串 ""）
  "tags": []                     // 集合类型永远返 []，严禁返回 null
}
```

新建 JSON 接口约定（与既有契约冲突时优先保持兼容并明确迁移方案）：
- 集合/列表类型**永不返回 `null`**，一律用 `[]`（空映射用 `{}`）
- 明确区分省略字段、`null`（「未设置 / 清空」）与默认值；严禁用空字符串 `""` 或魔法数字 `-1` 代替 `null`

### ⑤ 返工源一：类型与单位锁定（时间 `ISO-8601 UTC` vs epoch · 金额 `分/cents` vs decimal · 布尔 `true/false` vs `0/1`）

跨语言/跨端最常见的隐性精度与反序列化事故来自类型与单位混用，契约必须逐类锁死：
- **时间与时区**：新建 JSON 接口统一用带时区的 **ISO-8601 UTC**（`2026-09-05T14:30:00Z`），若沿用数值 epoch 必须锁死单位是**秒（`s`）还是毫秒（`ms`）**；严格区分纯日期 `2026-09-05` 与时刻 `2026-09-05T14:30:00Z`，禁用无时区本地时间字符串；当地营业/重复日程另带 IANA 时区名。
- **金额与计量单位**：严禁使用 IEEE-754 浮点数（`float/double`）传金额！必须显式锁死采用**最小货币整数单位（如人民币 `分` / USD `cents` + ISO-4217 `currency`）**，或带固定小数位约束的**精确十进制字符串（如 `"199.00"`）**；时长、字节数、百分比等字段字段名须带单位后缀（如 `timeout_ms`、`max_size_bytes`、`progress_bps`）。
- **布尔值**：JSON/OpenAPI 严守原生布尔 `true / false`，**严禁混用整数 `0 / 1` 或字符串 `"true" / "false"`**（历史遗留库映射在边界 Adapter 内消化，不得泄漏到契约层）。

### ⑥ 版本策略

| 变更 | 破坏性 | 处理 |
|---|---|---|
| 新增可选请求参数 | 否 | 直接加 |
| 新增响应字段 | 取决于消费者 | 检查严格解码/签名/生成客户端等兼容性，确认可容忍后扩展 |
| 新增错误码 | 边界 | 前端要有 default 分支 |
| 删除/重命名字段 | **是** | 走 expand-contract：先加新字段并存 → 客户端迁移 → 删旧字段 |
| 改字段类型 | **是** | 同上 |
| 收紧校验规则 | **是** | 原本能过的请求会失败 |
| 改默认值 | **是** | 不传该参数的客户端行为变了 |

破坏性变更的三种承载方式：

| 方式 | 例 | 适用 |
|---|---|---|
| 路径版本 | `/api/v2/tickets` | 大版本改造 |
| 字段并存 | 同时返回 `user_name` 与 `username` | 单字段演进（首选，成本最低） |
| 请求头协商 | `Accept: application/vnd.api.v2+json` | 需要细粒度控制 |

**字段并存是最常用也最省事的**，配合弃用期（在响应头或文档标注 `Deprecated`，给出下线日期）。

## 事件契约

事件比 API 更容易出问题，因为生产方看不到消费方。**四件事必须写明**：

### ① 投递语义

| 语义 | 含义 | 对消费方的要求 |
|---|---|---|
| 至多一次 | 可能丢 | 能容忍丢失（很少可接受） |
| **至少一次** | 可能重复 | **消费方必须幂等**（最常用） |
| 恰好一次 | 指定范围与故障假设下效果一次 | 核对 broker、事务边界、消费提交和外部副作用；不等同于全链路绝不重复 |

绝大多数消息中间件给的是「至少一次」。所以**消费幂等不是可选项**，契约里要显式写出幂等键是哪个字段。

### ② 顺序保证

```
无顺序保证        —— 消费方不能依赖先后（最常见）
分区内有序        —— 同一分区键（如同一订单 ID）的事件有序
全局有序          —— 单分区，吞吐受限
```

写清分区键是什么。**「订单状态变更事件」如果不按订单 ID 分区，消费方可能先收到 `shipped` 再收到 `paid`。**

### ③ 事件内容：状态传递 vs 增量通知

| 形态 | 内容 | 优点 | 缺点 |
|---|---|---|---|
| 增量通知 | 只有 ID 和变更类型 | 载荷小 | 消费方要回查，产生耦合与负载 |
| **状态传递** | 携带完整的相关状态 | 消费方自治，无需回查 | 载荷大，有冗余 |

**倾向状态传递**——消费方不必回调生产方，解耦更彻底。载荷里带上消费方需要的字段（生产方需要知道消费方要什么，这是契约协商的一部分）。

区分事件 schema_version、event_id 与业务聚合版本。需要处理乱序时指定 aggregate_id、单调版本/序列及比较规则；说明并发写、缺口、补发和旧版本处理。普通时间戳可能碰撞或受时钟偏移影响，不能独自保证顺序；occurred_at 主要表达事件时间。

### ④ 事件契约示例

```yaml
event: ticket.exported
version: 1
partition_key: export_id          # 仅在基础设施保证下同一导出任务内有序
delivery: at-least-once
idempotency_key: event_id         # 每个事件独立标识；重投沿用同一 ID
payload:
  event_id:     string   required  # 事件去重键
  aggregate_version: integer required # 同一导出任务的单调版本
  export_id:    string   required  # 聚合标识
  tenant_id:    integer  required
  actor_id:     integer  required
  row_count:    integer  required
  format:       string   required  # csv | xlsx
  occurred_at:  string   required  # ISO 8601 UTC，事件时间，不独自承担排序
  file_url:     string   optional  # 异步导出完成后才有
consumers:
  - 审计服务（记录导出行为）
  - 埋点服务（上报 export_completed）
producer_guarantees:
  - 事件在业务事务提交后发出（业务与 outbox 同事务；投递重试、监控和恢复另有义务）
  - 同一 event_id 可能重复投递；消费按聚合版本处理旧事件
```

**`consumers` 一栏很重要**：它让「改这个事件会影响谁」变得可见。加字段前先看这一栏。

## 流式传输契约（SSE / WebSocket / AI Streaming，适用时）

当切片涉及实时生成、长任务进度流或双向会话时，契约必须显式声明：

1. **类型化帧协议**：固定事件帧枚举（如 `event: meta | delta | tool_call | citation | usage | error | done`），每帧 JSON 含单调 `seq` 与 `run_id` / `trace_id`。
2. **中途失败与预算熔断语义**：HTTP `200 text/event-stream` 响应头一旦刷出，上游超时、安全拦截或 token/步数超限时**必须发送结构化 `event: error`（含稳定 `code`、`retryable`、`trace_id`）后关闭流**，严禁静默截断把半截输出伪装成正常完成。
3. **反缓冲、心跳与断连传播**：声明网关反缓冲头（如 `X-Accel-Buffering: no`）、保活心跳间隔、断线续传游标（`Last-Event-ID` 或 `resume_cursor`，不支持续传须写明重开语义），以及客户端取消（`AbortController`）向后端推理/工具任务的取消传播。

## CLI / SDK 与本地桥接契约（适用时）

- **CLI 契约**：标准输出 `stdout` 在 `--json` 模式下仅输出符合 schema 的纯机器可读结构；进度条、告警与诊断日志一律走 `stderr`；固定退出码语义（如 `0` 成功、`1` 业务/运行失败、`2` 参数/用法错误）；支持非交互无 TTY 环境（`--no-input`）与零副作用预演（`--dry-run`）。
- **SDK 与 N-2 兼容契约**：显式实例化配置（严禁模块级全局鉴权态污染多租户调用），注入超时与退避策略，暴露类型化异常层级（携带 `code`、`retryable`、`trace_id`），对未知新增响应字段与枚举保持前向容忍（满足客户端/固件异步升级的 `N-2` 兼容窗口）。
- **IPC / JSBridge / Deep Link**：将渲染进程、WebView 与外部 URI 视为不可信输入，契约显式列出命令白名单、来源校验与规范化路径边界（禁 `../` 越界）。

## 数据契约（给 dba）

架构师给 `dba` 的不是表结构，是**业务语义诉求**：

```
实体诉求：
  导出任务 —— 一行 = 一次导出请求
    需要记录：谁发起、筛选条件、行数、状态、文件位置、失败原因
    生命周期：创建 → 处理中 → 完成/失败；完成后文件保留 7 天（NFR-06）
    访问模式：按发起人查最近 10 条（用户看自己的导出历史）
              按状态查待处理（异步 worker 拉取）

约束诉求：
  同一用户同一分钟内只能有一个进行中的导出任务（FR-06 防滥用）
  → 这是唯一性约束还是应用层判断？请 dba 判断
```

**不要写「建一张 export_tasks 表，字段 id/user_id/status…」**——那是越界。给语义和约束，让 `dba` 用他的方法链推导结构。

## 契约评审清单

- [ ] **可执行契约锁定**：机器可读契约（`OpenAPI / JSON Schema / Protobuf`）已提交 Git 作为唯一事实源，遵守「先改契约 → 重生类型与跑契约测试 → 再改业务代码」，并通过 `scripts/check-contract.py` 校验
- [ ] 边界输入一次解析为窄类型/强标识；响应以可辨识联合消除冲突布尔/可空组合；`GET`/预检严格无副作用（CQS）
- [ ] **返工源①（类型与单位）**：时间（`ISO-8601 UTC` vs epoch `s/ms`）、金额（`分/cents` 整数 vs 精确十进制，禁 float）、布尔（`true/false` 禁混 `0/1`）及单位后缀全部锁死
- [ ] **返工源②（分页与排序）**：`0-based` vs `1-based` 页码（或 `cursor`）、默认/最大 `page_size`、默认排序已定；未知排序字段确定性返回 `400 INVALID_SORT_FIELD`
- [ ] **返工源③（可区分错误码）**：`400/422` 携带稳定 `code` + `field`，与 `401/403` 鉴权、`409` 冲突、`429` `Retry-After`、`5xx`（必带 `trace_id`）清晰区分，前端零 `message` 分支
- [ ] **返工源④（空值与删除幂等）**：集合永返 `[]` 不返 `null`；省略 vs `null` vs 默认值语义明确；`DELETE` 不存在的资源显式锁死为 `200/204` 幂等成功或 `404`，写超时 `In-Doubt` 恢复行为已定
- [ ] 版本与 N-2 兼容策略已定；删改字段破坏性变更走新版本或 `expand-contract`
- [ ] 流式（SSE/WS）或 CLI/SDK/IPC 帧协议、中途错误帧与退出码已定（如适用）
- [ ] 事件契约含投递语义、分区键、幂等键、聚合单调版本与 consumers 清单；给 `dba` 的是业务语义与约束，不是表结构
