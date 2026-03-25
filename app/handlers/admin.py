from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Payment, PaymentStatus, User
from app.keyboards.inline import AdminCallback, admin_main_keyboard
from app.services.texts import TextService
from app.utils.text import user_display_name
from app.utils.ui import edit_or_resend_callback_message

router = Router(name=__name__)


def _is_admin(telegram_id: int) -> bool:
    settings = get_settings()
    return telegram_id in settings.admin_ids


async def _build_stats_text(session: AsyncSession, text_service: TextService) -> str:
    now = datetime.now(timezone.utc)

    total_users = int((await session.execute(select(func.count(User.id)))).scalar_one())
    active_subscriptions = int(
        (
            await session.execute(
                select(func.count(User.id)).where(
                    User.subscription_expires_at.is_not(None),
                    User.subscription_expires_at > now,
                )
            )
        ).scalar_one()
    )
    total_payments = int((await session.execute(select(func.count(Payment.id)))).scalar_one())
    paid_payments = int(
        (
            await session.execute(select(func.count(Payment.id)).where(Payment.status == PaymentStatus.paid))
        ).scalar_one()
    )

    return await text_service.render(
        "tg_admin.title_stats",
        total_users=total_users,
        active_subscriptions=active_subscriptions,
        total_payments=total_payments,
        paid_payments=paid_payments,
    )


async def _build_users_text(session: AsyncSession, text_service: TextService, limit: int = 20) -> str:
    result = await session.execute(select(User).order_by(User.created_at.desc()).limit(limit))
    users = list(result.scalars().all())

    if not users:
        return await text_service.resolve("tg_admin.recent_users_empty")

    lines = [await text_service.resolve("tg_admin.recent_users_title")]
    for item in users:
        username = f" @{item.username}" if item.username else ""
        lines.append(f"- {user_display_name(item)}{username} (id: {item.telegram_id})")
    return "\n".join(lines)


async def _build_payments_text(session: AsyncSession, text_service: TextService, limit: int = 20) -> str:
    result = await session.execute(select(Payment).order_by(Payment.created_at.desc()).limit(limit))
    payments = list(result.scalars().all())

    if not payments:
        return await text_service.resolve("tg_admin.recent_payments_empty")

    lines = [await text_service.resolve("tg_admin.recent_payments_title")]
    for item in payments:
        lines.append(
            f"- user_id={item.user_id} | {item.amount} {item.currency} | {item.status.value} | {item.external_payment_id}"
        )
    return "\n".join(lines)


@router.message(Command("admin"))
async def admin_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    text_service = TextService(session)
    if not _is_admin(message.from_user.id):
        await message.answer(await text_service.resolve("tg_admin.no_access_message"))
        return

    text = await _build_stats_text(session, text_service)
    labels = await text_service.resolve_many(
        ["kb.admin_stats", "kb.admin_users", "kb.admin_payments", "kb.admin_refresh", "kb.admin_to_cabinet"]
    )
    await message.answer(
        text,
        reply_markup=admin_main_keyboard(
            stats_label=labels["kb.admin_stats"],
            users_label=labels["kb.admin_users"],
            payments_label=labels["kb.admin_payments"],
            refresh_label=labels["kb.admin_refresh"],
            to_cabinet_label=labels["kb.admin_to_cabinet"],
        ),
    )


@router.callback_query(AdminCallback.filter())
async def admin_callbacks(callback: CallbackQuery, callback_data: AdminCallback, session: AsyncSession) -> None:
    text_service = TextService(session)
    if callback.from_user is None:
        await callback.answer()
        return

    if not _is_admin(callback.from_user.id):
        await callback.answer(await text_service.resolve("tg_admin.no_access_alert"), show_alert=True)
        return

    if callback_data.action == "open":
        text = await _build_stats_text(session, text_service)
    elif callback_data.action == "stats":
        text = await _build_stats_text(session, text_service)
    elif callback_data.action == "users":
        text = await _build_users_text(session, text_service)
    elif callback_data.action == "payments":
        text = await _build_payments_text(session, text_service)
    else:
        await callback.answer()
        return

    labels = await text_service.resolve_many(
        ["kb.admin_stats", "kb.admin_users", "kb.admin_payments", "kb.admin_refresh", "kb.admin_to_cabinet"]
    )
    await edit_or_resend_callback_message(
        callback,
        text,
        reply_markup=admin_main_keyboard(
            stats_label=labels["kb.admin_stats"],
            users_label=labels["kb.admin_users"],
            payments_label=labels["kb.admin_payments"],
            refresh_label=labels["kb.admin_refresh"],
            to_cabinet_label=labels["kb.admin_to_cabinet"],
        ),
    )
    await callback.answer()
