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

### 注意

- Redis 是单点：Redis 不可用时所有 Worker 停止（`SCHEDULER_PERSIST=True` 时队列数据不丢）
- 去重指纹在 Redis：多 Worker 不会重复爬同一请求指纹；指纹集合会持续增长，需要过期或清理策略
- 每个 Worker 有独立内存，共享的只有 Redis 里的队列和指纹

## 常见问题

| 问题 | 原因 | 解决 |
|---|---|---|
| Worker 启动后一直等待 | 起始队列为空（正常——等任务） | 确认生产者投递到了正确的键 |
| 多 Worker 重复爬同一 URL | 去重没有用 Redis | 确认 `DUPEFILTER_CLASS` 是 `scrapy_redis.dupefilter.RFPDupeFilter` |
| 重启后队列丢失 | `SCHEDULER_PERSIST = False` | 需要保留时改为 True |
| 结果没有归属到任务 | 条目缺少任务标识，或翻页请求没有带上 `meta` | 投递 JSON 条目；后续请求显式传递任务标识 |
