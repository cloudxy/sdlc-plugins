# 更新日志

标题习惯来自 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。版本号来自提交说明和 `adapters/hosts.json` 的 `plugin.version`。本分支的 `git tag` 没有 `v4.*`；下面的日期是对应提交的作者日期。`9677b35` 之前的历史已在该提交压平，本文件不补写压平前的细节。

## [Unreleased]

- 使用指南、README 与最小样例说明对齐当前仓库：9 个行业原型、6 个 `traits`、交接退出条件、10 维审查、过程监督 `ESCAPEQA` 和可选 `extra_gates`。4.9.0 条目中的画像字段与 traits 数量改为与 `skills/sdlc/references/routing/industry-playbooks.md` 一致。
- 最小样例覆盖矩阵补上契约里的 `[SEC-1]`。`check-sdlc.sh --require` 在该功能目录上退出码为 0。闸门报表数据行为 65。
- 执行效率与写入审计加固：`SKIP_DIRS`/`SKIP_FILES` 过滤 IDE/OS 元数据噪音，新增 `workflow.py ensure-ignore` 与 `seal` 的 `dispatch_snippet`，固化单帽单轮机械检查、等待期禁副作用与独立返工上下文规则。
- 隐私与维护隔离：将维护归档、方法变更明细、拒绝记录、本机覆盖文件、IDE/运行时文件与本地回归样例纳入 `.gitignore`，公开校验仅依赖脱敏后的 `method-baseline.json` 与 `gate-provenance.json`。
- 目录架构分层重构：将 21 个测试脚本与夹具移出 `scripts/` 独立为顶层 `tests/`；`scripts/` 顶层仅保留 7 个稳定 CLI 入口，内部模块按职责拆分为 `runtime/`、`gates/`、`evals/`、`data/`、`packaging/`（与既有 `tools/`、`diagram/`、`image/`、`grok/` 并列）；`skills/sdlc/references/` 按 `protocol/`、`modes/`、`routing/`、`platform/` 四个语义目录归属并同步升级健康检查与生成器。

## [4.10.0] - 2026-11-27

新手零配置起步、可解释确定性路由、15+ 专业场景授权内补齐、默认上下文减载、纯标准库防御性核验工具与质量×效率双度量。插件版本由 `4.9.1` 升至 **`4.10.0`**（同步全部 5 宿主 manifest），注册表任务合同由 73 增至 **77**，技能由 26 增至 **27**（保留全部 19 角色与既有 v2/v3/`continuous` 兼容）。

### 零配置幂等引导、可解释路由与 15+ 域覆盖

- 新增 `workflow.py bootstrap --project-root <dir> [--json]`（[scripts/runtime/bootstrap_route.py](scripts/runtime/bootstrap_route.py)）：幂等写入本机 `.git/info/exclude`（不修改 `.gitignore` 与既有 `sdlc.config.yaml`），缓存 `.sdlc/_runtime/bootstrap.json`，非 UI/只读任务免配置直接开工，同时完整保留 `check_config.py` 的 UI 阻塞（`APP-START`/`APP-URL`/`E2E`）及全局阻塞（如 `REGISTRY` 置 `non_ui_ready: false`），并安全兼容只读工作区。
- 新增 `workflow.py route --text "<需求>" [--project-root <dir>] [--json]`：可解释确定性自然语言分流（`fast_track` / `scoped_team` / `full_sdlc` / `clarify_first` / `resume` / `L0` / `review_only` / `advice_only` / `out_of_scope`），保留原入口「继续」、L0 错字、只 review、只给建议，区分「运营环境」与产品运营、消歧「慢查询优化」与「召回策略」（`ops` vs `algo`），高风险精准需求强制升档 `full_sdlc` + `strict`，主动渗透/爆破请求确定性拒绝。
- 扩展 [workflow/registry.json](workflow/registry.json) 与技能：新增独立算法技能 `skills/algorithm/`（配套 `role-quality.md` 与 `evals.json`），并补齐 4 个授权内只读/设计任务——`sre/deliver/log-analysis`、`sre/deliver/ops-diagnose`、`architect/verify/security-audit`（严格防御性静态审计，零主动探测/利用）、`ops/define/ops-design`（人群分层/`SIG-…`/护栏/`kill-switch`）。

### 公共角色壳瘦身与按需装载

