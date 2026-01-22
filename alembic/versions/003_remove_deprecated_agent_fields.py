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
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "003_remove_deprecated"
down_revision = "002_debounce_prefix"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Remove deprecated columns (only if they exist - idempotent)
    deprecated_columns = [
        "default_agent",
        "agent_instance_type",
        "automagik_instance_id",
        "automagik_instance_name",
    ]

    for col in deprecated_columns:
        if column_exists("omni_instance_configs", col):
            op.drop_column("omni_instance_configs", col)


def downgrade() -> None:
    # Re-add the columns if downgrading (only if they don't exist)
    if not column_exists("omni_instance_configs", "default_agent"):
        op.add_column(
            "omni_instance_configs",
            sa.Column("default_agent", sa.String(length=255), nullable=True),
        )
    if not column_exists("omni_instance_configs", "agent_instance_type"):
        op.add_column(
            "omni_instance_configs",
            sa.Column("agent_instance_type", sa.String(length=255), nullable=True, server_default="hive"),
        )
    if not column_exists("omni_instance_configs", "automagik_instance_id"):
        op.add_column(
            "omni_instance_configs",
            sa.Column("automagik_instance_id", sa.String(length=255), nullable=True),
        )
    if not column_exists("omni_instance_configs", "automagik_instance_name"):
        op.add_column(
            "omni_instance_configs",
            sa.Column("automagik_instance_name", sa.String(length=255), nullable=True),
        )
