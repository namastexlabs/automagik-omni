"""Add process_media_on_blocked column to omni_instance_configs.

Revision ID: 017_add_process_media_on_blocked
Revises: 016_add_user_channel_type
Create Date: 2025-01-28
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "017_add_process_media_on_blocked"
down_revision = "016_user_channel_type"
branch_labels = None
depends_on = None


def upgrade():
    """Add process_media_on_blocked column.

    When True (default), media will be transcribed/described even if access rules
    block the sender. This enables passive media collection without agent responses.
    """
    op.add_column(
        "omni_instance_configs",
        sa.Column(
            "process_media_on_blocked",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )


def downgrade():
    """Remove process_media_on_blocked column."""
    op.drop_column("omni_instance_configs", "process_media_on_blocked")
