# collect：auto_agents 项目专属写法（归档）

- 归档日期：2026-09-27（第二轮改进方案 3.5「项目专属规则从通用执行方法移出」）。
- 来源：本插件 `skills/collect/references/scrapy-redis-distributed.md`、`skills/collect/templates/spider-template.py`、`skills/collect/templates/spider-config.py` 在 2026-09-26 基线中的原文，未改写。
- 专属点：`spiders/base.py` 的 `TaskAwareRedisSpider`、`TaskAttributionSpiderMiddleware`、`sites.yml`、`project_settings.REDIS.DEFAULT.URL`、Pipeline 名称与优先级、`spider:item_queue`、`scrapy/` 目录与 `runspider` 命令、项目红线编号 R5 / R6 / B2。
- 去向：这些是 auto_agents 仓库的约定，只能由该项目授权后写进它自己的知识（例如 `.sdlc/_lessons.md` 或项目文档）；插件不写那个仓库。任何 skill 都不再路由到本档。
- 插件里现在的通用写法：分布式队列采集的结构、scrapy-redis 配置的适用条件、「项目有任务感知基类时才继承」、「按项目架构决定是否允许直写主库」。

## 原文：references/scrapy-redis-distributed.md

````markdown
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
````

## 原文：templates/spider-template.py

```python
"""新爬虫模板——基于 TaskAwareRedisSpider（scrapy-redis 分布式）

使用方式：
1. 复制此文件到 scrapy/spiders/，重命名为你的爬虫名
2. 替换 name、start_urls 队列名、parse 方法
3. 确认 DOWNLOAD_DELAY 与目标站点速率匹配（R5 红线）
4. Item 字段用 dataclass 定义（含 validate 方法）
"""
from scrapy import Request
from spiders.base import TaskAwareRedisSpider


class MySpider(TaskAwareRedisSpider):
    name = "my_spider"  # ← Redis 队列名 = spider:<name>:start_urls

    # 可选：覆盖站点级反爬配置（sites.yml 优先级更高）
    custom_settings = {
        "DOWNLOAD_DELAY": 2,  # 根据目标站点调整
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    def parse(self, response):
        """解析列表页/详情页"""
        task_id = response.meta.get("task_id")

        # 提取数据
        for item in response.css("YOUR_SELECTOR"):
            yield {
                "url": response.url,
                "title": item.css("YOUR_TITLE_SELECTOR::text").get(),
                "content": item.css("YOUR_CONTENT_SELECTOR::text").get(),
                "task_id": task_id,
            }

        # 翻页（如有）
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, self.parse)

    def parse_detail(self, response):
        """详情页解析（如列表页只有链接，详情页有内容）"""
        task_id = response.meta.get("task_id")
        yield {
            "url": response.url,
            "title": response.css("h1::text").get(),
            "content": response.css(".content::text").get(),
            "task_id": task_id,
        }
```

## 原文：templates/spider-config.py

```python
# Spider 配置模板（基于项目 Scrapy 规范）
# R5: DOWNLOAD_DELAY 必须配置
# R6: USER_AGENT 必须配置
# B2: 数据通过 Redis 队列，禁止直接写 MySQL

import scrapy


class SpiderConfig:
    """Spider 基础配置——每个新爬虫必须遵循的最低标准"""

    # ── R5 红线：速率控制 ──
    DOWNLOAD_DELAY = 2                    # 秒，根据目标站点调整
    AUTOTHROTTLE_ENABLED = True           # 自动限速
    AUTOTHROTTLE_START_DELAY = 2
    AUTOTHROTTLE_MAX_DELAY = 10
    CONCURRENT_REQUESTS = 4               # 并发请求数
    CONCURRENT_REQUESTS_PER_DOMAIN = 2    # 单域名并发

    # ── R6 红线：UA 轮换 ──
    USER_AGENT = '<从 UA 池随机选取>'
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        # ... 至少 10 个真实 UA
    ]

    # ── 重试 ──
    RETRY_ENABLED = True
    RETRY_TIMES = 3

    # ── 数据流转（B2 边界）──
    # Item → Redis 队列（spider:<name>:items）
    # 禁止直接写 MySQL——由 backend 消费者处理
    ITEM_PIPELINE = [
        'scrapy_pipelines.RedisQueuePipeline',
    ]

    # ── 反爬升级 ──
    # 第 1-2 级（速率+UA）是标配
    # 第 3 级（代理）需要配置代理池地址
    # 第 5 级（JS 渲染）需要 Splash 或 Playwright


class ItemValidation:
    """Item 级数据质量校验——垃圾进 = 垃圾出"""

    REQUIRED_FIELDS = []      # 子类覆盖：必填字段列表
    FIELD_TYPES = {}          # 子类覆盖：{field: type}

    @classmethod
    def validate(cls, item: dict) -> tuple[bool, list[str]]:
        """返回 (is_valid, errors)"""
        errors = []
        for field in cls.REQUIRED_FIELDS:
            if field not in item or item[field] is None:
                errors.append(f"缺少必填字段: {field}")
        for field, expected_type in cls.FIELD_TYPES.items():
            if field in item and item[field] is not None:
                if not isinstance(item[field], expected_type):
                    errors.append(f"字段 {field} 类型错误: 期望 {expected_type.__name__}, 实际 {type(item[field]).__name__}")
        return len(errors) == 0, errors
```
