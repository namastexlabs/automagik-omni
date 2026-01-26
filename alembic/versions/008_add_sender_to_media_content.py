"""Add sender_id to omni_media_content for uniqueness

When a message is forwarded, it keeps the same message ID but has a different sender.
We need to track the sender to properly identify unique media content.

Revision ID: 008_media_sender
Revises: 007_media_cost_tracking
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "008_media_sender"
down_revision = "007_media_cost_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add sender_id column and update unique constraint."""
    # Add sender_id column (remoteJid for WhatsApp, user_id for Discord)
    op.add_column(
        "omni_media_content",
        sa.Column("sender_id", sa.String(length=255), nullable=True),
    )

    # Create index for sender_id
    op.create_index(
        "ix_omni_media_content_sender",
        "omni_media_content",
        ["sender_id"],
    )

    # Drop the old unique constraint
    op.drop_constraint(
        "uq_media_content_instance_msg_type",
        "omni_media_content",
        type_="unique",
    )

    # Create new unique constraint including sender_id
    # This ensures that forwarded messages (same msg_id, different sender) are treated as separate
    op.create_unique_constraint(
        "uq_media_content_instance_msg_sender_type",
        "omni_media_content",
        ["instance_name", "original_message_id", "sender_id", "content_type"],
    )


def downgrade() -> None:
    """Remove sender_id and restore old constraint."""
    # Drop new unique constraint
    op.drop_constraint(
        "uq_media_content_instance_msg_sender_type",
        "omni_media_content",
        type_="unique",
    )

    # Restore old unique constraint
    op.create_unique_constraint(
        "uq_media_content_instance_msg_type",
        "omni_media_content",
        ["instance_name", "original_message_id", "content_type"],
    )

    # Drop index
    op.drop_index("ix_omni_media_content_sender", "omni_media_content")

    # Drop column
    op.drop_column("omni_media_content", "sender_id")
