from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppText


class TextRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_key(self, key: str) -> AppText | None:
        result = await self.session.execute(select(AppText).where(AppText.key == key))
        return result.scalar_one_or_none()

    async def get_many(self, keys: list[str]) -> dict[str, AppText]:
        if not keys:
            return {}
        result = await self.session.execute(select(AppText).where(AppText.key.in_(keys)))
        rows = list(result.scalars().all())
        return {row.key: row for row in rows}

    async def list_all(self) -> list[AppText]:
        result = await self.session.execute(select(AppText).order_by(AppText.key.asc()))
        return list(result.scalars().all())

    async def upsert(self, key: str, value: str) -> AppText:
        row = await self.get_by_key(key)
        if row is None:
            row = AppText(key=key, value=value)
            self.session.add(row)
        else:
            row.value = value
        await self.session.flush()
        return row

    async def delete_by_key(self, key: str) -> None:
        row = await self.get_by_key(key)
        if row is None:
            return
        await self.session.delete(row)
        await self.session.flush()
