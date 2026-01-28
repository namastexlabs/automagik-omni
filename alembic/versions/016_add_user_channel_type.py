"""Add channel_type and Discord fields to User model

Revision ID: 016_user_channel_type
Revises: 015_randomized_timing
Create Date: 2026-01-28
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "016_user_channel_type"
down_revision = "015_randomized_timing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add channel_type field (default 'whatsapp' for existing users)
    op.add_column(
        "omni_users",
        sa.Column("channel_type", sa.String(20), nullable=False, server_default="whatsapp"),
    )
    op.create_index("ix_omni_users_channel_type", "omni_users", ["channel_type"])

    # Add Discord-specific fields
    op.add_column(
        "omni_users",
        sa.Column("discord_user_id", sa.String(), nullable=True),
    )
    op.add_column(
        "omni_users",
        sa.Column("discord_username", sa.String(), nullable=True),
    )
    op.create_index("ix_omni_users_discord_user_id", "omni_users", ["discord_user_id"])

    # Make phone_number and whatsapp_jid nullable (for Discord users)
    op.alter_column("omni_users", "phone_number", existing_type=sa.String(), nullable=True)
    op.alter_column("omni_users", "whatsapp_jid", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    # Make phone_number and whatsapp_jid non-nullable again
    # First update any null values
    op.execute("UPDATE omni_users SET phone_number = 'unknown' WHERE phone_number IS NULL")
    op.execute("UPDATE omni_users SET whatsapp_jid = 'unknown' WHERE whatsapp_jid IS NULL")
    op.alter_column("omni_users", "phone_number", existing_type=sa.String(), nullable=False)
    op.alter_column("omni_users", "whatsapp_jid", existing_type=sa.String(), nullable=False)

    # Drop Discord fields
    op.drop_index("ix_omni_users_discord_user_id", "omni_users")
    op.drop_column("omni_users", "discord_username")
    op.drop_column("omni_users", "discord_user_id")

    # Drop channel_type
    op.drop_index("ix_omni_users_channel_type", "omni_users")
    op.drop_column("omni_users", "channel_type")
