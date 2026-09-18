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
