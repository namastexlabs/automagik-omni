"""Add total_found column to batch_jobs table.

Tracks how many items were found matching criteria before filtering out
already-processed items. This allows UI to show "Found X, Skipped Y, Processed Z".

Revision ID: 010_batch_total_found
Revises: 009_batch_jobs
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = "010_batch_total_found"
down_revision = "009_batch_jobs"
branch_labels = None
depends_on = None


def upgrade():
    # Add total_found column to track items found before filtering
    op.add_column(
        "omni_batch_jobs",
        sa.Column("total_found", sa.Integer(), nullable=True, server_default="0"),
    )

    # Update existing rows to have total_found = total_items + skipped_items
    # This is a reasonable approximation for historical data
    op.execute(
        """
        UPDATE omni_batch_jobs
        SET total_found = COALESCE(total_items, 0) + COALESCE(skipped_items, 0)
        """
    )


def downgrade():
    op.drop_column("omni_batch_jobs", "total_found")
