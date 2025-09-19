"""Merge discord and hive cleanup migrations

Revision ID: e6087278efbd
Revises: 2b88f12c9d34, 3d824d2d6df9
Create Date: 2025-09-19 14:13:35.637729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6087278efbd'
down_revision: Union[str, Sequence[str], None] = ('2b88f12c9d34', '3d824d2d6df9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
