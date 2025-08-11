"""add profile fields to instance config

Revision ID: 1b77edd50bf1
Revises: fa60b37b5e16
Create Date: 2025-08-11 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b77edd50bf1'
down_revision = 'fa60b37b5e16'
branch_labels = None
depends_on = None


def upgrade():
    """Add profile fields to instance_configs table."""
    # Add profile fields
    op.add_column('instance_configs', sa.Column('profile_name', sa.String(), nullable=True))
    op.add_column('instance_configs', sa.Column('profile_pic_url', sa.String(), nullable=True))
    op.add_column('instance_configs', sa.Column('owner_jid', sa.String(), nullable=True))


def downgrade():
    """Remove profile fields from instance_configs table."""
    # Drop profile fields
    op.drop_column('instance_configs', 'owner_jid')
    op.drop_column('instance_configs', 'profile_pic_url')  
    op.drop_column('instance_configs', 'profile_name')