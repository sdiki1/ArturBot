from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BroadcastContentType, User
from app.db.repo.broadcast_repo import BroadcastRepo
from app.db.repo.user_repo import UserRepo

logger = logging.getLogger(__name__)


class BroadcastService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.broadcast_repo = BroadcastRepo(session)
        self.user_repo = UserRepo(session)

    async def send_broadcast(
        self,
        bot: Bot,
        sender_user: User,
        content_type: BroadcastContentType,
        text: str | None,
        photo_file_id: str | None,
        video_file_id: str | None,
        recipients: list[User] | None = None,
    ) -> tuple[int, int, int]:
        target_recipients = recipients if recipients is not None else await self.user_repo.list_all_users()
        total = len(target_recipients)

        broadcast = await self.broadcast_repo.create(
            user_id=sender_user.id,
            content_type=content_type,
            text=text,
            photo_file_id=photo_file_id,
            video_file_id=video_file_id,
        )
        await self.broadcast_repo.set_sending(broadcast, total_recipients=total)

        success_count = 0
        fail_count = 0
        for recipient in target_recipients:
            try:
                if content_type == BroadcastContentType.text:
                    await bot.send_message(chat_id=recipient.telegram_id, text=text or "")
                elif content_type == BroadcastContentType.text_photo:
                    await bot.send_photo(chat_id=recipient.telegram_id, photo=photo_file_id or "", caption=text or "")
                elif content_type == BroadcastContentType.text_video:
                    await bot.send_video(chat_id=recipient.telegram_id, video=video_file_id or "", caption=text or "")

                success_count += 1
                await self.broadcast_repo.add_log(
                    broadcast_id=broadcast.id,
                    recipient_user_id=recipient.id,
                    status="sent",
                    sent_at=datetime.now(timezone.utc),
                )
            except TelegramAPIError as exc:
                fail_count += 1
                await self.broadcast_repo.add_log(
                    broadcast_id=broadcast.id,
                    recipient_user_id=recipient.id,
                    status="failed",
                    error_text=str(exc),
                )
            except Exception as exc:
                fail_count += 1
                logger.exception("Unexpected error while broadcast")
                await self.broadcast_repo.add_log(
                    broadcast_id=broadcast.id,
                    recipient_user_id=recipient.id,
                    status="failed",
                    error_text=str(exc),
                )

        await self.broadcast_repo.finish(
            item=broadcast,
            success_count=success_count,
            fail_count=fail_count,
            failed=False,
        )
        await self.session.commit()
        return total, success_count, fail_count
