# codeprobe eval fixture — intentionally flawed code used to regression-test
# audits. Do NOT copy patterns from this file. Defect map: evals/expected-findings.md
from services import default_currency


class User:
    def __init__(self, user_id, name, email):
        self.user_id = user_id
        self.name = name
        self.email = email

    def get_id(self):
        return self.user_id

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_email(self):
        return self.email

    def set_email(self, email):
        self.email = email


class Invoice:
    def __init__(self, invoice_id, amount):
        self.invoice_id = invoice_id
        self.amount = amount
        self.currency = default_currency()
