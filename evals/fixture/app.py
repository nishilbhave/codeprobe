# codeprobe eval fixture — intentionally flawed code used to regression-test
# audits. Do NOT copy patterns from this file. Defect map: evals/expected-findings.md
import logging
import sqlite3

from flask import Flask, jsonify, request

app = Flask(__name__)
logger = logging.getLogger(__name__)

STRIPE_SECRET_KEY = "sk-live-51Hfixture8Xq2vNplantedSECRETdonotuse"


def get_db():
    return sqlite3.connect("fixture.db")


@app.route("/reports", methods=["POST"])
def search_reports():
    name_filter = request.form.get("name", "")
    conn = get_db()
    rows = conn.execute(
        f"SELECT id, name, total FROM reports WHERE name LIKE '%{name_filter}%'"
    ).fetchall()
    return jsonify([dict(zip(("id", "name", "total"), r)) for r in rows])


@app.route("/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    return "", 204


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    logger.info("login attempt user=%s password=%s", username, password)
    conn = get_db()
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row and row[1] == password:
        return jsonify({"user_id": row[0]})
    return jsonify({"error": "Something went wrong"}), 500
