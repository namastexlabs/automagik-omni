"""Add batch jobs table for async processing with progress tracking.

Revision ID: 009_add_batch_jobs
Revises: 008_add_sender_to_media_content
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "009_batch_jobs"
down_revision = "008_media_sender"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "omni_batch_jobs",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("instance_name", sa.String(length=255), nullable=True),
        sa.Column("request_params", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True, server_default="pending"),
        sa.Column("total_items", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("processed_items", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("skipped_items", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("current_item", sa.String(length=255), nullable=True),
        sa.Column("results_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("total_cost_usd", sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(op.f("ix_omni_batch_jobs_job_id"), "omni_batch_jobs", ["job_id"], unique=False)
    op.create_index(op.f("ix_omni_batch_jobs_job_type"), "omni_batch_jobs", ["job_type"], unique=False)
    op.create_index(op.f("ix_omni_batch_jobs_instance_name"), "omni_batch_jobs", ["instance_name"], unique=False)
    op.create_index(op.f("ix_omni_batch_jobs_status"), "omni_batch_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_omni_batch_jobs_created_at"), "omni_batch_jobs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_omni_batch_jobs_created_at"), table_name="omni_batch_jobs")
    op.drop_index(op.f("ix_omni_batch_jobs_status"), table_name="omni_batch_jobs")
    op.drop_index(op.f("ix_omni_batch_jobs_instance_name"), table_name="omni_batch_jobs")
    op.drop_index(op.f("ix_omni_batch_jobs_job_type"), table_name="omni_batch_jobs")
    op.drop_index(op.f("ix_omni_batch_jobs_job_id"), table_name="omni_batch_jobs")
    op.drop_table("omni_batch_jobs")
