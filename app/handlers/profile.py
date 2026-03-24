from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.repo.user_repo import UserRepo
from app.keyboards.inline import CabinetCallback, single_back_to_cabinet_keyboard
from app.services.referrals import ReferralService
from app.states.forms import BioForm
from app.utils.ui import CABINET_BANNER_MESSAGE_KEY, clear_state_message_id, edit_or_resend_callback_message

router = Router(name=__name__)


@router.callback_query(CabinetCallback.filter(F.action == "link"))
async def ask_external_link(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await clear_state_message_id(
            bot=callback.bot,
            state=state,
            chat_id=callback.message.chat.id,
            key=CABINET_BANNER_MESSAGE_KEY,
        )
    await edit_or_resend_callback_message(
        callback,
        "Раздел «Добавьте свою ссылку» отключен.",
        reply_markup=single_back_to_cabinet_keyboard("Назад в Личный кабинет"),
    )
    await callback.answer()


@router.callback_query(CabinetCallback.filter(F.action == "bio"))
async def ask_bio(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message:
        await clear_state_message_id(
            bot=callback.bot,
            state=state,
            chat_id=callback.message.chat.id,
            key=CABINET_BANNER_MESSAGE_KEY,
        )
    await state.set_state(BioForm.waiting_bio)
    await edit_or_resend_callback_message(
        callback,
        "Расскажите о себе вашим подписчикам",
        reply_markup=single_back_to_cabinet_keyboard("НАЗАД В ЛИЧНЫЙ КАБИНЕТ"),
    )
    await callback.answer()


@router.message(BioForm.waiting_bio)
async def save_bio(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None or message.text is None:
        await message.answer("Пожалуйста, отправьте текст.")
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(message.from_user)

    repo = UserRepo(session)
    await repo.set_bio(user, message.text.strip())

    await state.clear()
    await message.answer(
        "Информация о себе успешно сохранена.",
        reply_markup=single_back_to_cabinet_keyboard("НАЗАД В ЛИЧНЫЙ КАБИНЕТ"),
    )
