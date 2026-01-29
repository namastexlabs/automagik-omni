"""Add batch_job_id column to omni_media_content.

Revision ID: 018_media_batch_job_id
Revises: 017_add_process_media_on_blocked
Create Date: 2025-01-29
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "018_media_batch_job_id"
down_revision = "017_add_process_media_on_blocked"
branch_labels = None
depends_on = None


def upgrade():
    """Add batch_job_id column for tracking which batch job processed each media item."""
    op.add_column(
        "omni_media_content",
        sa.Column(
            "batch_job_id",
            sa.String(36),
            sa.ForeignKey("omni_batch_jobs.job_id"),
            nullable=True,
        ),
    )
    # Add index for efficient lookups by batch job
    op.create_index(
        "ix_omni_media_content_batch_job",
        "omni_media_content",
        ["batch_job_id"],
    )


def downgrade():
    """Remove batch_job_id column."""
    op.drop_index("ix_omni_media_content_batch_job", table_name="omni_media_content")
    op.drop_column("omni_media_content", "batch_job_id")
