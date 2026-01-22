"""Add agent providers table and link to instance configs

Adds reusable Agent Provider configurations that can be shared across instances.
When creating/configuring instances, users can select a saved provider to auto-populate
API credentials and fetch available agents/teams.

New table: omni_agent_providers
- id: Primary key
- name: Unique display name
- api_url: Base API URL
- api_key: API authentication key
- description: Optional description
- is_active: Enable/disable provider
- last_health_check: Last health check timestamp
- last_health_status: 'healthy', 'unhealthy', 'unknown'
- created_at, updated_at: Timestamps

New column in omni_instance_configs:
- agent_provider_id: FK to omni_agent_providers (nullable)

Revision ID: 004_agent_providers
Revises: 003_remove_deprecated
Create Date: 2026-01-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "004_agent_providers"
down_revision = "003_remove_deprecated"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Create omni_agent_providers table if it doesn't exist
    if not table_exists("omni_agent_providers"):
        op.create_table(
            "omni_agent_providers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(255), nullable=False, unique=True, index=True),
            sa.Column("api_url", sa.Text(), nullable=False),
            sa.Column("api_key", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("last_health_check", sa.DateTime(), nullable=True),
            sa.Column("last_health_status", sa.String(20), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        )

        # Create indexes
        op.create_index("ix_omni_agent_providers_name", "omni_agent_providers", ["name"], unique=True)
        op.create_index("ix_omni_agent_providers_is_active", "omni_agent_providers", ["is_active"])

    # Add agent_provider_id column to omni_instance_configs if it doesn't exist
    if not column_exists("omni_instance_configs", "agent_provider_id"):
        op.add_column(
            "omni_instance_configs",
            sa.Column("agent_provider_id", sa.Integer(), nullable=True),
        )
        # Create foreign key
        op.create_foreign_key(
            "fk_instance_configs_agent_provider",
            "omni_instance_configs",
            "omni_agent_providers",
            ["agent_provider_id"],
            ["id"],
            ondelete="SET NULL",
        )
        # Create index
        op.create_index(
            "ix_omni_instance_configs_agent_provider_id",
            "omni_instance_configs",
            ["agent_provider_id"],
        )


def downgrade() -> None:
    # Remove the foreign key and column from omni_instance_configs
    if column_exists("omni_instance_configs", "agent_provider_id"):
        op.drop_constraint("fk_instance_configs_agent_provider", "omni_instance_configs", type_="foreignkey")
        op.drop_index("ix_omni_instance_configs_agent_provider_id", table_name="omni_instance_configs")
        op.drop_column("omni_instance_configs", "agent_provider_id")

    # Drop the omni_agent_providers table
    if table_exists("omni_agent_providers"):
        op.drop_index("ix_omni_agent_providers_is_active", table_name="omni_agent_providers")
        op.drop_index("ix_omni_agent_providers_name", table_name="omni_agent_providers")
        op.drop_table("omni_agent_providers")
