<!-- sdlc:unfilled — 写入本次的真实内容后删除本行；带这一行的文件在闸门里等于没交 -->
# 埋点需求 · <功能名>

> 作者：pm 帽（伴生 collect）｜泳道：L<n>｜日期：<YYYY-MM-DD>
> 上游：spec 度量蓝图｜下游：data-collector（合并进产品 tracking-plan）· frontend/backend（实现）· qa（EV-n 校验）
> 规范：优先复用产品 `data/tracking-plan.yaml` 已有的对象、属性与身份规则。**决策绑定铁律：每条 `EV-n` 必须绑定到具体产品/运营决策或可证伪假设（`H-n`），严禁「先埋着以后可能用」的投机性埋点！**

## 1. 指标 → 决策/可证伪假设 → 行为 → 事件

| 指标 id（`metrics.yaml`） | 绑定的具体决策或可证伪假设（`H-n` + 触发阈值，禁泛泛而谈） | 需要观察的行为 | 事件（`EV-n`） |
|---|---|---|---|
| `<metric_id>` | `<例：验证 H-02；若配置确认步流失 > 40%，下迭代重做移动端列选择器>` | `<点击导出并提交配置>` | `EV-1` |

## 2. 事件清单

```yaml
- id: EV-1
  event: <object_action>
  decision_or_hypothesis: <支撑的具体决策或 H-n 可证伪假设；无明确决策绑定的一律砍除>
  journey: <J-n 第几步>
  trigger: <从用户视角描述的触发时刻>
  placement: <client | server | both（注明口径以哪端为准）>
  properties:
    <name>: {type: <string|integer|boolean|enum>, required: <true|false>, values: [<枚举值>]}
  metric: <metrics.yaml id>
  owner: pm
  validation: <qa 怎么看到它触发一次且属性正确>
```

## 3. 身份与合规

| 项 | 本功能涉及？ | 说明 |
|---|---|---|
| 登录前行为需要归并到用户 | 是/否 | |
| 新增公共属性 | 是/否 | |
| 涉及个人信息 / 同意状态 | 是/否 | |

## 4. 不做的埋点（及理由 — 凡「先埋着以后可能用」均在此拒入）

| 候选 | 为什么不做（如：无绑定决策/可证伪假设，属「先埋着以后可能用」） |
|---|---|
