from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class CabinetCallback(CallbackData, prefix="cab"):
    action: str


class PhotoCallback(CallbackData, prefix="photo"):
    slot: int


class BroadcastStartCallback(CallbackData, prefix="brs"):
    action: str


class BroadcastTypeCallback(CallbackData, prefix="brt"):
    content_type: str


class BroadcastConfirmCallback(CallbackData, prefix="brc"):
    action: str


def go_to_menu_keyboard(chat_url: str | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if chat_url:
        builder.button(text="Перейти в чат", url=chat_url)
    else:
        builder.button(text="Перейти в чат", callback_data=CabinetCallback(action="chat_not_set"))
    return builder.as_markup()


def cabinet_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Моя подписка", callback_data=CabinetCallback(action="subscription"))
    builder.button(text="🔗 Моя реф.ссылка", callback_data=CabinetCallback(action="referral"))
    builder.button(text="📷 Изменить фото", callback_data=CabinetCallback(action="photos"))
    builder.button(text="🔗 Добавьте свою ссылку", callback_data=CabinetCallback(action="link"))
    builder.button(text="ℹ️ Добавить информацию о себе", callback_data=CabinetCallback(action="bio"))
    builder.button(text="🙋‍♂️ Мои подписчики", callback_data=CabinetCallback(action="subscribers"))
    builder.button(text="💌 Рассылка подписчикам", callback_data=CabinetCallback(action="broadcast"))
    builder.adjust(1)
    return builder.as_markup()


def subscription_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="♻️ Продлить подписку (+30 дней)", callback_data=CabinetCallback(action="renew_subscription"))
    builder.button(text="← Назад в Личный кабинет", callback_data=CabinetCallback(action="open"))
    builder.adjust(1)
    return builder.as_markup()


def single_back_to_cabinet_keyboard(label: str = "Назад в Личный кабинет") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=label, callback_data=CabinetCallback(action="open"))
    return builder.as_markup()


def photo_slot_keyboard(slot_number: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Изменить мое фото {slot_number}", callback_data=PhotoCallback(slot=slot_number))
    return builder.as_markup()


def photos_footer_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Назад в Личный кабинет", callback_data=CabinetCallback(action="open"))
    return builder.as_markup()


def broadcast_start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=BroadcastStartCallback(action="yes"))
    builder.button(text="❌ Нет", callback_data=BroadcastStartCallback(action="no"))
    builder.button(text="⬅️ Назад в Личный Кабинет", callback_data=CabinetCallback(action="open"))
    builder.adjust(2, 1)
    return builder.as_markup()


def broadcast_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Текст 📝", callback_data=BroadcastTypeCallback(content_type="text"))
    builder.button(text="Текст + картинка 📝🖼️", callback_data=BroadcastTypeCallback(content_type="text_photo"))
    builder.button(text="Текст + Видео 📝🎥", callback_data=BroadcastTypeCallback(content_type="text_video"))
    builder.button(text="⬅️ Назад в Личный кабинет", callback_data=CabinetCallback(action="open"))
    builder.adjust(1)
    return builder.as_markup()


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data=BroadcastConfirmCallback(action="send"))
    builder.button(text="✏️ Изменить", callback_data=BroadcastConfirmCallback(action="edit"))
    builder.button(text="❌ Отмена", callback_data=BroadcastConfirmCallback(action="cancel"))
    builder.adjust(1)
    return builder.as_markup()
