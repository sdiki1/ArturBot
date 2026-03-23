from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.repo.user_repo import UserRepo
from app.keyboards.inline import CabinetCallback, single_back_to_cabinet_keyboard
from app.services.referrals import ReferralService
from app.utils.text import split_text_by_limit, subscriber_line
from app.utils.ui import CABINET_BANNER_MESSAGE_KEY, clear_state_message_id, edit_or_resend_callback_message

router = Router(name=__name__)


@router.callback_query(CabinetCallback.filter(F.action == "subscribers"))
async def subscribers_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    await clear_state_message_id(
        bot=callback.bot,
        state=state,
        chat_id=callback.message.chat.id,
        key=CABINET_BANNER_MESSAGE_KEY,
    )

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(callback.from_user)

    repo = UserRepo(session)
    subscribers = await repo.list_subscribers(user.id)
    count = len(subscribers)

    lines = [f"Количество подписчиков: {count}", "", "Мои подписчики:"]
    if count == 0:
        lines.append("- Пока нет подписчиков")
    else:
        lines.extend(subscriber_line(item) for item in subscribers)

    chunks = split_text_by_limit(lines)
    for idx, chunk in enumerate(chunks):
        is_last = idx == len(chunks) - 1
        markup = single_back_to_cabinet_keyboard("Назад в Личный кабинет") if is_last else None
        if idx == 0:
            await edit_or_resend_callback_message(callback, chunk, reply_markup=markup)
            continue
        await callback.message.answer(chunk, reply_markup=markup)

    await callback.answer()