- 精简 `agent-sources/_lib/*.md` 与 `scripts/render-role-agents.py` 并重渲染五端角色文件，100% 保留全部 `SOUL.md`、`IDENTITY.md`、Principles/Pushback/Refuse、`Do NOT` 与 `reviewer`/`qc` 7 项只读隔离红线。
- 精简 `skills/sdlc/SKILL.md`，增设按轨按需加载参考表与新手白话沟通约束，并从 `orchestrator-gates.md` §13 移除跨宿主固定 token 阈值。

### 纯标准库防御性核验工具与 manifest 绑定轻/严入口

- 新增 3 个纯 Python 标准库只读工具（零联网、零主动探测、敏感凭据脱敏）：`scripts/tools/log_profiler.py`、`scripts/tools/schema_parity.py`（含 MySQL 64 字符上限校验与空/不支持输入拒判 `parity_ok=true`）、`scripts/tools/sec_quickscan.py`（严格防御性静态线索，同行多规则统一脱敏与符号链接防逃逸）。
- 新增 `workflow.py dispatch --mode light|strict` 与 `workflow.py finish --mode light|strict`（[scripts/runtime/dispatch_cli.py](scripts/runtime/dispatch_cli.py)）：轻轨封存含工作区内容基线快照与 `manifest_sha256` 的 light manifest，机械拒绝高风险/`protocol_required` 降级、点文件无损保留并拦截 `..` 越界与越权 `--deliverable`；收口强制绑定 `--run <manifest>`，保留未改既有脏文件，捕获脏文件再改、未跟踪写、跨角色 memory 篡改、跨/同 feature 并发重叠（`unknown_concurrent`）与超文件上限快照不可证（`unknown`，绝不误判 `ok: true`）。

### 质量 × 效率双度量与只读 ZCode 摘要

- 扩展 `scripts/gates/outcomes.py`：新增免 `phase: Closed` / 免 `state.yaml` 的 `record-run`（写 `.sdlc/_outcomes/runs/`），`stats` 兼容历史 `_outcomes/*.json` 并聚合质量+效率指标，对未采集字段显式标注 `缺测`。
- 扩展 `scripts/gates/session_digest.py`：新增可选只读 `--zcode-db <sqlite> --session <sid>`（SQLite `mode=ro` + 凭据脱敏），汇总根/子会话派发、调用、Token 与耗时，原 Claude Code `.jsonl` 模式 100% 兼容。

## [4.9.1] - 2026-11-22

全链路交接缝退出门槛（Exit Criteria）硬化与「过程监督 QA vs 产物检查 QC」闭环制度化。插件版本升至 `4.9.1`，闸门目录由 63 增至 **65**。

### 全链路 8 大交接缝退出门槛硬化

- **机会定义 → 准入（`signals` / `discover`）**：一线信号强制写清「场景 · 受影响人群 · 触发原因 · 可观测损失」；数据分析核验输出三态结论（`数据已证实` / `数据证伪` / `数据不可用，需先立项补埋点 EV-n`）；退出门槛强制锚定存量系统模块或数据链路（指不出对应链路不得准入，`0→1` 显式标 `greenfield`）。
- **需求与双向无孤立追溯（`prd-gwt`）**：建立 `业务目标/指标 ↔ 旅程 J-n ↔ FR-n ↔ GWT` 双向追溯，拦截无目标挂靠的镀金孤立功能；业务目标落齐四要素（定义、范围、基线、目标；缺基线必填待补责任人与时间）；定性验收条件强制指定「判定依据 + 判定人」。
- **UX 与架构并行规格（`design-contract` / `architecture`）**：融合组件交互 7 态（`default, hover/focus, disabled, loading, empty, error, success`）与页面数据 6 态，强制组件引设计系统源、微文案零 `TBD`、断点布局写死；架构明确自适应 HLD/LLD 分工与 NFR 逐项映射具体设计决策（禁无数字的「要快」）。
- **可执行契约锁与四大返工源清零（`architecture` / `warehouse` / `collect`）**：新增零依赖静态契约校验器 `skills/architecture/scripts/check-contract.py` 与可选 `CONTRACTLOCK` 闸门（核验 OpenAPI/Swagger 成功+错误响应语义及相对基线的破坏性变更）；补齐分页 `0/1` 起始基数、非法排序行为与 `DELETE` 不存在资源的幂等语义；数仓明确最小可行数据产品九要素契约；采集锁定 `(job_id, url_key)` 幂等键。
- **工程实现、特征时间纪律与全周期安全（`impl-evidence` / `collect` / `architecture` / `cicd`）**：前端基于锁定契约生成类型与 Mock 并行开发；采集严格区分「页面点击可交互」与「底层接口载荷获取成功」，强制主数据映射唯一权威源与请求/响应上下文回显对账；`feature-dict.md` 升级为 `event_time` + `availability_time` 双列（`availability_time <= decision_time`），补齐重叠窗口回填字节级幂等、PSI/KS 漂移检验与违约暂停告警；明确提交级 SAST、预发 DAST 与全链路最小权限核查。
- **提测准入、Feature Flag 发布解耦与归因前数据排障（`coverage-matrix` / `deliver` / `retro`）**：`test-report.md` 增设缺项即打回的提测准入勾选清单；明确 Feature Flag「部署≠发布」、Staging 实测回滚证据与 24h 观察窗统计级熔断四元组（`3σ/2min`、`150% SLO/3min`、`5x` 预算燃烧率、核心业务指标突跌）；`retro.md` 与 `analysis.md` 增设归因前 6 项数据链路排障门禁（数据异常时冻结归因，仅输出修复数据链路任务）。

