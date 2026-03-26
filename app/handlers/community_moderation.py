from __future__ import annotations

import logging

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from app.config import get_settings

router = Router(name=__name__)
logger = logging.getLogger(__name__)


def _normalize(value: str) -> str:
    return "".join(value.casefold().split())


def _is_target_chat(message: Message) -> bool:
    settings = get_settings()
    return settings.empire_chat_id is not None and message.chat.id == settings.empire_chat_id


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
async def moderate_empire_chat(message: Message) -> None:
    if not _is_target_chat(message):
        return

    if message.new_chat_members:
        await _safe_delete(message)
        return

    if _is_hidden_bot_message(message):
        await _safe_delete(message)
