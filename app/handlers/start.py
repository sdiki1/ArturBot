from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.repo.user_repo import UserRepo
from app.keyboards.inline import CabinetCallback, go_to_menu_keyboard
from app.services.referrals import ReferralService
from app.services.texts import TextService
from app.utils.text import user_display_name

router = Router(name=__name__)
logger = logging.getLogger(__name__)


async def _resolve_inviter_photo_file_id(message: Message, session: AsyncSession, inviter_telegram_id: int, inviter_user_id: int) -> str | None:
    repo = UserRepo(session)
    inviter_photos = await repo.list_user_photos(inviter_user_id)
    if inviter_photos:
        return inviter_photos[0].telegram_file_id

    try:
        profile_photos = await message.bot.get_user_profile_photos(user_id=inviter_telegram_id, limit=1)
    except TelegramBadRequest:
        return None

    if not profile_photos.photos or not profile_photos.photos[0]:
        return None
    return profile_photos.photos[0][-1].file_id


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    text_service = TextService(session)
    user, _ = await referral_service.ensure_user(message.from_user, command.args if command else None)
    inviter = await referral_service.get_inviter(user)
    if inviter:
        mentor_name = user_display_name(inviter)
        mentor_username = inviter.username or settings.default_mentor_username
    else:
        mentor_name, mentor_username = await referral_service.get_mentor_identity(user)

    first_name = user.first_name or await text_service.resolve("start.first_name_fallback")
    text = await text_service.render(
        "start.welcome",
        first_name=first_name,
        mentor_name=mentor_name,
        mentor_username=mentor_username,
    )
    button_label = await text_service.resolve("kb.start_to_chat")
    reply_markup = go_to_menu_keyboard(settings.community_chat_url or None, label=button_label)

    if settings.start_page_photo_url:
        try:
            await message.answer_photo(
                photo=settings.start_page_photo_url,
                caption=text,
                reply_markup=reply_markup,
            )
            return
        except TelegramBadRequest:
            logger.warning("Failed to send MAIN_PAGE_PHOTO_URL for user_id=%s", user.id)

    if inviter:
        inviter_photo_file_id = await _resolve_inviter_photo_file_id(
            message=message,
            session=session,
            inviter_telegram_id=inviter.telegram_id,
            inviter_user_id=inviter.id,
        )
        if inviter_photo_file_id:
            try:
                await message.answer_photo(
                    photo=inviter_photo_file_id,
                    caption=text,
                    reply_markup=reply_markup,
                )
                return
            except TelegramBadRequest:
                logger.warning("Failed to send inviter photo in start message for invited user_id=%s", user.id)

    await message.answer(text, reply_markup=reply_markup)


@router.callback_query(CabinetCallback.filter(F.action == "chat_not_set"))
async def chat_not_set_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    text_service = TextService(session)
    await callback.answer(await text_service.resolve("start.chat_not_set_alert"), show_alert=True)
