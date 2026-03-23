from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.repo.user_repo import UserRepo
from app.keyboards.inline import CabinetCallback, PhotoCallback, photo_slot_keyboard, photos_footer_keyboard
from app.services.media import photo_placeholder_path
from app.services.referrals import ReferralService
from app.states.forms import PhotoForm

logger = logging.getLogger(__name__)
router = Router(name=__name__)


async def show_photos_screen(bot: Bot, chat_id: int, user_id: int, session: AsyncSession) -> None:
    repo = UserRepo(session)
    existing = await repo.list_user_photos(user_id)
    photo_map = {item.slot_number: item.telegram_file_id for item in existing}
    placeholder_path = str(photo_placeholder_path())

    for slot in range(1, 5):
        file_id = photo_map.get(slot)
        caption = f"Фото слот {slot}"
        if file_id:
            await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption, reply_markup=photo_slot_keyboard(slot))
        else:
            await bot.send_photo(
                chat_id=chat_id,
                photo=FSInputFile(path=placeholder_path),
                caption=caption,
                reply_markup=photo_slot_keyboard(slot),
            )

    await bot.send_message(chat_id=chat_id, text="Выберите слот для изменения.", reply_markup=photos_footer_keyboard())


@router.callback_query(CabinetCallback.filter(lambda c: c.action == "photos"))
async def open_photos(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(callback.from_user)

    await show_photos_screen(callback.bot, callback.message.chat.id, user.id, session)
    await callback.answer()


@router.callback_query(PhotoCallback.filter())
async def select_photo_slot(callback: CallbackQuery, callback_data: PhotoCallback, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return

    await state.set_state(PhotoForm.waiting_photo)
    await state.update_data(photo_slot=callback_data.slot)
    await callback.message.answer(f"Отправьте новое фото для слота {callback_data.slot}.")
    await callback.answer()


@router.message(PhotoForm.waiting_photo, F.photo)
async def save_photo(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None or not message.photo:
        return

    data = await state.get_data()
    slot = int(data.get("photo_slot", 1))

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(message.from_user)

    file_id = message.photo[-1].file_id
    repo = UserRepo(session)
    await repo.upsert_user_photo(user_id=user.id, slot_number=slot, telegram_file_id=file_id)

    await message.answer(f"Фото {slot} успешно обновлено.")
    await state.clear()
    await show_photos_screen(message.bot, message.chat.id, user.id, session)


@router.message(PhotoForm.waiting_photo)
async def photo_expected(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте фото для выбранного слота.")
