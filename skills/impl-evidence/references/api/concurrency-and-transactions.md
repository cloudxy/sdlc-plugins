# 事务、幂等、并发、外部依赖

后端最容易出事的四个地方。它们的共同特征：**单线程测试全绿，上线后偶发出错**。

## 事务边界

### 判定：一个事务 = 一个业务上不可分割的操作

```
✅ 一个事务
   创建订单 + 扣库存 + 记流水
   理由：任一步失败，其余都必须撤销

❌ 不该在一个事务里
   创建订单 + 发通知           → 通知是外部调用
   创建订单 + 调支付网关       → 外部调用，且可能耗时数秒
   批量导入 1 万行            → 锁时间过长
```

### 三条红线

#### ① 事务里做外部调用

```python
❌ async with db.transaction():
       order = await repo.create(...)
       await http_client.post(notify_url, ...)   # 外部调用在事务里
       await repo.mark_notified(order.id)
```

两个具体故障：外部服务慢 500ms，你的行锁就持有 500ms，高并发下锁堆积拖垮数据库；外部调用成功但后续事务回滚，对方收到了通知而你的库里没有这条记录。

```python
✅ async with db.transaction():
       order = await repo.create(...)
   # 事务已提交
   await notify_service.send(order)      # 失败只影响通知，不影响订单
```

#### ② 事务跨越用户交互

「查出来给用户确认，用户点确认后提交」——事务持续数秒到数分钟。用乐观锁代替（见下文）。

#### ③ 一个事务写几万行

锁表、主从延迟、回滚耗时极长。分批，每批一个事务，见 `dba` 的 `expand-contract.md` 回填纪律。

#### ④ 把进程内存锁或全局变量当跨实例互斥

多 worker 或多副本部署下，`threading.RLock`、`asyncio.Lock` 和模块级 `dict` 只在当前单个进程内生效，无法阻止并发副本双写或丢状态。跨请求排他与共享状态必须落到数据库唯一约束/行锁或受治理的 Redis 协议。

### 事务提交后的操作失败怎么办

**这个问题必须显式回答，不能忽略。** 两种情况：

| 情况 | 处理 |
|---|---|
| 可接受丢失（通知、埋点） | 记日志 + 告警，不重试或有限重试 |
| **不可接受丢失**（下游必须收到的事件） | **本地消息表** |

本地消息表：事件与业务数据在**同一个事务**里写入，后台任务扫表投递。

```python
async with db.transaction():
    order = await repo.create_order(...)
    await repo.insert_outbox(                  # 同一事务
        topic="order.created", payload={...}, status="pending"
    )
# 后台 worker：扫 pending → 投递 → 标 sent；失败重试；超次数进死信
```

代价是需要扫表任务和死信处理，收益是**事件不丢**（业务数据存在则事件必然存在）。

## 幂等

### 为什么「先查后插」必错

```python
❌ if not await repo.exists(key):
       await repo.insert(key, ...)
```

两个并发请求：都执行 `exists` 得到 False，都执行 `insert`。结果是两条记录，或唯一约束报错（如果有约束的话——但如果你依赖 `exists` 判断，通常就没加约束）。

**这不是「概率很小」，在高并发下是必然发生。**

### 正确做法：唯一约束 + 捕获重复

```python
✅ try:
       task = await repo.create(idempotency_key=key, ...)
       return to_result(task)
   except UniqueViolation:
       existing = await repo.find_by_key(key)   # 另一个请求已插入
       return to_result(existing)               # 返回首次结果
```

数据库的唯一约束是**唯一可靠的串行化点**。应用层的任何判断在并发下都会漏。

### 幂等键的三种来源

| 来源 | 场景 | 注意 |
|---|---|---|
| 客户端传 `Idempotency-Key` | 用户主动操作（创建订单、发起导出） | 契约要定有效期；过期后可复用 |
| 业务自然键 | 有天然唯一标识（订单号、批次号） | 最省事，优先用 |
| 外部系统事务 ID | 支付回调、消息消费 | **必须用**——外部重投是常态 |

### 消息消费的幂等

消息中间件基本都是「至少一次」投递，**重复消费是常态不是异常**：

```python
async def handle(msg):
    async with db.transaction():
        try:
            await repo.insert_processed(msg.id)   # 唯一约束去重
        except UniqueViolation:
            logger.info("msg.duplicate", msg_id=msg.id)
            return                                # 已处理，直接 ack
        await do_business(msg)                    # 与去重记录同事务
```

去重记录与业务处理**必须同事务**——否则去重记录写了但业务失败，重投时会被当成已处理而跳过。

## 并发写

### 丢更新

```python
❌ order = await repo.get(id)        # 两个请求都读到 status='pending'
   order.status = 'paid'
   await repo.save(order)            # 后写的覆盖先写的
```

### 三种正确做法

#### 乐观锁（通用）

```sql
UPDATE orders SET status='paid', version=version+1
 WHERE id=? AND version=?
```

```python
rows = await repo.update_with_version(id, version, status='paid')
if rows == 0:
    raise ConcurrentModificationError()   # 被人改过：重试或报错给用户
```

**`rows == 0` 必须处理。** 忽略返回值 = 把并发冲突当成功，这是最隐蔽的数据错误。

#### 条件更新（状态机场景更自然）

```sql
UPDATE orders SET status='paid', paid_at=NOW(3)
 WHERE id=? AND status='pending'
```

