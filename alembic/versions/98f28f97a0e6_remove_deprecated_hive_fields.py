"""Remove deprecated hive fields

Revision ID: 98f28f97a0e6
Revises: fa60b37b5e16
Create Date: 2025-09-06 18:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98f28f97a0e6'
down_revision: Union[str, Sequence[str], None] = 'fa60b37b5e16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove deprecated hive_ columns from instance_configs table."""
    
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('instance_configs', schema=None) as batch_op:
        # Drop all deprecated hive_ columns
        batch_op.drop_column('hive_enabled')
        batch_op.drop_column('hive_api_url')
        batch_op.drop_column('hive_api_key')
        batch_op.drop_column('hive_agent_id')
        batch_op.drop_column('hive_team_id')
        batch_op.drop_column('hive_timeout')
        batch_op.drop_column('hive_stream_mode')


def downgrade() -> None:
    """Re-add deprecated hive_ columns to instance_configs table."""
    
    with op.batch_alter_table('instance_configs', schema=None) as batch_op:
        # Re-add deprecated hive_ columns
        batch_op.add_column(sa.Column('hive_enabled', sa.Boolean(), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('hive_api_url', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('hive_api_key', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('hive_agent_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('hive_team_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('hive_timeout', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('hive_stream_mode', sa.Boolean(), nullable=True))