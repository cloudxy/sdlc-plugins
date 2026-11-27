<!-- sdlc:unfilled — 写入本次的真实内容后删除本行；带这一行的文件在闸门里等于没交 -->
# 分析报告 · <标题>

> 作者：`analyst`｜日期：<YYYY-MM-DD>｜阶段：`retro/analyze`（`07-retro/analysis.md`）
> SVOT 口径源：`<product_root>/data/metrics.yaml` · `01-define/measurement-plan.md` · 运营信号：`outputs/signals-digest.md`

## 1. 结论先行

**<一段话给出结论、不确定性与可执行建议。无对照组时严格写「变化/差异」，严禁写「因为某功能导致」。>**

| 项 | 内容 |
|---|---|
| **支撑什么决策** | <决定下一轮优先修哪个环节> |
| **事前决策规则** | <若某环节绝对流失量 > 3 万且可排除埋点缺失，则进入下一轮优先范围> |
| **因果可识别性等级** | <描述性观测（无反事实对照，因果不可识别）/ 准实验（已验平行趋势）/ 随机实验（已验无 SRM 与无溢出）> |
| 窗口状态 | `<completed（窗口已闭合） | interim（观察窗未满，阶段性描述读数）>` |

## 2.0 归因前数据链路健康排障门禁

> **硬准出铁律**：开展指标拆解与归因前必须先过以下六点健康核查。一旦检出数据链路异常污染分析窗口，**必须打标 `[数据污染区间：<start..end>]`、立即中止对污染数据的业务/因果归因**，并在第 7 节首行输出 **`Fix Data Pipeline First (collect / warehouse)`** 任务单，严禁在坏数据上强推业务结论！

| # | 排障检查项 | 核验证据与量化结果 | 状态 |
|---|---|---|---|
| ① | **埋点与契约版本（Tracking Version）** | `<tracking-plan.yaml@v<n> 各端版本与属性枚举核对一致>` | ✅ / ❌ |
| ② | **采集与入仓延迟（Ingestion Lag）** | `<目标分区 availability_time 已过回溯窗且无延迟截断>` | ✅ / ❌ |
| ③ | **重复与缺失事件（Duplicate / Missing Events）** | `<去重唯一键有效；前后端日志与业务库对账偏差 < 3%>` | ✅ / ❌ |
| ④ | **身份映射（Identity Mapping）** | `<anonymous_id ↔ user_id 归并及 tenant_id 完整无串号>` | ✅ / ❌ |
| ⑤ | **查询过滤（Query Filters）** | `<与 metrics.yaml exclusions 1:1 一致（已剔除内部/测试/爬虫流量）>` | ✅ / ❌ |
| ⑥ | **同期代码发布与开关变更（Concurrent Releases）** | `<已核对 sre 窗口内发布、回滚与 Feature Flag 变更时间线>` | ✅ / ❌ |

- **数据健康门禁裁决**：`<✅ 六项全绿，允许进入下方分析 | ❌ 检出污染区间 [<start..end>] → 已熔断归因，转派 Fix Data Pipeline First (collect / warehouse)>`

## 2. 引用指标与配对护栏（SVOT 引用，必列可复算分子·分母·时间窗）

> 权威计算逻辑唯一保存在 `<product_root>/data/metrics.yaml`；每行指标读数必须展示**可复算分子、分母与精确时间窗**（保证 `ops`、`analyst`、`warehouse` 三方复算一致）。若需调整公式，先向 `pm` 与 `data-warehouse-engineer` 提版本变更提案。

| 角色 | SVOT 指标引用 (`metric:<id>@v<n>`) | `time_semantics` 与精确时间窗 | **可复算分子 / 分母** | 指标读数（含切片过滤与 95% CI） |
|---|---|---|---|---|
| 主分析指标 | `metric:export_weekly_usage_rate@v1` | `event_time` · `2026-08-01..2026-08-31` | 去重导出主管 `521` / 活跃主管 `1,240` | `42.0%`（排除 `tag:internal_user`） |
| 关联价值指标 | `metric:ticket_avg_resolution_time@v1` | `business_time` · `2026-08-01..2026-08-31`（含 7d 回溯） | 总解决时长 `761,760m` / 已结工单 `18,400` | `41.4m` |
| **配对护栏** | `metric:report_p95_load_ms@v1` | `event_time` · `2026-08-01..2026-08-31` | P95 请求耗时 / 有效请求 `94,120` | `835ms`（红线 `≤ 1000ms` ✅） |

## 3. 数据快照描述符与质量核查

| 项 | 内容 |
|---|---|
| 数据源与快照标识 | `<只读数仓 / 只读副本>`（**未直连生产 OLTP 主库**）· 快照/分区 ID：`<snapshot_id / dt 范围>` · 查询时刻：`<ISO 时间>` |
| 总体与样本量 | `<100,000 次列表访问，来自 1,240 个主管>` |
| **数据质量与异常披露** | `<8 月 12 日埋点延迟导致上报缺口，已按预设规则单独标注敏感性对比；SRM 检验：N/A 或 p=0.64>` |