### 过程监督 QA（`ESCAPEQA`）与产物检查 QC 分离

- 在 `check-sdlc.sh` 与 `state_view.py` 新增 **`ESCAPEQA`** 闸门：v4 下含 `escape:` 的缺陷修复在 `phase: Closed` 时，除记录漏检阶段与缺陷类别外，必须填写 `seam_fix`（补了哪条契约/测试/脚本门禁）与 `verified_by`（门禁生效核验证据），防止只修当次代码（QC）而放任产生同类缺陷的流程接缝继续漏检（QA）；`outcomes.py stats` 同步输出逃逸缺陷的过程接缝闭环统计。

## [4.9.0] - 2026-11-22

全链路专家化、工程设计原则贯通、9 大行业细分 SOP 与静态门禁加固。插件版本升至 `4.9.0`，注册表任务合同由 69 增至 **73**，闸门目录由 61 增至 **63**。

### 19 角色专家化与权威护栏

- 升级 `agent-sources/_lib/` 与全部 19 个角色的 `SOUL.md` / `IDENTITY.md`，并重新渲染五端角色文件（`agents/*.md`、`adapters/codex/agents/*.toml`、`adapters/kimi/agents/*.md`）。
- 赋予全部角色**基于证据的专业驳回权（Evidence-Backed Pushback）**与交接前的**二阶后果扫描（Second-Order Consequence Scan）**：上游输入违反领域不变量时仅阻断受影响切片，通过 `unresolved` / `proposed_changes` 返回反例与 1–2 个合规替代方案，禁止橡皮图章式盲从或静默篡改合同；保持 `reviewer` 与 `qc` 的严格只读隔离。
- 17 个主角色技能及 `debug`、`prototype`、`cicd` 全部配备不少于 8 行的实质性 `references/role-quality.md` 角色质量标尺（健康检查新增行数门禁）。

### 9 大高阶工程定律与 10 维独立审查

- 将 `SRP, ISP, OCP, LSP, DIP, KISS, YAGNI, SSOT, SVOT, DRY vs DIE (AHA), LoD, CQS/CQRS, Statelessness, Poka-Yoke, UX Laws` 与 **9 条高阶工程定律**安置进对应环节的技能、模板与门禁：
  1. **Ousterhout 深模块与耦合度（Connascence）最小化**（`architecture` / `refactor` / `findings`）
  2. **Parse, Don't Validate + 非法状态不可表示**（`architecture` / `schema` / `impl-evidence`）
  3. **纯函数业务内核与命令式外壳（Functional Core, Imperative Shell / Sans-IO）**（`architecture` / `impl-evidence` / `tdd`）
  4. **在途多版本共存（In-Flight Version Coexistence）与权限/资金 Fail-Closed**（`architecture` / `schema` / `deliver`）
  5. **三态外部副作用协议（`Success / Fail / In-Doubt`）与事务外 I/O**（`architecture` / `schema` / `impl-evidence`）
  6. **全链路有界（Bounded Everything）、背压与优雅褐变降级（Brownout）**（`architecture` / `collect` / `release-gate`）
  7. **守恒律与蜕变测试预言机（Conservation & Metamorphic Oracle）**（`tdd` / `coverage-matrix`）
  8. **Tesler 复杂度守恒与 `UI = f(State)` 状态同构**（`prd-gwt` / `design-contract` / `prototype`）
  9. **配对指标护栏（Paired Metric-Guardrail）与先观测后优化**（`prd-gwt` / `growth` / `signals` / `warehouse` / `debug`）
