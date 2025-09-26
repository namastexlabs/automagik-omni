"""Merge access rules and user external ID branches

Revision ID: 42a0f0c8f9f1
Revises: 83e35a661e81, c7a94f4da889
Create Date: 2025-09-25 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "42a0f0c8f9f1"
down_revision: Union[str, Sequence[str], None] = ("83e35a661e81", "c7a94f4da889")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Schema already reconciled via dependent revisions."""
    pass


def downgrade() -> None:
    """Downgrade not supported because it would reintroduce divergent heads."""
    raise RuntimeError("Cannot downgrade merge revision 42a0f0c8f9f1")
