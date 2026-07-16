# codeprobe eval fixture — intentionally flawed code used to regression-test
# audits. Do NOT copy patterns from this file. Defect map: evals/expected-findings.md
import urllib.request

from database import db


def create_order(user_id, items, payment_token):
    order_id = db.execute(
        "INSERT INTO orders (user_id, status) VALUES (?, 'pending')", (user_id,)
    )
    for item in items:
        db.execute(
            "INSERT INTO order_items (order_id, sku, qty) VALUES (?, ?, ?)",
            (order_id, item["sku"], item["qty"]),
        )
    db.execute(
        "INSERT INTO payments (order_id, token) VALUES (?, ?)",
        (order_id, payment_token),
    )
    db.execute(
        "UPDATE inventory SET stock = stock - 1 WHERE sku IN "
        "(SELECT sku FROM order_items WHERE order_id = ?)",
        (order_id,),
    )
    return order_id


def order_summaries(order_ids):
    summaries = []
    for order_id in order_ids:
        order = db.query_one("SELECT * FROM orders WHERE id = ?", (order_id,))
        items = db.query_all(
            "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
        )
        customer = db.query_one(
            "SELECT name FROM users WHERE id = ?", (order["user_id"],)
        )
        summaries.append(
            {"order": order, "items": items, "customer": customer["name"]}
        )
    return summaries


def notify_warehouse(order_id):
    try:
        urllib.request.urlopen(
            f"https://warehouse.internal/api/orders/{order_id}/notify"
        )
    except Exception:
        pass
