<!-- sdlc:unfilled — 写入真实内容后删除本行；未填写的模板不算交付 -->
# 实现证据 · <T-n / fix / explore / evaluate> <标题>

> 任务：`<implement/T-n | fix | explore | evaluate>`｜角色：`<frontend | backend | algo | miner>`｜`lane_file`：`<ui | api | ai | model>`
> 输入基准：票/问题 `<path@rev>` · FR/GWT `<IDs>` · 契约/原型/schema/eval `<paths@rev>`｜代码版本：`<commit>`｜日期：`<YYYY-MM-DD>`

保留本角色对应泳道与激活的伴随技能小节；不适用小节单行注明 `N/A + 原因` 后裁剪，严禁留空占位。行业专项义务对照 `references/industry-delivery-sops.md`。

## 1. 写入范围与上游契约对齐

| 文件路径 | 性质（新增/修改） | 对应契约 / 组件 / 规则锚点 | 是否在 packet `source_writes` 内 |
|---|---|---|---|
| `<path>` | <新增/修改> | <端点 / `data-component` / 评估器 / 特征> | ✅ |

- **契约零擅自漂移**：☐ 未私改 GWT / `schema.dbml` / tokens / 错误码（发现上游缺口已退回 `pm` / `dba` / `designer` / `architect`：`<无 或 问题描述>`）

## 2. 工程原则与高阶红线自检（全角色必填）

- ☐ **边界解析与消除非法状态**：不可信输入在入口一次性解析为窄类型/强 ID；状态用可辨识联合表示，无冲突布尔标记汤。
- ☐ **深模块与接口隔离（DIP / ISP / LoD）**：无浅层透传壳；跨层传窄 DTO/Props，零 ORM 越层泄露、零 `a.b.c.d()` 跨界穿透。
- ☐ **唯一事实源（DIE vs AHA）**：共享可见性谓词、输入限额、枚举与错误码单点同源；不同业务角色未用布尔开关强行合并。
- ☐ **读写分离与进程无状态（CQS & Statelessness）**：查询/预检零写副作用与零计费；**无模块级全局可变 `dict`/内存锁承载跨实例状态**。
- ☐ **全面有界与三态恢复**：查询/分页/并发/超时/重试抖动/token 均有硬上限；外部写超时按 `In-Doubt` 查回执/幂等恢复，严禁盲目重发。

## 3. 泳道专项核对（仅保留当前 `lane_file` 及激活伴随块）

### `[api]`（`backend` 必填）
- **分层与纯核心**：☐ `Router -> Service -> Repository` 单向依赖（复杂规则抽离零 I/O 纯核心） ☐ 冷启动子进程独立 `import` 通过
- **契约错误码与可执行契约测试（硬准出）**：☐ **100% 实现 LLD 错误分类**并返回契约精确 `code`（零泛化 `500` 或私造错误码） ☐ 移交 `qa` 前已执行**可执行契约测试**（校验响应结构、HTTP 状态码、字段可空性与错误信封，`exit: 0`）
- **LLD 韧性路径落盘（零静默省略）**：LLD 定义的重试（带抖动与预算）/ 熔断器 / 降级回退路径 → `<全部已实现 | 本次不实现（原因+授权）：<路径名 + 原因 + architect/pm 授权记录引用>>`
- **事务 / 幂等 / 并发 / 外部依赖**：事务边界 `<说明>`；幂等唯一约束 `<约束名>`（零先查后插）；条件更新 `rows == 0` `<处理方式>`；外部调用置于事务外并配超时 + Brownout 降级（账务类走只追加复式分录，禁单列覆盖余额）
- **ORM ↔ `schema.dbml` 原子对齐**：☐ 字段/可空/唯一键/外键/索引排序方向（`ASC`/`DESC`）及打包清单（如 `pyproject.toml`）1:1 一致（破坏性/共享表变更已交 `dba`）；附上 `SHOW CREATE TABLE` / `alembic check` 摘要
- **可观测与四类必测**：☐ 入口耗时与 `trace_id` 齐全且日志零敏感信息（密码/token/PII） ☐ 回滚 / 幂等竞态 / 并发冲突 / 依赖超时 `In-Doubt` 已测（或注明 `N/A + 理由`）

### `[ui]`（`frontend` 必填）
- **契约生成类型与并行 Mock（硬准出）**：☐ 从锁定契约文件（`02-shape/contract.md` / OpenAPI）直接生成 TypeScript 类型与 Mock 并行开发（零手写漂移接口） ☐ 生成类型编译通过（`tsc --noEmit` / 构建 `exit: 0`），确保联调仅处理真实业务状态
- **原型与 Token 还原**：定稿原型 `02-shape/prototypes/final/` 全部 `data-component` 与状态路由已映射；零硬编码色值/间距（`python3 PLUGIN_ROOT/skills/impl-evidence/scripts/check-frontend.py` 退出码 `0`）
- **7 交互态 × 页面状态矩阵与零 `TBD` 文案（硬准出）**：☐ 全部交互组件已覆盖并实证 **7 种交互态（`default, hover/focus, disabled, loading, empty, error, success`）× 适用页面状态** ☐ 全局界面文案**零 `TBD` / 占位符** ☐ 初次骨架 vs 刷新保旧 ☐ 初始空 vs 筛选空 ☐ 按稳定 `code` 分支报错并含 `trace_id` ☐ 权限/离线/极端边界已实测 ☐ 服务端状态归查询缓存、筛选分页归 URL ☐ 跨项目条目操作按 `item.project_id`/`owner_id` 路由 ☐ 键盘焦点与对比度达标

