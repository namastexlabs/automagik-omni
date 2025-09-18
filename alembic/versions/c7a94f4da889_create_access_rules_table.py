"""create access rules table

Revision ID: c7a94f4da889
Revises: 2b88f12c9d34
Create Date: 2025-09-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c7a94f4da889'
down_revision = '2b88f12c9d34'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create access_rules table for message filtering."""
    op.create_table(
        'access_rules',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('instance_name', sa.String(length=255), sa.ForeignKey('instance_configs.name', ondelete='CASCADE'), nullable=True),
        sa.Column('phone_number', sa.String(length=255), nullable=False),
        sa.Column('rule_type', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            server_onupdate=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.UniqueConstraint('instance_name', 'phone_number', 'rule_type', name='uq_access_rules_scope_phone_rule'),
        sa.CheckConstraint("rule_type IN ('allow', 'block')", name='ck_access_rules_rule_type'),
    )
    op.create_index('ix_access_rules_phone_number', 'access_rules', ['phone_number'])
    op.create_index('ix_access_rules_rule_type', 'access_rules', ['rule_type'])
    op.create_index('ix_access_rules_instance_name', 'access_rules', ['instance_name'])


def downgrade() -> None:
    """Drop access_rules table."""
    op.drop_index('ix_access_rules_instance_name', table_name='access_rules')
    op.drop_index('ix_access_rules_rule_type', table_name='access_rules')
    op.drop_index('ix_access_rules_phone_number', table_name='access_rules')
    op.drop_table('access_rules')
