from .order_validator import validate_items, validate_customer
from .order_pricing import line_total, apply_discount, round_total
from .order_repository import OrderRepository


class OrderService:
    def __init__(self, repo: OrderRepository):
        self.repo = repo

    def place(self, customer, items, coupon=None):
        validate_customer(customer)
        validate_items(items)
        subtotal = sum(line_total(i) for i in items)
        total = round_total(apply_discount(subtotal, coupon))
        return self.repo.save(customer, items, total)
