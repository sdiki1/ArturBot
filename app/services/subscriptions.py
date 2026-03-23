from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from app.db.models import User


class SubscriptionService:
    @staticmethod
    def get_days_left(expires_at: datetime | None) -> int:
        if expires_at is None:
            return 0
        now = datetime.now(timezone.utc)
        delta_seconds = (expires_at - now).total_seconds()
        if delta_seconds <= 0:
            return 0
        return int(math.ceil(delta_seconds / 86400))

    @staticmethod
    def extend_subscription(user: User, days: int) -> datetime:
        now = datetime.now(timezone.utc)
        current = user.subscription_expires_at
        base = current if current and current > now else now
        new_expires_at = base + timedelta(days=days)
        user.subscription_expires_at = new_expires_at
        return new_expires_at
