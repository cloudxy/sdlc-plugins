# Item 定义模板——每个爬虫的 Item 必须继承此模式
import hashlib
import json
from dataclasses import dataclass, field


@dataclass
class BaseItem:
    """所有爬虫 Item 的基类——分离 URL 去重键与业务内容变更哈希，数据质量在源头保障"""

    url: str
    url_key: str = field(default="", init=False)
    content_hash: str = field(default="", init=False)

    def payload_fields(self) -> dict[str, object]:
        """子类覆盖：返回参与内容变更检测的归一化业务字段（不含 url_key / content_hash / 采集时间戳）"""
        return {"url": self.url.strip()}

    def __post_init__(self):
        """url_key 用于请求/URL 去重；content_hash 用于业务载荷变更检测"""
        normalized_url = self.url.strip().lower()
        self.url_key = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
        canonical_payload = json.dumps(
            self.payload_fields(), sort_keys=True, ensure_ascii=False
        )
        self.content_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    def validate(self) -> tuple[bool, list[str]]:
        """子类覆盖：追加校验后统一按 len(errors) == 0 计算返回 (is_valid, errors)"""
        errors: list[str] = []
        if not self.url or not self.url.strip():
            errors.append("url 不能为空")
        return len(errors) == 0, errors


@dataclass
class ProductItem(BaseItem):
    """示例：商品价格采集 Item"""

    product_name: str = ""
    price: float = 0.0
    currency: str = "CNY"

    def payload_fields(self) -> dict[str, object]:
        return {
            "product_name": self.product_name.strip(),
            "price": round(float(self.price), 4),
            "currency": self.currency.strip().upper(),
        }

    def validate(self) -> tuple[bool, list[str]]:
        # 先调用基类校验，再追加子类校验并重新汇总 len(errors) == 0
        _, errors = super().validate()
        if not self.product_name or not self.product_name.strip():
            errors.append("product_name 不能为空")
        if self.price < 0:
            errors.append(f"price 不能为负: {self.price}")
        if not self.currency or not self.currency.strip():
            errors.append("currency 不能为空")
        return len(errors) == 0, errors
