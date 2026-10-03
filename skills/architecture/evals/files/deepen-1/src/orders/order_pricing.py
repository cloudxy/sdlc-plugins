def line_total(item):
    return item["price"] * item["qty"]


def apply_discount(subtotal, coupon):
    if coupon and coupon.get("percent"):
        return subtotal * (100 - coupon["percent"]) / 100
    return subtotal


def round_total(value):
    return round(value, 2)
