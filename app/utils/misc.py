from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_referral_code(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
