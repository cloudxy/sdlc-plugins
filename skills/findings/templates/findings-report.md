<!-- sdlc:unfilled — 写入本次的真实内容后删除本行；带这一行的文件在闸门里等于没交 -->
# G-fresh 审查报告

> 审查对象：{feature 名} · 审查时间：{ISO 时间} · 审查者：sdlc-reviewer（无记忆只读子代理）

## Snapshot

> 经理在 spawn 前计算并写入；同一组 sha256 再审 = 跳过第二次 spawn（非用户强制）。

- path: {相对 feature 的工件路径}
  sha256: {hex}

## FINDINGS

> 若无发现，在此明确写出 `zero findings`（沉默不等于通过），并在下方 `## Dimensions checked` / `## 已查维度` 完整列出 1–10 维核查结果。

### QA-01 <一句话问题>
- **维度**：{1 标准符合 / 2 标准质量 / 3 证据有效性 / 4 安全 / 5 性能与有界性 / 6 契约一致性 / 7 规范 / 8 边界 / 9 产品价值与体验 / 10 架构与设计原则}
- **严重度**：{blocker / major / minor}
- **证据**：{文件:行号 或 工件段落引用（区分静态源码核查 vs 已记录运行证据）}
- **修复建议**：{一句话可执行方向}

### QA-02 …

## Dimensions checked

> 已查维度（1–10 维每次必列；当前阶段不适用项标 `➖` 并写明原因）

| # | 维度 | 结果 |
|---|---|---|
| 1 | 标准符合（Standard conformance） | ✅ 无发现 / ⚠️ 见 QA-n / ➖ 不适用（原因） |
| 2 | 标准质量（Standard quality） | … |
| 3 | 证据有效性（Evidence validity：含交互等价的运行证据 vs 静态形状） | … |
| 4 | 安全（Security：含 `[SEC-n]` 边界锚点与租户隔离） | … |
| 5 | 性能与有界性（Performance & boundedness：SQL / 并发内存 / CLS·INP / 数仓扫描 / AI Token·延迟） | … |
| 6 | 契约一致性（Contract consistency：跨 spec/code/tests 及 GWT↔GWT） | … |
| 7 | 规范（Compliance：宪章红线、隐私、许可与访问合同） | … |
| 8 | 边界（Boundaries：空值 / 界上 / 超限 / 并发 / 越权 / 部分失败） | … |
| 9 | 产品价值与体验（Product value & experience：核心价值 / 旅程 / 原型 / 卖点 / 产品层一致） | …（引用截图、E2E、验收文件） |
| 10 | 架构与设计原则（Architecture & design principles：深模块 / SSOT·SVOT·DIE·AHA / 非法状态不可表示 / Sans-IO·CQS·无状态 / 三态外部副作用 / UX 定律与行业 SOP） | … |

## 总计

| 严重度 | 数量 | 已处置 |
|---|---|---|
| blocker | {n} | {fixed n / open n} |
| major | {n} | … |
| minor | {n} | … |
