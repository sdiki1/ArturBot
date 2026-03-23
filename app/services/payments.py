from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Payment, PaymentStatus
from app.db.repo.payment_repo import PaymentRepo
from app.db.repo.user_repo import UserRepo
from app.services.subscriptions import SubscriptionService

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.payment_repo = PaymentRepo(session)
        self.user_repo = UserRepo(session)

    def _build_yoomoney_url(self, external_payment_id: str, amount: int) -> str:
        params = {
            "receiver": self.settings.yoomoney_receiver,
            "quickpay-form": "shop",
            "targets": "Подписка PRO возможности",
            "sum": str(amount),
            "label": external_payment_id,
        }
        if self.settings.yoomoney_success_url:
            params["successURL"] = self.settings.yoomoney_success_url
        if self.settings.yoomoney_fail_url:
            params["failURL"] = self.settings.yoomoney_fail_url
        return f"https://yoomoney.ru/quickpay/confirm.xml?{urlencode(params)}"

    async def create_subscription_payment(self, user_id: int) -> tuple[Payment, str]:
        external_payment_id = str(uuid4())
        payment_url = self._build_yoomoney_url(
            external_payment_id=external_payment_id,
            amount=self.settings.subscription_price_rub,
        )

        payment = await self.payment_repo.create_pending(
            user_id=user_id,
            amount=self.settings.subscription_price_rub,
            currency="RUB",
            provider="yoomoney",
            external_payment_id=external_payment_id,
            payment_url=payment_url,
        )

        intermediate_url = f"{self.settings.web_base_url}/pay/{external_payment_id}"
        return payment, intermediate_url

    async def get_payment(self, external_payment_id: str) -> Payment | None:
        return await self.payment_repo.get_by_external_payment_id(external_payment_id)

    def verify_yoomoney_notification(self, payload: dict[str, Any]) -> bool:
        secret = self.settings.yoomoney_label_secret
        if not secret:
            return True

        sha1_hash = payload.get("sha1_hash")
        if not isinstance(sha1_hash, str) or not sha1_hash:
            return False

        source = "&".join(
            [
                str(payload.get("notification_type", "")),
                str(payload.get("operation_id", "")),
                str(payload.get("amount", "")),
                str(payload.get("currency", "")),
                str(payload.get("datetime", "")),
                str(payload.get("sender", "")),
                str(payload.get("codepro", "")),
                secret,
                str(payload.get("label", "")),
            ]
        )
        expected = hashlib.sha1(source.encode("utf-8")).hexdigest()
        return expected == sha1_hash

    async def mark_paid_and_extend(self, external_payment_id: str) -> bool:
        payment = await self.payment_repo.get_by_external_payment_id(external_payment_id)
        if payment is None:
            return False

        if payment.status == PaymentStatus.paid:
            return True

        user = await self.user_repo.get_by_id(payment.user_id)
        if user is None:
            logger.error("User not found for payment: %s", payment.external_payment_id)
            return False

        await self.payment_repo.mark_paid(payment)
        SubscriptionService.extend_subscription(user, days=self.settings.subscription_days)
        await self.session.commit()
        return True

    async def mark_failed(self, external_payment_id: str) -> bool:
        payment = await self.payment_repo.get_by_external_payment_id(external_payment_id)
        if payment is None:
            return False
        await self.payment_repo.mark_status(payment, PaymentStatus.failed)
        await self.session.commit()
        return True

    @staticmethod
    def paid_at_iso(dt: datetime | None) -> str:
        if dt is None:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
