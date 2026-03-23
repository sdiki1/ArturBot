from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.inline import CabinetCallback, subscription_keyboard
from app.services.payments import PaymentService
from app.services.referrals import ReferralService
from app.services.subscriptions import SubscriptionService
from app.utils.ui import CABINET_BANNER_MESSAGE_KEY, clear_state_message_id, edit_or_resend_callback_message

router = Router(name=__name__)


async def _show_subscription_text(target: Message | CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()

    tg_user = target.from_user
    if tg_user is None:
        return

    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(tg_user)

    first_name = user.first_name or "Пользователь"
    days_left = SubscriptionService.get_days_left(user.subscription_expires_at)
    text = f"{first_name}, у Вас осталось дней подписки: {days_left}"

    if isinstance(target, Message):
        await target.answer(text, reply_markup=subscription_keyboard())
    else:
        await edit_or_resend_callback_message(target, text, reply_markup=subscription_keyboard())


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
    _, intermediate_url = await payment_service.create_subscription_payment(user.id)

    await callback.answer(url=intermediate_url)
    await edit_or_resend_callback_message(
        callback,
        "Переход к оплате открыт.\n\n"
        "Если страница оплаты не открылась автоматически, перейдите по ссылке:\n"
        f"{intermediate_url}",
        reply_markup=subscription_keyboard(),
    )
