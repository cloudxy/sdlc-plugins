# 常见业务建模模式

七类反复出现的建模题。每类给判据和落地方案,不要每次从零推。

## 1. 层级结构（分类树、组织架构、评论嵌套）

| 方案 | 结构 | 查子树 | 查祖先 | 移动子树 | 适用 |
|---|---|---|---|---|---|
| 邻接表 | `parent_id` | 递归 CTE 或 N 次查询 | 递归 | **改一行** | 层级浅（≤3）或写多读少 |
| 路径枚举 | `path VARCHAR '1/4/9/'` | `LIKE '1/4/%'` **一次查完** | 拆字符串 | 批量改 path | 读多写少,深度不限 |
| 闭包表 | 额外表存所有祖先-后代对 | 一次 JOIN | 一次 JOIN | 改 O(子树×祖先) 行 | 读极频繁,树相对稳定 |

默认选**邻接表**;出现「一次查整棵子树」的高频模式再升级到路径枚举。闭包表只在前两者都撑不住时用——它的写成本很高。

MySQL 8 递归 CTE 查子树：

```sql
WITH RECURSIVE tree AS (
  SELECT id, parent_id, name, 1 AS depth FROM categories WHERE id = ?
  UNION ALL
  SELECT c.id, c.parent_id, c.name, t.depth + 1
    FROM categories c JOIN tree t ON c.parent_id = t.id
   WHERE t.depth < 10          -- 必须有深度上限,防环导致无限递归
)
SELECT * FROM tree;
```

**存环的防护**:邻接表允许 `A→B→A` 这种环,数据库不会阻止。要么应用层写入时检测,要么用路径枚举（路径里出现重复 ID 即环）。

## 2. 审计与历史（谁在什么时候改了什么）

三种需求,别混:

| 需求 | 方案 |
|---|---|
| 「谁改了这条记录」——操作日志 | 独立 `*_audit_log` 表：`entity_type`、`entity_id`、`action`、`actor_id`、`changed_fields JSON`、`at` |
| 「这条记录三个月前是什么样」——版本历史 | 影子表 `*_history`（同结构 + `version`、`valid_from`、`valid_to`），或事件溯源 |
| 「这个值当时是多少」——快照 | **不建表,直接冗余字段**（见第 4 节） |

审计表的纪律：**只追加,不更新不删除**,自己不加软删,不加外键（被审计的行可能已被删）。

```sql
CREATE TABLE order_audit_log (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_id BIGINT UNSIGNED NOT NULL,      -- 不加外键：订单删了日志要留
  action VARCHAR(32) NOT NULL,            -- created / status_changed / refunded
  actor_id BIGINT UNSIGNED NULL,          -- NULL = 系统自动操作
  actor_type VARCHAR(16) NOT NULL,        -- user / system / admin
  changes JSON NULL,                      -- {"status": ["pending", "paid"]}
  at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  INDEX idx_audit_order_at (order_id, at)
);
```

量会很大,一开始就想好归档策略（按月分区或定期归档到冷存储）。

## 3. 金额与货币

- 一律 `DECIMAL(p, s)`,**永不用浮点**
- 多币种必须**币种与金额同行存**：`amount DECIMAL(12,2)` + `currency CHAR(3)`。只存金额不存币种,后面永远说不清
- 需要跨币种汇总 → 同时存**记账币种金额**与**汇率快照**：`amount`、`currency`、`base_amount`、`fx_rate`、`fx_rate_at`
- 精度按币种定：日元无小数,多数币种 2 位,加密货币可能 8 位以上——`DECIMAL(20,8)` 或按币种存精度
- 涉及分账/优惠的,存**明细项**而不是只存总额,否则对不上账

```sql
amount        DECIMAL(12,2)  NOT NULL,   -- 原币金额
currency      CHAR(3)        NOT NULL,   -- ISO 4217
base_amount   DECIMAL(12,2)  NOT NULL,   -- 记账币种金额（快照）
fx_rate       DECIMAL(18,8)  NOT NULL,   -- 换算汇率（快照）
fx_rate_at    DATETIME(3)    NOT NULL,   -- 汇率取值时刻
```

