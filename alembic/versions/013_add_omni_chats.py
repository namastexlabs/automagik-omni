"""Add omni_chats table for local chat metadata storage

Revision ID: 013_omni_chats
Revises: 012_chat_id_mappings
Create Date: 2026-01-27

Stores chat metadata locally for fast queries without Evolution API dependency.
Synced from evo_Chat table with additional computed fields.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "013_omni_chats"
down_revision = "012_chat_id_mappings"
branch_labels = None
depends_on = None


def upgrade():
    # Create omni_chats table
    op.create_table(
        "omni_chats",
        # Primary key: composite for uniqueness
        sa.Column("id", sa.String(512), nullable=False),  # Format: {instance}:{chat_id}
        # Instance linkage
        sa.Column("instance_name", sa.String(255), nullable=False),
        sa.Column("channel_type", sa.String(20), nullable=False),  # 'whatsapp', 'discord'
        # Chat identification
        sa.Column("chat_id", sa.String(255), nullable=False),  # remoteJid for WhatsApp
        sa.Column("canonical_chat_id", sa.String(255), nullable=True),  # Unified ID
        # Chat metadata
        sa.Column("name", sa.String(255), nullable=True),  # Display name
        sa.Column("chat_type", sa.String(20), nullable=False),  # 'direct', 'group', 'channel'
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        # Participant info (for groups)
        sa.Column("participant_count", sa.Integer, nullable=True),
        # Status flags
        sa.Column("is_muted", sa.Boolean, default=False, nullable=False),
        sa.Column("is_archived", sa.Boolean, default=False, nullable=False),
        sa.Column("is_pinned", sa.Boolean, default=False, nullable=False),
        sa.Column("is_read_only", sa.Boolean, default=False, nullable=False),
        # Message stats (computed from omni_messages)
        sa.Column("unread_count", sa.Integer, default=0, nullable=True),
        sa.Column("message_count", sa.Integer, default=0, nullable=True),
        sa.Column("last_message_at", sa.DateTime, nullable=True),
        sa.Column("last_message_preview", sa.String(255), nullable=True),
        # Contact info (for direct chats)
        sa.Column("contact_name", sa.String(255), nullable=True),  # From sender_name
        sa.Column("contact_phone", sa.String(50), nullable=True),  # Extracted phone
        # Sync tracking
        sa.Column("evo_chat_id", sa.String(255), nullable=True),  # Link to evo_Chat.id
        sa.Column("synced_at", sa.DateTime, nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instance_name", "chat_id", name="uq_omni_chats_instance_chat"),
    )

    # Create indexes
    op.create_index(
        "ix_omni_chats_instance",
        "omni_chats",
        ["instance_name"],
    )
    op.create_index(
        "ix_omni_chats_canonical",
        "omni_chats",
        ["instance_name", "canonical_chat_id"],
    )
    op.create_index(
        "ix_omni_chats_type",
        "omni_chats",
        ["instance_name", "chat_type"],
    )
    op.create_index(
        "ix_omni_chats_last_message",
        "omni_chats",
        ["instance_name", "last_message_at"],
    )


def downgrade():
    op.drop_index("ix_omni_chats_last_message", table_name="omni_chats")
    op.drop_index("ix_omni_chats_type", table_name="omni_chats")
    op.drop_index("ix_omni_chats_canonical", table_name="omni_chats")
    op.drop_index("ix_omni_chats_instance", table_name="omni_chats")
    op.drop_table("omni_chats")
