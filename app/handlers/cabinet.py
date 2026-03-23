from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.inline import CabinetCallback, cabinet_keyboard
from app.services.media import cabinet_banner_path
from app.services.referrals import ReferralService

logger = logging.getLogger(__name__)
router = Router(name=__name__)


async def show_cabinet_screen(bot: Bot, chat_id: int) -> None:
    try:
        banner = FSInputFile(path=str(cabinet_banner_path()))
        await bot.send_photo(chat_id=chat_id, photo=banner)
    except Exception:
        logger.exception("Failed to send cabinet banner")

    await bot.send_message(chat_id=chat_id, text="Личный кабинет", reply_markup=cabinet_keyboard())


@router.message(Command("cabinet"))
async def cabinet_command_handler(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    await referral_service.ensure_user(message.from_user)
    await show_cabinet_screen(message.bot, message.chat.id)


@router.callback_query(CabinetCallback.filter(F.action == "open"))
async def cabinet_router(callback: CallbackQuery, callback_data: CabinetCallback, session: AsyncSession, state: FSMContext) -> None:
    if callback.from_user is None:
        await callback.answer()
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    await referral_service.ensure_user(callback.from_user)
    await state.clear()

    if callback.message:
        await show_cabinet_screen(callback.bot, callback.message.chat.id)
    await callback.answer()