- `$findings` 独立审查由 9 维扩展为 **10 维**，新增第 10 维 **Architecture & design principles**，配套更新 `skills/findings/SKILL.md`、`skills/findings/templates/findings-report.md` 与 `skills/findings/references/role-quality.md`。

### 9 大行业原型与可组合 `traits` SOP 体系

- `sdlc.config.yaml` 新增 `profile`（`industry`、`traits`、`surfaces`、`db_engines`、`architecture_style`、`compliance`）及仓库信号自动推断（`check_config.py` 输出 `[推断] profile` 提示，不阻断普通本地开发；`task_runtime.py` 自动将 `project_profile` 与 `constitution` 注入 v3 派单包）。
- 建立主路由 `skills/sdlc/references/routing/industry-playbooks.md` 与 4 份领域共享 SSOT（`industry-product-sops.md`、`industry-architecture-sops.md`、`industry-data-sops.md`、`industry-delivery-sops.md`），覆盖 `b2b-saas`、`fintech-ledger`、`ecommerce-marketplace`、`consumer-social`、`ai-agentic`、`aigc-workbench`、`data-crawler`、`regulated-compliance`、`client-iot-localfirst` 九大行业原型与 6 项可组合 `traits`（`multi-tenant`、`payments`、`ai-enabled`、`realtime`、`offline-first`、`regulated`）。

### 注册表、模板补齐与工具权限

- `workflow/registry.json` 为 `algo` 补齐执行、评测与排障闭环：新增 `implement/explore`、`implement/evaluate`、`implement/diagnose`、`implement/fix` 四个任务合同与对应工件（总任务合同 **73**）；保持全部 19 条角色描述满足 Grok 180 字符派单窗口约束。
- `adapters/zcode.json` 为 `algo`、`data-collector`、`dba` 开通 `WebSearch` / `WebFetch`（遵守 `research.offline`）。
- 明确 `dba` 与 `backend` 在 `db-migration` / ORM / manifest 上的三件套原子归属；精简按泳道自适应的 `impl-evidence.md`，补齐 `security-review`、`algo-*`、`fix-*`、`diagnosis-*`、`tracking-impl`、`cicd` 等缺失模板，清理 v3 遗留话术。

### 闸门与静态核验器升级

- 新增 `RELEASEOPINION` 闸门（`check-sdlc.sh`）：v4 下核验 `06-deliver/release-opinion.md` 的明确放行结论，阻断缺失、歧义或「不放行」状态越过 `qc` 或关闭功能。
- 新增可选 `FRONTEND` 静态闸门（`skills/impl-evidence/scripts/check-frontend.py`）：拦截样式裸色值（Token SSOT）、`onClick={() => {}}` 空回调与内联样式 CSP 违规。
- 升级 `check-layering.py`（支持 Python + TS/JS、反向依赖与 `domain -> infra/orm/api/repo` DIP 检查）、`check-explain.py`（支持 MySQL、PostgreSQL 文本/JSON、SQLite EQP）、`check-matrix.py`（拦截缺口/待补/裸 N/A，校验 `[SEC-n]` 闭环，放行带理由的 `➖ N/A`）。
- 新增共享零依赖内核 `scripts/runtime/_sdlc_core.py`，统一 `SKIP_DIRS`（修复 `runtime_protocol.py` 与 `evidence.py` 因 `.pytest_cache`/`target` 误报 `changed_during_run`）、引号安全的行内 `#` 注释剥离与 `extra_gates` 解析；`diagram/lint.py` 新增只读 `--verify-only`；`data_dictionary.py` 接入 `tracking-plan.yaml` 与 `tags.yaml` SVOT 核对；`health_check.py` 将 `GATECATALOG` 升为错误并校验脚本引用存在性。

## [4.8.0] - 2026-11-21

自 `4.7.5`（`edca5c2`）到本次封版之前的提交。编辑记录 `release-version-4.8.0` 只把 `adapters/hosts.json` 的插件版本从 `4.7.5` 同步到 `4.8.0`，不改路由或权限。

### 维护规则

