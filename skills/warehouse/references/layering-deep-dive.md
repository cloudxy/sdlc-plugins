# 数据仓库分层——完整设计规则

## ODS（Operational Data Store）— 贴源镜像

ODS 层的唯一职责：把在线库的数据原样同步过来，只做类型规整。

### 设计规则
- 命名：`ods_<源表名>`（如 `ods_spider_tasks`）
- 同步方式：全量（小表 < 10 万行）或增量（按 updated_at / 自增 ID）
- 字段：与源表一一对应，仅类型映射（MySQL DATETIME → 数仓标准格式）
- 主键：保留源表主键

### 禁止事项
- JOIN 其他 ODS 表
- 聚合计算
- 数据清洗（脏值处理是 DWD 的职责）
- 添加业务逻辑字段

### 反例
```
❌ ods_orders 加了 status 过滤（WHERE status != 'test'）
   → ODS 是镜像，过滤是 DWD 的事
❌ ods_orders 和 ods_users 做了 JOIN
   → JOIN 是 DWD 的事
```

---

## DWD (Data Warehouse Detail) — 明细事实层

DWD 层做三件事：去重、脏值处理、时区统一。**粒度 = 业务过程的最低原子粒度。**

### 设计规则
- 命名：`dwd_<业务域>_<业务过程>`（如 `dwd_spider_task_exec`）
- 粒度声明：「一行 = 一次爬取完成」或「一行 = 一次状态变更」
- 去重：按业务唯一键去重（如 task_id + created_at）
- 脏值：空值打标（`is_dirty` 字段）或剔除（记日志）
- 时区：统一 UTC 或统一北京时间——写进 db-spec
- PII：手机号中间四位掩码、邮箱打码——在 DWD 完成
- 退化维度：常用维度字段冗余进事实表（用户名、爬虫名），减少 JOIN

### 禁止事项
- 跨主题拼宽表（订单和用户行为是不同主题）
- 聚合计算（那是 DWS 的职责）
- 反向引用 ADS 层

---

## DWS (Data Warehouse Summary) — 轻度汇总层

DWS 层按 **主题 × 粒度 × 周期** 三维组织。

### 设计规则
- 命名：`dws_<主题>_<粒度>`（如 `dws_spider_daily_stats`）
- 后缀：`_di`（每日增量）/ `_df`（每日全量）/ `_hi`（历史增量）
- 粒度声明：「一行 = 某租户某天的汇总统计」

### 禁止事项
- 直接服务 UI 分页查询（那是 ADS 的职责）
- 包含明细级数据（应查 DWD）
- 被其他 DWS 表引用（汇总层之间不应有依赖）

---

## ADS (Application Data Store) — 应用数据层

ADS 层是看板和 API 的直接数据源。

### 设计规则
- 命名：`ads_<应用场景>`（如 `ads_spider_dashboard`）
- 面向消费优化：列名可读、预计算完成、直接可查
- 从 DWS 取数，做最终格式化

### 禁止事项
- 被其他层引用（ADS 是"终点"——如果 ADS 被 DWD 引用了，分层设计有问题）

---

## 维度表与事实表

维度表（`dim_`）：描述"什么"（用户、商品、团队、爬虫）。
- 变化缓慢，通常全量刷新
- 主键 = 维度代理键（`dim_user_id`）

事实表（`fct_`）：描述"发生了什么"（下单、退款、爬取完成）。
- 追加为主，增量刷新
- 外键关联维度表

星型模型是默认选择：一个事实表 + 多个维度表。雪花模型（维度表再关联维度表）只在维度层级很深时使用。

---

## ETL 幂等规则

### 分区覆盖写入
```sql
-- 正确：覆盖写入（同分区重跑结果一致）
INSERT OVERWRITE TABLE dwd_spider_task_exec PARTITION (dt = '2026-09-06')
SELECT ... FROM ods_spider_tasks WHERE dt = '2026-09-06';

-- 错误：追加写入（重跑会翻倍）
INSERT INTO dwd_spider_task_exec PARTITION (dt = '2026-09-06')
SELECT ...;
```

### 幂等键
每条记录必须有唯一标识（业务键 + 时间分区）。重跑时，同键的数据被覆盖而非重复插入。

### 双跑验证
同分区双跑，diff 为空才叫幂等：
```bash
# 第一次跑
etl_job --partition 2026-09-06
# 保存快照
SELECT * FROM dwd_table WHERE dt = '2026-09-06' ORDER BY id > /tmp/run1.sql
# 第二次跑
etl_job --partition 2026-09-06
# 对比
SELECT * FROM dwd_table WHERE dt = '2026-09-06' ORDER BY id > /tmp/run2.sql
diff /tmp/run1.sql /tmp/run2.sql  # 必须为空
```

---

## 租户隔离

同实例部署时，数仓表与在线表共享同一个 MySQL。租户隔离机制（`tenant_context.py` 的 `do_orm_execute` 行级过滤 + `TENANT_EXEMPT_TABLES` 豁免白名单）会作用于全库查询。

**数仓表的三种处理方式**：
1. 数仓表不含 `tenant_id`（聚合层 DWS/ADS 不按租户分）→ 注册进 `TENANT_EXEMPT_TABLES`
2. 数仓表含 `tenant_id`（DWD 明细层按租户分）→ 不需要豁免，行级过滤自动生效
3. ETL 写入时使用 `platform_scope()` → 跳过租户写入断言（ETL 是系统行为，不是租户行为）

**最容易踩的坑**：ETL 管线用普通会话写入数仓表，触发了 `before_flush` 的租户写入断言（"tenant_id 与上下文租户不符"），导致 ETL 全部失败。修复方式：ETL 连接使用 `platform_scope()`。
