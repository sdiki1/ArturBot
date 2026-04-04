from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.inline import CabinetCallback, subscription_keyboard
from app.services.payments import PaymentService
from app.services.referrals import ReferralService
from app.services.subscriptions import SubscriptionService
from app.services.texts import TextService
from app.utils.ui import CABINET_BANNER_MESSAGE_KEY, clear_state_message_id, edit_or_resend_callback_message

router = Router(name=__name__)
logger = logging.getLogger(__name__)


async def _subscription_markup(text_service: TextService) -> InlineKeyboardMarkup:
    labels = await text_service.resolve_many(
        [
            "kb.subscription_renew",
            "kb.subscription_check_payment",
            "kb.back_to_cabinet_arrow",
        ]
    )
    return subscription_keyboard(
        renew_label=labels["kb.subscription_renew"],
        check_payment_label=labels["kb.subscription_check_payment"],
        back_label=labels["kb.back_to_cabinet_arrow"],
    )


async def _show_subscription_text(target: Message | CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()

    tg_user = target.from_user
    if tg_user is None:
        return

    referral_service = ReferralService(session, settings)
    text_service = TextService(session)
    user, _ = await referral_service.ensure_user(tg_user)

    first_name = user.first_name or await text_service.resolve("subscription.first_name_fallback")
    days_left = SubscriptionService.get_days_left(user.subscription_expires_at)
    text = await text_service.render("subscription.days_left", first_name=first_name, days_left=days_left)
    markup = await _subscription_markup(text_service)

    if isinstance(target, Message):
        await target.answer(text, reply_markup=markup)
    else:
        await edit_or_resend_callback_message(target, text, reply_markup=markup)


async def _answer_with_payment_url(callback: CallbackQuery, preferred_url: str, fallback_url: str) -> str:
    try:
        await callback.answer(url=preferred_url)
        return preferred_url
    except TelegramBadRequest as exc:
        logger.warning("Failed to open payment callback URL '%s': %s", preferred_url, exc)
        if preferred_url != fallback_url:
            try:
                await callback.answer(url=fallback_url)
                return fallback_url
            except TelegramBadRequest as fallback_exc:
                logger.warning("Failed to open fallback payment URL '%s': %s", fallback_url, fallback_exc)
        await callback.answer()
        return fallback_url


@router.callback_query(CabinetCallback.filter(F.action == "subscription"))
async def open_subscription(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.message:
        await clear_state_message_id(
            bot=callback.bot,
            state=state,
            chat_id=callback.message.chat.id,
            key=CABINET_BANNER_MESSAGE_KEY,
        )
    await _show_subscription_text(callback, session)
    await callback.answer()


@router.callback_query(CabinetCallback.filter(F.action == "renew_subscription"))
async def renew_subscription(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()

    if callback.from_user is None:
        await callback.answer()
        return
    if callback.message:
        await clear_state_message_id(
            bot=callback.bot,
            state=state,
            chat_id=callback.message.chat.id,
            key=CABINET_BANNER_MESSAGE_KEY,
        )

    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(callback.from_user)

    payment_service = PaymentService(session, settings)
    text_service = TextService(session)
    try:
        payment, intermediate_url = await payment_service.create_subscription_payment(user.id)
    except Exception:
        logger.exception("Failed to create YooKassa payment for user_id=%s", user.id)
        text = await text_service.resolve("subscription.payment_create_error")
        await edit_or_resend_callback_message(
            callback,
            text,
            reply_markup=await _subscription_markup(text_service),
        )
        await callback.answer()
        return

    opened_url = await _answer_with_payment_url(
        callback,
        preferred_url=intermediate_url or payment.payment_url,
        fallback_url=payment.payment_url,
    )
    text = await text_service.render("subscription.payment_opened", intermediate_url=opened_url)
    await edit_or_resend_callback_message(
        callback,
        text,
        reply_markup=await _subscription_markup(text_service),
    )


@router.callback_query(CabinetCallback.filter(F.action == "check_payments"))
async def check_payments(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()

    if callback.from_user is None:
        await callback.answer()
        return
    if callback.message:
        await clear_state_message_id(
            bot=callback.bot,
            state=state,
            chat_id=callback.message.chat.id,
            key=CABINET_BANNER_MESSAGE_KEY,
        )

    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(callback.from_user)

    payment_service = PaymentService(session, settings)
    text_service = TextService(session)

    try:
        check_result = await payment_service.check_unfinished_payments(user.id)
        await session.refresh(user)
    except Exception:
        logger.exception("Failed to check unfinished payments for user_id=%s", user.id)
        text = await text_service.resolve("subscription.payment_check_error")
    else:
        first_name = user.first_name or await text_service.resolve("subscription.first_name_fallback")
        days_left = SubscriptionService.get_days_left(user.subscription_expires_at)

        if check_result.checked_count == 0:
            text = await text_service.render(
                "subscription.payment_check_none",
                first_name=first_name,
                days_left=days_left,
            )
        else:
            text = await text_service.render(
                "subscription.payment_check_result",
                first_name=first_name,
                checked_count=check_result.checked_count,
                paid_count=check_result.paid_count,
                pending_count=check_result.pending_count,
                failed_count=check_result.failed_count,
                error_count=check_result.error_count,
                days_left=days_left,
            )

    await edit_or_resend_callback_message(
        callback,
        text,
        reply_markup=await _subscription_markup(text_service),
    )
    await callback.answer()
