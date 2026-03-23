"""make timestamps timezone aware

Revision ID: 20260323_0002
Revises: 20260323_0001
Create Date: 2026-03-23 23:30:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260323_0002"
down_revision: Union[str, None] = "20260323_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _to_timestamptz(table_name: str, column_name: str) -> None:
    op.execute(
        f"""
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = '{table_name}'
          AND column_name = '{column_name}'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE TIMESTAMP WITH TIME ZONE USING {column_name} AT TIME ZONE ''UTC''';
    END IF;
END $$;
"""
    )


def _to_timestamp(table_name: str, column_name: str) -> None:
    op.execute(
        f"""
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = '{table_name}'
          AND column_name = '{column_name}'
          AND data_type = 'timestamp with time zone'
    ) THEN
        EXECUTE 'ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE TIMESTAMP WITHOUT TIME ZONE USING {column_name} AT TIME ZONE ''UTC''';
    END IF;
END $$;
"""
    )


def upgrade() -> None:
    for table_name, column_name in [
        ("users", "created_at"),
        ("users", "updated_at"),
        ("user_photos", "created_at"),
        ("user_photos", "updated_at"),
        ("payments", "created_at"),
        ("broadcasts", "created_at"),
    ]:
        _to_timestamptz(table_name, column_name)


def downgrade() -> None:
    for table_name, column_name in [
        ("broadcasts", "created_at"),
        ("payments", "created_at"),
        ("user_photos", "updated_at"),
        ("user_photos", "created_at"),
        ("users", "updated_at"),
        ("users", "created_at"),
    ]:
        _to_timestamp(table_name, column_name)
