"""add app texts

Revision ID: 20260325_0003
Revises: 20260323_0002
Create Date: 2026-03-25 02:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260325_0003"
down_revision: Union[str, None] = "20260323_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_texts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_app_texts_key"), "app_texts", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_app_texts_key"), table_name="app_texts")
    op.drop_table("app_texts")
