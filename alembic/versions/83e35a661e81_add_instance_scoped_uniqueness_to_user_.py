"""add_instance_scoped_uniqueness_to_user_external_ids

Revision ID: 83e35a661e81
Revises: 7f3a2b1c9a01
Create Date: 2025-09-24 20:56:06.006483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83e35a661e81'
down_revision: Union[str, Sequence[str], None] = '7f3a2b1c9a01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply instance-scoped uniqueness constraint to user external IDs."""
    with op.batch_alter_table("user_external_ids") as batch_op:
        batch_op.drop_constraint(
            "uq_user_external_ids_provider_external",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_user_external_provider_instance",
            ["provider", "external_id", "instance_name"],
        )


def downgrade() -> None:
    """Revert instance-scoped uniqueness to provider/external pair."""
    with op.batch_alter_table("user_external_ids") as batch_op:
        batch_op.drop_constraint(
            "uq_user_external_provider_instance",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_user_external_ids_provider_external",
            ["provider", "external_id"],
        )
