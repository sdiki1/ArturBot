from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Enum as SqlaEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PaymentStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    expired = "expired"


class BroadcastContentType(str, Enum):
    text = "text"
    text_photo = "text_photo"
    text_video = "text_video"


class BroadcastStatus(str, Enum):
    draft = "draft"
    sending = "sending"
    done = "done"
    failed = "failed"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    inviter_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    referral_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    inviter: Mapped[User | None] = relationship("User", remote_side=[id], back_populates="invitees")
    invitees: Mapped[list[User]] = relationship("User", back_populates="inviter")

    photos: Mapped[list[UserPhoto]] = relationship("UserPhoto", back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="user")
    broadcasts: Mapped[list[Broadcast]] = relationship("Broadcast", back_populates="user")


class UserPhoto(Base, TimestampMixin):
    __tablename__ = "user_photos"
    __table_args__ = (
        UniqueConstraint("user_id", "slot_number", name="uq_user_photos_user_id_slot_number"),
        CheckConstraint("slot_number >= 1 AND slot_number <= 4", name="slot_number_between_1_and_4"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    slot_number: Mapped[int] = mapped_column(Integer)
    telegram_file_id: Mapped[str] = mapped_column(Text)

    user: Mapped[User] = relationship("User", back_populates="photos")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    provider: Mapped[str] = mapped_column(String(50))
    external_payment_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    status: Mapped[PaymentStatus] = mapped_column(SqlaEnum(PaymentStatus), default=PaymentStatus.pending)
    payment_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="payments")


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content_type: Mapped[BroadcastContentType] = mapped_column(SqlaEnum(BroadcastContentType))
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[BroadcastStatus] = mapped_column(SqlaEnum(BroadcastStatus), default=BroadcastStatus.draft)
    total_recipients: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="broadcasts")
    logs: Mapped[list[BroadcastLog]] = relationship("BroadcastLog", back_populates="broadcast", cascade="all, delete-orphan")


class BroadcastLog(Base):
    __tablename__ = "broadcast_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    broadcast_id: Mapped[int] = mapped_column(ForeignKey("broadcasts.id", ondelete="CASCADE"), index=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    broadcast: Mapped[Broadcast] = relationship("Broadcast", back_populates="logs")
