from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext

CABINET_BANNER_MESSAGE_KEY = "cabinet_banner_message_id"


def _is_not_modified_error(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def safe_delete_message(message: Message | None) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except TelegramBadRequest:
        return


async def edit_or_resend_callback_message(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    disable_web_page_preview: bool = True,
) -> Message | None:
    message = callback.message
    if message is None:
        return None

    try:
        if message.text is not None:
            await message.edit_text(
                text=text,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
            return message

        if message.caption is not None:
            await message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
            )
            return message
    except TelegramBadRequest as exc:
        if _is_not_modified_error(exc):
            return message

    await safe_delete_message(message)
    return await callback.bot.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_web_page_preview,
    )


async def replace_callback_message_with_new(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    disable_web_page_preview: bool = True,
) -> Message | None:
    message = callback.message
    if message is None:
        return None

    await safe_delete_message(message)
    return await callback.bot.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_web_page_preview,
    )


async def clear_state_messages(
    bot,
    state: FSMContext,
    chat_id: int,
    key: str,
    except_message_id: int | None = None,
) -> None:
    data = await state.get_data()
    ids = data.get(key, [])
    if not isinstance(ids, list):
        await state.update_data(**{key: []})
        return

    for raw_id in ids:
        try:
            message_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if except_message_id is not None and message_id == except_message_id:
            continue
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramBadRequest:
            continue

    await state.update_data(**{key: []})


async def store_state_messages(state: FSMContext, key: str, message_ids: list[int]) -> None:
    await state.update_data(**{key: message_ids})


async def clear_state_message_id(bot, state: FSMContext, chat_id: int, key: str) -> None:
    data = await state.get_data()
    raw_message_id = data.get(key)
    if raw_message_id is None:
        return
    try:
        message_id = int(raw_message_id)
    except (TypeError, ValueError):
        await state.update_data(**{key: None})
        return

    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        pass

    await state.update_data(**{key: None})


async def store_state_message_id(state: FSMContext, key: str, message_id: int | None) -> None:
    await state.update_data(**{key: message_id})
