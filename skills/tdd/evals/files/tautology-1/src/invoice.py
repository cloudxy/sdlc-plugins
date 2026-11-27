from decimal import Decimal, ROUND_HALF_UP

DISCOUNT_RATE = Decimal("0.10")
DISCOUNT_THRESHOLD = Decimal("100.00")


def _cents(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def invoice_total(lines):
    subtotal = sum(Decimal(str(price)) * qty for price, qty in lines)
    return _cents(subtotal)
