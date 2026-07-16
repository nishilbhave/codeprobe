# codeprobe eval fixture — intentionally flawed code used to regression-test
# audits. Do NOT copy patterns from this file. Defect map: evals/expected-findings.md
import sqlite3


class Database:
    def __init__(self, path="fixture.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    def execute(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur.lastrowid

    def query_one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def query_all(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()


db = Database()
