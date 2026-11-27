<!-- sdlc:unfilled — 写入真实内容后删除本行；未填写的模板不算交付 -->
# 度量与识别计划（Measurement Plan）· <功能名>

> 阶段：`define/measurement-plan`（`01-define/measurement-plan.md`）｜作者：`analyst`｜日期：<YYYY-MM-DD>
> SVOT 口径源：`<product_root>/data/metrics.yaml@v<n>`｜上游：`01-define/spec.md` · `01-define/tracking.md`
> **纪律：事前锁定决策规则、SVOT 指标引用、配对护栏与因果识别设计；普通运营报表不强套随机实验。**

## 1. 支撑的决策与事前决策规则

| 项 | 内容 |
|---|---|
| 要支撑的业务决策 | <例：上线 2 周后决定全量保留、迭代优化还是下线新导出入口> |
| **事前写死的决策规则** | <例：主指标相对基线提升 `≥ +3pp` 且所有配对护栏未破红线 → 全量保留；护栏破线 → 立即回滚> |
| 关联策略假设（`strategy.md`） | `<H-01, H-02>` |

## 2. 配对指标体系（引用 SVOT `metric:<id>@v<n>`，禁止在此另抄 SQL 口径）

| 角色 | SVOT 引用 (`metric:<id>@v<n>`) | `time_semantics` | 基线值（窗口） | 目标 / **护栏红线** | 配对关系说明 |
|---|---|---|---|---|---|
| 北极星 / 主决策指标（OEC） | `metric:first_report_view_rate@v1` | `event_time` | `28.0%`（近 4 周） | `≥ 33.0%` | 衡量核心价值兑现 |
| 驱动指标 | `metric:export_weekly_usage_rate@v1` | `event_time` | `12.0%` | `≥ 18.0%` | 衡量功能触达采纳 |
| **配对护栏 1（性能/可靠）** | `metric:report_p95_load_ms@v1` | `event_time` | `820ms` | **红线 `≤ 1000ms`** | 防止新入口拖慢列表与首屏 |
| **配对护栏 2（体验/负向）** | `metric:unsubscribe_rate@v1` | `business_time` | `0.4%` | **红线 `≤ 0.6%`** | 防过度引导引发反感或退订 |

## 3. 目标人群、窗口与埋点/数据就绪核查

| 项 | 设定 |
|---|---|
| 分析单位与目标总体 | `<user_id / tenant_id>` · 排除项遵循 `metrics.yaml`（如 `tag:internal_user`） |
| 观察窗口与成熟期 | 上线后 `<14 天>`（至少覆盖完整自然周 + 指标回溯成熟窗口 `<24h>`；未满期输出一律标 `interim`） |
| 依赖事件与数据表 | 事件：`EV-1, EV-2`（见 `01-define/tracking.md`）· 表：`<dwd_events / fct_orders>`（只读数仓/副本） |
| 读数前必跑数据健康检查 | 事件非空率、身份打通率、（若实验）**SRM 分流比卡方检验 `p ≥ 0.01`** |

## 4. 因果识别与评估方法（按实际设计选择，不强加 RCT）

| 项 | 本次采用方案 |
|---|---|
| **评估类型** | `<随机实验 RCT / 租户或地域聚类实验 / Switchback 轮转实验 / 准实验 DID·RDD / 前后描述性监测>` |
| **溢出与网络干扰判断（SUTVA）** | <例：B2B 同租户内主管共享界面会互相影响 → **按 `tenant_id` 分流**（双边共享供给市场必须用 `Switchback` 或双边隔离，严禁个人级分流）> |
| **可识别性前提与反驳检验** | <RCT：验 AA 均衡 + SRM + ITT 估计｜DID：验处理前平行趋势｜无对照：声明**因果不可识别**，核对 `sre` 同期变更、季节性与使用前基线选择偏差> |
| **实验参数（仅实验时填）** | 分流比例 `<50/50>` · MDE `<+3pp>` · 样本量 `<n/组>` · **停止规则：跑满 `<14>` 天前严禁 peeking OEC（中途仅看护栏止损）** |

## 5. 待决依赖

- [ ] <例：若新增指标尚未合入 `<product_root>/data/metrics.yaml`，须由 `pm` 确认语义后交 `data-warehouse-engineer` 注册版本>
