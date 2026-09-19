# expand-contract：破坏性变更三步法

## 为什么不能一步到位

迁移与代码不是同时生效的。滚动/灰度发布和可能回滚的场景存在一个窗口，**新旧两版代码同时在跑**（滚动发布、多副本、灰度、回滚）。一步到位的变更让这个窗口成为故障窗口：

```
DDL 先跑 → 旧代码还在读被删的列 → 报错
代码先发 → 新代码读还不存在的列 → 报错
```

expand-contract 的核心：**任何时刻，schema 都同时兼容前一版和后一版代码。**

```
expand（扩展）  新旧结构并存，只加不减 —— 回退条件需逐项证明
migrate（迁移） 回填数据 + 双写，切读 —— 回退条件需逐项证明
contract（收缩） 删掉旧结构 —— 确认无人使用后才做
```

按兼容阶段分开部署和验证；文件数取决于迁移工具。离线维护窗口可采用已批准的原子切换，但必须证明所有消费者停用、数据与恢复条件满足；不能把文件数当兼容性证据。

## 判定：什么变更算破坏性

| 变更 | 破坏性 | 原因 |
|---|---|---|
| 加表 / 加可空列 / 加索引 | 否 | 旧代码无视新结构 |
| 删列 / 删表 | **是** | 旧代码仍在读 |
| 重命名列 / 表 | **是** | 等于「删 + 加」 |
| 改类型（扩大：`INT`→`BIGINT`、`VARCHAR(20)`→`VARCHAR(50)`） | 边界 | 通常安全，但需确认应用层校验与序列化 |
| 改类型（缩小或换族：`VARCHAR`→`INT`、`DATETIME`→`DATE`） | **是** | 数据可能截断或失败 |
| 加 `NOT NULL` | **是** | 老数据有 NULL，或旧代码不传该列 |
| 加 `UNIQUE` | **是** | 老数据可能已重复 |
| 加外键 | **是** | 老数据可能有孤儿行 |
| 改默认值 | 边界 | 新写入行为可能改变，核对业务与旧消费者 |
| 删索引 | 边界 | 结构安全，但可能让线上查询雪崩——先确认无查询依赖 |

## 三个标准场景

### 场景一：重命名列（`user_name` → `username`）

**Step 1 · expand**

```sql
-- migration_001_expand.up
ALTER TABLE users ADD COLUMN username VARCHAR(64) NULL;
CREATE INDEX idx_users_username ON users (username);

-- migration_001_expand.down
DROP INDEX idx_users_username ON users;
ALTER TABLE users DROP COLUMN username;
```

代码侧同步发布**双写**：写路径同时写 `user_name` 与 `username`，读路径仍读 `user_name`。

**Step 2 · migrate**

```sql
-- migration_002_backfill.up
-- 分批回填，避免长事务锁表
UPDATE users SET username = user_name
 WHERE username IS NULL AND id BETWEEN ? AND ?;   -- 应用层循环，每批 1000-5000 行

-- 校验：回填完整性（必须为 0）
SELECT COUNT(*) FROM users WHERE username IS NULL AND user_name IS NOT NULL;

-- migration_002_backfill.down
-- 不盲目清空 username：可能已含新写入。保留数据，切回兼容读路径；是否删除需单独证明。
```

回填校验通过后，发布**切读**：读路径改读 `username`，写路径继续双写。此时若发现问题，回滚代码即可——两列数据都是完整的。

**Step 3 · contract**

观察期（建议至少一个完整发布周期，确认无代码引用 `user_name`）后：

```sql
-- migration_003_contract.up
ALTER TABLE users DROP COLUMN user_name;

-- migration_003_contract.down
ALTER TABLE users ADD COLUMN user_name VARCHAR(64) NULL;
UPDATE users SET user_name = username;   -- 从新列恢复
```

仅当新列保留旧语义且覆盖期间所有写入，这种恢复才成立。不可重建时明确不可逆点、备份恢复实测、增量写入处置/RPO 或前滚修复；备份文件存在本身不等于可恢复。

### 场景二：加非空列

不能直接 `ADD COLUMN ... NOT NULL`（无默认值时老数据违约；有默认值时大表可能长时间锁表）。

