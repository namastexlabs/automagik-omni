"""Add message debounce and disable username prefix settings

Revision ID: 002_debounce_prefix
Revises: 001_ground_zero
Create Date: 2026-01-21
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002_debounce_prefix"
down_revision = "001_ground_zero"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add message_debounce_seconds column (0 = disabled)
    op.add_column(
        "omni_instance_configs", sa.Column("message_debounce_seconds", sa.Integer(), nullable=False, server_default="0")
    )

    # Add disable_username_prefix column (false by default)
    op.add_column(
        "omni_instance_configs",
        sa.Column("disable_username_prefix", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("omni_instance_configs", "message_debounce_seconds")
    op.drop_column("omni_instance_configs", "disable_username_prefix")
