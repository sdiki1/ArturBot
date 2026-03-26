from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserPhoto


class UserRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_referral_code(self, referral_code: str) -> User | None:
        result = await self.session.execute(select(User).where(User.referral_code == referral_code))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        referral_code: str,
        inviter_user_id: int | None = None,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            referral_code=referral_code,
            inviter_user_id=inviter_user_id,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_profile(self, user: User, username: str | None, first_name: str | None, last_name: str | None) -> User:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        await self.session.flush()
        return user

    async def set_external_link(self, user: User, link: str) -> None:
        user.external_link = link
        await self.session.flush()

    async def set_bio(self, user: User, bio: str) -> None:
        user.bio = bio
        await self.session.flush()

    async def list_subscribers(self, inviter_user_id: int) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.inviter_user_id == inviter_user_id).order_by(User.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_all_users(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.created_at.asc()))
        return list(result.scalars().all())

    async def count_subscribers(self, inviter_user_id: int) -> int:
        result = await self.session.execute(select(func.count(User.id)).where(User.inviter_user_id == inviter_user_id))
        return int(result.scalar_one())

    async def get_user_photo(self, user_id: int, slot_number: int) -> UserPhoto | None:
        result = await self.session.execute(
            select(UserPhoto).where(UserPhoto.user_id == user_id, UserPhoto.slot_number == slot_number)
        )
        return result.scalar_one_or_none()

    async def list_user_photos(self, user_id: int) -> list[UserPhoto]:
        result = await self.session.execute(select(UserPhoto).where(UserPhoto.user_id == user_id).order_by(UserPhoto.slot_number))
        return list(result.scalars().all())

    async def upsert_user_photo(self, user_id: int, slot_number: int, telegram_file_id: str) -> UserPhoto:
        slot_number = 1
        photo = await self.get_user_photo(user_id=user_id, slot_number=slot_number)
        if photo is None:
            photo = UserPhoto(user_id=user_id, slot_number=slot_number, telegram_file_id=telegram_file_id)
            self.session.add(photo)
        else:
            photo.telegram_file_id = telegram_file_id
        await self.session.flush()
        return photo