- 改为定向检查与测试：结构改动跑 `bash scripts/health-check.sh`，Python 模块跑对应的 `tests/test_<affected>.py`，只有 `scripts/check-sdlc.sh` 或其直接依赖改动时才跑 `tests/test-check-sdlc.sh`（含 `zh_CN.UTF-8`）。

### 方法台账与能力增强

- 补充浏览器连续性与通知观察、CDP 浏览器提取参考（登录墙、虚拟化文档、blob 与图片去重），以及「形状分析不能代替行为验证」规则。
- 强化多代理工程经验（7 个角色 IDENTITY 及生成宿主角色；schema、交付回滚、采集恢复、覆盖矩阵、findings、实现证据和持续工作）。
- 对齐采集访问合同、渲染资源边界、同页共享行、目录可见集与结果/smoke 路由契约。
- `skills/discover/evals/evals.json` 与 `skills/sdlc-eval/evals/evals.json` 补齐对应评测用例。

### 闸门目录

- `2b365ff`：`maintainers/gate-provenance.json` 的 61 个标签都写了 `cost`。标签集合没有增减，原先这些 `cost` 为空字符串。
- `dff2447`：`sdlc_version` 为 4 或更新时，失败的脚本闸门若没有合法 `stage:`，记为 `HATADVANCE`。更旧的状态文件仍按原读法。台账 `hatadvance-v4-stage-required`。

### 宿主清单与角色描述

- `8061e62`：Grok `1.0.89` 把 `.grok-plugin/plugin.json` 的 `"agents"` 按目录解析。文件数组会被忽略并加载 0 个角色。清单改为 `"agents": "./agents"`。`.claude-plugin/plugin.json` 仍是 19 个显式 `./agents/<role>.md`。
- `87888c5`：Grok `1.0.89` 的 `spawn_subagent.subagent_type` 在大约 182–198 字符处截断角色描述。19 个角色里，18 个被派单角色的 `/sdlc` 派单句，以及 architect 的「不是 `/sdlc` 经理」句，结束位置都在第 180 个字符以内。原先已经在这个窗口内的描述没有改句子。台账 `role-desc-frontload`。
- `50f1fdb`：Codex CLI `0.169.0` 的离线探测记入 `adapters/HOST-NOTES.md`。`codex --version` 退出码 0，未执行在线 `codex exec` 实机派单。`hosts.md` 仍保留 0.157.1 的无类型父会话回退。

### METHODPENDING

`3749f4b` 把原先 5 条 `pending` 都结案为 `evaluated`：

- `b1-smoke-mode`
- `b5-outcome-templates`
- `script-gate-hatadvance`
- `inherited-unrecorded-methods-20261110`
- `4.3.4-role-descriptions`：完成 Grok `1.0.89` 实机派单验收。

当前 0 条 `METHODPENDING`。

### 状态总览与 `$falsify`

- `3345bdd`：`scripts/gates/state_view.py summary` 打印操作者可读的状态总览。用法写在 `docs/usage.md`。
- `c9ab40b`：`$falsify` 在原定 2026-12-31 之前退役。证伪用例留在 discover 的 id 23–25；`tracks.falsify` 与发现带第 4 步不动。磁盘技能与注册表技能都是 26。台账 `retire-falsify` 当次健康检查：skill metadata 预算 `3370/4200`，0 `[COMPAT]`，0 `METHODPENDING`。

### 样例、逃逸与报表

- `3ba2114`：端到端最小可跑通样例 `docs/examples/minimal-feature/`（导出租户审计 CSV，L2，`local_verified`）。
- `7d8dcbe`：同一条样例补上 `.sdlc/_outcomes/`（功能结果、`EVID` 逃逸、赌注索引）。`gate_catalog.py report` 打出全部 61 个闸门；维护成本在 `gate-provenance.json` 的 `cost` 字段。`docs/usage.md` 写了复现命令。

### 条件任务

- `0ac9bdb`：鉴权、隐私留存或新增外部依赖时派 `architect` 的 `shape/security-review`。纯静态文案或内部样式不派，也不把 `02-shape/security-review.md` 加进 shape 阶段闸门。任务合同 69。台账 `security-privacy-task`。
- `5a9abe4`：非 Web 端按需实现参考 `skills/impl-evidence/references/client-platforms.md`（原生、桌面、小程序）。台账 `client-platforms-reference`。不新增阶段或权限。

### 仓库入口

