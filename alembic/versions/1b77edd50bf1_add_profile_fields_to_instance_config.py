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
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('instance_configs', schema=None) as batch_op:
        # Add profile fields
        batch_op.add_column(sa.Column('profile_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('profile_pic_url', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('owner_jid', sa.String(), nullable=True))

def downgrade():
    """Remove profile fields from instance_configs table."""
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('instance_configs', schema=None) as batch_op:
        # Drop profile fields
        batch_op.drop_column('owner_jid')
        batch_op.drop_column('profile_pic_url')
        batch_op.drop_column('profile_name')
