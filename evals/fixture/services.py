# codeprobe eval fixture — intentionally flawed code used to regression-test
# audits. Do NOT copy patterns from this file. Defect map: evals/expected-findings.md
from models import User


def default_currency():
    return "USD"


def rename_user(user: User, new_name: str) -> User:
    user.set_name(new_name)
    return user


def user_display_label(user: User) -> str:
    return f"{user.get_name()} <{user.get_email()}>"
