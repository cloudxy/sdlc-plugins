# 历史项目回归案例

本目录保存 4 个 `auto_agents` 能力市场案例的输入、旧工件和评分标准定义。JSON 是案例来源；README 是索引，不记录本轮评测结论。

| 案例 | 能力 | 旧工件 | 新产物概要 |
|---|---|---|---|
| [R1-agents-market-pm](R1-agents-market-pm.json) | 双边价值、核心功能与用户旅程 | `01-define/spec.md` | spec、tracking、产品策略与功能地图 |
| [R2-agents-market-design](R2-agents-market-design.json) | 可渲染、可选择的设计方向 | `02-shape/edge-states.md` | 设计简报、方向、原型、流程、状态、令牌与设计系统 |
| [R3-agents-market-architecture](R3-agents-market-architecture.json) | 架构约束、决策与消费者交付 | `02-shape/contract.md` | 合同、ADR、接口合同与产品架构；缺最终设计的依赖项保持待完成 |
| [R4-agents-market-dba](R4-agents-market-dba.json) | 领域建模与扩展性 | `02-shape/db-spec.md`、`schema.dbml` | db-spec、DBML、产品领域模型与 ER |

## 输入与隔离

案例通过 `--project-root` 指向具备所需 Git 历史的 `auto_agents` 仓库。当前 JSON 将 `baseline_before` 设为 `2026-09-15T00:00:00+08:00`，输入与旧工件来自 `artifacts_ref: 2f256dfaa6d5214e5e2c63408329a71336d5f3f2`；具体快照由准备脚本解析。

案例的 `exclude_paths`、`hindsight_paths` 标明应排除的功能目录和后见资料。新产物在隔离快照上生成；实时工作树不能代替历史输入。`v3_gaps_observed` 是案例记录的观察线索，不是本次质量判定。

## 使用与结果

- 运行入口：`/sdlc-eval regression <case-id|all>`；项目根可以复用已提供的路径。
- 准备、泄漏检查、盲评与聚合流程见[评测技能 Step 4](../SKILL.md#step-4--real-failure-regressions-mode-regression)。
- 新案例使用[案例模板](../templates/regression-case.md)；新受控对照另见[对照协议](../references/controlled-comparisons.md)。
- 结果报告区分 `PASS`、`FAIL`、`SPLIT`、`REVIEW`、`INVALID`，保留逐项判定依据；未运行的案例不能算通过。

技能修改需要实际场景评测，但维护规则不限定模型、客户端、调用次数或模型对照。这组历史对照是可选评测方式之一；是否宣称相对旧版提高，取决于实际对照证据。当前维护要求见[维护者指南](../../../maintainers/README.md)。
