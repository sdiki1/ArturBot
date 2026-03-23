from __future__ import annotations

from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import User
from app.db.repo.user_repo import UserRepo
from app.utils.misc import generate_referral_code


class ReferralService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.user_repo = UserRepo(session)

    @staticmethod
    def parse_referral_code(start_arg: str | None) -> str | None:
        if not start_arg:
            return None
        if start_arg.startswith("link_"):
            raw = start_arg.replace("link_", "", 1).strip()
            return raw or None
        return None

    async def _generate_unique_referral_code(self) -> str:
        while True:
            code = generate_referral_code()
            exists = await self.user_repo.get_by_referral_code(code)
            if exists is None:
                return code

    async def ensure_user(self, tg_user: TgUser, start_arg: str | None = None) -> tuple[User, bool]:
        user = await self.user_repo.get_by_telegram_id(tg_user.id)
        if user is not None:
            await self.user_repo.update_profile(
                user=user,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
            )
            return user, False

        inviter_user_id: int | None = None
        referral_code = self.parse_referral_code(start_arg)
        if referral_code:
            inviter = await self.user_repo.get_by_referral_code(referral_code)
            if inviter and inviter.telegram_id != tg_user.id:
                inviter_user_id = inviter.id

        new_code = await self._generate_unique_referral_code()
        user = await self.user_repo.create_user(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            referral_code=new_code,
            inviter_user_id=inviter_user_id,
        )
        return user, True

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.user_repo.get_by_telegram_id(telegram_id)

    async def get_inviter(self, user: User) -> User | None:
        if not user.inviter_user_id:
            return None
        return await self.user_repo.get_by_id(user.inviter_user_id)

    async def get_mentor_identity(self, user: User) -> tuple[str, str]:
        inviter = await self.get_inviter(user)
        if inviter:
            mentor_name = " ".join(part for part in [inviter.first_name, inviter.last_name] if part).strip() or (
                inviter.username or self.settings.default_mentor_name
            )
            mentor_username = inviter.username or self.settings.default_mentor_username
            return mentor_name, mentor_username
        return self.settings.default_mentor_name, self.settings.default_mentor_username

    def build_referral_link(self, referral_code: str) -> str:
        return f"https://t.me/{self.settings.bot_username}?start=link_{referral_code}"
