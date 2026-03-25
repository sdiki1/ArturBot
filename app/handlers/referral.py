from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.inline import CabinetCallback, single_back_to_cabinet_keyboard
from app.services.referrals import ReferralService
from app.services.texts import TextService
from app.utils.text import user_display_name
from app.utils.ui import CABINET_BANNER_MESSAGE_KEY, clear_state_message_id, edit_or_resend_callback_message

router = Router(name=__name__)


@router.callback_query(CabinetCallback.filter(F.action == "referral"))
async def referral_link_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    text_service = TextService(session)
    user, _ = await referral_service.ensure_user(callback.from_user)
    link = referral_service.build_referral_link(user.referral_code)

    text = await text_service.render("referral.my_link", link=link)
    back_label = await text_service.resolve("kb.back_to_cabinet")
    await edit_or_resend_callback_message(
        callback,
        text,
        reply_markup=single_back_to_cabinet_keyboard(back_label),
    )
    await callback.answer()


@router.message(Command("priglasil"))
async def who_invited_handler(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    settings = get_settings()
    referral_service = ReferralService(session, settings)
    text_service = TextService(session)
    user, _ = await referral_service.ensure_user(message.from_user)
    inviter = await referral_service.get_inviter(user)

    if inviter is None:
        self_name = user_display_name(user)
        self_username = f"@{user.username}" if user.username else ""
        text = await text_service.render(
            "referral.no_inviter_self",
            self_name=self_name,
            self_username_line=f"\n{self_username}" if self_username else "",
        )
        await message.answer(text)
        return

    inviter_name = user_display_name(inviter)
    inviter_username = f"@{inviter.username}" if inviter.username else ""
    text = await text_service.render(
        "referral.invited_by",
        inviter_name=inviter_name,
        inviter_username_line=f"\n{inviter_username}" if inviter_username else "",
    )
    await message.answer(text)
