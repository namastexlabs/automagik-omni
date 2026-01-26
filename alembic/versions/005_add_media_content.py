"""Add omni_media_content table for processed media

Revision ID: 005_add_media_content
Revises: 004_add_agent_providers
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "005_media_content"
down_revision = "004_agent_providers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create omni_media_content table for storing processed media content."""
    op.create_table(
        "omni_media_content",
        sa.Column("id", sa.Integer(), nullable=False),
        # Link to original message
        sa.Column("instance_name", sa.String(length=255), nullable=False),
        sa.Column("channel_type", sa.String(length=20), nullable=False),
        sa.Column("original_message_id", sa.String(length=255), nullable=False),
        # Content type
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("source_media_type", sa.String(length=50), nullable=False),
        # Processed content
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_format", sa.String(length=20), server_default="text"),
        # Processing metadata
        sa.Column("processor_name", sa.String(length=100), nullable=True),
        sa.Column("processor_model", sa.String(length=100), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        # Source media info
        sa.Column("media_url", sa.Text(), nullable=True),
        sa.Column("media_mime_type", sa.String(length=100), nullable=True),
        sa.Column("media_size_bytes", sa.Integer(), nullable=True),
        sa.Column("media_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("media_key", sa.Text(), nullable=True),
        # Status
        sa.Column("status", sa.String(length=20), server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        # Primary key
        sa.PrimaryKeyConstraint("id"),
        # Foreign key
        sa.ForeignKeyConstraint(
            ["instance_name"],
            ["omni_instance_configs.name"],
            name="fk_media_content_instance",
            ondelete="CASCADE",
        ),
    )

    # Create indexes
    op.create_index("ix_omni_media_content_instance", "omni_media_content", ["instance_name"])
    op.create_index("ix_omni_media_content_status", "omni_media_content", ["status"])
    op.create_index("ix_omni_media_content_type", "omni_media_content", ["content_type"])
    op.create_index("ix_omni_media_content_message_id", "omni_media_content", ["original_message_id"])
    op.create_index("ix_omni_media_content_created_at", "omni_media_content", ["created_at"])

    # Create unique constraint for (instance_name, original_message_id, content_type)
    op.create_unique_constraint(
        "uq_media_content_instance_msg_type",
        "omni_media_content",
        ["instance_name", "original_message_id", "content_type"],
    )


def downgrade() -> None:
    """Drop omni_media_content table."""
    op.drop_constraint("uq_media_content_instance_msg_type", "omni_media_content", type_="unique")
    op.drop_index("ix_omni_media_content_created_at", table_name="omni_media_content")
    op.drop_index("ix_omni_media_content_message_id", table_name="omni_media_content")
    op.drop_index("ix_omni_media_content_type", table_name="omni_media_content")
    op.drop_index("ix_omni_media_content_status", table_name="omni_media_content")
    op.drop_index("ix_omni_media_content_instance", table_name="omni_media_content")
    op.drop_table("omni_media_content")
