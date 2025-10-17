"""add_enable_auto_split_to_instance_config

Revision ID: 49e3788203da
Revises: 42a0f0c8f9f1
Create Date: 2025-10-17 19:06:02.911982

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "49e3788203da"
down_revision: Union[str, Sequence[str], None] = "42a0f0c8f9f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add enable_auto_split column to instance_configs table."""
    # Add the column with default True to maintain backward compatibility
    op.add_column("instance_configs", sa.Column("enable_auto_split", sa.Boolean(), nullable=False, server_default="1"))


def downgrade() -> None:
    """Remove enable_auto_split column from instance_configs table."""
    op.drop_column("instance_configs", "enable_auto_split")
