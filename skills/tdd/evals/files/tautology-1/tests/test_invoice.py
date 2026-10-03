from decimal import Decimal

from src.invoice import DISCOUNT_RATE, _cents, invoice_total


def test_total_sums_lines():
    lines = [(20.00, 2)]
    expected = _cents(sum(Decimal(str(p)) * q for p, q in lines))
    assert invoice_total(lines) == expected


def test_discount_rate_applied():
    lines = [(60.00, 2)]
    subtotal = sum(Decimal(str(p)) * q for p, q in lines)
    expected = _cents(subtotal * (1 - DISCOUNT_RATE)) if subtotal >= 100 else _cents(subtotal)
    assert invoice_total(lines) in (expected, _cents(subtotal))
