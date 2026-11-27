<!-- sdlc:unfilled — 写入本次的真实内容后删除本行；带这一行的文件在闸门里等于没交 -->
# 特征字典 · <项目名>

> 上游：`problem-framing.md`｜作者：miner｜特征集版本：`feature_set@v<n>`｜日期：<YYYY-MM-DD>
> **铁律：每个特征必须显式区分 `event_time`（业务发生时间）与 `availability_time`（入库可用时间），统一按 `(entity, availability_time <= decision_time)` 关联，防止 T+1 落库延迟在离线训练中穿越！**

## 特征清单（双时间戳与 Point-in-Time 契约）

| # | 特征名 | 计算逻辑 | `event_time`（业务发生时间列） | `availability_time`（入库可用时间列） | Point-in-Time 关联口径 `(entity, availability_time <= decision_time)` | 来源 | 缺失率 | 缺失含义与处理 |
|---|---|---|---|---|---|---|---|---|
| 1 | `logins_30d_before_asof` | 30 天内登录去重天数 | `logins.occurred_at` | `logins.ingested_at`（流式 `<5s`） | `user_id = :entity AND occurred_at >= :decision_time - 30d AND occurred_at < :decision_time AND ingested_at <= :decision_time` | `logins` | 0% | 无缺失（无登录=0） |
| 2 | `days_since_last_login_at_asof` | 决策时刻距最后可用登录天数 | `logins.occurred_at` | `logins.ingested_at` | `DATEDIFF(:decision_time, MAX(occurred_at)) WHERE ingested_at <= :decision_time` | `logins` | 0% | — |
| 3 | `orders_90d_before_asof` | 90 天已支付订单数 | `orders.paid_at` | `orders.dwd_available_at` | `user_id = :entity AND paid_at >= :decision_time - 90d AND paid_at < :decision_time AND dwd_available_at <= :decision_time` | `orders` | 0% | 无订单=0 |
| 4 | `avg_amount_90d_before_asof` | 90 天平均订单额 | `orders.paid_at` | `orders.dwd_available_at` | 同上，`AVG(amount)` | `orders` | 42% | **缺失=期内无订单**（结构性缺失）→ 填 0 + 缺失标记列 |
| 5 | `tickets_30d_before_asof` | 30 天工单数（T+1 批处理表） | `tickets.created_at` | `tickets.partition_ready_at`（次日 `04:00`） | `user_id = :entity AND created_at >= :decision_time - 30d AND partition_ready_at <= :decision_time` | `tickets` | 0% | 无工单=0（T+1 延迟已被 `availability_time` 严格截断） |
| 6 | `city_churn_rate_before_asof` | 所在城市历史流失率 | `churn_labels.label_matured_at` | `churn_labels.published_at` | `published_at <= :decision_time` 且**排除本用户** | 派生 | 3% | 新城市样本不足 → 填训练集全局均值 |

**缺失含义必须区分「结构性缺失」与「未知」**：第 4 行的 42% 缺失是因为期内无订单（信息本身有意义），不是数据丢失——填 0 并加缺失标记列，让模型能区分「金额为 0」和「无订单」。

## 双时间戳与 Point-in-Time 口径核对

每个特征的离线回填与线上取数 SQL 必须同时受 `event_time` 与 `availability_time <= decision_time` 约束：

- [ ] 特征 1–6 逐个声明了 `event_time` 与 `availability_time`，且关联键严格满足 `(entity, availability_time <= decision_time)`
- [ ] 无仅按 `event_time < :decision_time` 关联却忽略 T+1 入仓/结算延迟的隐式泄漏
- [ ] 无使用 `CURRENT_DATE` / `NOW()` 计算的时间差，无直接读取维度表当前覆盖态（如 `users.status`）
- [ ] 群体统计特征（第 6 行）已按 `availability_time <= decision_time` 截断并排除自身

### 被排除的候选特征（记录下来，防止有人再加回去）

| 候选特征 | 排除原因 |
|---|---|
| `user_total_orders` | **时间泄漏**——全期订单数含未来 |
| `customer_lifetime_value` | **时间泄漏**——通常含未来数据 |
| `users.status` | **标签泄漏**——流失后该字段会被更新 |
| `retention_coupon_sent` | **标签泄漏**——运营给疑似流失用户发券，预测时刻不存在 |
| `third_party_profile_score` | **预测时拿不到**——外部数据源已下线 |
| `refund_amount_after_asof` | **时间泄漏**——字段名即含 after |

**这张表是防泄漏的制度保障**：新人加特征时先看这里，避免重犯。

## 特征重要度与三问核对

模型训练后，对 top-10 特征逐个过三问：

| 排名 | 特征 | ① 怎么产生的 | ② 产生时间在 as-of 前？ | ③ 预测时刻一定存在？ | 结论 |
|---|---|---|---|---|---|
| 1 | `days_since_last_login_at_asof` | 登录日志聚合 | ✅ | ✅ | 安全 |
| 2 | `logins_30d_before_asof` | 同上 | ✅ | ✅ | 安全 |
| 3 | `tickets_30d_before_asof` | 工单表 | ✅ | ⚠️ T+1 | 已调口径 |

**第 ③ 问最关键**：离线数据里有，不等于预测时刻有。

## 统计变换与切分顺序

- [ ] 标准化/归一化的统计量**只从训练集拟合**
- [ ] 缺失填充的均值/中位数**只从训练集计算**
- [ ] 目标编码（若用）**只用训练集且做了 K 折内部编码**
- [ ] 分箱边界**只从训练集确定**
- [ ] 过采样/SMOTE（若用）**只在训练集做**