- `e6df613`：新增本文件。新增 `.github/workflows/self-check.yml`：`health-check`、注册表渲染、角色渲染和闸门目录为必跑；Python 单测只按本次 diff 映射。工作流不调用 `/sdlc-eval`。

## [4.7.5] - 2026-11-14

- `edca5c2` `feat(skills): preserve continuous configuration and notice lifecycles (v4.7.5)`。连续配置跳顶和短提示的生命周期写入设计、实现和验收指引（`continuous-configuration-feedback`）。

## [4.7.4] - 2026-11-14

- `9922784`。跨页面主题或不同原生标签的共享控件，使用稳定组件属性和已批准的语义变体。前端诊断追踪祖先选择器与层叠归属；QA 检查受影响宿主和真实导航。保留 4.7.3 的当前结果 / 历史方法。提交说明记录了有界场景应用，并写明没有盲评对照。

## [4.7.3] - 2026-11-14

- `58b168f`。区分草稿、已提交输入、当前输出和历史，按任务刷新，部分成功可恢复（`result-history-lifecycle`）。记录写明五条有范围场景已评测，没有对照收益结论。
- 编辑记录 `result-lifecycle-release-version` 只同步宿主元数据版本，不改路由或权限。

## [4.7.2] - 2026-11-14

- `45befe2`。菜单、预览/结果、按身份查询、提供方授权、来源分页和有范围发布的观察，写入既有角色技能（`interaction-dataflow-scoped-delivery`）。

## [4.7.1] - 2026-11-14

- `dbf38c6`。资源范围与本地性、所有权类别、紧凑卡片、跨入口消费者证据和运行就绪（`replication-module-local-media`）。不新增阶段或权限。

## 4.7.0 与 4.7.1 之间

这些提交在 main 上，提交说明没有单独的 4.x 版本号。

- `2026-10-13` `176743c`：忽略本地 IDE 设置。`86a45da`：各 AI 宿主可以在本仓库自托管测试插件。
- `2026-10-19`：数据采集流水线经验写入 collect、API 实现证据、debug，以及 backend / data-collector 的 SOUL。
- `2026-11-10`：architecture、collect、schema 写入任务归属、可恢复写入、发布确认和缓存相对权威数据的生命周期；技能场景评测保留为必需，同时取消对模型、客户端、调用次数和模型对照的硬性规定。
- `2026-11-10`：README 导航按现有注册表和生成物重组。

## [4.7.0] - 2026-10-07

- `d9b8329`。discover 复审：当前格式的 briefing 必须选定结论，bet 需要复盘指标，交接就绪和 Discuss-P 不能只留模板句。模板补上待定、调研选择、带日期的竞品证据和切片理由。falsify 先读 `.sdlc/_outcomes/` 里的相关结果；产品界面只在新产品或新界面时逐行走查；否决后重开由用户决定并记入 `discovery.reopened`。调研模式只门禁实际跑过的轨道。评测增加案例 15–22。提交说明记载了相对 4.6.0 的对照结果，并写明闸门标签目录当时仍是 61 个。

## [4.6.0] - 2026-10-06

- `1fdf5bf`。视觉方向先落到主题、受众和页面任务；主视觉用该主题最有特征的东西；字型按简报选择，方案里的字体项要求字号阶梯。`trigger_smoke.py` 增加分组与别名计分。提交说明记载了案例 9 的对照，以及 prd-gwt、discover、tdd 的近失配提示两臂相同、技能描述未改。

## [4.5.0] - 2026-10-03

- `5083543`。闸门目录 `scripts/gates/gate_catalog.py` 与 `maintainers/gate-provenance.json`（每个标签要有夹具和来历）。结果记录 `scripts/gates/outcomes.py`。失败的分阶段脚本闸门阻挡阶段（HATADVANCE）；seal 拒绝把没有结果的任务再跑一遍。architect 的 deepen-survey；tdd 要求独立期望值；工作项可标 `uncertainty`。`VENDORDRIFT` 在改写文件的上游摘要与锁文件不一致时告警。`trigger_smoke.py` 测量提示会加载哪个技能。

## [4.4.0] - 2026-10-02

