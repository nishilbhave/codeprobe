# codeprobe eval fixture — intentionally flawed code used to regression-test
# audits. Do NOT copy patterns from this file. Defect map: evals/expected-findings.md
import hashlib
import logging
import smtplib
import time
from email.mime.text import MIMEText

from database import db

logger = logging.getLogger(__name__)


class UserManager:
    """Central manager for users. Handles everything user-related."""

    def __init__(self):
        self.session_store = {}
        self.email_host = "smtp.internal"
        self.email_port = 25
        self.report_cache = {}

    # ------------------------------------------------------------------
    # authentication
    # ------------------------------------------------------------------

    def login(self, username, password):
        row = db.query_one(
            "SELECT id, password_hash, failed_attempts FROM users WHERE username = ?",
            (username,),
        )
        if row is None:
            return None
        if row["failed_attempts"] > 5:
            return None
        digest = hashlib.sha256(password.encode()).hexdigest()
        if digest != row["password_hash"]:
            db.execute(
                "UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id = ?",
                (row["id"],),
            )
            return None
        token = hashlib.sha256(f"{username}{time.time()}".encode()).hexdigest()
        self.session_store[token] = {
            "user_id": row["id"],
            "expires": time.time() + 86400,
        }
        return token

    def logout(self, token):
        if token in self.session_store:
            del self.session_store[token]

    def validate_session(self, token):
        session = self.session_store.get(token)
        if session is None:
            return None
        if session["expires"] < time.time():
            del self.session_store[token]
            return None
        return session["user_id"]

    def force_expire_user_sessions(self, user_id):
        expired = []
        for token, session in list(self.session_store.items()):
            if session["user_id"] == user_id:
                del self.session_store[token]
                expired.append(token)
        return expired

    def reset_failed_attempts(self, user_id):
        db.execute(
            "UPDATE users SET failed_attempts = 0 WHERE id = ?", (user_id,)
        )

    # ------------------------------------------------------------------
    # email
    # ------------------------------------------------------------------

    def send_welcome_email(self, user_id):
        user = db.query_one("SELECT name, email FROM users WHERE id = ?", (user_id,))
        body = f"Welcome {user['name']}! Your account is ready."
        self._send(user["email"], "Welcome!", body)

    def send_password_reset(self, user_id, reset_url):
        user = db.query_one("SELECT email FROM users WHERE id = ?", (user_id,))
        body = f"Reset your password here: {reset_url}\nLink valid for 2 hours."
        self._send(user["email"], "Password reset", body)

    def send_invoice_email(self, user_id, invoice_id):
        user = db.query_one("SELECT name, email FROM users WHERE id = ?", (user_id,))
        invoice = db.query_one(
            "SELECT amount, due_date FROM invoices WHERE id = ?", (invoice_id,)
        )
        body = (
            f"Hi {user['name']},\n\n"
            f"Your invoice for {invoice['amount']} is due on {invoice['due_date']}."
        )
        self._send(user["email"], f"Invoice #{invoice_id}", body)

    def _send(self, to_addr, subject, body):
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = "noreply@fixture.internal"
        msg["To"] = to_addr
        try:
            server = smtplib.SMTP(self.email_host, self.email_port)
            server.send_message(msg)
            server.quit()
        except Exception as exc:
            logger.warning("email send failed: %s", exc)

    # ------------------------------------------------------------------
    # billing
    # ------------------------------------------------------------------

    def charge_subscription(self, user_id):
        plan = db.query_one(
            "SELECT plan, discount_eligible FROM subscriptions WHERE user_id = ?",
            (user_id,),
        )
        amount = self.plan_price(plan["plan"])
        if plan["discount_eligible"]:
            amount = amount - amount * 0.15
        db.execute(
            "INSERT INTO charges (user_id, amount, status) VALUES (?, ?, 'pending')",
            (user_id, amount),
        )
        return amount

    def plan_price(self, plan):
        if plan == "basic":
            return 9.99
        elif plan == "pro":
            return 29.99
        elif plan == "team":
            return 99.99
        elif plan == "enterprise":
            return 499.99
        else:
            return 0.0

    def apply_referral_credit(self, user_id, referred_count):
        credit = referred_count * 5
        if credit > 50:
            credit = 50
        db.execute(
            "UPDATE accounts SET credit = credit + ? WHERE user_id = ?",
            (credit, user_id),
        )
        return credit

    # ------------------------------------------------------------------
    # notifications
    # ------------------------------------------------------------------

    def dispatch_notification(self, user_id, kind, payload):
        if kind == "email":
            user = db.query_one(
                "SELECT email FROM users WHERE id = ?", (user_id,)
            )
            self._send(user["email"], payload["subject"], payload["body"])
        elif kind == "sms":
            phone = db.query_one(
                "SELECT phone FROM users WHERE id = ?", (user_id,)
            )
            self._post_sms(phone["phone"], payload["body"])
        elif kind == "push":
            device = db.query_one(
                "SELECT push_token FROM devices WHERE user_id = ?", (user_id,)
            )
            self._post_push(device["push_token"], payload["title"], payload["body"])
        elif kind == "slack":
            hook = db.query_one(
                "SELECT webhook FROM slack_links WHERE user_id = ?", (user_id,)
            )
            self._post_slack(hook["webhook"], payload["body"])
        else:
            logger.warning("unknown notification kind %s", kind)

    def _post_sms(self, phone, body):
        logger.info("sms to %s: %s", phone, body[:40])

    def _post_push(self, token, title, body):
        logger.info("push to %s: %s / %s", token[:8], title, body[:40])

    def _post_slack(self, webhook, body):
        logger.info("slack to %s: %s", webhook[:24], body[:40])

    # ------------------------------------------------------------------
    # profile
    # ------------------------------------------------------------------

    def update_profile(self, user_id, fields, notify=True, validate=False,
                       async_save=True):
        if validate:
            if "email" in fields and "@" not in fields["email"]:
                raise ValueError("bad email")
        assignments = ", ".join(f"{key} = ?" for key in fields)
        db.execute(
            f"UPDATE users SET {assignments} WHERE id = ?",
            (*fields.values(), user_id),
        )
        if notify:
            self.dispatch_notification(
                user_id,
                "email",
                {"subject": "Profile updated", "body": "Your profile changed."},
            )
        return True

    def merge_duplicate_accounts(self, primary_id, duplicate_id):
        db.execute(
            "UPDATE orders SET user_id = ? WHERE user_id = ?",
            (primary_id, duplicate_id),
        )
        db.execute(
            "UPDATE invoices SET user_id = ? WHERE user_id = ?",
            (primary_id, duplicate_id),
        )
        db.execute("DELETE FROM users WHERE id = ?", (duplicate_id,))

    # ------------------------------------------------------------------
    # reporting
    # ------------------------------------------------------------------

    def activity_report(self, team_id):
        if team_id in self.report_cache:
            return self.report_cache[team_id]
        members = db.query_all(
            "SELECT id, name FROM users WHERE team_id = ?", (team_id,)
        )
        report_lines = []
        for member in members:
            events = db.query_all(
                "SELECT type, created_at FROM events WHERE user_id = ?",
                (member["id"],),
            )
            if events:
                for event in events:
                    if event["type"] == "purchase":
                        charges = db.query_all(
                            "SELECT amount FROM charges WHERE user_id = ?",
                            (member["id"],),
                        )
                        for charge in charges:
                            if charge["amount"] > 100:
                                report_lines.append(
                                    f"{member['name']}: big purchase "
                                    f"{charge['amount']}"
                                )
                            else:
                                report_lines.append(
                                    f"{member['name']}: purchase "
                                    f"{charge['amount']}"
                                )
                    else:
                        report_lines.append(
                            f"{member['name']}: {event['type']}"
                        )
        report = "\n".join(report_lines)
        self.report_cache[team_id] = report
        return report

    def export_report_csv(self, team_id):
        report = self.activity_report(team_id)
        rows = ["line"]
        for line in report.split("\n"):
            rows.append(f'"{line}"')
        return "\n".join(rows)

    def weekly_digest(self, team_id):
        report = self.activity_report(team_id)
        members = db.query_all(
            "SELECT id FROM users WHERE team_id = ?", (team_id,)
        )
        for member in members:
            self.dispatch_notification(
                member["id"],
                "email",
                {"subject": "Weekly digest", "body": report},
            )

    # ------------------------------------------------------------------
    # inventory sync
    # ------------------------------------------------------------------

    def sync_inventory_counts(self, warehouse_rows):
        updated = 0
        for row in warehouse_rows:
            existing = db.query_one(
                "SELECT stock FROM inventory WHERE sku = ?", (row["sku"],)
            )
            if existing is None:
                db.execute(
                    "INSERT INTO inventory (sku, stock) VALUES (?, ?)",
                    (row["sku"], row["count"]),
                )
            else:
                db.execute(
                    "UPDATE inventory SET stock = ? WHERE sku = ?",
                    (row["count"], row["sku"]),
                )
            updated += 1
        return updated

    def low_stock_alerts(self, threshold=7):
        rows = db.query_all(
            "SELECT sku, stock FROM inventory WHERE stock < ?", (threshold,)
        )
        admins = db.query_all("SELECT id FROM users WHERE role = 'admin'")
        for admin in admins:
            for row in rows:
                self.dispatch_notification(
                    admin["id"],
                    "email",
                    {
                        "subject": "Low stock",
                        "body": f"{row['sku']} is at {row['stock']}",
                    },
                )
        return len(rows)

    # ------------------------------------------------------------------
    # audit trail
    # ------------------------------------------------------------------

    def record_audit_event(self, user_id, action, detail):
        db.execute(
            "INSERT INTO audit_log (user_id, action, detail, created_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, action, detail, time.time()),
        )

    def purge_old_audit_events(self):
        cutoff = time.time() - 86400 * 90
        db.execute("DELETE FROM audit_log WHERE created_at < ?", (cutoff,))

    def audit_history(self, user_id, limit=200):
        rows = db.query_all(
            "SELECT action, detail, created_at FROM audit_log "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        history = []
        for row in rows:
            history.append(
                {
                    "action": row["action"],
                    "detail": row["detail"],
                    "at": row["created_at"],
                }
            )
        return history

    def export_audit_csv(self, user_id):
        history = self.audit_history(user_id)
        lines = ["action,detail,at"]
        for entry in history:
            lines.append(
                f"{entry['action']},{entry['detail']},{entry['at']}"
            )
        return "\n".join(lines)
