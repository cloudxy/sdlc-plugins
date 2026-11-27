<!-- sdlc:unfilled — 写入本次的真实内容后删除本行；带这一行的文件在闸门里等于没交 -->
# 效果复盘 · <功能名>

> 作者：`analyst`｜日期：<YYYY-MM-DD>｜上线日期：<日期>｜窗口状态：`<completed（已满判定周期） | interim（观察窗未满）>`
> 上游：`<product_root>/data/metrics.yaml`（SVOT 口径）· `01-define/measurement-plan.md`（事前预测与规则）· `01-define/spec.md` · `outputs/signals-digest.md`（`ops` 信号汇总）
> **复盘的价值在于检验因果假设与判断力，而不是美化现状；假设变更仅以提案交给 `pm` `apply-decisions`，严禁直接改写 `strategy.md`。**

## 1. 结论先行

**<一段话：对照 `01-define/measurement-plan.md` 事前规则，哪些指标与配对护栏达标、因果效应是否可识别、`strategy.md` 哪条假设应更新、下一步最佳押注是什么。>**

## 2.0 归因前数据链路健康排障门禁

> **硬准出铁律**：进入效果判定与因果归因前逐项核查以下六点。若存在污染目标窗口的数据系统故障，**必须打标 `[数据污染区间：<start..end>]`、立即中止基于污染数据的业务归因**，并在第 8 节首条直接输出 **`Fix Data Pipeline First (collect / warehouse)`** 任务单，严禁基于失真遥测推导产品结论！

| # | 排障检查项 | 核验结果与量化证据 | 状态 |
|---|---|---|---|
| ① | **埋点与契约版本（Tracking Version）** | `<tracking-plan.yaml@v<n> 在各端覆盖率 ≥ 99.5%，属性枚举无缺失>` | ✅ / ❌ |
| ② | **采集与入仓延迟（Ingestion Lag）** | `<各分区 availability_time 准点就绪，已留足迟到回溯窗，无尾部未落盘截断>` | ✅ / ❌ |
| ③ | **重复与缺失事件（Duplicate / Missing Events）** | `<事件去重唯一键生效；前端上报与后端事实表交叉对账偏差 1.2% < 阈值>` | ✅ / ❌ |
| ④ | **身份映射（Identity Mapping）** | `<anonymous_id → user_id 归并率正常，登出已轮换，tenant_id 零空值串号>` | ✅ / ❌ |
| ⑤ | **查询过滤（Query Filters）** | `<严格对齐 metrics.yaml exclusions（已剔除测试租户、内部员工与压测流量）>` | ✅ / ❌ |
| ⑥ | **同期代码发布与开关变更（Concurrent Releases）** | `<已对齐 sre 发布与 Feature Flag 放量日志：<列出时间轴或无重叠变更>>` | ✅ / ❌ |

- **数据健康门禁裁决**：`<✅ 六项全绿，允许进入下方归因 | ❌ 检出数据链路异常 [数据污染区间：<...>] → 已熔断业务归因，转派 P-00 Fix Data Pipeline First (collect / warehouse)>`

## 2. 对照事前目标与配对护栏（引用 SVOT `metric:<id>@v<n>`，必含可复算分子·分母·时间窗）

> 每行读数必须展示**可复算分子、分母与精确时间窗**，确保 `ops`、`analyst`、`warehouse` 三方复算完全一致。

| 层 | SVOT 指标引用 (`metric:<id>@v<n>`) | `time_semantics` 与精确时间窗 | **事前基线 → 目标 / 红线** | **可复算分子 / 分母** | 实际读数（含 95% CI） | 判定 |
|---|---|---|---|---|---|---|
| **北极星** | `metric:ticket_avg_resolution_time@v1` | `business_time` · `2026-08-03..08-31` | `45.0m → 下降 ≥15%` | 总解决时长 `761,760m` / 已结工单 `18,400` 单 | `41.4m（下降 8.0%, 95% CI [-9.1%, -6.9%]）` | ⚠️ **未达成** |
| 驱动 | `metric:export_weekly_usage_rate@v1` | `event_time` · `2026-08-03..08-31` | `12.0% → ≥30.0%` | 去重导出主管 `521` 人 / 活跃主管 `1,240` 人 | `42.0%（95% CI [39.3%, 44.8%]）` | ✅ 超预期 |
| **配对护栏 1** | `metric:report_p95_load_ms@v1` | `event_time` · `2026-08-03..08-31` | **红线 `≤ 1000ms`** | 第 95 百分位请求耗时 / 有效请求 `94,120` 次 | `835ms` | ✅ 未破线 |
| **配对护栏 2** | `metric:unsubscribe_rate@v1` | `business_time` · `2026-08-03..08-31` | **红线 `≤ 0.6%`** | 退订人数 `19` 人 / 触达人数 `5,000` 人 | `0.38%` | ✅ 未破线 |

**关键机制洞察**：「驱动指标超预期但北极星未达成」说明执行到位但当初的**因果链假设有误**（瓶颈在下游环节而非本功能），这是复盘最高价值的发现。

## 3. 三类全报（达成 / 未达成 / 意外与定性信号）

- **✅ 达成**：`<指标 + 样本量 + 成立机制>`
- **⚠️ 未达成（逐条标注「已数据验证」或「待验推测」）**：`<目标差距 + 可能原因拆解 + 验证状态>`
- **❌ 意外发现与用户信号（关联 `outputs/signals-digest.md`）**：`<如信号 S-04「导出列不足」7 条、移动端采纳率仅 4% 等>`

