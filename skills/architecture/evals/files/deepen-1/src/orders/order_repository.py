class OrderRepository:
    def __init__(self, db):
        self.db = db

    def save(self, customer, items, total):
        return self.db.insert("orders", {"customer": customer["id"], "items": items, "total": total})
