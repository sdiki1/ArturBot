"""fix user photos unique constraint

Revision ID: 20260325_0004
Revises: 20260325_0003
Create Date: 2026-03-25 20:05:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260325_0004"
down_revision: Union[str, None] = "20260325_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop legacy unique constraints/indexes on user_id if they are present.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_user_photos_user_id'
                  AND conrelid = 'user_photos'::regclass
            ) THEN
                ALTER TABLE user_photos DROP CONSTRAINT uq_user_photos_user_id;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'user_photos_user_id_key'
                  AND conrelid = 'user_photos'::regclass
            ) THEN
                ALTER TABLE user_photos DROP CONSTRAINT user_photos_user_id_key;
            END IF;
        END
        $$;
        """
    )

    op.execute("DROP INDEX IF EXISTS uq_user_photos_user_id;")
    op.execute("DROP INDEX IF EXISTS user_photos_user_id_key;")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_user_photos_user_id_slot_number'
                  AND conrelid = 'user_photos'::regclass
            ) THEN
                ALTER TABLE user_photos
                ADD CONSTRAINT uq_user_photos_user_id_slot_number UNIQUE (user_id, slot_number);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_user_photos_user_id_slot_number'
                  AND conrelid = 'user_photos'::regclass
            ) THEN
                ALTER TABLE user_photos DROP CONSTRAINT uq_user_photos_user_id_slot_number;
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_user_photos_user_id'
                  AND conrelid = 'user_photos'::regclass
            ) THEN
                ALTER TABLE user_photos
                ADD CONSTRAINT uq_user_photos_user_id UNIQUE (user_id);
            END IF;
        END
        $$;
        """
    )