```python
✅ X_train, X_val, X_test = time_split(...)      # 先切
   scaler.fit(X_train)                           # 只拟合训练集
   X_val, X_test = scaler.transform(...)         # 应用
```

## 版本化特征幂等回填校验（Idempotent Versioned Backfill）

重叠时间窗重复回填必须产出**字节级完全一致（byte-identical）**的特征快照：

```text
$ python scripts/verify_feature_backfill_idempotency.py --feature-version v1 --window 2026-06-01..2026-06-15 --overlap-rerun 2026-06-08..2026-06-20
overlap_window=2026-06-08..2026-06-15 rows=48,200 sha256_run1=9f8a... sha256_run2=9f8a... byte_diff=0
exit: 0
```

- [ ] 特征定义已显式版本化（`feature_set@v<n>`），破坏性口径变更必须升版而非原地覆写
- [ ] 重叠时间窗回填双跑 `SHA-256` / 字节级比对零差异（`byte_diff = 0`）

## Fail-Closed 特征数据契约（违规暂停推理并告警，严禁静默降级推理）

| 检查维度 | 契约约束 | 违例处置动作（硬红线：Fail-Closed） |
|---|---|---|
| **Schema 与类型** | 字段集合、精度与主键 `(entity_id, decision_time)` 严格匹配 `feature_set@v<n>` | **立即暂停批量打分/在线推理并触发 P1 告警**（严禁跳过列或填默认 `0` 静默带病推理） |
| **可空性与缺失上界** | 非结构性缺失列 `NULL = 0%`；结构性缺失率偏离基线 `≤ ±15pp` | 同上（阻断发布/推理并告警） |
| **合法值域（Value Range）** | 例：`logins_30d ∈ [0, 30]`、`avg_amount_90d ≥ 0`、`city_churn_rate ∈ [0, 1]` | 同上 |
| **数据量上下界（Volume Bounds）** | 单批次覆盖实体数 `∈ [基线 × 0.85, 基线 × 1.20]`，非空非零截断 | 同上 |
| **新鲜度 SLA（Freshness SLA）** | 实时流延迟 `≤ 60s`；日批 `availability_time` 不晚于每日 `05:00` | 超时未就绪**暂停打分并告警**，严禁拿过期未对齐分区伪造实时预测 |

## 训练/服务一致性与 PSI/KS 分布对齐校验（Train/Serve Parity）

**上线前硬门禁：** 优先离线训练与在线服务共用同一份特征计算代码/特征平台；无法同源时，必须抽样 `N ≥ 200` 条线上真实请求，按相同 `decision_time` 离线重算，同时通过**精确值比对（`mismatches: 0`）**与**逐特征分布一致性检验（PSI / KS test）**：

| 特征 | 离线重算值 | 线上服务值 | 精确一致 | 逐特征 PSI（`< 0.10`） | KS 检验 `p-value`（`> 0.05`） | 不一致根因与修复 |
|---|---|---|---|---|---|---|
| 1 `logins_30d_before_asof` | 12 | 12 | ✅ | `0.012` | `0.84` | — |
| 4 `avg_amount_90d_before_asof` | 235.50 | 235.50 | ✅ | `0.019` | `0.71` | — |
| 5 `tickets_30d_before_asof` | 2 | 2 | ✅ | `0.024` | `0.63` | 历史曾混用 `event_time` 与 `availability_time`，已统一按 `availability_time <= decision_time` 修复 |

```text
$ python scripts/check_feature_consistency.py --samples 200 --max-psi 0.10 --min-ks-pvalue 0.05
200 samples × 6 features = 1200 comparisons
mismatches: 0 | max_psi: 0.024 (< 0.10) | min_ks_pvalue: 0.63 (> 0.05)
exit: 0
```

- [ ] 抽样 `N ≥ 100` 条完成全特征精确比对（`mismatches: 0`）且逐特征 **PSI / KS 分布检验**通过
- [ ] 所有历史偏差已定位修复，校验脚本已交 `qa` 纳入回归

## 特征存储（与 `dba` 对齐）

| 项 | 内容 |
|---|---|
| 存储形态 | <离线特征表 `user_features_daily`> |
| 主键 | <(user_id, decision_time)> |
| 更新频率与新鲜度 SLA | <每日 `04:00` 产出，SLA `≤ 05:00`> |
| 访问模式 | <按 `(user_id, availability_time <= decision_time)` 查最新可用行（推理）；按窗口批量读（训练）> |
| 数据量 | <n 用户 × 保留 90 天 = <n> 行> |

访问模式已交 `dba` 做索引设计：☐

## 自检

- [ ] 每个特征均显式声明 `event_time` 与 `availability_time`，且关联口径严格执行 `(entity, availability_time <= decision_time)`
- [ ] 缺失含义区分了结构性缺失与未知；被排除候选特征及泄漏原因已记录
- [ ] 重叠窗口版本化特征回填测试证明字节级一致（`byte_diff = 0`）
- [ ] Fail-Closed 特征契约（Schema/可空/值域/体量/新鲜度 SLA）已定义，违例时暂停推理并告警（严禁静默 fallback）
- [ ] top-10 特征过了三问；统计变换严格在切分之后仅拟合训练集
- [ ] 训练/服务一致性（精确值 `mismatches: 0` + 逐特征 **PSI / KS 分布检验**）已通过并交 `qa` 纳入回归
- [ ] 特征表访问模式已交 `dba`
