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
