# M 档功能工件索引

用于 L2 / L3 功能；L4 按数据任务追加工件。这是功能目录的阅读索引，具体必需项由已选任务、条件与完成目标决定，以[阶段合同](../../references/stage-map.md)和 `workflow/registry.json` 为准。

下表路径相对于业务项目的 `.sdlc/<feature>/`；本目录不存放业务产物。需要正文模板时，从各技能的 `templates/` 取用，通用章节可复用 [S 档模板](../spec-s.md)。

| 目录 | 常见工件与用途 |
|---|---|
| `00-discover/` | `briefing.md`；按需产出 `market.md`、`compete.md`、`growth.md` |
| `01-define/` | `spec.md`、`test-plan.md`、`measurement-plan.md`；需要时补 `tracking.md` 与 `architecture-feasibility.md` |
| `02-shape/` | UI：`design-brief.md`、`design-directions.md`、`prototypes/`、`flows.md`、`edge-states.md`、`design-tokens.json`；工程：`contract.md`、`adr-*.md`、`contracts/`、`tickets/`、`db-spec.md`、`schema.dbml` |
| `03-impl/` | `T-<n>-<role>-evidence.md`；UI 旅程切片的 `T-<n>-integration.md` 附真实后端联调与截图证据 |
| `04-verify/` | `coverage.md`；`accept-pm.md`、`accept-design.md`、`accept-growth.md`；按需产出架构与数据校验 |
| `05-review/` | `findings.md`：独立审查结果 |
| `06-deliver/` | `readiness.md`（SRE 准备）、`release-opinion.md`（QC 意见）、`checklist.md`（SRE 交付）；`enablement.md`、`launch.md` 按任务执行 |
| `07-retro/` | `retro.md`：真实数据复盘 |
| 功能根目录 | `state.yaml`、`product-delta.md`、`packets/`、`evidence/runs/`、`memory/<role>.md`；reviewer / qc 不保存角色记忆 |

`coverage.md` 连接 FR / NFR / J / EV、契约、实现票与用例；缺口必须明确标注。最终原型代码在 `02-shape/prototypes/final/`。目录或模板存在不等于对应阶段已经完成。

## 数据任务与局部工作

数据任务按需增加 `02-shape/collect/`、`02-shape/warehouse/`、实现证据和 `04-verify/` 中的校验；精确文件名查任务合同，避免把旧示例目录当作必需路径。

只诊断、打磨、审计或补数等任务使用相同的任务合同与证据协议；工件版本、工作区导入和完成记录见[持续工作协议](../../references/continuous-work.md)。

## 跨功能产品层

长期资料放在 `<product_root>/`（默认 `docs/product/`），包括策略、功能地图、增长、设计系统、架构、领域模型、ER 与 `data/` 定义。功能产出后按归属回写，并在 `product-delta.md` 留记录。见[产品层协议](../../references/product-layer.md)和[产品 README 模板](../product-readme.md)。
