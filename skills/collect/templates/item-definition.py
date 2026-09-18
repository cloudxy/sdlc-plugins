# Item 定义模板——每个爬虫的 Item 必须继承此模式
import hashlib
from dataclasses import dataclass, field


@dataclass
class BaseItem:
    """所有爬虫 Item 的基类——数据质量在源头保障"""

    url: str
    content_hash: str = field(default="", init=False)

    def __post_init__(self):
        """自动计算内容哈希（去重用）"""
        normalized = self.url.strip().lower()
        self.content_hash = hashlib.md5(normalized.encode()).hexdigest()

    def validate(self) -> tuple[bool, list[str]]:
        """子类覆盖：返回 (is_valid, errors)"""
        errors = []
        if not self.url:
            errors.append("url 不能为空")
        return len(errors) == 0, errors


@dataclass
class ProductItem(BaseItem):
    """示例：商品价格采集 Item"""
    product_name: str = ""
    price: float = 0.0
    currency: str = "CNY"

    def validate(self) -> tuple[bool, list[str]]:
        # 先调用基类校验
        is_valid, errors = super().validate()
        # 追加子类校验
        if not self.product_name:
            errors.append("product_name 不能为空")
        if self.price < 0:
            errors.append(f"price 不能为负: {self.price}")
        return is_valid, errors
