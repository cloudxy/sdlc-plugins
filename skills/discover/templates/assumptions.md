<!-- sdlc:unfilled — 写入本次的真实内容后删除本行；带这一行的文件在闸门里等于没交 -->
# Falsify · <本变更>

> **唯一事实源（SSOT）纪律**：完整发现流程直接写在 `00-discover/briefing.md` § Falsify；仅在无完整 briefing 的局部假设检验或 briefing 超长外链时单独使用本文件，**禁止同时维护两份内容漂移的表**（并存时以 `briefing.md` 为准）。

| ID | 假设（可证伪的一句） | 若假则 | 最便宜检验 | 证据级 | 结果 |
|---|---|---|---|---|---|
| A1 | | | | E0–E4 | 存活/杀死/赌注/待定 |

杀死条件（预先写死）：
- 

本轮裁决：<只写一个：杀死 | 缩小后存活 | 当作赌注 | 通过 | 待定（写明缺的是场景、投入边界还是指标）>

本轮裁决为「当作赌注」时必填（其他裁决不编造赌注，键名与 `briefing.md` 及 `state.yaml` `bet:` / `scripts/gates/outcomes.py` 严格一致）：
- 不确定性与可承受损失：<一句话>
- `hypothesis`：`H-<n>`（对应产品层 `strategy.md` §7 假设编号）
- `metric`（复盘指标）：`<metric_id>`（define 的北极星或驱动必须是它）
- 配对反向护栏：`<guardrail_metric_id>` < `<红线阈值>`（防局部优化损害留存/退款/成本）
- `evidence_grade`：`E0–E4`
- `readout_due`：`<YYYY-MM-DD>`（功能关闭前写入 `state.yaml` `bet:`，到期由经理提醒复盘）
