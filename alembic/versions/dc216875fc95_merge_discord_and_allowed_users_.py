"""merge discord and allowed users migrations

Revision ID: dc216875fc95
Revises: 2b88f12c9d34, c3d8e9f1a2b4
Create Date: 2025-09-03 22:54:15.401403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc216875fc95'
down_revision: Union[str, Sequence[str], None] = ('2b88f12c9d34', 'c3d8e9f1a2b4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
