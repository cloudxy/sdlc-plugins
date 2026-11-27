<!-- sdlc:unfilled — 写入本周期的真实内容后删除本行 -->
# 周期增长实验 · <cycle-id>

> 作者：growth（周期任务 `cycle/experiments`，在 `analyst` `readout` 之后执行）｜输出：`<cycle_dir>/outputs/experiments.md`
> 纪律：每项实验绑定 `data/metrics.yaml` 的目标 `metric:<id>` 与**配对反向护栏** `metric:<id>`；分群只用 `data/tags.yaml` 可计算的 `tag:<id>`。**本文件是实验复盘与计划，不代表已发送触达或已消耗预算**（真实外发/投放须操作者显式授权）。长期结论回写 `<product_root>/growth.md` §7 并返回 delta 行。

## 1. 在跑与刚收尾实验状态（引用 `outputs/readout.md`）

| 实验 ID | 面向分群（`tag:<id>`） | 假设 | 目标指标 · 配对护栏（`metric:<id>`） | 窗口与对照（holdout / A/B） | 读数结论（引用 `outputs/readout.md` 章节） | 处置（固化全量 / 关停 / 继续观察 / 迭代） |
|---|---|---|---|---|---|---|
| EXP-1 | `tag:<id>` | | `metric:<target>` ↔ `metric:<guardrail>` | | `pending-observation` / 已显著 / 已证伪 | |

- 观察窗口未满或数据未截止时，如实标 `pending-observation`，绝不提前窥探宣布胜出或编造提升比例。

## 2. 下一周期实验提议（交 `pm` `cycle/apply-decisions` 裁决）

| 提议 ID | 分群与估计规模（`tag:<id>` + 排除规则） | 触达假设（渠道 × 时机 × 已核验卖点） | 目标指标（`metric:<id>` · MDE） | 配对反向护栏与熔断红线 | 实验设计（参照 analyst 测量方案） | 所需授权 / 埋点缺口 |
|---|---|---|---|---|---|---|
| P-EXP-1 | | | | 退订/投诉/退款/成本红线 | holdout 10% · 周期 <n> 天 | 需操作者授权外发 / 缺 `tag:…` |

## 3. 合规与真实性自检

- [ ] 所有触达文案仅引用 `accept-growth.md` 或 `<product_root>/growth.md` 已标 `✅ 已核验` 的卖点（AI 能力严禁拿挑出来的单次最佳生成冒充普遍效果；金融/医疗/合规场景严禁保本或未证实承诺）
- [ ] 跨渠道频控、退订入口、隐私同意依据（GDPR / PIPL / CAN-SPAM 等适用法域）齐备
- [ ] 固化或关停的实验已同步更新 `<product_root>/growth.md`（若在 `product_writes` 内）并返回 delta 行
