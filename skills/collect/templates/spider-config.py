# Spider 配置模板（Scrapy）。项目有自己的规范编号与配置入口时以项目为准。
# 前提：来源访问合同（ToS / 授权 API / 限速与已批准预算）。合同不允许的手段不写进配置。
# 速率：DOWNLOAD_DELAY 按合同与预算配置
# 标识：USER_AGENT 使用项目已声明的一个客户端标识，同一会话保持不变
# 交接：数据去向由项目架构决定；采集与存储分离时经队列交接，不直写主库

import scrapy


class SpiderConfig:
    """Spider 基础配置——每个新爬虫必须遵循的最低标准"""

    # ── 速率控制（必配）──
    DOWNLOAD_DELAY = 2                    # 秒，根据目标站点调整
    AUTOTHROTTLE_ENABLED = True           # 自动限速
    AUTOTHROTTLE_START_DELAY = 2
    AUTOTHROTTLE_MAX_DELAY = 10
    CONCURRENT_REQUESTS = 4               # 并发请求数
    CONCURRENT_REQUESTS_PER_DOMAIN = 2    # 单域名并发

    # ── 客户端标识（必配）──
    # 已声明的一个标识。不得配置 UA 池，不得用中间件轮换来规避风控或配额。
    USER_AGENT = '<项目声明的一个客户端标识>'

    # ── 重试 ──
    RETRY_ENABLED = True
    RETRY_TIMES = 3

    # ── 数据交接（按项目架构）──
    # 采集与存储分离时：Item → 队列（键名按项目约定），由消费者落库，Spider/Pipeline 不开主库会话
    ITEM_PIPELINE = [
        '<项目的队列交接 Pipeline>',
    ]

    # ── 访问受阻 ──
    # 降速、暂停受影响操作、使用合同写明的授权出口，或走授权通道与人工升级。
    # 不得配置住宅或数据中心代理池，不得打码。JS 渲染只在合同允许时使用。


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