### `[ai]`（`algo` 必填）
- **可复现五锚点与预注册实验判据**：随机种子 `<seed>` · 依赖锁文件 `<lockfile@sha>` · **固定数据集快照 ID** `<eval-set-v<n>@snapshot_id（严禁写 latest partition）>` · 配置摘要 `<config SHA-256>` · 容器/运行时与模型版本摘要 `<digest>`；☐ **先过离线门禁，再进在线 A/B 或 Interleaving**（事前锁定 `1` 个主指标 + `≤ 3` 个次要/护栏指标 + 停止规则）
- **评估基准与单变量迭代**：绑定 `eval-set-v<n>`（冻结 `test` 集）；最简规则基线 `<分数>` vs 选定方案 `<分数>`（完整保留全部正向与负向轮次表）
- **Fail-Closed 上下文契约与三层降级**：☐ 检索层强制 `tenant_id`/ACL 过滤且契约违例暂停告警（禁静默胡编） ☐ 用户输入分隔防注入 + 输出 schema/引用校验 ☐ 步数/token/成本熔断器 + 工具沙箱/HITL 生效 ☐ 主模型 → 备模型 → 规则/拒答降级链已注入验证

### `[model]`（`miner` 必填）
- **双时间戳防泄漏与可复现五锚点**：绑定业务动作与容量上限指标（`Precision@K` / `lift` / `PR-AUC` / 校准）；☐ 特征字典同时声明 `event_time` 与 `availability_time` 且严格按 **`(entity, availability_time <= decision_time)`** 关联 ☐ 重叠窗口版本化特征回填测试输出**字节级完全一致（byte-identical）** ☐ 锁定五锚点（`seed` / `lockfile` / **固定快照 ID 禁 `latest partition`** / `config SHA-256` / `runtime digest`） ☐ 统计变换仅在训练集 `fit` ☐ Top-10 特征通过三问核查 ☐ 时间/实体切分 + 滚动折方差 `<数值>`
- **Fail-Closed 特征契约、PSI/KS 对齐与实验预注册**：☐ 特征契约（schema/可空/值域/行数/新鲜度 SLA）违例时**暂停推理并告警**（严禁静默降级带病推理） ☐ 训练/服务特征代码同源或抽样 `N` 条线上请求离线重算：`mismatches: 0` 且逐特征 **PSI / KS 分布检验**达标 ☐ 预注册「先离线门禁、后在线 A/B 或 Interleaving」（`1` 主指标 + `≤ 3` 次要/护栏指标 + 上线前停止规则） ☐ 下游分群/分值已整理为提案交 `data-warehouse-engineer` 登记 `data/tags.yaml`（`miner` 不直写该文件）

### `[fix / debug]`（`implement/fix` 或携带 `debug_protocol` 时追加 `## Debug record`）
- **复现命令与退出码** → **已排除假设（`hypothesis -> probe -> result`）** → **`root_cause` 确认机制** → **最小改动面** → **原命令重跑结果**

### `[tdd / refactor]`（伴随技能激活时必填）
- **TDD Red → Green**（红灯预期失败须单独标明 `Red (expected pre-impl failure)` 与字面量独立期望值，严禁混入第 4 节终态通过命令块以免触发 `EVIDMISMATCH`；补充守恒/幂等性质断言）：`<逐条 GWT 红→绿摘要与输出>`
- **Refactor Steps**：首改前特征化测试 `exit: 0` → 每步单一缝隙（删除测试/降耦合）命令 + `exit: 0` → 测试适配等价性说明 → 行为零差异结论

## 4. 定向自测证据（严禁跑无关全量测试套件）

> 原样粘贴**定向**测试、架构/前端静态检查与构建命令及退出码（终态验证命令须全部 `exit: 0`；未执行项坦白标 `unverified`）：

```text
$ <定向单元/并发/评估/一致性检查命令>
<原样输出>
exit: 0

$ <定向分层 / check-frontend.py / 构建检查命令>
<原样输出>
exit: 0
```

| GWT / NFR / 埋点 ID | 覆盖用例或验证动作 | 结果 | 下游交接角色与说明（`qa` / `frontend` / `backend` / `architect` / `dba` / `sre` / `pm` / `data-warehouse-engineer`） |
|---|---|---|---|
| `<GWT-n / NFR-n / EV-n>` | `<test_name 或命令>` | ✅ | `<需真库/真机复验边界或标签提案>` |
