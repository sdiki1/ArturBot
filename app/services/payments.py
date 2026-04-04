from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Payment, PaymentStatus
from app.db.repo.payment_repo import PaymentRepo
from app.db.repo.user_repo import UserRepo
from app.services.subscriptions import SubscriptionService
from app.services.texts import TextService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PaymentCheckResult:
    checked_count: int = 0
    paid_count: int = 0
    pending_count: int = 0
    failed_count: int = 0
    error_count: int = 0


class PaymentService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.payment_repo = PaymentRepo(session)
        self.user_repo = UserRepo(session)

    def _yookassa_credentials_ready(self) -> bool:
        return bool(self.settings.yookassa_shop_id.strip() and self.settings.yookassa_api_key.strip())

    def _build_yookassa_return_url(self) -> str:
        explicit = self.settings.yookassa_return_url.strip()
        if explicit:
            return explicit

        base_url = self.settings.web_base_url.strip().rstrip("/")
        if base_url:
            return f"{base_url}/payments/yookassa/return"

        return "https://yookassa.ru"

    async def _request_yookassa(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        idempotence_key: str | None = None,
    ) -> dict[str, Any]:
        if not self._yookassa_credentials_ready():
            raise RuntimeError("YOOKASSA_SHOP_ID или YOOKASSA_API_KEY не настроены")

        url = f"https://api.yookassa.ru/v3{path}"
        headers: dict[str, str] = {}
        if idempotence_key:
            headers["Idempotence-Key"] = idempotence_key

        timeout = aiohttp.ClientTimeout(total=20)
        auth = aiohttp.BasicAuth(
            login=self.settings.yookassa_shop_id,
            password=self.settings.yookassa_api_key,
        )

        request_kwargs: dict[str, Any] = {"headers": headers}
        if payload is not None:
            request_kwargs["json"] = payload

        async with aiohttp.ClientSession(timeout=timeout, auth=auth) as client:
            async with client.request(method, url, **request_kwargs) as response:
                status_code = response.status
                body_text = await response.text()

        body: dict[str, Any]
        if body_text:
            try:
                parsed = json.loads(body_text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"YooKassa вернула не-JSON ответ: {body_text[:200]}") from exc
            if isinstance(parsed, dict):
                body = parsed
            else:
                raise RuntimeError("YooKassa вернула неожиданный формат ответа")
        else:
            body = {}

        if status_code >= 400:
            details = str(body.get("description") or body.get("code") or "")
            if details:
                raise RuntimeError(f"Ошибка YooKassa ({status_code}): {details}")
            raise RuntimeError(f"Ошибка YooKassa ({status_code})")

        return body

    async def _fetch_yookassa_status(self, external_payment_id: str) -> str:
        body = await self._request_yookassa("GET", f"/payments/{external_payment_id}")
        status = body.get("status")
        if not isinstance(status, str) or not status:
            raise RuntimeError("В ответе YooKassa отсутствует поле status")
        return status

    async def _sync_yookassa_payment(self, payment: Payment) -> str:
        status = await self._fetch_yookassa_status(payment.external_payment_id)

        if status == "succeeded":
            ok = await self.mark_paid_and_extend(payment.external_payment_id)
            return "paid" if ok else "error"

        if status == "canceled":
            await self.mark_failed(payment.external_payment_id)
            return "failed"

        return "pending"

    async def create_subscription_payment(self, user_id: int) -> tuple[Payment, str]:
        text_service = TextService(self.session)
        payload = {
            "amount": {
                "value": f"{self.settings.subscription_price_rub:.2f}",
                "currency": "RUB",
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": self._build_yookassa_return_url(),
            },
            "description": await text_service.resolve("payment.subscription_description"),
            "metadata": {
                "user_id": str(user_id),
            },
        }

        response = await self._request_yookassa(
            "POST",
            "/payments",
            payload=payload,
            idempotence_key=str(uuid4()),
        )

        external_payment_id = str(response.get("id") or "").strip()
        confirmation = response.get("confirmation")
        payment_url = ""
        if isinstance(confirmation, dict):
            payment_url = str(confirmation.get("confirmation_url") or "").strip()

        if not external_payment_id or not payment_url:
            raise RuntimeError("YooKassa не вернула id или confirmation_url")

        payment = await self.payment_repo.create_pending(
            user_id=user_id,
            amount=self.settings.subscription_price_rub,
            currency="RUB",
            provider="yookassa",
            external_payment_id=external_payment_id,
            payment_url=payment_url,
        )

        base_url = self.settings.web_base_url.strip().rstrip("/")
        intermediate_url = f"{base_url}/pay/{external_payment_id}" if base_url else payment_url
        return payment, intermediate_url

    async def check_unfinished_payments(self, user_id: int) -> PaymentCheckResult:
        result = PaymentCheckResult()
        payments = await self.payment_repo.list_unfinished_by_user(user_id=user_id)
        result.checked_count = len(payments)

        for payment in payments:
            if payment.provider != "yookassa":
                result.pending_count += 1
                continue

            try:
                sync_status = await self._sync_yookassa_payment(payment)
            except Exception:
                logger.exception("Failed to sync payment %s", payment.external_payment_id)
                result.error_count += 1
                continue

            if sync_status == "paid":
                result.paid_count += 1
            elif sync_status == "failed":
                result.failed_count += 1
            elif sync_status == "pending":
                result.pending_count += 1
            else:
                result.error_count += 1

        return result

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
