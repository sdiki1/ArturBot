from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.inline import CabinetCallback, cabinet_keyboard
from app.services.media import cabinet_banner_path
from app.services.referrals import ReferralService
from app.services.texts import TextService
from app.utils.ui import (
    CABINET_BANNER_MESSAGE_KEY,
    clear_state_message_id,
    clear_state_messages,
    safe_delete_message,
    store_state_message_id,
)

logger = logging.getLogger(__name__)
router = Router(name=__name__)
PHOTOS_SCREEN_MESSAGES_KEY = "photos_screen_message_ids"


async def show_cabinet_screen(bot: Bot, chat_id: int, state: FSMContext, session: AsyncSession) -> None:
    await clear_state_message_id(bot=bot, state=state, chat_id=chat_id, key=CABINET_BANNER_MESSAGE_KEY)
    try:
        banner = FSInputFile(path=str(cabinet_banner_path()))
        banner_message = await bot.send_photo(chat_id=chat_id, photo=banner)
        await store_state_message_id(state, CABINET_BANNER_MESSAGE_KEY, banner_message.message_id)
    except Exception:
        logger.exception("Failed to send cabinet banner")
        await store_state_message_id(state, CABINET_BANNER_MESSAGE_KEY, None)

    text_service = TextService(session)
    texts = await text_service.resolve_many(
        [
            "cabinet.title",
            "kb.cabinet_subscription",
            "kb.cabinet_referral",
            "kb.cabinet_photos",
            "kb.cabinet_bio",
            "kb.cabinet_subscribers",
        ]
    )
    await bot.send_message(
        chat_id=chat_id,
        text=texts["cabinet.title"],
        reply_markup=cabinet_keyboard(
            subscription_label=texts["kb.cabinet_subscription"],
            referral_label=texts["kb.cabinet_referral"],
            photos_label=texts["kb.cabinet_photos"],
            bio_label=texts["kb.cabinet_bio"],
            subscribers_label=texts["kb.cabinet_subscribers"],
        ),
    )


@router.message(Command("cabinet"))
async def cabinet_command_handler(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None:
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    await referral_service.ensure_user(message.from_user)
    await clear_state_messages(
        bot=message.bot,
        state=state,
        chat_id=message.chat.id,
        key=PHOTOS_SCREEN_MESSAGES_KEY,
    )
    await show_cabinet_screen(message.bot, message.chat.id, state, session)


@router.callback_query(CabinetCallback.filter(F.action == "open"))
async def cabinet_router(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.from_user is None:
        await callback.answer()
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    await referral_service.ensure_user(callback.from_user)
    if callback.message:
        await clear_state_messages(
            bot=callback.bot,
            state=state,
            chat_id=callback.message.chat.id,
            key=PHOTOS_SCREEN_MESSAGES_KEY,
        )
        await safe_delete_message(callback.message)
    await state.clear()

    if callback.message:
        await show_cabinet_screen(callback.bot, callback.message.chat.id, state, session)
    await callback.answer()