```sql
-- Step 1 expand：先加可空
ALTER TABLE orders ADD COLUMN channel VARCHAR(20) NULL;

-- Step 2 migrate：回填 + 代码保证新写入必填
UPDATE orders SET channel = 'legacy' WHERE channel IS NULL AND id BETWEEN ? AND ?;
SELECT COUNT(*) FROM orders WHERE channel IS NULL;   -- 必须为 0

-- Step 3 contract：加约束
ALTER TABLE orders MODIFY COLUMN channel VARCHAR(20) NOT NULL;
-- down: ALTER TABLE orders MODIFY COLUMN channel VARCHAR(20) NULL;
```

`NOT NULL` 约束必须等代码侧「新写入一定带 channel」上线之后再加，否则约束加上的瞬间旧代码写入全失败。

### 场景三：加唯一键

老数据大概率已有重复，先查清楚：

```sql
-- Step 0：先看有没有重复（不改结构）
SELECT tenant_id, email, COUNT(*) c FROM users
 GROUP BY tenant_id, email HAVING c > 1;
```

有重复 → **这是业务决策，不是 DBA 能拍的**：保留哪条？合并还是软删？带着数据回 `/pm` 定规则，处理完再继续。

```sql
-- Step 1 expand：先建普通索引（不带唯一约束），验证查询性能
CREATE INDEX idx_users_tenant_email ON users (tenant_id, email);

-- Step 2 migrate：使用能串行化竞争的写入协议/约束或受控维护窗口阻止新重复；无锁的先查后插不成立

-- Step 3 contract：改成唯一索引
DROP INDEX idx_users_tenant_email ON users;
CREATE UNIQUE INDEX uk_users_tenant_email ON users (tenant_id, email);
-- down: 反向，改回普通索引
```

## 回填的操作纪律

- **分批**：每批 1000–5000 行，批间 sleep（几十到几百毫秒），避免主从延迟与长事务
- **可续跑**：用主键区间或状态标记推进，中断后能从断点继续，不要依赖「跑一次成功」
- **幂等**：加 `WHERE 目标列 IS NULL` 之类的守卫，重跑不会覆盖已正确的数据
- **有校验**：结束必须有一条返回 0 的 count 查询作为完成证据
- **不在迁移里跑大回填**：迁移工具通常有超时和单事务限制。大表回填写成独立可重跑脚本，迁移文件里只做 DDL

## 每步的交付证据

```
Step 1 expand
  cmd: alembic upgrade +1        exit: 0
  cmd: alembic downgrade -1      exit: 0     # 验证可逆
  cmd: alembic upgrade +1        exit: 0
  验证: SHOW CREATE TABLE users  → 新列存在且可空

Step 2 migrate
  cmd: python scripts/backfill_username.py --batch 2000   exit: 0
  校验: SELECT COUNT(*) FROM users WHERE username IS NULL AND user_name IS NOT NULL;  → 0
  代码: 双写已发布（commit / PR 链接）

Step 3 contract
  前置: 确认无代码引用 user_name（grep 结果贴出）
  cmd: alembic upgrade +1        exit: 0
  cmd: alembic downgrade -1      exit: 0
  cmd: alembic upgrade +1        exit: 0
```

## 常见错误

| 错误 | 后果 |
|---|---|
| 三步写进一个迁移文件 | 等于一步到位，没有安全窗口 |
| expand 之后立刻 contract（同次发布） | 旧副本仍在跑，报错 |
| 回填不分批，一条 UPDATE 打全表 | 锁表 + 主从延迟 |
| 回填脚本没有幂等守卫 | 中断重跑覆盖正确数据 |
| contract 的 `down` 只恢复结构不恢复数据 | 回滚后列在但数据空 |
| 加唯一键前没查重复 | 迁移失败，或更糟：静默丢数据 |
| 观察期太短就 contract | 灰度中的旧副本崩 |

## 验证边界

以上 SQL 是 MySQL 风格的教学例，按实际引擎和锁行为改写。在隔离环境验证兼容读写、并发回填、数据量/校验和/业务不变量与恢复。up/down/up 只在 down 安全且有意义时执行，不能拿退出码代替业务数据核对。生产操作另需已有发布/数据权限。
