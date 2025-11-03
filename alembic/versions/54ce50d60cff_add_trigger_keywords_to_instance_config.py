"""add_trigger_keywords_to_instance_config

Revision ID: 54ce50d60cff
Revises: 49e3788203da
Create Date: 2025-11-03 17:19:09.689004

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "54ce50d60cff"
down_revision: Union[str, Sequence[str], None] = "49e3788203da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add trigger configuration columns to instance_configs table."""
    op.add_column("instance_configs", sa.Column("trigger_keywords", sa.String(), nullable=True))


def downgrade() -> None:
    """Remove trigger configuration columns from instance_configs table."""
    op.drop_column("instance_configs", "trigger_keywords")
