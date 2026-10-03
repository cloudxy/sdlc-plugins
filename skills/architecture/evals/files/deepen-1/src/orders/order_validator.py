def validate_customer(customer):
    if not customer.get("id"):
        raise ValueError("customer required")


def validate_items(items):
    for item in items:
        if item["qty"] <= 0:
            raise ValueError("qty must be positive")
