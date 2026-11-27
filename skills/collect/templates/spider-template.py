"""新爬虫模板——scrapy-redis 分布式（适用条件见 references/scrapy-redis-distributed.md）

使用方式：
1. 复制到项目的爬虫目录，重命名为你的爬虫名
2. 项目有任务感知基类时，把 RedisSpider 换成它，并删掉下面重复的条目解析
3. 替换 name、起始队列键、parse 方法
4. 确认下载延迟与并发符合目标站点的访问约定（反爬是底线）
5. Item 字段用项目的 item 定义（含校验）
"""
import json

from scrapy import Request
from scrapy_redis.spiders import RedisSpider


class MySpider(RedisSpider):
    name = "my_spider"  # 默认起始队列键 = <name>:start_urls；项目另有约定时以项目为准

    # 可选：站点级速率；项目有站点配置时以项目配置为准
    custom_settings = {
        "DOWNLOAD_DELAY": 2,  # 根据目标站点调整
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    def make_request_from_data(self, data):
        """JSON 条目 → 请求，并把任务标识放进 meta（签名按已安装的 scrapy-redis 版本核对）"""
        entry = json.loads(data)
        return Request(entry["url"], meta={"task_id": entry.get("task_id")})

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

        # 翻页（如有）：显式传递任务标识
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, self.parse, meta={"task_id": task_id})

    def parse_detail(self, response):
        """详情页解析（如列表页只有链接，详情页有内容）"""
        task_id = response.meta.get("task_id")
        yield {
            "url": response.url,
            "title": response.css("h1::text").get(),
            "content": response.css(".content::text").get(),
            "task_id": task_id,
        }
