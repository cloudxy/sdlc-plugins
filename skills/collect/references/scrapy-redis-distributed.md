# Scrapy-Redis 分布式采集架构

适用条件：项目已采用（或经架构决定采用）scrapy-redis 做分布式队列采集。其他栈把同样的义务（共享队列、去重、持久调度、采集与存储的交接）映射到项目已接受的边界，不要为了套用本文而引入 scrapy-redis。项目自己的基类、配置入口、队列名和目录约定以项目文档为准，本文只给通用做法。

## 核心架构

```
任务生产者 → Redis 起始队列（默认键 <spider>:start_urls，或项目配置的 REDIS_START_URLS_KEY）
                  ↓ 条目：URL 或 JSON（如 {"url": "...", "task_id": "..."}）
            Scrapy-Redis Scheduler（从 Redis 取请求）
                  ↓
            多个 Worker 并行爬取
                  ↓
            Item Pipeline（清洗 → 校验 → 质量评分 → 交接）
                  ↓
            交接目标由项目架构决定（队列 / API / 直写存储）
```

### Spider 是常驻 Worker，不是一次性运行

普通 Scrapy Spider 跑完就退出。scrapy-redis 的 `RedisSpider` 是**常驻 Worker**：

- 启动后监听 Redis 起始队列
- 有新条目就爬，队列空了就等（是否空闲自动退出由所用版本的相应设置决定，名称以版本文档为准）
- 多个 Worker 可同时运行，共享同一个 Redis 队列（天然负载均衡）

## 分布式配置（修改前先读项目现有 settings）

```python
SCHEDULER = "scrapy_redis.scheduler.Scheduler"               # 从 Redis 取请求，不用本地内存队列
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"   # 去重指纹存在 Redis，多 Worker 共享
SCHEDULER_PERSIST = True                                     # 重启不清空已排队请求
SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.PriorityQueue"   # 任务有优先级时；否则 FifoQueue
REDIS_URL = ...  # 从项目的配置层读取；不要在代码里写连接串
```

- **优先级队列**：任务确实分优先级（如 high / normal / low）时才用；没有优先级需求时 FIFO 更容易推理。类名随 scrapy-redis 版本变化，按已安装版本核对。
- **`SCHEDULER_PERSIST = True`**：Worker 重启后不丢已排队请求。设为 False 等于重启清空队列，只适合一次性任务。代价是停用的爬虫会留下残余队列，需要有清理办法。

## Spider 基类

项目已有任务感知基类（负责解析队列条目、注入任务 ID、应用站点级限速）时，新 Spider 继承它，不要直接继承 `RedisSpider` 绕开这些职责。项目没有时，至少自己完成三件事：

1. **解析队列条目**：JSON 条目取出 URL 和任务标识，放进请求 `meta`
2. **站点级限速**：按目标站点的访问约定覆盖全局 `DOWNLOAD_DELAY` / 并发（来自项目的站点配置或本 Spider 的 `custom_settings`）
3. **结果归属**：每个 item 带上任务标识，下游才能把结果归到正确的任务

```python
import json

from scrapy import Request
from scrapy_redis.spiders import RedisSpider


class MyNewSpider(RedisSpider):  # 项目有任务感知基类时换成它
    name = "my_new_spider"

    def make_request_from_data(self, data):
        entry = json.loads(data)
        return Request(entry["url"], meta={"task_id": entry.get("task_id")})

    def parse(self, response):
        task_id = response.meta.get("task_id")
        for item in response.css(".product"):
            yield {
                "url": response.url,
                "title": item.css("h2::text").get(),
                "price": item.css(".price::text").get(),
                "task_id": task_id,
            }
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, self.parse, meta={"task_id": task_id})
```

`make_request_from_data` 的签名和默认 JSON 支持随 scrapy-redis 版本变化；按已安装版本核对后再覆盖。

## 业务任务队列：分级、领取与所有权交接

Scrapy-Redis 调度队列管的是「请求」；需要按业务控制「先采谁、采多少」时，在调度队列之外再加一层**业务任务队列**（Redis ZSET，条目为 JSON，score 编码优先级），Worker 轮询自行消费。要点：

