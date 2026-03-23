from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.repo.user_repo import UserRepo
from app.keyboards.inline import CabinetCallback, single_back_to_cabinet_keyboard
from app.services.referrals import ReferralService
from app.utils.text import split_text_by_limit, subscriber_line

router = Router(name=__name__)


@router.callback_query(CabinetCallback.filter(F.action == "subscribers"))
async def subscribers_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

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
        await callback.message.answer(chunk, reply_markup=markup)

    await callback.answer()
