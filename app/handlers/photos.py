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
from app.services.texts import TextService
from app.states.forms import PhotoForm
from app.utils.ui import (
    CABINET_BANNER_MESSAGE_KEY,
    clear_state_message_id,
    clear_state_messages,
    safe_delete_message,
    store_state_messages,
)

logger = logging.getLogger(__name__)
router = Router(name=__name__)
PHOTOS_SCREEN_MESSAGES_KEY = "photos_screen_message_ids"


async def show_photos_screen(bot: Bot, chat_id: int, user_id: int, session: AsyncSession, state: FSMContext) -> None:
    await clear_state_messages(bot=bot, state=state, chat_id=chat_id, key=PHOTOS_SCREEN_MESSAGES_KEY)

    repo = UserRepo(session)
    text_service = TextService(session)
    labels = await text_service.resolve_many(
        [
            "photos.slot_caption",
            "photos.choose_slot",
            "kb.photo_change_template",
            "kb.back_to_cabinet",
        ]
    )
    existing = await repo.list_user_photos(user_id)
    photo_map = {item.slot_number: item.telegram_file_id for item in existing}
    placeholder_path = str(photo_placeholder_path())
    message_ids: list[int] = []

    for slot in range(1, 5):
        file_id = photo_map.get(slot)
        caption = labels["photos.slot_caption"].format(slot=slot)
        if file_id:
            sent = await bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=caption,
                reply_markup=photo_slot_keyboard(slot, label_template=labels["kb.photo_change_template"]),
            )
        else:
            sent = await bot.send_photo(
                chat_id=chat_id,
                photo=FSInputFile(path=placeholder_path),
                caption=caption,
                reply_markup=photo_slot_keyboard(slot, label_template=labels["kb.photo_change_template"]),
            )
        message_ids.append(sent.message_id)

    footer = await bot.send_message(
        chat_id=chat_id,
        text=labels["photos.choose_slot"],
        reply_markup=photos_footer_keyboard(back_label=labels["kb.back_to_cabinet"]),
    )
    message_ids.append(footer.message_id)
    await store_state_messages(state, PHOTOS_SCREEN_MESSAGES_KEY, message_ids)


@router.callback_query(CabinetCallback.filter(F.action == "photos"))
async def open_photos(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    user, _ = await referral_service.ensure_user(callback.from_user)
    await clear_state_message_id(
        bot=callback.bot,
        state=state,
        chat_id=callback.message.chat.id,
        key=CABINET_BANNER_MESSAGE_KEY,
    )

    await safe_delete_message(callback.message)
    await show_photos_screen(callback.bot, callback.message.chat.id, user.id, session, state)
    await callback.answer()


@router.callback_query(PhotoCallback.filter())
async def select_photo_slot(callback: CallbackQuery, callback_data: PhotoCallback, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return

    text_service = TextService(state.storage.proxy.session) if False else None
    await clear_state_messages(
        bot=callback.bot,
        state=state,
        chat_id=callback.message.chat.id,
        key=PHOTOS_SCREEN_MESSAGES_KEY,
        except_message_id=callback.message.message_id,
    )
    await safe_delete_message(callback.message)
    await state.set_state(PhotoForm.waiting_photo)
    await state.update_data(photo_slot=callback_data.slot)
    # session is unavailable in callback-only stage, fetch text via bot-independent default template from service map
    ask_text = TextService.DEFAULTS_PLACEHOLDER if False else None
    await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text=f"Отправьте новое фото для слота {callback_data.slot}.",
    )
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

    text_service = TextService(session)
    await message.answer(await text_service.render("photos.updated", slot=slot))
    await state.clear()
    await show_photos_screen(message.bot, message.chat.id, user.id, session, state)


@router.message(PhotoForm.waiting_photo)
async def photo_expected(message: Message, session: AsyncSession) -> None:
    text_service = TextService(session)
    await message.answer(await text_service.resolve("photos.expected_photo"))
