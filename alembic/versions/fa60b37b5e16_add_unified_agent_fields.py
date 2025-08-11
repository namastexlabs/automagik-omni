"""Add unified agent fields and AutomagikHive configuration

Revision ID: fa60b37b5e16
Revises: be1e23d77eed
Create Date: 2025-08-11 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa60b37b5e16'
down_revision: Union[str, Sequence[str], None] = 'be1e23d77eed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unified agent fields and legacy AutomagikHive fields to instance_configs table."""
    
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('instance_configs', schema=None) as batch_op:
        # Add unified agent fields
        batch_op.add_column(sa.Column('agent_instance_type', sa.String(), server_default='automagik', nullable=False))
        batch_op.add_column(sa.Column('agent_id', sa.String(), server_default='default', nullable=True))
        batch_op.add_column(sa.Column('agent_type', sa.String(), server_default='agent', nullable=False))
        batch_op.add_column(sa.Column('agent_stream_mode', sa.Boolean(), server_default='0', nullable=False))
        
        # Add legacy AutomagikHive fields for backward compatibility (deprecated)
        batch_op.add_column(sa.Column('hive_enabled', sa.Boolean(), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('hive_api_url', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('hive_api_key', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('hive_agent_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('hive_team_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('hive_timeout', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('hive_stream_mode', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Remove unified agent fields and AutomagikHive configuration fields."""
    
    with op.batch_alter_table('instance_configs', schema=None) as batch_op:
        # Remove unified fields
        batch_op.drop_column('agent_stream_mode')
        batch_op.drop_column('agent_type')
        batch_op.drop_column('agent_id')
        batch_op.drop_column('agent_instance_type')
        
        # Remove legacy hive fields
        batch_op.drop_column('hive_stream_mode')
        batch_op.drop_column('hive_timeout')
        batch_op.drop_column('hive_team_id')
        batch_op.drop_column('hive_agent_id')
        batch_op.drop_column('hive_api_key')
        batch_op.drop_column('hive_api_url')
        batch_op.drop_column('hive_enabled')