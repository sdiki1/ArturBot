from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Broadcast, BroadcastContentType, BroadcastLog, BroadcastStatus


class BroadcastRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        content_type: BroadcastContentType,
        text: str | None,
        photo_file_id: str | None,
        video_file_id: str | None,
    ) -> Broadcast:
        item = Broadcast(
            user_id=user_id,
            content_type=content_type,
            text=text,
            photo_file_id=photo_file_id,
            video_file_id=video_file_id,
            status=BroadcastStatus.draft,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def set_sending(self, item: Broadcast, total_recipients: int) -> Broadcast:
        item.status = BroadcastStatus.sending
        item.total_recipients = total_recipients
        await self.session.flush()
        return item

    async def finish(self, item: Broadcast, success_count: int, fail_count: int, failed: bool = False) -> Broadcast:
        item.status = BroadcastStatus.failed if failed else BroadcastStatus.done
        item.success_count = success_count
        item.fail_count = fail_count
        item.finished_at = datetime.now(timezone.utc)
        await self.session.flush()
        return item

    async def add_log(
        self,
        broadcast_id: int,
        recipient_user_id: int,
        status: str,
        error_text: str | None = None,
        sent_at: datetime | None = None,
    ) -> BroadcastLog:
        log = BroadcastLog(
            broadcast_id=broadcast_id,
            recipient_user_id=recipient_user_id,
            status=status,
            error_text=error_text,
            sent_at=sent_at,
        )
        self.session.add(log)
        await self.session.flush()
        return log
