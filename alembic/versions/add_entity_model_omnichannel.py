"""add_entity_model_omnichannel

Revision ID: add_entity_omni
Revises: 30974a03f6b8
Create Date: 2025-11-27

Add Entity model for omnichannel presence - one entity (person/company) can own
multiple channel integrations (WhatsApp, Discord, Telegram, etc.)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_entity_omni'
down_revision: Union[str, Sequence[str], None] = '012_add_omni_prefix'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Entity table and entity_id FK to omni_instance_configs."""
    # Create omni_entities table
    op.create_table('omni_entities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False, server_default='person'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_omni_entities_id'), 'omni_entities', ['id'], unique=False)
    op.create_index(op.f('ix_omni_entities_name'), 'omni_entities', ['name'], unique=False)

    # Add entity_id column to omni_instance_configs (SQLite compatible - no FK constraint)
    # The FK relationship is enforced at application level via SQLAlchemy
    op.add_column('omni_instance_configs',
        sa.Column('entity_id', sa.Integer(), nullable=True)
    )
    op.create_index(op.f('ix_omni_instance_configs_entity_id'), 'omni_instance_configs', ['entity_id'], unique=False)


def downgrade() -> None:
    """Remove Entity table and entity_id FK from omni_instance_configs."""
    # Drop column from omni_instance_configs
    op.drop_index(op.f('ix_omni_instance_configs_entity_id'), table_name='omni_instance_configs')
    op.drop_column('omni_instance_configs', 'entity_id')

    # Drop omni_entities table
    op.drop_index(op.f('ix_omni_entities_name'), table_name='omni_entities')
    op.drop_index(op.f('ix_omni_entities_id'), table_name='omni_entities')
    op.drop_table('omni_entities')
