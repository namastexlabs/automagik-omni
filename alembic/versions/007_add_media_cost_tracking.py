"""Add cost tracking fields to omni_media_content

Revision ID: 007_media_cost_tracking
Revises: 006_media_settings
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "007_media_cost_tracking"
down_revision = "006_media_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add cost tracking fields to omni_media_content."""
    # Token/usage tracking
    op.add_column(
        "omni_media_content",
        sa.Column("input_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "omni_media_content",
        sa.Column("output_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "omni_media_content",
        sa.Column("total_tokens", sa.Integer(), nullable=True),
    )

    # Cost tracking (in USD, stored as decimal for precision)
    op.add_column(
        "omni_media_content",
        sa.Column("cost_input_usd", sa.Numeric(precision=10, scale=8), nullable=True),
    )
    op.add_column(
        "omni_media_content",
        sa.Column("cost_output_usd", sa.Numeric(precision=10, scale=8), nullable=True),
    )
    op.add_column(
        "omni_media_content",
        sa.Column("cost_total_usd", sa.Numeric(precision=10, scale=8), nullable=True),
    )

    # Pricing metadata (for audit/debugging)
    op.add_column(
        "omni_media_content",
        sa.Column("pricing_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "omni_media_content",
        sa.Column("pricing_rate_input", sa.Numeric(precision=10, scale=8), nullable=True),
    )
    op.add_column(
        "omni_media_content",
        sa.Column("pricing_rate_output", sa.Numeric(precision=10, scale=8), nullable=True),
    )


def downgrade() -> None:
    """Remove cost tracking fields."""
    op.drop_column("omni_media_content", "pricing_rate_output")
    op.drop_column("omni_media_content", "pricing_rate_input")
    op.drop_column("omni_media_content", "pricing_model")
    op.drop_column("omni_media_content", "cost_total_usd")
    op.drop_column("omni_media_content", "cost_output_usd")
    op.drop_column("omni_media_content", "cost_input_usd")
    op.drop_column("omni_media_content", "total_tokens")
    op.drop_column("omni_media_content", "output_tokens")
    op.drop_column("omni_media_content", "input_tokens")