## 4. 因果可识别性与反驳自检（Causal Identifiability & Refutation）

| 项 | 核查结果 |
|---|---|
| **识别设计** | `<RCT（SRM p=0.58，ITT 口径）/ Tenant·Cluster·Switchback 实验（已排除双边抢单与跨租户溢出）/ DID（已验平行趋势）/ 全量上线无对照（因果不可识别，仅报可观测变化）>` |
| **同期变更排查** | <已核对 `sre` 发布记录：列出窗口内上线的其它功能/配置及影响交集> |
| **季节性与外部冲击** | <对比去年同月与大盘趋势：淡季可解释约 `-5%`> |
| **选择偏差检验** | <核对采纳人群上线前基线：使用导出的主管在上线前处理时长已比均值低 `12%` → 不可做横截面直接归因> |
| **修正后净结论** | <剔除混淆后可确立的效应范围与不确定性边界> |

## 5. 增长触达与埋点数据质量回顾

| 项 | 状态与证据 |
|---|---|
| 增长实验/触达活动表现（对照 `06-deliver/launch.md`） | `<各渠道/分群转化与配对退订护栏表现；无增长活动填 N/A>` |
| `01-define/tracking.md` (`EV-n`) 数据健康度 | `<事件完整率、身份打通率、迟到率；暴露的新埋点缺口>` |

## 6. 可复现 SQL 与数据快照（Reproducible SQL & Snapshot）

```sql
-- Snapshot: <snapshot_id / partition range> | Cutoff: <ISO timestamp> | Store: read-only warehouse
-- Consumes canonical SVOT views for metric:export_weekly_usage_rate@v1 & metric:ticket_avg_resolution_time@v1
SELECT week_start,
       active_supervisors,
       export_supervisors,
       ROUND(export_supervisors * 1.0 / NULLIF(active_supervisors, 0), 4) AS export_weekly_usage_rate,
       avg_resolution_minutes,
       p95_load_ms
FROM ads_feature_export_readout_weekly
WHERE week_start BETWEEN '2026-08-03' AND '2026-08-31'
ORDER BY week_start;
```

## 7. 结构化假设更新提案表 `H-<n>`（交 `pm` `apply-decisions` 审定）

| 假设 ID（`strategy.md`） | 原假设陈述 | 建议状态变更 | 核心证据与可识别性等级 | 团队认知更新 |
|---|---|---|---|---|
| `H-01` | <主管高频需要批量导出工单> | `validated` | 周使用率达 `42.0%`（目标 `30%`，`N=1,240`） | 取数诉求真实存在 |
| `H-02` | <批量导出可使工单总处理时长下降 `≥15%`> | `invalidated` | 总时长仅降 `8%` 且含 `-5%` 淡季混淆；外部协作往返占总时长 `72%` | 真正瓶颈在跨组织回填，不在本地导出 |

## 8. 结构化下一步行动提案表 `P-<n>`（明确归口角色，闭环回流 Seam 1）

| 提案 ID | 建议动作（若 `## 2.0` 异常则首行必填 `Fix Data Pipeline First`） | 关联依据（`H-n` / 信号 ID / 污染区间） | 目标指标与配对护栏 (`metric:<id>@v<n>`) | **归口角色（Feedback Intake Owner）** | **Seam 1 / 下游承接入口** |
|---|---|---|---|---|---|
| `P-01` | <立项评估「外部协作在线回填」，替代线下表格往返> | `H-02` · `S-04` | `metric:ticket_avg_resolution_time@v1` + 护栏 `metric:external_submit_error_rate@v1` | `pm` | `00-discover/briefing.md` / 下周期 `cycle` |
| `P-02` | <设计按 `tenant_id` 分流的双周聚类实验验证新协作流真实因果净效> | `H-02` | 同上（防租户内协作溢出） | `analyst`（协同 `growth`） | 下轮 `01-define/measurement-plan.md` |
| `P-03` | <补齐移动端配置弹窗交互埋点（若数据异常则为 `Fix Data Pipeline First (collect / warehouse)`）> | 移动端使用率仅 `4%` | `metric:export_weekly_usage_rate@v1` | `data-collector` / `data-warehouse-engineer` | `data/tracking-plan.yaml` / `02-shape/collect/` |

## 9. 自检

- [ ] 结论先行；未结束观察窗已明确标注 `interim`
- [ ] **`## 2.0 归因前数据链路健康排障门禁`** 六项已先行核验；存在污染区间时已停止业务归因并派发 `Fix Data Pipeline First (collect / warehouse)`
- [ ] 每行指标严格引用 `<product_root>/data/metrics.yaml` (`metric:<id>@v<n>`)，完整列出**可复算分子、分母与精确时间窗**（`ops`/`analyst`/`warehouse` 对齐），且含配对护栏
- [ ] 达成、未达成与 `outputs/signals-digest.md` 意外信号三类齐全
- [ ] 因果可识别性声明清晰（含 SRM / SUTVA 干扰 / 同期变更 / 季节性 / 选择偏差检验），无对照绝未宣称因果
- [ ] 附可复现 SQL 与只读快照标识，无明文 PII
- [ ] 已输出结构化 `H-<n>` 与 `P-<n>` 提案表，明确指定**归口角色（Feedback Intake Owner）**回流 Seam 1（`00-discover` / `cycle`），未直接修改 `strategy.md`
