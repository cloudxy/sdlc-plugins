# 产品层 · <产品名>

> 这是产品的长期记忆。每个功能的每顶帽子**先读这里**，产出后**回写这里**。功能目录（`.sdlc/<feature>/`）只放这一次变更的工件。
> 规则全文：插件 `skills/sdlc/references/product-layer.md`。

## 文件与负责人

| 文件 | 负责人（写） | 一句话 |
|---|---|---|
| `strategy.md` | pm | 为谁解决什么、为什么是我们、北极星、关键假设 |
| `feature-map.md` | pm | 核心价值路径、功能分层（Kano）、关键用户旅程、Now/Next/Later |
| `growth.md` | growth | 定位、卖点（可演示时刻）、人群分群、渠道、增长回路、实验记录 |
| `design-system.md` | designer | 设计原则、品牌性格、视觉语言、签名时刻、可访问性底线 |
| `architecture.md` | architect | 质量属性场景、容量模型、架构基线、演进路线、适应度函数、ADR 索引 |
| `domain-model.md` · `erd.dbml` | dba | 限界上下文、统一语言、聚合与不变量、扩展点、全局 ER |
| `data/tracking-plan.yaml` | data-collector（pm 经 tracking.md 提事件） | 埋点规范与事件字典 |
| `data/metrics.yaml` | data-warehouse-engineer | 指标树（北极星 → 驱动 → 护栏），全产品唯一口径 |
| `data/tags.yaml` | data-warehouse-engineer | 用户标签体系，供增长运营精准分群 |
| `CHANGELOG.md` | 经理（按帽子返回的变更行） | 每次变更一行 |

## 约定

- 模板里的 `sdlc:unfilled` 标记 = 还没填。负责人写入真实内容后删除标记；闸门把带标记的文件当作缺失。
- 只放**长期成立的事实**，不贴功能细节。`strategy.md` 控制在两屏内。
- 改别人负责的文件 → 提 open question 给负责人，不直接改。
- 推断出的内容标 `[推断]`，并列为负责人的待确认项。
