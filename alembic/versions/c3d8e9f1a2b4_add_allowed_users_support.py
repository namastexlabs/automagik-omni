"""Add allowed users support

Revision ID: c3d8e9f1a2b4
Revises: 1b77edd50bf1
Create Date: 2025-09-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c3d8e9f1a2b4'
down_revision = '1b77edd50bf1'
branch_labels = None
depends_on = None


def upgrade():
    """Add allowed users support to the database."""
    
    # Add allowlist_enabled column to instance_configs table
    op.add_column('instance_configs', 
                  sa.Column('allowlist_enabled', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create allowed_users table
    op.create_table('allowed_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instance_name', sa.String(), nullable=False),
        sa.Column('channel_type', sa.String(), nullable=False),
        sa.Column('user_identifier', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('added_by', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['instance_name'], ['instance_configs.name'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_allowed_users_instance_name', 'allowed_users', ['instance_name'])
    op.create_index('ix_allowed_users_channel_type', 'allowed_users', ['channel_type'])
    op.create_index('ix_allowed_users_user_identifier', 'allowed_users', ['user_identifier'])
    op.create_index('ix_allowed_users_is_active', 'allowed_users', ['is_active'])
    
    # Create unique constraint for the combination of instance, channel, and user
    op.create_index('ix_allowed_users_unique_combo', 'allowed_users', 
                   ['instance_name', 'channel_type', 'user_identifier'], unique=True)


def downgrade():
    """Remove allowed users support from the database."""
    
    # Drop allowed_users table and its indexes
    op.drop_index('ix_allowed_users_unique_combo', table_name='allowed_users')
    op.drop_index('ix_allowed_users_is_active', table_name='allowed_users')
    op.drop_index('ix_allowed_users_user_identifier', table_name='allowed_users')
    op.drop_index('ix_allowed_users_channel_type', table_name='allowed_users')
    op.drop_index('ix_allowed_users_instance_name', table_name='allowed_users')
    op.drop_table('allowed_users')
    
    # Remove allowlist_enabled column from instance_configs
    op.drop_column('instance_configs', 'allowlist_enabled')