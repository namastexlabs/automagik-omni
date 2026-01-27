"""Add omni_messages table for unified message store.

This table consolidates ALL messages from both webhooks and synced history,
enabling media processing on all messages and reducing Evolution API dependency.

Features:
- Unified store: All messages regardless of source (webhook, sync, API)
- Media tracking: Status-based workflow for download and processing
- Deduplication: Composite key on instance_name + platform_message_id
- Full message data: Stores raw content for reprocessing capability

Revision ID: 011_omni_messages
Revises: 010_batch_total_found
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic
revision = "011_omni_messages"
down_revision = "010_batch_total_found"
branch_labels = None
depends_on = None


def upgrade():
    # Create the omni_messages table
    op.create_table(
        "omni_messages",
        # Primary key: composite format {instance}:{platform_message_id}
        sa.Column("id", sa.String(512), primary_key=True),
        # Instance and chat linkage
        sa.Column("instance_name", sa.String(255), sa.ForeignKey("omni_instance_configs.name"), nullable=False),
        sa.Column("channel_type", sa.String(20), nullable=False),  # 'whatsapp', 'discord'
        sa.Column("chat_id", sa.String(255), nullable=False),  # remoteJid for WhatsApp, channel_id for Discord
        # Platform-specific identification
        sa.Column("platform_message_id", sa.String(255), nullable=False),  # WhatsApp key.id, Discord message.id
        sa.Column(
            "platform_key", JSONB, nullable=True
        ),  # Full WhatsApp key object {id, remoteJid, fromMe, participant}
        # Direction and sender
        sa.Column("direction", sa.String(10), nullable=False),  # 'inbound', 'outbound'
        sa.Column("sender_id", sa.String(255), nullable=True),  # JID or user ID
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("is_from_me", sa.Boolean, default=False, nullable=False),
        # Message content
        sa.Column("message_type", sa.String(50), nullable=False),  # 'text', 'audio', 'image', etc.
        sa.Column("content_text", sa.Text, nullable=True),  # Text content or caption
        sa.Column("content_raw", JSONB, nullable=True),  # Raw platform-specific message object
        # Media information
        sa.Column("has_media", sa.Boolean, default=False, nullable=False),
        sa.Column("media_url", sa.Text, nullable=True),  # Original URL (may expire)
        sa.Column("media_local_path", sa.Text, nullable=True),  # Local file path after download
        sa.Column("media_mime_type", sa.String(100), nullable=True),
        sa.Column("media_size_bytes", sa.Integer, nullable=True),
        sa.Column("media_duration_seconds", sa.Integer, nullable=True),
        sa.Column("media_key", sa.Text, nullable=True),  # WhatsApp encryption key (base64)
        sa.Column("media_sha256", sa.String(64), nullable=True),  # For deduplication
        sa.Column(
            "media_status", sa.String(20), default="pending", nullable=False
        ),  # pending, downloaded, processed, failed, expired
        # Context/threading
        sa.Column("quoted_message_id", sa.String(255), nullable=True),
        sa.Column("context_info", JSONB, nullable=True),
        # Delivery status (WhatsApp)
        sa.Column("delivery_status", sa.String(20), nullable=True),  # pending, sent, delivered, read, failed
        sa.Column("status_updated_at", sa.DateTime, nullable=True),
        # Source tracking (CRITICAL for this feature)
        sa.Column("source", sa.String(20), nullable=False),  # 'webhook', 'sync', 'api'
        sa.Column("sync_batch_id", sa.String(255), nullable=True),  # For tracking sync operations
        sa.Column("trace_id", sa.String(255), nullable=True),  # Link to omni_message_traces if from webhook
        # Timestamps
        sa.Column("message_timestamp", sa.DateTime, nullable=False),  # Original message time
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("synced_at", sa.DateTime, nullable=True),  # When imported from Evolution
    )

    # Create unique constraint on instance + platform message ID
    op.create_unique_constraint(
        "uq_omni_messages_platform",
        "omni_messages",
        ["instance_name", "platform_message_id"],
    )

    # Create performance indexes
    op.create_index(
        "ix_omni_messages_instance_chat",
        "omni_messages",
        ["instance_name", "chat_id"],
    )
    op.create_index(
        "ix_omni_messages_timestamp",
        "omni_messages",
        [sa.text("message_timestamp DESC")],
    )
    op.create_index(
        "ix_omni_messages_media_pending",
        "omni_messages",
        ["media_status"],
        postgresql_where=sa.text("has_media = TRUE"),
    )
    op.create_index(
        "ix_omni_messages_source",
        "omni_messages",
        ["source"],
    )
    op.create_index(
        "ix_omni_messages_type",
        "omni_messages",
        ["message_type"],
    )
    op.create_index(
        "ix_omni_messages_trace_id",
        "omni_messages",
        ["trace_id"],
    )
    op.create_index(
        "ix_omni_messages_chat_timestamp",
        "omni_messages",
        ["chat_id", sa.text("message_timestamp DESC")],
    )


def downgrade():
    # Drop indexes first
    op.drop_index("ix_omni_messages_chat_timestamp", table_name="omni_messages")
    op.drop_index("ix_omni_messages_trace_id", table_name="omni_messages")
    op.drop_index("ix_omni_messages_type", table_name="omni_messages")
    op.drop_index("ix_omni_messages_source", table_name="omni_messages")
    op.drop_index("ix_omni_messages_media_pending", table_name="omni_messages")
    op.drop_index("ix_omni_messages_timestamp", table_name="omni_messages")
    op.drop_index("ix_omni_messages_instance_chat", table_name="omni_messages")

    # Drop unique constraint
    op.drop_constraint("uq_omni_messages_platform", "omni_messages", type_="unique")

    # Drop table
    op.drop_table("omni_messages")