影响 0 行说明状态已不是 `pending`——可能已支付（重复回调，幂等返回成功）或已取消（业务上要拒绝）。**先查当前状态再决定怎么响应**，不要笼统报错。

这种写法比乐观锁更适合状态机：它同时完成了「并发保护」和「状态合法性校验」。

#### 原子操作（非账务计数器与配额）

```sql
UPDATE tickets SET view_count = view_count + 1 WHERE id=?     ✅
UPDATE quotas SET remaining_seats = remaining_seats - ? WHERE id=? AND remaining_seats >= ?   ✅ 非资金配额的条件扣减
```

不要读出来加一再写回；配额扣减**必须带 `>=` 条件**，否则并发下会扣成负数。
**账务红线**：涉及真实资金、钱包、清结算或积分账本时，**严禁**仅用可变单列 `UPDATE users SET balance = balance - ?` 充当账务权威！必须采用**只追加复式记账流水（`Σ debits == Σ credits`）+ 同事务余额投影 + T+1 三方对账**，冲正走反向分录（见 [industry-data-sops.md](../../../schema/references/industry-data-sops.md) §2）。

### 悲观锁：谨慎使用

```sql
SELECT * FROM inventory WHERE sku=? FOR UPDATE
```

只在临界区极短且必须串行时用（扣库存）。两条纪律：

- **加锁顺序必须一致**（都按 SKU 升序锁），否则死锁
- 临界区内不做外部调用（否则锁持有时间不可控）

### 热点行

同一行被极高频更新时（秒杀库存、全局计数器），行锁成为瓶颈。**分桶**：

```
counter_buckets(id, bucket_no, count)     # 拆成 N 行
写：随机选一个 bucket 更新
读：SUM(count)
```

代价是读需要聚合，收益是写并发提升 N 倍。

## 外部依赖韧性

调外部服务必须四件套齐全，缺一个都会在故障时放大影响。

### ① 超时

```python
❌ await http_client.post(url, json=data)                    # 无超时
✅ await http_client.post(url, json=data, timeout=3.0)      # 连接+读取超时
```

**无超时是最危险的默认值**：对方卡住不返回，你的连接池/线程池逐渐耗尽，最后整个服务不可用——**故障从对方传染到你**。

超时值要分开设：连接超时短（1–2 秒，连不上就是连不上），读取超时按对方 P99 设（通常 3–10 秒）。

### ② 重试

**只重试瞬时故障**：

| 情况 | 重试 | 理由 |
|---|---|---|
| 连接超时、连接重置 | ✅ | 瞬时网络问题 |
| 503 / 429 | ✅ | 对方过载，退避后可能恢复（429 按 `Retry-After`） |
| 500 | ⚠️ 谨慎 | 可能是确定性错误，重试无用 |
| 4xx 业务错误 | ❌ | 参数错了不会因重试变对 |
| 读超时 / 发包后断连（写操作） | ⚠️ **`In-Doubt` 三态** | **未知对方是否已执行**——先查上游回执/对账，或确认对方支持幂等后**沿用原幂等键**重放，严禁换新键盲目重试 |

```python
✅ 指数退避 + 抖动 + 上限
   for attempt in range(3):
       try: return await call()
       except TransientError:
           if attempt == 2: raise
           await sleep(2 ** attempt + random.uniform(0, 0.5))
```

**抖动不是可选的**：所有客户端同时退避同样时长 → 同时重试 → 二次冲击。

**三态副作用纪律（`Success / Fail / In-Doubt`）**：外部写操作前先落盘本地意图与幂等键；遇到读超时或连接中断一律归为 `In-Doubt`，绝不当作 `Fail` 直接发起无幂等键的二次扣款/发货，必须走回执查询或对账恢复。

### ③ 有界并发与优雅降级（Graceful Brownout）

```
核心依赖挂了   → 快速失败，带 trace_id 明确告知（绝不无界阻塞耗尽连接池）
非核心依赖挂了 → Brownout 降级继续（返回缓存旧值 / 确定性默认值 / 隐藏次要模块）
```

哪些是非核心必须在设计时定（`architect` 的 `contract.md` 里应有），并为外部扇出调用配置并发信号量（Semaphore/Bulkhead）上限，不要在故障现场临时判断。

### ④ 熔断

同一依赖连续失败达阈值时**直接快速失败一段时间**，不再发请求：

- 保护自己（不再浪费线程等超时）
- 保护对方（不再加剧它的过载）

有成熟库就用库，自己实现要注意半开状态（冷却后放少量请求试探）。

## 自测清单

这四类问题的测试很容易漏。最低要求：

- [ ] **事务回滚**：中途抛异常，验证前面的写入已回滚
- [ ] **幂等**：同一请求发两次，验证结果一致且只产生一条记录
- [ ] **并发写**：并发两个更新同一行，验证一个成功一个得到冲突
- [ ] **`rows == 0` 分支**：构造版本冲突，验证有正确处理
- [ ] **外部依赖超时**：mock 一个永不返回的依赖，验证有超时且降级正确
- [ ] **外部依赖失败**：mock 抛错，验证降级行为符合契约
- [ ] **重复消费**：同一消息投两次，验证只处理一次

并发测试写法（Python 示例）：

```python
async def test_concurrent_update_conflict():
    order = await create_order(status="pending")
    results = await asyncio.gather(
        svc.mark_paid(order.id), svc.mark_paid(order.id),
        return_exceptions=True,
    )
    successes = [r for r in results if not isinstance(r, Exception)]
    assert len(successes) == 1        # 恰好一个成功
```
