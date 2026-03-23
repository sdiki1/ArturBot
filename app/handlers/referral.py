from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.inline import CabinetCallback, single_back_to_cabinet_keyboard
from app.services.referrals import ReferralService
from app.utils.text import user_display_name

router = Router(name=__name__)


@router.callback_query(CabinetCallback.filter(F.action == "referral"))
async def referral_link_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None:
        await callback.answer()
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(callback.from_user)
    link = referral_service.build_referral_link(user.referral_code)

    text = f"Моя реф.ссылка:\n\n{link}"
    if callback.message:
        await callback.message.answer(text, reply_markup=single_back_to_cabinet_keyboard("Назад в Личный кабинет"))
    await callback.answer()


@router.message(Command("priglasil"))
async def who_invited_handler(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(message.from_user)
    inviter = await referral_service.get_inviter(user)

    if inviter is None:
        await message.answer("У Вас нет пригласившего пользователя.")
        return

    inviter_name = user_display_name(inviter)
    inviter_username = f"@{inviter.username}" if inviter.username else ""
    text = f"Вас пригласил:\n{inviter_name}"
    if inviter_username:
        text += f"\n{inviter_username}"
    await message.answer(text)
