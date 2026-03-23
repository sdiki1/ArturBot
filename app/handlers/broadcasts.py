from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import BroadcastContentType
from app.keyboards.inline import (
    BroadcastConfirmCallback,
    BroadcastStartCallback,
    BroadcastTypeCallback,
    CabinetCallback,
    broadcast_confirm_keyboard,
    broadcast_start_keyboard,
    broadcast_type_keyboard,
    single_back_to_cabinet_keyboard,
)
from app.services.broadcasts import BroadcastService
from app.services.referrals import ReferralService
from app.states.forms import BroadcastForm

router = Router(name=__name__)


@router.callback_query(CabinetCallback.filter(lambda c: c.action == "broadcast"))
async def broadcast_entry(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.answer(
            "Вы хотите отправить сообщение своим подписчикам?",
            reply_markup=broadcast_start_keyboard(),
        )
    await callback.answer()


@router.callback_query(BroadcastStartCallback.filter())
async def broadcast_start(callback: CallbackQuery, callback_data: BroadcastStartCallback, state: FSMContext) -> None:
    if callback_data.action == "no":
        await state.clear()
        if callback.message:
            await callback.message.answer(
                "Рассылка отменена.",
                reply_markup=single_back_to_cabinet_keyboard("⬅️ Назад в Личный кабинет"),
            )
        await callback.answer()
        return

    if callback.message:
        await callback.message.answer(
            "Выберите какой контент вы хотите отправить вашим подписчикам",
            reply_markup=broadcast_type_keyboard(),
        )
    await callback.answer()


@router.callback_query(BroadcastTypeCallback.filter())
async def choose_broadcast_type(callback: CallbackQuery, callback_data: BroadcastTypeCallback, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(content_type=callback_data.content_type)
    await state.set_state(BroadcastForm.waiting_text)
    if callback.message:
        await callback.message.answer("Отправьте текст сообщения для рассылки.")
    await callback.answer()


@router.message(BroadcastForm.waiting_text, F.text)
async def receive_broadcast_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    content_type = data.get("content_type")
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст не должен быть пустым. Отправьте текст сообщения.")
        return

    await state.update_data(text=text)

    if content_type == BroadcastContentType.text.value:
        await state.set_state(BroadcastForm.waiting_confirm)
        await message.answer(f"Предпросмотр:\n\n{text}", reply_markup=broadcast_confirm_keyboard())
        return

    if content_type == BroadcastContentType.text_photo.value:
        await state.set_state(BroadcastForm.waiting_photo)
        await message.answer("Отправьте картинку для рассылки.")
        return

    if content_type == BroadcastContentType.text_video.value:
        await state.set_state(BroadcastForm.waiting_video)
        await message.answer("Отправьте видео для рассылки.")
        return

    await state.clear()
    await message.answer("Не удалось определить тип рассылки. Начните заново.")


@router.message(BroadcastForm.waiting_text)
async def receive_broadcast_text_wrong_type(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте текст сообщения.")


@router.message(BroadcastForm.waiting_photo, F.photo)
async def receive_broadcast_photo(message: Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer("Пожалуйста, отправьте картинку.")
        return

    file_id = message.photo[-1].file_id
    data = await state.get_data()
    text = data.get("text", "")

    await state.update_data(photo_file_id=file_id)
    await state.set_state(BroadcastForm.waiting_confirm)

    await message.answer_photo(photo=file_id, caption=str(text))
    await message.answer("Подтвердите отправку:", reply_markup=broadcast_confirm_keyboard())


@router.message(BroadcastForm.waiting_photo)
async def receive_broadcast_photo_wrong_type(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте изображение.")


@router.message(BroadcastForm.waiting_video, F.video)
async def receive_broadcast_video(message: Message, state: FSMContext) -> None:
    if not message.video:
        await message.answer("Пожалуйста, отправьте видео.")
        return

    file_id = message.video.file_id
    data = await state.get_data()
    text = data.get("text", "")

    await state.update_data(video_file_id=file_id)
    await state.set_state(BroadcastForm.waiting_confirm)

    await message.answer_video(video=file_id, caption=str(text))
    await message.answer("Подтвердите отправку:", reply_markup=broadcast_confirm_keyboard())


@router.message(BroadcastForm.waiting_video)
async def receive_broadcast_video_wrong_type(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте видеофайл.")


@router.callback_query(BroadcastConfirmCallback.filter(), BroadcastForm.waiting_confirm)
async def broadcast_confirm(
    callback: CallbackQuery,
    callback_data: BroadcastConfirmCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    action = callback_data.action

    if action == "cancel":
        await state.clear()
        if callback.message:
            await callback.message.answer(
                "Рассылка отменена.",
                reply_markup=single_back_to_cabinet_keyboard("⬅️ Назад в Личный кабинет"),
            )
        await callback.answer()
        return

    if action == "edit":
        await state.set_state(BroadcastForm.waiting_text)
        if callback.message:
            await callback.message.answer("Отправьте новый текст сообщения.")
        await callback.answer()
        return

    if callback.from_user is None:
        await callback.answer()
        return

    data = await state.get_data()
    content_type_raw = data.get("content_type")
    text = data.get("text")
    photo_file_id = data.get("photo_file_id")
    video_file_id = data.get("video_file_id")

    if not content_type_raw:
        await state.clear()
        if callback.message:
            await callback.message.answer("Не найден тип рассылки. Запустите сценарий заново.")
        await callback.answer()
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    sender_user, _ = await referral_service.ensure_user(callback.from_user)

    broadcast_service = BroadcastService(session)
    total, success, fail = await broadcast_service.send_broadcast(
        bot=callback.bot,
        sender_user=sender_user,
        content_type=BroadcastContentType(content_type_raw),
        text=text,
        photo_file_id=photo_file_id,
        video_file_id=video_file_id,
    )

    await state.clear()
    if callback.message:
        await callback.message.answer(
            "Рассылка завершена.\n\n"
            f"Всего получателей: {total}\n"
            f"Успешно: {success}\n"
            f"Ошибок: {fail}",
            reply_markup=single_back_to_cabinet_keyboard("⬅️ Назад в Личный кабинет"),
        )
    await callback.answer()
