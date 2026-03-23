"""initial

Revision ID: 20260323_0001
Revises:
Create Date: 2026-03-23 21:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260323_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

payment_status_enum = sa.Enum("pending", "paid", "failed", "expired", name="paymentstatus")
broadcast_content_type_enum = sa.Enum("text", "text_photo", "text_video", name="broadcastcontenttype")
broadcast_status_enum = sa.Enum("draft", "sending", "done", "failed", name="broadcaststatus")


def upgrade() -> None:
    payment_status_enum.create(op.get_bind(), checkfirst=True)
    broadcast_content_type_enum.create(op.get_bind(), checkfirst=True)
    broadcast_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("inviter_user_id", sa.Integer(), nullable=True),
        sa.Column("referral_code", sa.String(length=64), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("external_link", sa.String(length=1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referral_code"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"], unique=True)
    op.create_index(op.f("ix_users_referral_code"), "users", ["referral_code"], unique=True)

    op.create_table(
        "user_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("slot_number", sa.Integer(), nullable=False),
        sa.Column("telegram_file_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("slot_number >= 1 AND slot_number <= 4", name="slot_number_between_1_and_4"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "slot_number", name="uq_user_photos_user_id_slot_number"),
    )
    op.create_index(op.f("ix_user_photos_user_id"), "user_photos", ["user_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("external_payment_id", sa.String(length=128), nullable=False),
        sa.Column("status", payment_status_enum, nullable=False),
        sa.Column("payment_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_payment_id"),
    )
    op.create_index(op.f("ix_payments_external_payment_id"), "payments", ["external_payment_id"], unique=True)
    op.create_index(op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False)

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content_type", broadcast_content_type_enum, nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("photo_file_id", sa.Text(), nullable=True),
        sa.Column("video_file_id", sa.Text(), nullable=True),
        sa.Column("status", broadcast_status_enum, nullable=False),
        sa.Column("total_recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_broadcasts_user_id"), "broadcasts", ["user_id"], unique=False)

    op.create_table(
        "broadcast_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("broadcast_id", sa.Integer(), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["broadcast_id"], ["broadcasts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_broadcast_logs_broadcast_id"), "broadcast_logs", ["broadcast_id"], unique=False)
    op.create_index(op.f("ix_broadcast_logs_recipient_user_id"), "broadcast_logs", ["recipient_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_broadcast_logs_recipient_user_id"), table_name="broadcast_logs")
    op.drop_index(op.f("ix_broadcast_logs_broadcast_id"), table_name="broadcast_logs")
    op.drop_table("broadcast_logs")

    op.drop_index(op.f("ix_broadcasts_user_id"), table_name="broadcasts")
    op.drop_table("broadcasts")

    op.drop_index(op.f("ix_payments_user_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_external_payment_id"), table_name="payments")
    op.drop_table("payments")

    op.drop_index(op.f("ix_user_photos_user_id"), table_name="user_photos")
    op.drop_table("user_photos")

    op.drop_index(op.f("ix_users_referral_code"), table_name="users")
    op.drop_index(op.f("ix_users_telegram_id"), table_name="users")
    op.drop_table("users")

    broadcast_status_enum.drop(op.get_bind(), checkfirst=True)
    broadcast_content_type_enum.drop(op.get_bind(), checkfirst=True)
    payment_status_enum.drop(op.get_bind(), checkfirst=True)
