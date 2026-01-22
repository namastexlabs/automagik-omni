"""Remove deprecated agent fields (default_agent, agent_instance_type, automagik_instance_*)

This migration removes deprecated columns that were used for the old Automagik/Hive
dual-agent system. Now we only support Agno, so these fields are no longer needed.

Removed columns:
- default_agent: replaced by agent_id
- agent_instance_type: no longer needed (only Agno supported)
- automagik_instance_id: Automagik legacy field
- automagik_instance_name: Automagik legacy field

Revision ID: 003_remove_deprecated
Revises: 002_debounce_prefix
Create Date: 2026-01-22
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "003_remove_deprecated"
down_revision = "002_debounce_prefix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove deprecated columns
    op.drop_column("omni_instance_configs", "default_agent")
    op.drop_column("omni_instance_configs", "agent_instance_type")
    op.drop_column("omni_instance_configs", "automagik_instance_id")
    op.drop_column("omni_instance_configs", "automagik_instance_name")


def downgrade() -> None:
    # Re-add the columns if downgrading
    op.add_column(
        "omni_instance_configs",
        sa.Column("default_agent", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "omni_instance_configs",
        sa.Column("agent_instance_type", sa.String(length=255), nullable=True, server_default="hive"),
    )
    op.add_column(
        "omni_instance_configs",
        sa.Column("automagik_instance_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "omni_instance_configs",
        sa.Column("automagik_instance_name", sa.String(length=255), nullable=True),
    )
