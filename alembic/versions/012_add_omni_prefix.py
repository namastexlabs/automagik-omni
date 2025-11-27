"""Add omni_ prefix to all tables for shared PostgreSQL support

Revision ID: 012_add_omni_prefix
Revises: 30974a03f6b8
Create Date: 2025-11-27 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '012_add_omni_prefix'
down_revision: Union[str, Sequence[str], None] = '30974a03f6b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename all tables to add omni_ prefix."""
    # Rename tables to add omni_ prefix
    op.rename_table('instance_configs', 'omni_instance_configs')
    op.rename_table('users', 'omni_users')
    op.rename_table('user_external_ids', 'omni_user_external_ids')
    op.rename_table('access_rules', 'omni_access_rules')
    op.rename_table('message_traces', 'omni_message_traces')
    op.rename_table('trace_payloads', 'omni_trace_payloads')
    op.rename_table('global_settings', 'omni_global_settings')
    op.rename_table('setting_change_history', 'omni_setting_change_history')


def downgrade() -> None:
    """Remove omni_ prefix from all tables."""
    op.rename_table('omni_instance_configs', 'instance_configs')
    op.rename_table('omni_users', 'users')
    op.rename_table('omni_user_external_ids', 'user_external_ids')
    op.rename_table('omni_access_rules', 'access_rules')
    op.rename_table('omni_message_traces', 'message_traces')
    op.rename_table('omni_trace_payloads', 'trace_payloads')
    op.rename_table('omni_global_settings', 'global_settings')
    op.rename_table('omni_setting_change_history', 'setting_change_history')