## 4. 分析与分层拆解

### 4.1 漏斗 / 同期群 / 分组全景（必给分母、绝对量与不确定性）

- **漏斗规则（适用时）**：允许跳步 `<否>` · 回退重算 `<算单次用户去重>` · 转化时间窗 `<30 分钟>`

| 步骤 / 分组（窗口：`2026-08-01..2026-08-31`） | **可复算分子（转化数）** | **进入分母 (`N`)** | 转化率 / 指标值 | **绝对流失 / 绝对差值** | 95% CI / 波动范围（抽样或推断时必填） |
|---|---|---|---|---|---|
| 浏览列表 → 点击导出 | 85,000 | 100,000 | 85.0% | 15,000 | —（全量普查） |
| **点击导出 → 配置确认** | **31,280** | 78,200 | **40.0%** | **46,920（最大流失点）** | — |
| ↳ 其中：桌面端 vs **移动端** | 29,498 vs **1,782** | 62,000 vs **16,200** | 47.6% vs **11.0%** | -36.6pp（移动端流失 14,418） | `95% CI [-37.7pp, -35.5pp]` |

**防辛普森悖论**：总体指标常被流量结构（移动端占比、新老租户结构）掩盖，关键结论必须交叉核对核心维度并结合 `outputs/signals-digest.md` 定性信号定位机制。

## 5. 因果可识别性与反驳自检（Refutation Checks）

| 替代解释 / 混淆源 | 检验方法 | 实测证据 | 判定 |
|---|---|---|---|
| ① 选择偏差（使用者原本就更活跃） | 对比使用与未使用人群在功能上线前的历史基线 | <上线前两组处理时长差异 11.8% vs 12.0%> | 可排除 / **成立（阻断因果归因）** |
| ② 同期其它变更混淆 | 核对 `sre` 同期发布与配置变更记录 | <列出同期上线项及受影响人群交集> | 可排除 / 无法排除 |
| ③ 季节性 / 埋点端侧偏差 | 对比历史同期 + 前后端请求日志交叉对账 | <移动端前端事件与后端请求差异仅 2.8%> | 可排除 |

**修正后的结论**：<明确指出哪些效应已确立、哪些因缺乏反事实对照仍属待验证假设。>

## 6. 可复现 SQL / 代码（Reproducible Query）

```sql
-- Snapshot: <snapshot_id> | Engine: <dialect> | Metrics: metric:export_weekly_usage_rate@v1
SELECT platform,
       COUNT(DISTINCT actor_id) AS entered_users,
       COUNT(DISTINCT CASE WHEN confirmed = 1 THEN actor_id END) AS confirmed_users
FROM ads_export_funnel_daily
WHERE dt BETWEEN '2026-08-01' AND '2026-08-31'
  AND is_internal_user = FALSE
GROUP BY platform;
```

## 7. 决策建议与 Seam 1 回流归口（提交下游，不直接改写 `strategy.md`）

| # | 建议动作（若 `## 2.0` 检出污染则首行必填 `Fix Data Pipeline First (collect / warehouse)`） | 支撑的决策 | **归口角色（Feedback Intake Owner）** | **回流 Seam 1 / 下游承接入口** |
|---|---|---|---|---|
| P-01 | <优先针对移动端列选择控件做可用性优化与原型验证> | <下一轮范围优先级> | `pm`（协同 `designer`） | `00-discover/briefing.md` / 下周期 `cycle` |
| P-02 | <补齐移动端步骤内交互细粒度事件（或修复异常埋点/数仓链路）> | <消除机制盲区 / 修复数据污染> | `data-collector` / `data-warehouse-engineer` | `data/tracking-plan.yaml` / `02-shape/collect/` |

## 8. 自检

- [ ] 结论先行，说清支撑的决策与事前规则；未满窗口已标 `interim`
- [ ] **`## 2.0 归因前数据链路健康排障门禁`** 六项已核查；数据污染区间已打标并熔断归因、优先派发 `Fix Data Pipeline First (collect / warehouse)`
- [ ] 口径严格引用 `<product_root>/data/metrics.yaml` (`metric:<id>@v<n>`)，每行读数均列出**可复算分子、分母与精确时间窗**（`ops`/`analyst`/`warehouse` 一致），且含配对护栏
- [ ] 明确声明因果可识别性，无有效对照组绝未使用「导致 / 归因于」
- [ ] 已做反驳自检（选择偏差、同期变更、季节性、辛普森悖论、数据缺口）
- [ ] 附原样可复现 SQL 与快照标识；使用只读库；无明文 PII（分组聚合 `≥ 5` 人）；每条提案均指明**归口角色（Feedback Intake Owner）**回流 Seam 1（`00-discover` / `cycle`）
