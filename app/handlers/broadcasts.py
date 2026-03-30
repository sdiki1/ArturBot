from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import BroadcastContentType
from app.db.repo.user_repo import UserRepo
from app.keyboards.inline import (
    AdminCallback,
    BroadcastConfirmCallback,
    BroadcastStartCallback,
    BroadcastTypeCallback,
    CabinetCallback,
    broadcast_confirm_keyboard,
    broadcast_start_keyboard,
    broadcast_type_keyboard,
)
from app.services.broadcasts import BroadcastService
from app.services.referrals import ReferralService
from app.services.texts import TextService
from app.states.forms import BroadcastForm
from app.utils.ui import CABINET_BANNER_MESSAGE_KEY, clear_state_message_id, edit_or_resend_callback_message

router = Router(name=__name__)

BROADCAST_TARGET_KEY = "broadcast_target"
BROADCAST_TARGET_ALL = "all_users"
BROADCAST_TARGET_INVITEES = "invitees"


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in get_settings().admin_ids


def _normalize_broadcast_target(data: dict[str, object]) -> str | None:
    target_raw = data.get(BROADCAST_TARGET_KEY)
    if isinstance(target_raw, str) and target_raw in {BROADCAST_TARGET_ALL, BROADCAST_TARGET_INVITEES}:
        return target_raw

    legacy_admin_mode = data.get("admin_broadcast")
    if isinstance(legacy_admin_mode, bool):
        return BROADCAST_TARGET_ALL if legacy_admin_mode else BROADCAST_TARGET_INVITEES

    return None


def _is_allowed_sender(target: str, telegram_id: int) -> bool:
    if target == BROADCAST_TARGET_ALL:
        return _is_admin(telegram_id)
    return target == BROADCAST_TARGET_INVITEES


def _is_admin_mode(target: str) -> bool:
    return target == BROADCAST_TARGET_ALL


async def _resolve_message_context(
    message: Message,
    state: FSMContext,
) -> tuple[str, dict[str, object]] | None:
    if message.from_user is None:
        await state.clear()
        return None

    data = await state.get_data()
    target = _normalize_broadcast_target(data)
    if target is None or not _is_allowed_sender(target, message.from_user.id):
        await state.clear()
        return None

    return target, data


async def _single_back_markup(text_service: TextService, admin_mode: bool):
    label_key = "kb.back_to_admin" if admin_mode else "kb.back_to_cabinet_with_arrow_emoji"
    label = await text_service.resolve(label_key)
    builder = InlineKeyboardBuilder()
    builder.button(
        text=label,
        callback_data=AdminCallback(action="open").pack() if admin_mode else CabinetCallback(action="open").pack(),
    )
    return builder.as_markup()


async def _broadcast_start_markup(text_service: TextService, admin_mode: bool):
    labels = await text_service.resolve_many(["kb.broadcast_yes", "kb.broadcast_no"])
    back_label = await text_service.resolve("kb.back_to_admin" if admin_mode else "kb.back_to_cabinet_with_arrow_emoji_upper")
    return broadcast_start_keyboard(
        yes_label=labels["kb.broadcast_yes"],
        no_label=labels["kb.broadcast_no"],
        back_label=back_label,
        back_callback_data=AdminCallback(action="open").pack() if admin_mode else CabinetCallback(action="open").pack(),
    )


async def _broadcast_type_markup(text_service: TextService, admin_mode: bool):
    labels = await text_service.resolve_many(["kb.broadcast_text", "kb.broadcast_text_photo", "kb.broadcast_text_video"])
    back_label = await text_service.resolve("kb.back_to_admin" if admin_mode else "kb.back_to_cabinet_with_arrow_emoji")
    return broadcast_type_keyboard(
        text_label=labels["kb.broadcast_text"],
        text_photo_label=labels["kb.broadcast_text_photo"],
        text_video_label=labels["kb.broadcast_text_video"],
        back_label=back_label,
        back_callback_data=AdminCallback(action="open").pack() if admin_mode else CabinetCallback(action="open").pack(),
    )


async def _broadcast_confirm_markup(text_service: TextService):
    labels = await text_service.resolve_many(["kb.confirm_send", "kb.confirm_edit", "kb.confirm_cancel"])
    return broadcast_confirm_keyboard(
        send_label=labels["kb.confirm_send"],
        edit_label=labels["kb.confirm_edit"],
        cancel_label=labels["kb.confirm_cancel"],
    )


