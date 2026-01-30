"""add omni_group_participants table

Revision ID: 7e7921fdc88e
Revises: 018_media_batch_job_id
Create Date: 2026-01-30 00:01:43.371426

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e7921fdc88e"
down_revision: Union[str, Sequence[str], None] = "018_media_batch_job_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "omni_group_participants",
        sa.Column("id", sa.String(768), primary_key=True),
        sa.Column("instance_name", sa.String(255), nullable=False, index=True),
        sa.Column("group_id", sa.String(255), nullable=False, index=True),
        sa.Column("participant_id", sa.String(255), nullable=False),
        sa.Column("phone_number", sa.String(50), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), server_default="member", nullable=False),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_omni_group_participants_instance_group",
        "omni_group_participants",
        ["instance_name", "group_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_omni_group_participants_instance_group", table_name="omni_group_participants")
    op.drop_table("omni_group_participants")
