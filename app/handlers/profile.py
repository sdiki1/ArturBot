from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.repo.user_repo import UserRepo
from app.keyboards.inline import CabinetCallback, single_back_to_cabinet_keyboard
from app.services.referrals import ReferralService
from app.states.forms import BioForm, LinkForm
from app.utils.validators import is_valid_url

router = Router(name=__name__)


@router.callback_query(CabinetCallback.filter(lambda c: c.action == "link"))
async def ask_external_link(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(LinkForm.waiting_link)
    if callback.message:
        await callback.message.answer(
            "Отправьте вашу ссылку для подписчиков.\nНапример: https://example.com",
            reply_markup=single_back_to_cabinet_keyboard("Назад в Личный кабинет"),
        )
    await callback.answer()


@router.message(LinkForm.waiting_link)
async def save_external_link(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None or message.text is None:
        await message.answer("Пожалуйста, отправьте текстовую ссылку.")
        return

    value = message.text.strip()
    if not is_valid_url(value):
        await message.answer("Некорректная ссылка. Отправьте ссылку формата https://example.com")
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(message.from_user)

    repo = UserRepo(session)
    await repo.set_external_link(user, value)

    await state.clear()
    await message.answer(
        "Ссылка успешно сохранена.",
        reply_markup=single_back_to_cabinet_keyboard("Назад в Личный кабинет"),
    )


@router.callback_query(CabinetCallback.filter(lambda c: c.action == "bio"))
async def ask_bio(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BioForm.waiting_bio)
    if callback.message:
        await callback.message.answer(
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