@router.callback_query(CabinetCallback.filter(F.action == "broadcast"))
async def broadcast_entry(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    text_service = TextService(session)
    if callback.from_user is None:
        await callback.answer()
        return

    if callback.message:
        await clear_state_message_id(
            bot=callback.bot,
            state=state,
            chat_id=callback.message.chat.id,
            key=CABINET_BANNER_MESSAGE_KEY,
        )
    await state.clear()
    await state.update_data(**{BROADCAST_TARGET_KEY: BROADCAST_TARGET_INVITEES})
    await edit_or_resend_callback_message(
        callback,
        await text_service.resolve("broadcast.entry_question_partners"),
        reply_markup=await _broadcast_start_markup(text_service, admin_mode=False),
    )
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "broadcast"))
async def admin_broadcast_entry(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    text_service = TextService(session)
    if callback.from_user is None or not _is_admin(callback.from_user.id):
        await callback.answer(await text_service.resolve("tg_admin.no_access_alert"), show_alert=True)
        return

    await state.clear()
    await state.update_data(**{BROADCAST_TARGET_KEY: BROADCAST_TARGET_ALL})
    await edit_or_resend_callback_message(
        callback,
        await text_service.resolve("broadcast.entry_question"),
        reply_markup=await _broadcast_start_markup(text_service, admin_mode=True),
    )
    await callback.answer()


@router.callback_query(BroadcastStartCallback.filter())
async def broadcast_start(
    callback: CallbackQuery,
    callback_data: BroadcastStartCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    text_service = TextService(session)
    if callback.from_user is None:
        await state.clear()
        await callback.answer()
        return

    data = await state.get_data()
    target = _normalize_broadcast_target(data)
    if target is None:
        await state.clear()
        await callback.answer(await text_service.resolve("broadcast.not_started"), show_alert=True)
        return
    if not _is_allowed_sender(target, callback.from_user.id):
        await state.clear()
        await callback.answer(await text_service.resolve("tg_admin.no_access_alert"), show_alert=True)
        return

    admin_mode = _is_admin_mode(target)

    if callback_data.action == "no":
        await state.clear()
        await edit_or_resend_callback_message(
            callback,
            await text_service.resolve("broadcast.cancelled"),
            reply_markup=await _single_back_markup(text_service, admin_mode),
        )
        await callback.answer()
        return

    choose_content_key = "broadcast.choose_content" if admin_mode else "broadcast.choose_content_partners"
    await edit_or_resend_callback_message(
        callback,
        await text_service.resolve(choose_content_key),
        reply_markup=await _broadcast_type_markup(text_service, admin_mode),
    )
    await callback.answer()


@router.callback_query(BroadcastTypeCallback.filter())
async def choose_broadcast_type(
    callback: CallbackQuery,
    callback_data: BroadcastTypeCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    text_service = TextService(session)
    if callback.from_user is None:
        await state.clear()
        await callback.answer()
        return

    data = await state.get_data()
    target = _normalize_broadcast_target(data)
    if target is None:
        await state.clear()
        await callback.answer(await text_service.resolve("broadcast.not_started"), show_alert=True)
        return
    if not _is_allowed_sender(target, callback.from_user.id):
        await state.clear()
        await callback.answer(await text_service.resolve("tg_admin.no_access_alert"), show_alert=True)
        return

    await state.clear()
    await state.update_data(content_type=callback_data.content_type, **{BROADCAST_TARGET_KEY: target})
    await state.set_state(BroadcastForm.waiting_text)
    await edit_or_resend_callback_message(callback, await text_service.resolve("broadcast.ask_text"))
    await callback.answer()


@router.message(BroadcastForm.waiting_text, F.text)
async def receive_broadcast_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    context = await _resolve_message_context(message, state)
    if context is None:
        return

    _, data = context
    text_service = TextService(session)
    content_type = data.get("content_type")
    text = (message.text or "").strip()
    if not text:
        await message.answer(await text_service.resolve("broadcast.text_empty"))
        return

    await state.update_data(text=text)

    if content_type == BroadcastContentType.text.value:
        await state.set_state(BroadcastForm.waiting_confirm)
        await message.answer(
            await text_service.render("broadcast.preview", text=text),
            reply_markup=await _broadcast_confirm_markup(text_service),
        )
        return

    if content_type == BroadcastContentType.text_photo.value:
        await state.set_state(BroadcastForm.waiting_photo)
        await message.answer(await text_service.resolve("broadcast.ask_photo"))
        return

    if content_type == BroadcastContentType.text_video.value:
        await state.set_state(BroadcastForm.waiting_video)
        await message.answer(await text_service.resolve("broadcast.ask_video"))
        return

    await state.clear()
    await message.answer(await text_service.resolve("broadcast.unknown_type"))


@router.message(BroadcastForm.waiting_text)
async def receive_broadcast_text_wrong_type(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if await _resolve_message_context(message, state) is None:
        return

    text_service = TextService(session)
    await message.answer(await text_service.resolve("broadcast.expect_text"))


@router.message(BroadcastForm.waiting_photo, F.photo)
async def receive_broadcast_photo(message: Message, state: FSMContext, session: AsyncSession) -> None:
    context = await _resolve_message_context(message, state)
    if context is None:
        return

    _, data = context
    text_service = TextService(session)
    if not message.photo:
        await message.answer(await text_service.resolve("broadcast.expect_photo"))
        return

    file_id = message.photo[-1].file_id
    text = data.get("text", "")

    await state.update_data(photo_file_id=file_id)
    await state.set_state(BroadcastForm.waiting_confirm)

    await message.answer_photo(photo=file_id, caption=str(text))
    await message.answer(
        await text_service.resolve("broadcast.confirm_send"),
        reply_markup=await _broadcast_confirm_markup(text_service),
    )


@router.message(BroadcastForm.waiting_photo)
async def receive_broadcast_photo_wrong_type(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if await _resolve_message_context(message, state) is None:
        return

    text_service = TextService(session)
    await message.answer(await text_service.resolve("broadcast.expect_image"))


@router.message(BroadcastForm.waiting_video, F.video)
async def receive_broadcast_video(message: Message, state: FSMContext, session: AsyncSession) -> None:
    context = await _resolve_message_context(message, state)
    if context is None:
        return

    _, data = context
    text_service = TextService(session)
    if not message.video:
        await message.answer(await text_service.resolve("broadcast.expect_video"))
        return

    file_id = message.video.file_id
    text = data.get("text", "")

    await state.update_data(video_file_id=file_id)
    await state.set_state(BroadcastForm.waiting_confirm)

    await message.answer_video(video=file_id, caption=str(text))
    await message.answer(
        await text_service.resolve("broadcast.confirm_send"),
        reply_markup=await _broadcast_confirm_markup(text_service),
    )


@router.message(BroadcastForm.waiting_video)
async def receive_broadcast_video_wrong_type(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if await _resolve_message_context(message, state) is None:
        return

    text_service = TextService(session)
    await message.answer(await text_service.resolve("broadcast.expect_video_file"))


@router.callback_query(BroadcastConfirmCallback.filter(), BroadcastForm.waiting_confirm)
async def broadcast_confirm(
    callback: CallbackQuery,
    callback_data: BroadcastConfirmCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    text_service = TextService(session)
    if callback.from_user is None:
        await state.clear()
        await callback.answer()
        return

    data = await state.get_data()
    target = _normalize_broadcast_target(data)
    if target is None:
        await state.clear()
        await callback.answer(await text_service.resolve("broadcast.not_started"), show_alert=True)
        return
    if not _is_allowed_sender(target, callback.from_user.id):
        await state.clear()
        await callback.answer(await text_service.resolve("tg_admin.no_access_alert"), show_alert=True)
        return

    admin_mode = _is_admin_mode(target)
    action = callback_data.action

    if action == "cancel":
        await state.clear()
        await edit_or_resend_callback_message(
            callback,
            await text_service.resolve("broadcast.cancelled"),
            reply_markup=await _single_back_markup(text_service, admin_mode),
        )
        await callback.answer()
        return

    if action == "edit":
        await state.set_state(BroadcastForm.waiting_text)
        await edit_or_resend_callback_message(callback, await text_service.resolve("broadcast.ask_new_text"))
        await callback.answer()
        return

    content_type_raw = data.get("content_type")
    text = data.get("text")
    photo_file_id = data.get("photo_file_id")
    video_file_id = data.get("video_file_id")

    if not isinstance(content_type_raw, str):
        await state.clear()
        await edit_or_resend_callback_message(callback, await text_service.resolve("broadcast.type_not_found"))
        await callback.answer()
        return

    try:
        content_type = BroadcastContentType(content_type_raw)
    except ValueError:
        await state.clear()
        await edit_or_resend_callback_message(callback, await text_service.resolve("broadcast.type_not_found"))
        await callback.answer()
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    sender_user, _ = await referral_service.ensure_user(callback.from_user)

    recipients = None
    done_key = "broadcast.done"
    if target == BROADCAST_TARGET_INVITEES:
        recipients = await UserRepo(session).list_subscribers(sender_user.id)
        if not recipients:
            await state.clear()
            await edit_or_resend_callback_message(
                callback,
                await text_service.resolve("broadcast.no_partners"),
                reply_markup=await _single_back_markup(text_service, admin_mode=False),
            )
            await callback.answer()
            return
        done_key = "broadcast.done_partners"

    broadcast_service = BroadcastService(session)
    total, success, fail = await broadcast_service.send_broadcast(
        bot=callback.bot,
        sender_user=sender_user,
        content_type=content_type,
        text=text if isinstance(text, str) else None,
        photo_file_id=photo_file_id if isinstance(photo_file_id, str) else None,
        video_file_id=video_file_id if isinstance(video_file_id, str) else None,
        recipients=recipients,
    )

    await state.clear()
    await edit_or_resend_callback_message(
        callback,
        await text_service.render(done_key, total=total, success=success, fail=fail),
        reply_markup=await _single_back_markup(text_service, admin_mode),
    )
    await callback.answer()
