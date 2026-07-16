# codeprobe eval fixture — intentionally flawed code used to regression-test
# audits. Do NOT copy patterns from this file. Defect map: evals/expected-findings.md
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import orders  # noqa: E402


def test_create_order():
    orders.create_order(42, [{"sku": "SKU-1", "qty": 1}], "tok_test")


def test_order_summaries():
    orders.order_summaries([1])