- **分级队列**：按业务语义分键——`urgent`（插队）/ `p`（重点）/ `np`（非重点）/ `dupe`（补采）。队列扫描顺序即优先级；把顺序存成 Redis 里的一个列表，可以不发版在运行时调整采集侧重。
- **原子弹出**：ZSET 的 `ZPOPMIN` 避免先读再删的竞争；它不覆盖弹出到保存 pending 的窗口，也不保证一个业务任务在不同 member/队列中只有一份。
- **所有权交接**：失败或准入不满足时，可保留 pending 等待，也可移交回原队列；回队保留优先级与稳定任务身份，并完成旧执行权的释放/失效校验，避免 pending 与队列各自可执行。不能将“一律回队”替代状态设计。
- **崩溃恢复**：选择适用的原子接管、租约回收或对账机制，明确中断后的接管者。唯一 pending 不应仅靠 TTL 消失；租约到期必须有回收和旧执行者提交校验。参见 [业务断点与恢复](collection-recovery.md)。
- **统一 key 工厂**：所有业务队列 / pending / 游标 key 由单一模块统一生成。key 散落在各中间件里硬编码，等于埋点侧的命名漂移——三个月后没人说得清 `x:store:p` 和 `x:store:np` 各是什么。

## 交接可靠性：未同步集合作同步游标

采集写入暂存与消费侧同步落库是两段传输，至少一次语义下要显式分界：

- 数据及 `unsynced` 要有可恢复的关联写入；先写数据再 `SADD` 仍有中断窗口。按实际引擎/权限采用事务、可恢复计划或可靠对账，不能仅凭两条命令宣称可靠交接。
- 同步程序按游标取数据，确认目标端接管后再推进游标。删除半成品时维护对应游标，并防止删除期间有并发更新；中断后能对账，避免悬空游标或遗漏新版本。
- `unsynced` 集合的基数就是「采集完成但未落库」的积压指标，接入告警；完成日志同时记录实体数、翻页数等证据，供对账。

这和埋点侧「emitted ≠ accepted ≠ persisted ≠ queryable」是同一条纪律：宣称「采集完成」之前，先指明数据到了哪一段。

## Pipeline 与交接

```
Spider yield item
  ↓ 清洗     去空白、统一编码
  ↓ 校验     必填字段、类型
  ↓ 质量评分 完整率、非空率、重复
  ↓ 交接     按项目架构：序列化进队列 / 调用 API / 写存储
```

爬虫能否直写主库由项目架构决定。项目把采集与存储分开时（常见理由：避免爬虫与在线服务争用连接池、把脏数据挡在主库外），Pipeline 最后一步只做序列化交接，由消费者落库；此时不要在 Spider 或 Pipeline 里打开主库会话。

## 多 Worker 部署

```bash
# 机器 A、机器 B 连接同一个 Redis，各自启动同一个 Spider
scrapy crawl my_new_spider
# 生产者向起始队列投递条目后，两个 Worker 从同一队列竞争取请求
```

项目有自己的启动脚本或进程管理时用项目的入口。

### 多机错峰

按来源访问约定、共享账号/IP 的总预算与实际负载配置 Worker 时间窗、间隔、配额及必要抖动；逐机覆盖可以错峰，但不能用机器数扩大共享预算。观测结果决定调整，不把“一机一号、不同作息”作为通用架构条件或无法被识别的保证。

### 注意

- Redis 的故障影响取决于实际拓扑与依赖；暂停依赖它的领取/提交。`SCHEDULER_PERSIST=True` 只控制调度器清理策略，服务器故障耐久性仍取决于持久化、复制及恢复配置。
- 去重指纹在 Redis：多 Worker 不会重复爬同一请求指纹；指纹集合会持续增长，需要过期或清理策略
- 每个 Worker 有独立内存，共享的只有 Redis 里的队列和指纹

## 常见问题

| 问题 | 原因 | 解决 |
|---|---|---|
| Worker 启动后一直等待 | 起始队列为空（正常——等任务） | 确认生产者投递到了正确的键 |
| 多 Worker 重复爬同一 URL | 去重没有用 Redis | 确认 `DUPEFILTER_CLASS` 是 `scrapy_redis.dupefilter.RFPDupeFilter` |
| 重启后队列丢失 | `SCHEDULER_PERSIST = False` | 需要保留时改为 True |
| 结果没有归属到任务 | 条目缺少任务标识，或翻页请求没有带上 `meta` | 投递 JSON 条目；后续请求显式传递任务标识 |
| Worker 崩溃后任务「消失」 | 领取到 pending 有窗口，或唯一 pending 到期失去恢复材料 | 验证原子接管/租约回收/对账；重启及到期都有恢复路径 |
| 多 Worker 消费到同一任务 | 消费用了先读后删的两步命令 | `ZPOPMIN` 原子弹出 |
| 同步程序漏数据或对已删 key 报错 | 写入与同步游标脱节 | 恢复关联写入并对账，确认接管后推进游标 |
| 下载中间件里 `time.sleep` 后全部请求停摆 | 同步 sleep 阻塞 reactor | 用 `DOWNLOAD_DELAY` / `AUTOTHROTTLE` 或项目已接受的异步延迟手段 |
