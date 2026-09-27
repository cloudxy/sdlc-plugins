# auto_agents 项目经验归档（插件维护者档案）

这里的前 12 份文件原先放在各 skill 的 `references/auto-agents-pitfalls.md`（第一轮，2026-09-24）；`collect.md` 是第二轮（2026-09-27）从 collect 的参考文件和模板里移出的项目约定原文。内容是 auto_agents 这一个项目里核实过的坑（代码与测试、ESC 编号、闸门命令与退出码）。按照方案 3.7：

- 项目里核实的坑属于项目本身，应记在该项目的 `.sdlc/_lessons.md`；插件 skill 只保留跨项目成立的原则。
- 插件没有 auto_agents 仓库的写入条件，所以没有替它写文件；这些条目先留在这里，**任何 skill 都不再路由到它们，角色不会默认加载**。
- 没有删除任何条目，事故证据保留在原文件里（未改写）。

接收方：auto_agents 项目的维护者。状态：**待接收**。

## 文件对照

| 归档文件 | 原位置 | 条目 |
|---|---|---|
| `architecture.md` | `skills/architecture/references/auto-agents-pitfalls.md` | PIT-1 … PIT-6 |
| `coverage-matrix.md` | `skills/coverage-matrix/references/auto-agents-pitfalls.md` | ESC-2、空心断言、ESC-1、ESC-3、ESC-8/9 |
| `deliver.md` | `skills/deliver/references/auto-agents-pitfalls.md` | P-SRE-01 … P-SRE-08 |
| `design-contract.md` | `skills/design-contract/references/auto-agents-pitfalls.md` | P-DES-01 … P-DES-05 |
| `impl-evidence-ai.md` | `skills/impl-evidence/references/ai/auto-agents-pitfalls.md` | P-AA-01 … P-AA-10 |
| `impl-evidence-api.md` | `skills/impl-evidence/references/api/auto-agents-pitfalls.md` | P-BE-01 … P-BE-03 |
| `impl-evidence-model.md` | `skills/impl-evidence/references/model/auto-agents-pitfalls.md` | P1 … P10 |
| `impl-evidence-ui.md` | `skills/impl-evidence/references/ui/auto-agents-pitfalls.md` | P-FE-01 … P-FE-08 |
| `prd-gwt.md` | `skills/prd-gwt/references/auto-agents-pitfalls.md` | P-01 … P-06 |
| `release-gate.md` | `skills/release-gate/references/auto-agents-pitfalls.md` | PIT-QC-01 … PIT-QC-04 |
| `signals.md` | `skills/signals/references/auto-agents-pitfalls.md` | P-OPS-01 … P-OPS-03 |
| `warehouse.md` | `skills/warehouse/references/auto-agents-pitfalls.md` | P-WH-01 |
| `collect.md` | `skills/collect/references/scrapy-redis-distributed.md`、`templates/spider-template.py`、`templates/spider-config.py` | TaskAwareRedisSpider 基类、sites.yml、Pipeline 名称与队列键、R5/R6/B2 编号 |

## 去重分组与去向

同一件事在多份文件里重复出现的，按主题合并。「通用原则」一栏是去掉项目名、技术栈和路径后留在插件里的写法；「项目专属」的条目只应进入 auto_agents 的 `.sdlc/_lessons.md`。

