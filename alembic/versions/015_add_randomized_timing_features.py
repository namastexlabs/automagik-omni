"""Add randomized debounce and split delay timing features

Revision ID: 015_randomized_timing
Revises: 014_add_skip_media_processing
Create Date: 2026-01-28
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "015_randomized_timing"
down_revision = "014_skip_media_processing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===== DEBOUNCE FIELDS =====
    # Mode: "disabled" (instant), "fixed" (use legacy seconds), "randomized" (min-max ms range)
    op.add_column(
        "omni_instance_configs",
        sa.Column("message_debounce_mode", sa.String(20), nullable=False, server_default="disabled"),
    )
    # Min delay in milliseconds (used when mode="randomized")
    op.add_column(
        "omni_instance_configs",
        sa.Column("message_debounce_min_ms", sa.Integer(), nullable=False, server_default="0"),
    )
    # Max delay in milliseconds (used when mode="randomized")
    op.add_column(
        "omni_instance_configs",
        sa.Column("message_debounce_max_ms", sa.Integer(), nullable=False, server_default="0"),
    )

    # ===== SPLIT MESSAGE DELAY FIELDS =====
    # Mode: "disabled" (instant), "fixed" (fixed_ms), "randomized" (min-max ms range)
    # Default: "randomized" to preserve existing 0.3-1.0s behavior
    op.add_column(
        "omni_instance_configs",
        sa.Column("message_split_delay_mode", sa.String(20), nullable=False, server_default="randomized"),
    )
    # Fixed delay in milliseconds (used when mode="fixed")
    op.add_column(
        "omni_instance_configs",
        sa.Column("message_split_delay_fixed_ms", sa.Integer(), nullable=False, server_default="0"),
    )
    # Min delay in milliseconds (default: 300ms to preserve current 0.3s)
    op.add_column(
        "omni_instance_configs",
        sa.Column("message_split_delay_min_ms", sa.Integer(), nullable=False, server_default="300"),
    )
    # Max delay in milliseconds (default: 1000ms to preserve current 1.0s)
    op.add_column(
        "omni_instance_configs",
        sa.Column("message_split_delay_max_ms", sa.Integer(), nullable=False, server_default="1000"),
    )


def downgrade() -> None:
    # Drop split delay columns
    op.drop_column("omni_instance_configs", "message_split_delay_max_ms")
    op.drop_column("omni_instance_configs", "message_split_delay_min_ms")
    op.drop_column("omni_instance_configs", "message_split_delay_fixed_ms")
    op.drop_column("omni_instance_configs", "message_split_delay_mode")

    # Drop debounce columns
    op.drop_column("omni_instance_configs", "message_debounce_max_ms")
    op.drop_column("omni_instance_configs", "message_debounce_min_ms")
    op.drop_column("omni_instance_configs", "message_debounce_mode")
