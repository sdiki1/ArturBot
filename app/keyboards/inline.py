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


class AdminCallback(CallbackData, prefix="adm"):
    action: str


def go_to_menu_keyboard(chat_url: str | None = None, label: str = "Перейти в чат") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if chat_url:
        builder.button(text=label, url=chat_url)
    else:
        builder.button(text=label, callback_data=CabinetCallback(action="chat_not_set"))
    return builder.as_markup()


def cabinet_keyboard(
    subscription_label: str = "📅 Моя подписка",
    referral_label: str = "🔗 Моя реф.ссылка",
    photos_label: str = "📷 Изменить фото",
    bio_label: str = "ℹ️ Добавить информацию о себе",
    subscribers_label: str = "🙋‍♂️ Мои подписчики",
    broadcast_label: str = "💌 Рассылка подписчикам",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=subscription_label, callback_data=CabinetCallback(action="subscription"))
    builder.button(text=referral_label, callback_data=CabinetCallback(action="referral"))
    builder.button(text=photos_label, callback_data=CabinetCallback(action="photos"))
    builder.button(text=bio_label, callback_data=CabinetCallback(action="bio"))
    builder.button(text=subscribers_label, callback_data=CabinetCallback(action="subscribers"))
    builder.button(text=broadcast_label, callback_data=CabinetCallback(action="broadcast"))
    builder.adjust(1)
    return builder.as_markup()


def subscription_keyboard(
    renew_label: str = "♻️ Продлить подписку (+30 дней)",
    back_label: str = "← Назад в Личный кабинет",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=renew_label, callback_data=CabinetCallback(action="renew_subscription"))
    builder.button(text=back_label, callback_data=CabinetCallback(action="open"))
    builder.adjust(1)
    return builder.as_markup()


def single_back_to_cabinet_keyboard(label: str = "Назад в Личный кабинет") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=label, callback_data=CabinetCallback(action="open"))
    return builder.as_markup()


def photo_slot_keyboard(slot_number: int, label_template: str = "Изменить мое фото {slot}") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    try:
        label = label_template.format(slot=slot_number)
    except Exception:
        label = f"Изменить мое фото {slot_number}"
    builder.button(text=label, callback_data=PhotoCallback(slot=slot_number))
    return builder.as_markup()


def photos_footer_keyboard(back_label: str = "Назад в Личный кабинет") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=back_label, callback_data=CabinetCallback(action="open"))
    return builder.as_markup()


def broadcast_start_keyboard(
    yes_label: str = "✅ Да",
    no_label: str = "❌ Нет",
    back_label: str = "⬅️ Назад в Личный Кабинет",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=yes_label, callback_data=BroadcastStartCallback(action="yes"))
    builder.button(text=no_label, callback_data=BroadcastStartCallback(action="no"))
    builder.button(text=back_label, callback_data=CabinetCallback(action="open"))
    builder.adjust(2, 1)
    return builder.as_markup()


def broadcast_type_keyboard(
    text_label: str = "Текст 📝",
    text_photo_label: str = "Текст + картинка 📝🖼️",
    text_video_label: str = "Текст + Видео 📝🎥",
    back_label: str = "⬅️ Назад в Личный кабинет",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=text_label, callback_data=BroadcastTypeCallback(content_type="text"))
    builder.button(text=text_photo_label, callback_data=BroadcastTypeCallback(content_type="text_photo"))
    builder.button(text=text_video_label, callback_data=BroadcastTypeCallback(content_type="text_video"))
    builder.button(text=back_label, callback_data=CabinetCallback(action="open"))
    builder.adjust(1)
    return builder.as_markup()


def broadcast_confirm_keyboard(
    send_label: str = "✅ Отправить",
    edit_label: str = "✏️ Изменить",
    cancel_label: str = "❌ Отмена",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=send_label, callback_data=BroadcastConfirmCallback(action="send"))
    builder.button(text=edit_label, callback_data=BroadcastConfirmCallback(action="edit"))
    builder.button(text=cancel_label, callback_data=BroadcastConfirmCallback(action="cancel"))
    builder.adjust(1)
    return builder.as_markup()


def admin_main_keyboard(
    stats_label: str = "📊 Статистика",
    users_label: str = "👥 Пользователи",
    payments_label: str = "💳 Платежи",
    refresh_label: str = "🔄 Обновить",
    to_cabinet_label: str = "⬅️ В Личный кабинет",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=stats_label, callback_data=AdminCallback(action="stats"))
    builder.button(text=users_label, callback_data=AdminCallback(action="users"))
    builder.button(text=payments_label, callback_data=AdminCallback(action="payments"))
    builder.button(text=refresh_label, callback_data=AdminCallback(action="open"))
    builder.button(text=to_cabinet_label, callback_data=CabinetCallback(action="open"))
    builder.adjust(2, 2, 1)
    return builder.as_markup()