| 主题 | 出现位置 | 通用原则现在在哪里 | 项目专属部分 |
|---|---|---|---|
| SQLite 放行、MySQL 拒绝的方言（`NULLS LAST`） | coverage ESC-2 · warehouse P-WH-01 | coverage-matrix、warehouse、collect 的 Gotchas | 修复提交与回归用例名 |
| 空心断言、全量套件绿 ≠ 本功能覆盖 | coverage「空心断言」· release-gate PIT-QC-03/04 | coverage-matrix、release-gate 的 Gotchas | 具体测试文件与行号 |
| 读数据的前置状态必须真落库 | coverage ESC-1 | coverage-matrix Gotchas「Preconditions must be real state」 | — |
| 权限缓存：未加载 ≠ 无权限 ≠ 全权限 | coverage ESC-3 · design P-DES-02 · ui P-FE-03 · prd P-04 | `impl-evidence/references/ui.md`、design-contract Gotchas | 菜单过滤实现细节 |
| 失败 ≠ 空、筛选后为空 ≠ 本来没有、CTA 名实相符 | design P-DES-01/03/04 | design-contract Gotchas、`templates/edge-states.md`、`references/ux-writing.md`（原本已有） | 具体页面与文案 |
| 不可信正文只按纯文本渲染，迁页时安全用例随迁 | design P-DES-05 · ui P-FE-06 · prd P-03 | `ui.md` Gotchas、`prd-gwt/references/gwt-authoring.md` | 具体页面与测试 |
| 卖点只写合同允许的字面量（Excel vs CSV） | prd P-01 · signals P-OPS-01 | growth Gotchas、`gwt-authoring.md` | 官网文案与导出实现 |
| 同一可见性规则只保留一份读模型 | architecture PIT-5 · prd P-02 · signals P-OPS-02 | `architecture/references/adr-and-tradeoffs.md`、`gwt-authoring.md` | 两个公开端点的现状 |
| 权限/状态语义变更要同时改钉住旧行为的测试 | architecture PIT-2/PIT-6 | `adr-and-tradeoffs.md` | 具体守卫与枚举 |
| 约定式租户隔离要逐表决定豁免或隔离；缺租户 ≠ 平台态 | architecture PIT-3 · api P-BE-03 | `adr-and-tradeoffs.md`、`impl-evidence/references/api.md`、`warehouse/references/layering-deep-dive.md` | 豁免清单与中间件名 |
| 迁移链才是表结构事实，ORM/create_all 会骗人 | architecture PIT-4 | `adr-and-tradeoffs.md` | 017 迁移与相关表 |
| 路由注册顺序（静态段先于动态段） | architecture PIT-1 | 未提升（框架特定） | 全部 |
| 异步代码里不能调同步客户端；提交后别再读 ORM 对象 | api P-BE-01/02 | `api.md` Gotchas | 具体函数名与闸门规则编号 |
| mock 不是效果评测；代理分不是准确率；换协议等于换模型；无人读取的配置不算改动 | ai P-AA-01/02/04/10 | `impl-evidence/references/ai.md` Gotchas | 具体服务与阈值 |
| 标签由被替代的规则产生会循环论证 | model P4/P7/P8 | `impl-evidence/references/model.md` Gotchas | 具体字段与阈值 |
| 其余算法与挖掘条目（MCP 健康判定、探针阈值、配额闸断开、as-of 缺失等） | ai P-AA-03/05/06/07/08/09 · model P1–P3/P5/P6/P9/P10 | `ai.md`、`model.md` 已有的评测与泄漏原则 | 全部 |
| 本机与 CI 的工具链、lockfile、架构差异 | deliver P-SRE-01/02/03 | deliver Gotchas | 版本号与提交 |
| 编排器读的健康探针在依赖失败时必须非 2xx | deliver P-SRE-04 | deliver Gotchas | compose 配置与看门狗 |
| 安全缺省要在真实路径上演练一次 | deliver P-SRE-05 | deliver Gotchas | 看门狗脚本细节 |
| runbook 与复盘要放在会提交的路径 | deliver P-SRE-08 | deliver Gotchas | `.gitignore` 规则 |
| 管道背压导致子进程僵死；dotenv 不做 `${}` 展开 | deliver P-SRE-06/07 | 未提升（栈特定） | 全部 |
| 共享包读构建产物会过期；ESM 依赖需要测试转译 | ui P-FE-01/02 | `ui.md` Gotchas | 包名与配置片段 |
| 其余前端条目（信封只解一层、422 保留表单、jsdom 补丁、antd v6 弃用） | ui P-FE-04/05/07/08 | 未提升（栈特定） | 全部 |
| 用户可见文案不出现内部错误码；默认拒绝 ≠ 已完成隔离 | prd P-05/P-06 | `gwt-authoring.md` | 具体页面与配置 |
| 北极星口径缺字段就不能报数 | signals P-OPS-03 | collect「Events defined after launch cannot measure the launch」 | 具体 GWT 与审查结论 |
| check-sdlc SUMMARY 退出码差一（3.5.x）、默认跳过 = 通过 | release-gate PIT-QC-01/02 | release-gate Gotchas（现行语义）；3.6.0 的修复沿革只留在本档 | — |

## 从 skill 正文里移出的项目内容

| 原位置 | 移出的内容 | 现在的通用写法 |
|---|---|---|
| `skills/growth/SKILL.md` | 「Verified trap (auto_agents)」中的项目名 | 保留为不带项目名的例子 |
| `skills/collect/SKILL.md` | 爬虫栈规则编号 B2、R5/R6 与 auto_agents 专属约束 | 「Crawlers are their own subsystem」一条通用原则 |
| `skills/collect/references/scrapy-redis-distributed.md` 及两个爬虫模板 | 项目基类、配置入口、Pipeline 名与优先级、队列键、目录与启动命令、规则编号 | 带适用条件的 scrapy-redis 通用做法；「项目有任务感知基类时继承它」「直写主库与否由项目架构决定」 |
| `skills/warehouse/SKILL.md` | 「在线库与数仓共用一个 MySQL 实例」的项目背景、`platform_scope` | 「分析与在线库同实例时」的通用做法；隔离用项目授权的机制 |
| `skills/warehouse/references/layering-deep-dive.md` | `tenant_context.py`、`TENANT_EXEMPT_TABLES`、`platform_scope()` | 项目隔离机制的通用描述 |
| `skills/impl-evidence/references/api.md` | `redis_client()` / `get_async_redis()`、R10 日志规则 | 事件循环、提交后读取、日志约定的通用写法 |
| `skills/impl-evidence/references/ui.md` | `@auto-agents/frontend-shared`、Jest 配置片段、antd v6 弃用 | 共享包、ESM 转译的通用写法（antd 条目未提升） |
| `skills/release-gate/SKILL.md` | 「Plugin 3.6.0 stopped incrementing V on SUMMARY」 | 现行退出语义 |
| `skills/prd-gwt/references/gwt-authoring.md` | 「feat-four-pillars QA-29」 | 「一次真实审查」 |
| `skills/coverage-matrix/SKILL.md`、`skills/deliver/SKILL.md` 等脚注 | 「auto_agents production incident / git history」 | 「a verified production escape」「a user project's history」 |

## 接收步骤（给 auto_agents 维护者）

1. 在 auto_agents 仓库里，把本档中与当前代码仍然相符的条目追加到 `.sdlc/_lessons.md`，保留证据（提交、测试名、ESC 编号），写明成立条件与复查条件。
2. 已经不成立的条目（代码已改、测试已删）标注失效，不要搬。
3. 接收完成后，在本文件把状态改为「已接收：<日期>」；此后插件维护者可以删除本档中对应的文件。
