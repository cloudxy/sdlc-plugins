# T-7 · FR-2 invoice discount

Lane: backend · Contract: C-3 (accepted 2026-09-30): `invoice_total(lines)` in `src/invoice.py` is the public seam for pricing; tests go through it.

FR-2: an invoice whose subtotal is at least 100.00 gets 10% off; the total is rounded half-up to cents.

| GWT | Given | When | Then |
|---|---|---|---|
| FR-2.1 | lines (19.99 × 3) and (45.50 × 2) | invoice_total | 135.87 |
| FR-2.2 | lines (20.00 × 2) | invoice_total | 40.00 (no discount below 100.00) |
