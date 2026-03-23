from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.inline import CabinetCallback, go_to_menu_keyboard
from app.services.referrals import ReferralService

router = Router(name=__name__)


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(message.from_user, command.args if command else None)
    mentor_name, mentor_username = await referral_service.get_mentor_identity(user)

    first_name = user.first_name or "друг"
    text = (
        f"Добрый день, {first_name}!\n\n"
        f"Меня зовут {mentor_name}\n"
        f"@{mentor_username}, я твой наставник и проводник в мир цифровых решений и онлайн-образования.\n\n"
        "С радостью помогу разобраться в системе, отвечу на любые вопросы и начнем двигаться к твоим результатам вместе!"
    )
    await message.answer(text, reply_markup=go_to_menu_keyboard(settings.community_chat_url or None))


@router.callback_query(CabinetCallback.filter(F.action == "chat_not_set"))
async def chat_not_set_handler(callback: CallbackQuery) -> None:
    await callback.answer("Чат пока не подключен.", show_alert=True)
