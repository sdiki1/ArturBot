from __future__ import annotations

import logging

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import User
from app.db.repo.user_repo import UserRepo
from app.services.referrals import ReferralService
from app.services.texts import TextService
from app.utils.text import user_display_name

router = Router(name=__name__)
logger = logging.getLogger(__name__)
_MALE_NAMES_ENDING_WITH_A_OR_YA = {
    "илья",
    "никита",
    "лука",
    "фома",
    "данила",
    "кузьма",
    "савва",
    "валера",
    "саша",
    "женя",
    "юра",
    "паша",
    "миша",
    "дима",
    "сережа",
    "леша",
    "витя",
    "толя",
    "вова",
    "коля",
    "рома",
    "степа",
    "федя",
    "лева",
    "петя",
    "костя",
    "гриша",
    "вася",
}


def _normalize(value: str) -> str:
    return "".join(value.casefold().split())


def _is_target_chat(message: Message) -> bool:
    settings = get_settings()
    return settings.empire_chat_id is not None and message.chat.id == settings.empire_chat_id


def _is_plus_trigger(message: Message) -> bool:
    return (message.text or "").strip() == "+"


def _is_hidden_bot_message(message: Message) -> bool:
    settings = get_settings()
    if message.from_user is None or not message.from_user.is_bot:
        return False

    if settings.empire_hide_bot_id is not None and message.from_user.id == settings.empire_hide_bot_id:
        return True

    configured_username = settings.empire_hide_bot_username.strip().lstrip("@").lower()
    sender_username = (message.from_user.username or "").lstrip("@").lower()
    if configured_username and sender_username and configured_username == sender_username:
        return True

    # Fallback by bot display name for cases when username/id are not known yet.
    sender_name = _normalize(" ".join(part for part in [message.from_user.first_name, message.from_user.last_name] if part))
    return "точкароста" in sender_name


def _resolve_gender_words(first_name: str | None, last_name: str | None) -> tuple[str, str]:
    normalized_last_name = _normalize(last_name or "")
    if normalized_last_name.endswith(("ова", "ева", "ёва", "ина", "ына", "ская", "цкая", "ая", "яя")):
        return "Рада", "приняла"
    if normalized_last_name.endswith(("ов", "ев", "ёв", "ин", "ын", "ский", "цкий")):
        return "Рад", "принял"

    if not first_name:
        return "Рад", "принял"

    normalized = _normalize(first_name)
    if normalized.endswith(("а", "я")) and normalized not in _MALE_NAMES_ENDING_WITH_A_OR_YA:
        return "Рада", "приняла"
    return "Рад", "принял"


async def _resolve_inviter_photo_file_id(message: Message, session: AsyncSession, inviter: User) -> str | None:
    repo = UserRepo(session)
    inviter_photos = await repo.list_user_photos(inviter.id)
    if inviter_photos:
        return inviter_photos[0].telegram_file_id

    try:
        profile_photos = await message.bot.get_user_profile_photos(user_id=inviter.telegram_id, limit=1)
    except TelegramAPIError:
        return None

    if not profile_photos.photos or not profile_photos.photos[0]:
        return None
    return profile_photos.photos[0][-1].file_id


async def _safe_delete(message: Message) -> None:
    try:
        await message.delete()
    except TelegramAPIError:
        logger.warning(
            "Cannot delete message_id=%s chat_id=%s; check admin rights for bot",
            message.message_id,
            message.chat.id,
        )


@router.message()
async def moderate_empire_chat(message: Message, session: AsyncSession) -> None:
    if not _is_target_chat(message):
        return

    if message.new_chat_members:
        await _safe_delete(message)
        return

    if _is_hidden_bot_message(message):
        await _safe_delete(message)
        return

    if not _is_plus_trigger(message):
        return

    if message.from_user is None or message.from_user.is_bot:
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    text_service = TextService(session)
    user, _ = await referral_service.ensure_user(message.from_user)
    inviter = await referral_service.get_inviter(user)

    member_name = user_display_name(user)
    glad_word, accepted_word = _resolve_gender_words(user.first_name, user.last_name)

    mentor_name, mentor_username = await referral_service.get_mentor_identity(user)
    inviter_photo_file_id = None
    if inviter is not None:
        mentor_name = user_display_name(inviter)
        mentor_username = inviter.username or settings.default_mentor_username
        inviter_photo_file_id = await _resolve_inviter_photo_file_id(message, session, inviter)

    mentor_username_line = f" @{mentor_username}" if mentor_username else ""
    text = await text_service.render(
        "community.plus_welcome",
        member_name=member_name,
        mentor_name=mentor_name,
        mentor_username_line=mentor_username_line,
        glad_word=glad_word,
        accepted_word=accepted_word,
    )

    if inviter_photo_file_id:
        try:
            await message.answer_photo(photo=inviter_photo_file_id, caption=text)
            return
        except TelegramAPIError:
            logger.warning(
                "Cannot send inviter photo in empire chat for user_id=%s",
                user.id,
            )

    try:
        await message.answer(text)
    except TelegramAPIError:
        logger.warning(
            "Cannot send plus-reply in empire chat for user_id=%s",
            user.id,
        )
