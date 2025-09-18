"""Remove legacy hive fields from instance_configs

Revision ID: 3d824d2d6df9
Revises: fa60b37b5e16
Create Date: 2025-02-14 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "3d824d2d6df9"
down_revision = "fa60b37b5e16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop deprecated hive_* columns now superseded by unified agent_* fields."""
    with op.batch_alter_table("instance_configs") as batch_op:
        batch_op.drop_column("hive_enabled")
        batch_op.drop_column("hive_api_url")
        batch_op.drop_column("hive_api_key")
        batch_op.drop_column("hive_agent_id")
        batch_op.drop_column("hive_team_id")
        batch_op.drop_column("hive_timeout")
        batch_op.drop_column("hive_stream_mode")


def downgrade() -> None:
    """No downgrade path because legacy hive_* columns are permanently removed."""
    raise NotImplementedError("Downgrade not supported for removal of legacy hive fields")
