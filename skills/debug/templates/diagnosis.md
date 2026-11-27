<!-- sdlc:unfilled — 写入真实内容后删除本行；未填写的模板不算交付 -->
# 技术诊断报告 · <症状或缺陷标识>

> 任务：`implement/diagnose` 或 `collect/diagnose`｜角色：<backend | frontend | algo | miner | collector>｜日期：<YYYY-MM-DD>
> 输入基准：代码 `<commit>` · 运行环境 `<env>` · 期望行为主源 `<spec / contract / eval-set / baseline@rev>`
> 诊断结论：<confirmed: 一句话机制 | suspected: 最优假设 + 缺口 | inconclusive: 已排除范围 + 下一步探测>

独立诊断阶段**严禁修改生产源码**或越权改写 GWT / schema / tokens。诊断探针退出码为 0 仅代表**复现确认（reproduction confirmed）**，绝不代表缺陷已修复。

## 1. 原始复现记录（先复现后假设）

```text
$ <最小定向复现命令或真实事件序列；UI 一致性/等价性问题须记录实际 click -> observe 交互>
<原样粘贴失败输出、状态码、跨项求和对比或 DOM/日志采样>
exit: <code（注明 reproduction confirmed 或 reproduction unavailable）>
```

失败集特征：☐ 稳定必现（指向语义/契约/查询/空集与缺失混淆） ☐ 间歇波动（指向并发竞态/跨 worker 局部状态/时序窗口/`In-Doubt` 超时）

## 2. 假设排查与二分隔离记录

| # | 候选假设（具体机制而非症状） | 区分性只读探针（直查存储/日志/计划/事件序） | 原始观测结果 | 判定（`confirmed` / `suspected` / `ruled out`） |
|---|---|---|---|---|
| H1 | <例：多 worker 下模块级字典缓存未共享导致权限闪烁> | <读取两实例状态或构造跨进程请求> | <观测事实> | <confirmed / ruled out> |
| H2 | <例：查询分页前未按身份过滤导致目标行被挤出前页> | <直连只读库核对计数与分页 SQL> | <观测事实> | <ruled out> |

## 3. 根因机制、置信度与影响面

- **`root_cause`（机制链）**：<精确到模块/边界/状态转换失守原因；若存在多因链或未证全，明确区分已证实环节与未知边界>。
- **置信度**：<high / medium / low + 仍缺的判别条件（如真机/生产流量样本）>。
- **受影响消费者与数据范围**：<受波及的接口、页面、历史数据或下游任务；事故场景下与止血缓解措施分开记录>。

## 4. 建议后续动作与路由（不在此执行修复）

| 动作类型 | 负责角色 | 建议最小改动面 / 需补回归检查 | 是否需上游先拍板 |
|---|---|---|---|
| <进入 `implement/fix` / 交 `dba` / 交 `pm` 澄清期望> | `<backend / frontend / algo / dba / pm>` | <触及模块 + 复现命令转回归用例> | <否 / 是（说明契约或需求歧义）> |
