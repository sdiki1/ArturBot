from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware

from app.db.session import SessionLocal


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        async with SessionLocal() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                if session.in_transaction():
                    await session.commit()
                return result
            except Exception:
                if session.in_transaction():
                    await session.rollback()
                raise
