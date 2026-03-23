from __future__ import annotations

from collections.abc import Iterable

from app.db.models import User


def user_display_name(user: User) -> str:
    full_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    if full_name:
        return full_name
    if user.username:
        return user.username
    return str(user.telegram_id)


def subscriber_line(user: User) -> str:
    name = user_display_name(user)
    if user.username:
        return f"- {name} @{user.username}"
    return f"- {name}"


def split_text_by_limit(lines: Iterable[str], limit: int = 3500) -> list[str]:
    chunks: list[str] = []
    buffer = ""
    for line in lines:
        candidate = f"{buffer}\n{line}".strip()
        if len(candidate) > limit and buffer:
            chunks.append(buffer)
            buffer = line
        else:
            buffer = candidate
    if buffer:
        chunks.append(buffer)
    return chunks
