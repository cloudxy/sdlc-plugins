# EXPLAIN 全字段判读

面向 MySQL 8.0。`EXPLAIN` 给执行计划（预估），`EXPLAIN ANALYZE` 实跑给真实耗时与行数——仅在获准、负载可控且副作用已评估的环境执行；不要把 ANALYZE 当作只读的静态检查，预估行数偏差大时只有它能暴露。

```sql
EXPLAIN ANALYZE SELECT ... ;   -- 实际执行，返回 actual time / actual rows / loops
```

## 字段逐个过

### `id` 与 `select_type`

`id` 相同 = 同一层级（连表），`id` 递增 = 嵌套子查询。`select_type` 常见值：

| 值 | 含义 | 关注点 |
|---|---|---|
| `SIMPLE` | 无子查询无 UNION | 正常 |
| `PRIMARY` | 最外层查询 | 正常 |
| `SUBQUERY` | 子查询，执行一次 | 可接受 |
| `DEPENDENT SUBQUERY` | 子查询依赖外层，**逐行执行** | 危险，改写成 JOIN |
| `DERIVED` | 派生表（FROM 里的子查询） | 检查是否物化了大结果集 |
| `MATERIALIZED` | 子查询被物化成临时表 | 看临时表大小 |

`DEPENDENT SUBQUERY` 是最常见的隐藏性能杀手：外层 1 万行，子查询就跑 1 万次。

### `type`（访问方式）

优劣序：`system > const > eq_ref > ref > fulltext > ref_or_null > index_merge > range > index > ALL`

| 值 | 含义 | 判读 |
|---|---|---|
| `const` | 主键/唯一键等值，最多 1 行 | 最优 |
| `eq_ref` | 连表时用主键/唯一键，每行匹配 1 行 | 优 |
| `ref` | 非唯一索引等值，匹配多行 | 良，最常见的健康值 |
| `range` | 索引范围扫（`>` `<` `BETWEEN` `IN`） | 良，看 `rows` 是否可控 |
| `index` | **全索引扫描**——扫完整棵索引树 | 差，只比全表扫省了回表 |
| `ALL` | **全表扫描** | 大表上是 blocker |

`ALL` 的合法例外：小表（几百行内，优化器认为扫表比走索引快）、或确实要全量导出。**这两种情况要在证据里写明是有意的**，否则视为缺陷。

### `possible_keys` 与 `key`

- `possible_keys` 有值但 `key` 为 `NULL` → 优化器认为走索引不如全表扫。常见原因：表太小、索引选择性太差、或查询条件让索引失效（见下文「索引失效」）
- `possible_keys` 为 `NULL` → 先判断是否需要索引；小表或全量聚合可能合理扫描
- `key` 命中的不是你预期的那个 → 用 `FORCE INDEX` 对比两者 `EXPLAIN ANALYZE` 的真实耗时再决定，不要盲目加 hint

### `key_len`

命中了复合索引的**前几列**。用它验证索引是否被完整利用：

```
INDEX (tenant_id INT NOT NULL, status VARCHAR(20) NOT NULL, created_at DATETIME NOT NULL)
key_len = 4                 → 只用了 tenant_id
key_len = 4 + 82            → 用到了 status（utf8mb4: 20*4+2）
key_len = 4 + 82 + 5        → 三列全用上
```

可空列多占 1 字节（NULL 标记）。`key_len` 小于预期 = 后续列没用上，检查查询条件是否漏了或类型不匹配。

### `rows` 与 `filtered`

`rows` = 预估要扫的行数，`filtered` = 扫完后满足条件的百分比。真正返回行数 ≈ `rows × filtered / 100`。

判读比值：**`rows` ÷ 实际返回行数**。

- 接近 1 → 索引精准
- 10 倍以内 → 可接受
- 超过 100 倍 → 白扫，索引选择性不足

`filtered = 10.00` 配 `rows = 100000` 意味着扫 10 万行只留 1 万——考虑把过滤字段并进索引。

### `Extra`（信息量最大的一栏）

**正面信号：**

| 值 | 含义 |
|---|---|
| `Using index` | **覆盖索引**：所有列都在索引里，不回表。最优 |
| `Using index condition` | 索引条件下推（ICP）：过滤在存储引擎层完成，减少回表。良 |
| `Using index for group-by` | GROUP BY 直接走索引，免临时表 |

`Using index` 和 `Using index condition` 差一个词，含义差很远：前者完全不回表，后者仍要回表但少回几次。**别看错。**

**危险信号：**

