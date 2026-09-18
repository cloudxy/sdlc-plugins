# sdlc-workflow

ZCode 插件 · v4.1.0 · MIT

闸门化的功能交付控制面：把「一个功能从想法到交付」变成以产品质量为目标的流水线——发现带（市场 ∥ 竞品 ∥ 增长定位）先行，体验设计先于架构，按用户旅程纵向切片实现并联调，E2E 与三方验收把关，产出回写产品层。每一步的结论都落在磁盘工件上，由脚本闸门与独立上下文审查判定，不靠口头汇报。

## 核心机制

| 机制 | 说明 |
|---|---|
| 经理窗口 + 角色帽 | `/sdlc` 父会话只做意图分类、派单与记账；具体工作全部派给 19 个专职角色子代理（独立上下文） |
| 产品层 | `product_root`（默认 `docs/product`）承载产品的长期记忆：策略、功能地图、增长、设计系统、架构、领域模型与数据；每个帽先读、产出回写 |
| 泳道 L0–L4 | 按风险分级流程重量（一行修复免流程 → 标准功能链 → 放行/交付 → 数据线），参与角色由判定问题决定而非固定名单 |
| 脚本闸门 G-script | `check-sdlc.sh` 以工件文件与内容判定各阶段是否可过，退出码即结论 |
| 独立审查 G-fresh | 审查者是无记忆的新上下文子代理，只看磁盘工件、无写权限、不读生产者推理过程 |
| 旅程切片与联调 | 实现按可演示的用户旅程切片，UI 切片须在真实后端上走通并截图留证 |
| 三方验收 | PM 走查旅程、设计走查对照原型、增长核验卖点，任何一方不通过即返工 |
| 状态账本 | 每个功能一份 `state.yaml`：当前阶段、闸门记录、返工轮数；会话中断后从它恢复 |

## 入口命令

| 命令 | 用途 |
|---|---|
| `/sdlc` | 全流程经理窗口（意图分类 → 发现带 → 泳道 → 派单 → 闸门 → 状态） |
| `/sdlc-product` | 单独构建或维护产品层 |
| `/sdlc-discover` | 只做发现带 HITL（画框 → 市场 ∥ 竞品 → 增长定位 → 讨论 → 验伪 → briefing） |
| `/sdlc-research` | 只做 AFK 调研（researcher + competitor） |
| `/sdlc-review` | 只做独立审查，只报告不推进进度 |
| `/sdlc-eval` | 人工触发的评测（烧真实模型调用，非例行闸门） |

做法技能（26 个）也可在未挂载 `/sdlc` 的会话里以 `$名称` 单独召唤，如 `$prd-gwt`、`$schema`、`$coverage-matrix`、`$debug`、`$tdd`。

## 角色与做法

19 个角色（`agents/`）：pm、researcher、competitor、growth、architect、dba、designer、frontend、backend、algo、miner、qa、reviewer、qc、sre、ops、analyst、data-collector、data-warehouse-engineer。角色定义身份、责任边界与红线，由 `profiles/` 与共享行为栈编译生成。

26 个做法（`skills/`）以产出物命名（prd-gwt 产出 spec、schema 产出 db-spec、coverage-matrix 产出覆盖矩阵……），承载各专业的步骤与卓越标准。角色与做法的多对多映射、工件路径、阶段等级与产品写权限的唯一事实源是 `workflow/registry.json`，速查视图由其生成。

## 目录结构

```
sdlc-workflow/
├── commands/        入口命令（生成产物）
├── agents/          19 个角色（生成产物；源在 profiles/ 与 _lib/）
├── skills/          26 个做法：SKILL.md + references/ + templates/ + evals/
├── workflow/        registry.json：命令路由、角色任务、工件路径、阶段合同
├── adapters/        宿主工具档、MCP 白名单与宿主事实
├── scripts/         闸门、健康检查、角色工厂、评测评分与一致性测试
├── vendor/          上游原件：仓库只含 install.sh 与锁文件，内容由使用者从源头下载
└── .zcode-plugin/   插件清单
```

`commands/`、`agents/*.md` 与角色速查表均为生成产物，不手改；数据与源文件的唯一维护位置见 `workflow/registry.json` 与 `agents/profiles/`。

## 项目侧配置与工件

- `sdlc.config.yaml`（项目根）：闸门命令、项目红线宪法路径、MCP 提醒清单、泳道阈值
- `<product_root>/`：产品层
- `.sdlc/<feature>/`：功能工件树（01-define → 02-shape → 03-impl → 04-verify → 05-review → 06-deliver → 07-retro）+ `state.yaml` + 各角色运行时记忆

## 质量保障

| 工具 | 职责 |
|---|---|
| `scripts/check-sdlc.sh` | 阶段工件闸门（存在性 + 内容语义） |
| `scripts/health-check.sh` | 插件结构门禁：描述形态、预算上限、生成产物与源一致、防回归规则 |
| `scripts/workflow.py` | 合同查询 / 任务级检查 / 生成 commands 与速查表 |
| `scripts/render-role-agents.py` | 从 profiles 与 _lib 编译角色（`--check` 抓漂移） |
| `scripts/grade_eval.py` / `blind_eval.py` | 评测机械评分（不调模型）与盲评 |
| `scripts/ui-evidence.sh` | UI 截图留证 |

## 上游原件（vendor/）

本仓库**不分发任何上游内容**：`vendor/` 只提交 `install.sh`、说明和每个来源的锁文件。克隆后运行 `bash vendor/install.sh`，脚本按锁文件从上游源头下载同一个 commit 的同一批文件，校验树摘要一致才落盘；许可证受限的来源默认跳过。来源清单与许可证见 [vendor/README.md](vendor/README.md)。

vendor 里的内容**不会自动变成能力**：宿主不扫描 `vendor/`，插件只通过引用使用它（技能链接、派单输入、脚本调用）。健康检查保证：已安装内容与锁文件一致；runtime 文件确有引用且来自可自由使用的许可证；维护者参考不进入技能；插件内没有副本。

`discover`、`prototype` 是借鉴后改写的派生技能，只在正文注释里记录来源，不跟随上游。

## 环境与安装

- 宿主：ZCode（插件机制：skills / commands / agents）
- 依赖：bash、python3
- 安装：将本仓库克隆或链接到 `~/.zcode/local-plugins/sdlc-workflow`，运行 `bash vendor/install.sh` 下载上游原件，并在 ZCode 中启用

## 许可

MIT（见 [LICENSE](LICENSE)）
