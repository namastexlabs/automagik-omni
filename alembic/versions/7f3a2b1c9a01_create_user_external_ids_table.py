"""
Create user_external_ids table for cross-channel identity linking

Revision ID: 7f3a2b1c9a01
Revises: e6087278efbd
Create Date: 2025-09-24 16:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f3a2b1c9a01"
down_revision: Union[str, Sequence[str], None] = "e6087278efbd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_external_ids",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("provider", sa.String(), nullable=False, index=True),
        sa.Column("external_id", sa.String(), nullable=False, index=True),
        sa.Column("instance_name", sa.String(), sa.ForeignKey("instance_configs.name"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("provider", "external_id", name="uq_user_external_ids_provider_external"),
    )


def downgrade() -> None:
    op.drop_table("user_external_ids")