| 值 | 含义 | 处理 |
|---|---|---|
| `Using filesort` | 排序无法用索引完成 | 小结果集可接受；大结果集把排序列并进索引 |
| `Using temporary` | 建了临时表（GROUP BY / DISTINCT / UNION） | 检查是否落磁盘，调整索引让 GROUP BY 走索引 |
| `Using join buffer (Block Nested Loop)` | 连表无索引 | 给连接列建索引 |
| `Using where` 配 `type: ALL` | 全表扫后逐行过滤 | 建索引 |
| `Impossible WHERE` | 条件恒假 | 查逻辑写错了 |
| `Select tables optimized away` | 聚合被优化掉 | 通常是好事（如 `MAX(主键)`） |

`Using filesort` 不必然是问题：20 行的排序在内存里瞬间完成。**结合 `rows` 判断**——`rows=50` 配 filesort 无所谓，`rows=500000` 配 filesort 是事故。

## 索引失效的常见原因

以下写法会让已有索引用不上，`EXPLAIN` 表现为 `key: NULL` 或 `type: ALL`：

| 写法 | 为什么失效 | 改写 |
|---|---|---|
| `WHERE DATE(created_at) = '2026-01-01'` | 列上套函数 | `WHERE created_at >= '2026-01-01' AND created_at < '2026-01-02'` |
| `WHERE user_id = 123`（`user_id` 是 VARCHAR） | 隐式类型转换 = 全表扫 | `WHERE user_id = '123'`，或修正列类型 |
| `WHERE name LIKE '%foo'` | 前导通配符无法用 B+ 树前缀 | 保持后缀匹配语义；评估引擎支持的反转列/专用索引或受控扫描，不能改成前缀匹配 |
| `WHERE a = 1 OR b = 2`（a、b 各自有索引） | 单索引无法同时满足 | 评估 `index_merge` 或保持去重语义的 UNION；单个 `(a,b)` 不自动优化 b 单独条件 |
| `WHERE status != 'done'` | 否定条件选择性差 | 改成 `IN` 列出目标值 |
| 复合索引 `(a, b, c)` 只查 `b`、`c` | 跳过最左列 | 补 `(b, c)` 索引，或调整查询 |
| 排序方向混用 `ORDER BY a ASC, b DESC` | 索引单一方向 | MySQL 8 支持降序索引：`INDEX (a ASC, b DESC)` |

## 真实反例

### 反例一：多租户漏最左前缀

```sql
-- 索引：INDEX (status, created_at)
EXPLAIN SELECT * FROM orders WHERE tenant_id = 42 AND status = 'paid' ORDER BY created_at DESC LIMIT 20;
-- type: ref | key: idx_status_created | key_len: 82 | rows: 480000 | Extra: Using where
```

命中了索引但扫了 48 万行：索引里没有 `tenant_id`，所有租户的 `paid` 订单全被扫出来，再逐行过滤租户。

修复——`tenant_id` 提到最左：

```sql
ALTER TABLE orders ADD INDEX idx_tenant_status_created (tenant_id, status, created_at);
-- type: ref | key_len: 86 | rows: 21 | Extra: NULL
```

`rows` 从 480000 降到 21，`Extra` 的 filesort 也消失了（`created_at` 在索引内已有序）。

### 反例二：隐式类型转换

```sql
-- user_no VARCHAR(32), INDEX (user_no)
EXPLAIN SELECT * FROM users WHERE user_no = 88001;
-- type: ALL | key: NULL | rows: 1200000
```

数字与字符串比较，MySQL 把**列**转成数字（不是把常量转成字符串），索引整棵废掉。加引号即恢复 `type: ref`。这个坑在 ORM 里尤其常见——参数类型没对齐就中招。

### 反例三：深分页

```sql
EXPLAIN SELECT id, title FROM articles ORDER BY id LIMIT 100000, 20;
-- type: index | key: PRIMARY | rows: 100020
```

索引用上了，仍要扫 10 万行再丢掉。索引救不了深分页，可评估游标、延迟关联或预计算；游标值应来自上一页最后一条实际记录：

```sql
SELECT id, title FROM articles WHERE id > :last_seen_id ORDER BY id LIMIT 20;
-- type: range | rows: 20
```

代价是不能跳页。产品要求「跳到第 5000 页」时，把这个约束提回 `/pm` 讨论，不要在 SQL 层硬撑。

## 证据留存格式

```
-- <模式 ID>：<一句话场景>
<完整 SQL>
<EXPLAIN 输出，原样粘贴，不要截断列>
判读：type=? 命中/未命中 ?；rows=? vs 实际返回 ?；Extra=?。结论：通过 / 需优化（原因）
```

只贴「已优化，走索引了」不算证据。

## 自动检查边界

`check-explain.py` 只识别带列名的 MySQL 传统表格；空白或其他格式返回不支持，不能报通过。扫描预算是可配置的诊断阈值，不是普适性能结论；小表扫描可通过结构检查，大批量报表需按业务负载评估并配置预算。最终以环境、数据规模、耗时和资源证据判断。
