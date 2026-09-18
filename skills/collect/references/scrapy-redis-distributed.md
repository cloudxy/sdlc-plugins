# Scrapy-Redis 分布式采集架构

本项目使用 scrapy-redis 实现分布式队列采集。这份文档是采集工程师的架构手册。

## 核心架构

```
Backend 任务消费者 → Redis 队列（spider:<name>:start_urls）
                          ↓ JSON 条目 {"url": "...", "task_id": 123, ...}
                    Scrapy-Redis Scheduler（从队列取请求）
                          ↓
                    多个 Worker 节点并行爬取
                          ↓
                    Item Pipeline（quality → store → Redis item_queue）
                          ↓
                    Backend 消费者（从 spider:item_queue 取结果 → 落库 MySQL）
```

### 关键：Spider 是常驻 Worker，不是一次性运行

普通 Scrapy Spider 跑完就退出。Scrapy-Redis 的 `RedisSpider` 是**常驻 Worker**：
- 启动后监听 Redis 队列 `spider:<name>:start_urls`
- 有新 URL 就爬，队列空了就等（`IDLE_CLOSE_SECONDS` 控制是否自动退出）
- 多个 Worker 可同时运行，共享同一个 Redis 队列（天然负载均衡）

## settings.py 分布式配置（已实现，修改前先读）

```python
# 分布式调度器（从 Redis 取请求，不是本地内存队列）
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"  # Redis 去重
SCHEDULER_PERSIST = True                                     # 重启不丢队列
SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderPriorityQueue"  # 优先级队列
REDIS_URL = project_settings.REDIS.DEFAULT.URL
```

### 为什么用 SpiderPriorityQueue（而非默认 FIFO）
任务有优先级（high/normal/low）。优先级队列确保高优先级任务先被消费。

### 为什么 SCHEDULER_PERSIST = True
Worker 重启后不丢已排队的请求。如果设为 False，重启 = 队列清空 = 任务丢失。

## 基类：TaskAwareRedisSpider

所有新 Spider **必须继承** `TaskAwareRedisSpider`（`spiders/base.py`），不要直接继承 RedisSpider。

基类提供：
1. **JSON 队列条目解析**：`{"url": "...", "task_id": 123}` → 注入 task_id 到请求 meta
2. **站点级反爬配置**：从 sites.yml 读取 anti_crawl.download_delay 覆盖全局延迟
3. **任务归属**：TaskAttributionSpiderMiddleware 把结果归属到正确的任务

### 新 Spider 最小代码

```python
from spiders.base import TaskAwareRedisSpider
from scrapy import Request

class MyNewSpider(TaskAwareRedisSpider):
    name = "my_new_spider"

    def parse(self, response):
        # response.meta['task_id'] 由基类自动注入
        task_id = response.meta.get('task_id')

        # 解析数据
        for item in response.css('.product'):
            yield {
                'url': response.url,
                'title': item.css('h2::text').get(),
                'price': item.css('.price::text').get(),
                'task_id': task_id,  # 基类已注入
            }

        # 翻页
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield Request(next_page, callback=self.parse)
```

## Pipeline 链（数据从爬虫到数据库的路径）

```
Spider yield item
  ↓ CleanPipeline (200)       清洗：去空白、编码统一
  ↓ ValidatePipeline (300)    校验：必填字段、类型
  ↓ QualityCheckPipeline (350) 质量评分：完整率 + 非空率 + 去重分
  ↓ StorePipeline (400)       存储：序列化 → Redis spider:item_queue
  ↓
Backend 消费者 → 落库 MySQL
```

**禁止**：Spider 直接写 MySQL。数据必须通过 Redis 队列流转（B2 边界）。

## 多 Worker 部署

```bash
# 机器 A
cd scrapy && scrapy runspider spiders/generic.py

# 机器 B（同一 Redis）
cd scrapy && scrapy runspider spiders/generic.py

# Backend 投递任务 → Redis 队列
# 两个 Worker 自动负载均衡（从同一队列竞争取请求）
```

### 注意
- Redis 是单点——Redis 挂了，所有 Worker 停止（但队列数据不丢，SCHEDULER_PERSIST=True）
- 去重指纹（RFPDupeFilter）存在 Redis——多 Worker 不会重复爬同一 URL
- 每个 Worker 有独立的内存（seen 集合在 Redis，非本地）

## 常见问题

| 问题 | 原因 | 解决 |
|---|---|---|
| Worker 启动后一直等待 | Redis 队列为空（正常——等任务） | 投递任务到 `spider:<name>:start_urls` |
| 多 Worker 重复爬同一 URL | DUPEFILTER_CLASS 配置错误 | 确认是 `scrapy_redis.dupefilter.RFPDupeFilter` |
| 重启后队列丢失 | SCHEDULER_PERSIST = False | 改为 True |
| 结果没有归属到任务 | start_urls 条目缺少 task_id | 确认投递的是 JSON 格式 `{"url":..., "task_id":...}` |