- `524bf5b`。方法台账 `scripts/gates/method_ledger.py`：方法源文件改动没有记录则健康检查报 `METHODCHANGE`，等待证据的行为改动报 `METHODPENDING`。`scripts/evals/behavior_smoke.py` 作为 sdlc-eval 的 smoke 模式。`scripts/gates/session_digest.py` 与只报告、不改方法的 diagnose 模式。
- 提交说明记载：reviewer 回退和 briefing/state 模板在 4.3.3 与 4.3.4 上都通过；diagnose 模式由失败转为通过。角色描述在只读运行里观察不到，`4.3.4-role-descriptions` 保持 pending。健康检查的退出码上限与 `check-sdlc.sh` 对齐。

## [4.3.4] - 2026-10-02

- `c3572d5`。`check-sdlc.sh` 改为经 `scripts/gates/state_view.py` 读状态，修掉一行 grep 造成的静默通过：阶段秩、泳道、数字决策编号、带空格路径、退出码上限、无验收却关闭、一行新鲜上下文失败记录、briefing 里的待确认、跳过原因，以及 `ui: yes` 不能跳过设计师。新增夹具组 61–72，C 与 `zh_CN` 两种 locale。

## [4.3.3] - 2026-10-01

- `7351a32`。4.3.2 的「一轮一个动作」只用于引出需求。依赖已满足、用户要求讨论的决定，当轮给出选项、后果和建议。

## [4.3.2] - 2026-10-01

- `5fedb61`。发现闸门拒绝仍带 `sdlc:unfilled` 的 briefing，现状和否决标准必须有模板以外的正文。讨论协议改为先提一个开放问题；用户答不上来之后才给对照。discover 评测案例 3 和 5 带上夹具文件。健康检查在列出的夹具缺失或逃出技能目录时失败。

## [4.3.1] - 2026-10-01

- `ea1e158`。规格模板里的例子与「后果性业务规则不得默认」对齐。文档改成与 `OPENQOPEN` / `DECISIONPENDING` 的实际行为一致：未决的规格问题挡住下一条泳道阶段，独立工作仍按范围进行。审查把被默认的后果性业务规则视为重要问题。

## [4.3.0] - 2026-10-01

- `443ae5f`。需求共创：discover、prd-gwt、prototype 和 sdlc 经理共用讨论协议。下一步按不确定的是什么来选，复用已定决定，分开事实、假设和决定。冻结表示当前切片可以进入下一步。增加非代码学习材料的 CONCEPT 原型分支，以及相应评测案例。

## [4.2.0] - 2026-09-30

- `6cf0ca4`。五个宿主接同一份插件目录：补上项目级 Kimi 技能和生成角色，角色源移出宿主扫描目录，Codex / Kimi 链接有归属保护。Codex 的类型化与非类型化派单写明只读审查要求。README 记录五宿主的安装、已核对行为和当时的运行时限制。

## 4.1.0 与 4.2.0 之间

版本号没有逐个提交递增。下列内容来自这些提交的说明，日期均为 2026-09-18 至 2026-09-29。

- `661231b` 截图必须存在，结论必须唯一，killed 保持 killed，模板不是交付物。
- `877a9b4` 任务检查和派单包对照注册表，不再靠黑名单。
- `6920649` 方向原型与最终原型是设计交付物；一次性 prototype 技能留在发现阶段。
- `bba1227` 引入 svg-diagram 约定和图闸门。
- `ad57b8e` 由 `erd.dbml`、术语表和 `metrics.yaml` 生成数据字典。
- `45298b5` 运行证据绑定当前代码；关闭、验收和安全按真实结束状态。
- `ae22432` 前端从最终原型代码构建；frontend-design 是设计与 UI 的必读。
- `df72aa7` 角色按任务范围工作：提前可行性、有范围的源码写入、有证据的调研、验证与发布分开。
- `196ec7b` 写出工作流、使用指南和流程图。
- `66deac7` Grok 订阅出图，放在已登记、有检查的闸门后面。
- `3921a98`、`1ed6158` 任务模型、产品周期、准备 / 封存 / 记录 / 检查。
- `bbbeed0`、`7d2438b`、`e563fd3`、`9c2066c` 宿主清单同源，引用插件目录，Codex 用链接接入。
- `4e83344`、`326270a`、`9042551` 持续工作（局部打磨与修复、版本、项目图、隔离并发）和带六张图的使用指南。

## [4.1.0] - 2026-09-18

- `9677b35` `sdlc-workflow v4.1.0: single-commit restart`。22 个提交压成一个提交（说明中写了 v3.15–v3.20.6、v4.1.0 分层重构、README / 教程重写和 `vendor/install.sh`）。压平前历史不在公开分支中。
