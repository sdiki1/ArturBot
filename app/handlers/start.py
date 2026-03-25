from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.inline import CabinetCallback, go_to_menu_keyboard
from app.services.referrals import ReferralService
from app.services.texts import TextService

router = Router(name=__name__)


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    text_service = TextService(session)
    user, _ = await referral_service.ensure_user(message.from_user, command.args if command else None)
    mentor_name, mentor_username = await referral_service.get_mentor_identity(user)

    first_name = user.first_name or await text_service.resolve("start.first_name_fallback")
    text = await text_service.render(
        "start.welcome",
        first_name=first_name,
        mentor_name=mentor_name,
        mentor_username=mentor_username,
    )
    button_label = await text_service.resolve("kb.start_to_chat")
    await message.answer(text, reply_markup=go_to_menu_keyboard(settings.community_chat_url or None, label=button_label))


@router.callback_query(CabinetCallback.filter(F.action == "chat_not_set"))
async def chat_not_set_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    text_service = TextService(session)
    await callback.answer(await text_service.resolve("start.chat_not_set_alert"), show_alert=True)
