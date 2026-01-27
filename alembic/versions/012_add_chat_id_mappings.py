"""Add chat_id_mappings table and canonical_chat_id field

Revision ID: 012
Revises: 011
Create Date: 2026-01-27

WhatsApp uses different chat ID formats:
- @s.whatsapp.net: Phone number format (e.g., 553488722041@s.whatsapp.net)
- @lid: Linked device ID format (e.g., 179538357133535@lid)
- @g.us: Group format

The same contact can have multiple chat IDs depending on how messages are sent.
This migration adds:
1. chat_id_mappings table to store known mappings
2. canonical_chat_id field to omni_messages for unified queries
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "012_chat_id_mappings"
down_revision = "011_omni_messages"
branch_labels = None
depends_on = None


def upgrade():
    # Create chat_id_mappings table
    op.create_table(
        "omni_chat_id_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instance_name", sa.String(255), nullable=False),
        # The canonical ID (usually @s.whatsapp.net format with phone number)
        sa.Column("canonical_chat_id", sa.String(255), nullable=False),
        # The alternative ID (@lid format)
        sa.Column("alternate_chat_id", sa.String(255), nullable=False),
        # Contact name for reference
        sa.Column("contact_name", sa.String(255), nullable=True),
        # Phone number extracted (if available)
        sa.Column("phone_number", sa.String(50), nullable=True),
        # How this mapping was discovered
        sa.Column("discovery_method", sa.String(50), nullable=True),  # 'sender_name', 'manual', 'api'
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instance_name", "alternate_chat_id", name="uq_chat_mapping_alternate"),
    )

    # Create indexes
    op.create_index(
        "ix_chat_mappings_canonical",
        "omni_chat_id_mappings",
        ["instance_name", "canonical_chat_id"],
    )
    op.create_index(
        "ix_chat_mappings_alternate",
        "omni_chat_id_mappings",
        ["instance_name", "alternate_chat_id"],
    )

    # Add canonical_chat_id to omni_messages
    op.add_column(
        "omni_messages",
        sa.Column("canonical_chat_id", sa.String(255), nullable=True),
    )

    # Create index for canonical_chat_id
    op.create_index(
        "ix_omni_messages_canonical_chat",
        "omni_messages",
        ["instance_name", "canonical_chat_id"],
    )

    # Populate canonical_chat_id with chat_id for non-lid chats
    op.execute("""
        UPDATE omni_messages
        SET canonical_chat_id = chat_id
        WHERE chat_id NOT LIKE '%@lid'
    """)


def downgrade():
    op.drop_index("ix_omni_messages_canonical_chat", table_name="omni_messages")
    op.drop_column("omni_messages", "canonical_chat_id")
    op.drop_index("ix_chat_mappings_alternate", table_name="omni_chat_id_mappings")
    op.drop_index("ix_chat_mappings_canonical", table_name="omni_chat_id_mappings")
    op.drop_table("omni_chat_id_mappings")
