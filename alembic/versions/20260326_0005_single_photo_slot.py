"""enforce single photo slot per user

Revision ID: 20260326_0005
Revises: 20260325_0004
Create Date: 2026-03-26 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260326_0005"
down_revision: Union[str, None] = "20260325_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep only one photo per user (prefer slot 1, then newest row), then normalize to slot 1.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id
                    ORDER BY
                        CASE WHEN slot_number = 1 THEN 0 ELSE 1 END,
                        updated_at DESC,
                        id DESC
                ) AS rn
            FROM user_photos
        )
        DELETE FROM user_photos p
        USING ranked r
        WHERE p.id = r.id
          AND r.rn > 1;
        """
    )
    op.execute("UPDATE user_photos SET slot_number = 1 WHERE slot_number <> 1;")

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

            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'slot_number_between_1_and_4'
                  AND conrelid = 'user_photos'::regclass
            ) THEN
                ALTER TABLE user_photos DROP CONSTRAINT slot_number_between_1_and_4;
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

            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'slot_number_is_1'
                  AND conrelid = 'user_photos'::regclass
            ) THEN
                ALTER TABLE user_photos
                ADD CONSTRAINT slot_number_is_1 CHECK (slot_number = 1);
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
                WHERE conname = 'slot_number_is_1'
                  AND conrelid = 'user_photos'::regclass
            ) THEN
                ALTER TABLE user_photos DROP CONSTRAINT slot_number_is_1;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_user_photos_user_id'
                  AND conrelid = 'user_photos'::regclass
            ) THEN
                ALTER TABLE user_photos DROP CONSTRAINT uq_user_photos_user_id;
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
                WHERE conname = 'slot_number_between_1_and_4'
                  AND conrelid = 'user_photos'::regclass
            ) THEN
                ALTER TABLE user_photos
                ADD CONSTRAINT slot_number_between_1_and_4 CHECK (slot_number >= 1 AND slot_number <= 4);
            END IF;

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
