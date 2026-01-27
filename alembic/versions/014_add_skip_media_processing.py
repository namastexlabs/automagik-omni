"""Add skip_media_processing column to omni_chats

Revision ID: 014_skip_media_processing
Revises: 013_omni_chats
Create Date: 2026-01-27

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "014_skip_media_processing"
down_revision = "013_omni_chats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add skip_media_processing column (default false)
    op.add_column(
        "omni_chats",
        sa.Column("skip_media_processing", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Add processing_note column
    op.add_column(
        "omni_chats",
        sa.Column("processing_note", sa.String(255), nullable=True),
    )

    # Add index for quick filtering of skipped chats
    op.create_index(
        "ix_omni_chats_skip_media",
        "omni_chats",
        ["instance_name", "skip_media_processing"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_omni_chats_skip_media", table_name="omni_chats")
    op.drop_column("omni_chats", "processing_note")
    op.drop_column("omni_chats", "skip_media_processing")
