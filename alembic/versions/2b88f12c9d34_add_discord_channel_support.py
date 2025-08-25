"""add discord channel support

Revision ID: 2b88f12c9d34
Revises: 1b77edd50bf1
Create Date: 2025-08-23 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2b88f12c9d34'
down_revision = '1b77edd50bf1'
branch_labels = None
depends_on = None


def upgrade():
    """Add Discord-specific fields to instance_configs table."""
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('instance_configs', schema=None) as batch_op:
        # Discord authentication fields
        batch_op.add_column(sa.Column('discord_bot_token', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('discord_client_id', sa.String(255), nullable=True))
        
        # Discord server/guild configuration
        batch_op.add_column(sa.Column('discord_guild_id', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('discord_default_channel_id', sa.String(255), nullable=True))
        
        # Discord feature flags
        batch_op.add_column(sa.Column('discord_voice_enabled', sa.Boolean, default=False, nullable=True))
        batch_op.add_column(sa.Column('discord_slash_commands_enabled', sa.Boolean, default=True, nullable=True))
        
        # Discord webhook integration
        batch_op.add_column(sa.Column('discord_webhook_url', sa.String(500), nullable=True))
        
        # Discord permissions (integer representation of permission flags)
        batch_op.add_column(sa.Column('discord_permissions', sa.Integer, nullable=True))
        
    # Create indexes for performance
    with op.batch_alter_table('instance_configs', schema=None) as batch_op:
        batch_op.create_index('ix_instance_configs_discord_guild_id', ['discord_guild_id'])
        batch_op.create_index('ix_instance_configs_discord_client_id', ['discord_client_id'])


def downgrade():
    """Remove Discord-specific fields from instance_configs table."""
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('instance_configs', schema=None) as batch_op:
        # Drop indexes first
        batch_op.drop_index('ix_instance_configs_discord_client_id')
        batch_op.drop_index('ix_instance_configs_discord_guild_id')
        
        # Drop Discord fields
        batch_op.drop_column('discord_permissions')
        batch_op.drop_column('discord_webhook_url')
        batch_op.drop_column('discord_slash_commands_enabled')
        batch_op.drop_column('discord_voice_enabled')
        batch_op.drop_column('discord_default_channel_id')
        batch_op.drop_column('discord_guild_id')
        batch_op.drop_column('discord_client_id')
        batch_op.drop_column('discord_bot_token')