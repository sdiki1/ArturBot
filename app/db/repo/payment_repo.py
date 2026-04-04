from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Payment, PaymentStatus


class PaymentRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_pending(
        self,
        user_id: int,
        amount: int,
        currency: str,
        provider: str,
        external_payment_id: str,
        payment_url: str,
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            provider=provider,
            external_payment_id=external_payment_id,
            payment_url=payment_url,
            status=PaymentStatus.pending,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_external_payment_id(self, external_payment_id: str) -> Payment | None:
        result = await self.session.execute(select(Payment).where(Payment.external_payment_id == external_payment_id))
        return result.scalar_one_or_none()

    async def list_unfinished_by_user(self, user_id: int) -> list[Payment]:
        result = await self.session.execute(
            select(Payment)
            .where(
                Payment.user_id == user_id,
                Payment.status == PaymentStatus.pending,
            )
            .order_by(Payment.created_at.asc())
        )
        return list(result.scalars().all())

    async def mark_paid(self, payment: Payment) -> Payment:
        payment.status = PaymentStatus.paid
        payment.paid_at = datetime.now(timezone.utc)
        await self.session.flush()
        return payment

    async def mark_status(self, payment: Payment, status: PaymentStatus) -> Payment:
        payment.status = status
        await self.session.flush()
        return payment