## 4. 快照 vs 引用（最容易错）

**判据一句话：这个值被事后追溯时,应该是「当时的样子」还是「现在的样子」?**

| 场景 | 存法 | 为什么 |
|---|---|---|
| 订单里的商品价格 | **快照** `price_at_purchase` | 涨价后历史订单金额不能变 |
| 订单里的收货地址 | **快照**（整段冗余,不是 `address_id`） | 用户改地址不能改历史订单 |
| 发票里的税率 | **快照** | 税率调整不追溯 |
| 合同里的费率 | **快照** | 签约时锁定 |
| 消息里的发送者昵称 | **快照**（视产品而定） | 改名后历史消息显示哪个?问 `/pm` |
| 订单里的商品名称 | 看产品要求 | 商品改名,历史订单显示旧名还是新名?问 `/pm` |
| 订单关联的用户 | **引用** `user_id` | 要能跳转到用户当前信息 |
| 商品所属分类 | **引用** | 分类改名应全局生效 |

快照不是「反范式的性能优化」,是**业务正确性要求**。所以它不需要「有性能证据才做」——需求要求追溯当时状态,就必须存快照。

同时存快照与引用是常见且正确的做法：`product_id`（引用,用于跳转）+ `product_name_at_purchase`、`price_at_purchase`（快照,用于展示历史）。

## 5. 多租户隔离

三种模式:

| 模式 | 做法 | 适用 |
|---|---|---|
| 共享表 + `tenant_id` | 每表带租户列,所有查询强制带 | 绝大多数 SaaS |
| 独立 schema | 每租户一套表 | 强隔离合规要求 |
| 独立库 | 每租户一个库 | 大客户定制、数据主权 |

共享表模式的纪律：

- `tenant_id` **每张业务表都有**,且 `NOT NULL`
- **所有唯一键都以 `tenant_id` 开头**：邮箱是租户内唯一,不是全局唯一
- **所有索引以 `tenant_id` 最左**
- 应用层用统一的查询过滤器保证不漏（漏一处 = 跨租户数据泄露,这是安全事故不是 bug）
- 交给 `/qa` 的必测项：越权访问其它租户数据

## 6. 状态机

`status VARCHAR` + 应用层枚举校验 + **必须画出流转图**（进 `db-spec.md` 第 2.1 节）。

三件事必须明确:

1. **终态是哪些**（不可再流转）
2. **每个流转的触发者**（用户 / 系统 / 管理员）
3. **非法流转清单** → 交 `/qa` 做负向用例

需要记录「什么时候进入这个状态」时,给关键状态各配一个时间字段（`paid_at`、`shipped_at`）而不是只靠审计日志反查——报表口径要用它们。

状态多且流转复杂（超过 ~8 个状态）时,考虑独立的状态流转表记录每次变更,而不是只在主表存当前状态。

## 7. 幂等与并发

**幂等键**：外部请求（支付回调、消息消费、开放 API）必须有幂等键去重。

```sql
CREATE TABLE payment_callbacks (
  idempotency_key VARCHAR(64) NOT NULL,
  ...
  UNIQUE KEY uk_idem (idempotency_key)     -- 靠唯一约束兜底,不靠先查后插
);
```

**先查后插在并发下必漏**——两个请求同时查到「不存在」,同时插入。唯一约束是唯一可靠的防线,应用层捕获重复键错误当作「已处理」。

**乐观锁**：并发更新同一行且要防覆盖时,加 `version` 列:

```sql
UPDATE orders SET status = 'paid', version = version + 1
 WHERE id = ? AND version = ?;      -- 影响 0 行 = 被别人改过,重试或报错
```

**悲观锁**（`SELECT ... FOR UPDATE`）只在临界区极短且必须串行时用（如扣库存),注意加锁顺序一致以防死锁。

**计数器**不要用「读出来 +1 写回去」,用 `UPDATE t SET n = n + 1 WHERE id = ?`（原子）。高并发热点计数考虑分桶（`counter_bucket` 多行,读时求和)。
