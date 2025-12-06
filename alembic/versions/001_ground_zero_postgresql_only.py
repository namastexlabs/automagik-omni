"""Ground zero migration - PostgreSQL only, complete fresh schema

Revision ID: 001_ground_zero
Revises: None
Create Date: 2025-12-05

This is a BREAKING CHANGE migration that:
- Removes all SQLite support
- Creates the complete schema from scratch with omni_ prefix
- Adds PostgreSQL-native types and optimizations
- Includes the new omni_user_preferences table for browser storage migration
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_ground_zero'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create complete PostgreSQL-only schema."""

    # ==========================================================================
    # 1. omni_global_settings - Application-wide settings
    # ==========================================================================
    op.create_table(
        'omni_global_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=True),
        sa.Column('value_type', sa.String(length=20), nullable=False, server_default='string'),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('is_secret', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_value', sa.String(), nullable=True),
        sa.Column('validation_rules', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_omni_global_settings_id', 'omni_global_settings', ['id'], unique=False)
    op.create_index('ix_omni_global_settings_key', 'omni_global_settings', ['key'], unique=True)
    op.create_index('ix_omni_global_settings_category', 'omni_global_settings', ['category'], unique=False)

    # ==========================================================================
    # 2. omni_setting_change_history - Audit trail for settings
    # ==========================================================================
    op.create_table(
        'omni_setting_change_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('setting_id', sa.Integer(), nullable=False),
        sa.Column('old_value', sa.String(), nullable=True),
        sa.Column('new_value', sa.String(), nullable=True),
        sa.Column('changed_by', sa.String(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('change_reason', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['setting_id'], ['omni_global_settings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_omni_setting_change_history_id', 'omni_setting_change_history', ['id'], unique=False)
    op.create_index('ix_omni_setting_change_history_setting_id', 'omni_setting_change_history', ['setting_id'], unique=False)
    op.create_index('ix_omni_setting_change_history_changed_at', 'omni_setting_change_history', ['changed_at'], unique=False)

    # ==========================================================================
    # 3. omni_instance_configs - Multi-tenant instance configuration
    # ==========================================================================
    op.create_table(
        'omni_instance_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('channel_type', sa.String(), nullable=False, server_default='whatsapp'),
        # WhatsApp/Evolution API configuration
        sa.Column('evolution_url', sa.String(), nullable=True),
        sa.Column('evolution_key', sa.String(), nullable=True),
        sa.Column('whatsapp_instance', sa.String(), nullable=True),
        sa.Column('session_id_prefix', sa.String(), nullable=True),
        sa.Column('webhook_base64', sa.Boolean(), nullable=False, server_default='true'),
        # Discord configuration
        sa.Column('discord_bot_token', sa.String(), nullable=True),
        sa.Column('discord_client_id', sa.String(), nullable=True),
        sa.Column('discord_guild_id', sa.String(), nullable=True),
        sa.Column('discord_default_channel_id', sa.String(), nullable=True),
        sa.Column('discord_voice_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('discord_slash_commands_enabled', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('discord_webhook_url', sa.String(), nullable=True),
        sa.Column('discord_permissions', sa.Integer(), nullable=True),
        # Unified Agent API configuration
        sa.Column('agent_instance_type', sa.String(), nullable=True, server_default='automagik'),
        sa.Column('agent_api_url', sa.String(), nullable=True),
        sa.Column('agent_api_key', sa.String(), nullable=True),
        sa.Column('agent_id', sa.String(), nullable=True, server_default='default'),
        sa.Column('agent_type', sa.String(), nullable=False, server_default='agent'),
        sa.Column('agent_timeout', sa.Integer(), nullable=True, server_default='60'),
        sa.Column('agent_stream_mode', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_agent', sa.String(), nullable=True),  # Legacy, deprecated
        # Automagik identification
        sa.Column('automagik_instance_id', sa.String(), nullable=True),
        sa.Column('automagik_instance_name', sa.String(), nullable=True),
        # Profile information
        sa.Column('profile_name', sa.String(), nullable=True),
        sa.Column('profile_pic_url', sa.String(), nullable=True),
        sa.Column('owner_jid', sa.String(), nullable=True),
        # Status flags
        sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('enable_auto_split', sa.Boolean(), nullable=False, server_default='true'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_omni_instance_configs_id', 'omni_instance_configs', ['id'], unique=False)
    op.create_index('ix_omni_instance_configs_name', 'omni_instance_configs', ['name'], unique=True)
    op.create_index('ix_omni_instance_configs_is_default', 'omni_instance_configs', ['is_default'], unique=False)
    op.create_index('ix_omni_instance_configs_is_active', 'omni_instance_configs', ['is_active'], unique=False)
    op.create_index('ix_omni_instance_configs_channel_type', 'omni_instance_configs', ['channel_type'], unique=False)

    # ==========================================================================
    # 4. omni_users - User identity and session tracking
    # ==========================================================================
    op.create_table(
        'omni_users',
        sa.Column('id', sa.String(), nullable=False),  # UUID as string
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('whatsapp_jid', sa.String(), nullable=False),
        sa.Column('instance_name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('last_session_name_interaction', sa.String(), nullable=True),
        sa.Column('last_agent_user_id', sa.String(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('message_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['instance_name'], ['omni_instance_configs.name'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_omni_users_id', 'omni_users', ['id'], unique=False)
    op.create_index('ix_omni_users_phone_number', 'omni_users', ['phone_number'], unique=False)
    op.create_index('ix_omni_users_whatsapp_jid', 'omni_users', ['whatsapp_jid'], unique=False)
    op.create_index('ix_omni_users_instance_name', 'omni_users', ['instance_name'], unique=False)
    op.create_index('ix_omni_users_last_session_name_interaction', 'omni_users', ['last_session_name_interaction'], unique=False)
    op.create_index('ix_omni_users_last_seen_at', 'omni_users', ['last_seen_at'], unique=False)

    # ==========================================================================
    # 5. omni_user_external_ids - Cross-platform identity linking
    # ==========================================================================
    op.create_table(
        'omni_user_external_ids',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('external_id', sa.String(), nullable=False),
        sa.Column('instance_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['omni_users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instance_name'], ['omni_instance_configs.name'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'external_id', 'instance_name', name='uq_user_external_provider_instance')
    )
    op.create_index('ix_omni_user_external_ids_id', 'omni_user_external_ids', ['id'], unique=False)
    op.create_index('ix_omni_user_external_ids_user_id', 'omni_user_external_ids', ['user_id'], unique=False)
    op.create_index('ix_omni_user_external_ids_provider', 'omni_user_external_ids', ['provider'], unique=False)
    op.create_index('ix_omni_user_external_ids_external_id', 'omni_user_external_ids', ['external_id'], unique=False)
    op.create_index('ix_omni_user_external_ids_instance_name', 'omni_user_external_ids', ['instance_name'], unique=False)

    # ==========================================================================
    # 6. omni_access_rules - Allow/block phone number rules
    # ==========================================================================
    op.create_table(
        'omni_access_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instance_name', sa.String(), nullable=True),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('rule_type', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("rule_type IN ('allow', 'block')", name='ck_access_rules_rule_type'),
        sa.ForeignKeyConstraint(['instance_name'], ['omni_instance_configs.name'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_name', 'phone_number', 'rule_type', name='uq_access_rules_scope_phone_rule')
    )
    op.create_index('ix_omni_access_rules_id', 'omni_access_rules', ['id'], unique=False)
    op.create_index('ix_omni_access_rules_instance_name', 'omni_access_rules', ['instance_name'], unique=False)
    op.create_index('ix_omni_access_rules_phone_number', 'omni_access_rules', ['phone_number'], unique=False)

    # ==========================================================================
    # 7. omni_message_traces - Message lifecycle tracking
    # ==========================================================================
    op.create_table(
        'omni_message_traces',
        sa.Column('trace_id', sa.String(), nullable=False),
        sa.Column('instance_name', sa.String(), nullable=True),
        sa.Column('whatsapp_message_id', sa.String(), nullable=True),
        # Sender information
        sa.Column('sender_phone', sa.String(), nullable=True),
        sa.Column('sender_name', sa.String(), nullable=True),
        sa.Column('sender_jid', sa.String(), nullable=True),
        # Message metadata
        sa.Column('message_type', sa.String(), nullable=True),
        sa.Column('has_media', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('has_quoted_message', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('message_length', sa.Integer(), nullable=True),
        # Session tracking
        sa.Column('session_name', sa.String(), nullable=True),
        sa.Column('agent_session_id', sa.String(), nullable=True),
        # Timestamps
        sa.Column('received_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('processing_started_at', sa.DateTime(), nullable=True),
        sa.Column('agent_request_at', sa.DateTime(), nullable=True),
        sa.Column('agent_response_at', sa.DateTime(), nullable=True),
        sa.Column('evolution_send_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        # Status
        sa.Column('status', sa.String(), nullable=True, server_default='received'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_stage', sa.String(), nullable=True),
        # Access rule tracking
        sa.Column('blocked_by_access_rule', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('access_rule_id', sa.Integer(), nullable=True),
        sa.Column('blocking_reason', sa.String(), nullable=True),
        # Performance metrics
        sa.Column('agent_processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('total_processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('agent_request_tokens', sa.Integer(), nullable=True),
        sa.Column('agent_response_tokens', sa.Integer(), nullable=True),
        # Agent response
        sa.Column('agent_response_success', sa.Boolean(), nullable=True),
        sa.Column('agent_response_length', sa.Integer(), nullable=True),
        sa.Column('agent_tools_used', sa.Integer(), nullable=True, server_default='0'),
        # Evolution API response
        sa.Column('evolution_response_code', sa.Integer(), nullable=True),
        sa.Column('evolution_success', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['instance_name'], ['omni_instance_configs.name'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['access_rule_id'], ['omni_access_rules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('trace_id')
    )
    op.create_index('ix_omni_message_traces_trace_id', 'omni_message_traces', ['trace_id'], unique=False)
    op.create_index('ix_omni_message_traces_instance_name', 'omni_message_traces', ['instance_name'], unique=False)
    op.create_index('ix_omni_message_traces_whatsapp_message_id', 'omni_message_traces', ['whatsapp_message_id'], unique=False)
    op.create_index('ix_omni_message_traces_sender_phone', 'omni_message_traces', ['sender_phone'], unique=False)
    op.create_index('ix_omni_message_traces_session_name', 'omni_message_traces', ['session_name'], unique=False)
    op.create_index('ix_omni_message_traces_received_at', 'omni_message_traces', ['received_at'], unique=False)
    op.create_index('ix_omni_message_traces_status', 'omni_message_traces', ['status'], unique=False)
    op.create_index('ix_omni_message_traces_blocked_by_access_rule', 'omni_message_traces', ['blocked_by_access_rule'], unique=False)

    # ==========================================================================
    # 8. omni_trace_payloads - Compressed request/response storage
    # ==========================================================================
    op.create_table(
        'omni_trace_payloads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trace_id', sa.String(), nullable=True),
        sa.Column('stage', sa.String(), nullable=True),
        sa.Column('payload_type', sa.String(), nullable=True),
        sa.Column('payload_compressed', sa.Text(), nullable=True),
        sa.Column('payload_size_original', sa.Integer(), nullable=True),
        sa.Column('payload_size_compressed', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('contains_media', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('contains_base64', sa.Boolean(), nullable=True, server_default='false'),
        sa.ForeignKeyConstraint(['trace_id'], ['omni_message_traces.trace_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_omni_trace_payloads_trace_id', 'omni_trace_payloads', ['trace_id'], unique=False)
    op.create_index('ix_omni_trace_payloads_stage', 'omni_trace_payloads', ['stage'], unique=False)
    op.create_index('ix_omni_trace_payloads_timestamp', 'omni_trace_payloads', ['timestamp'], unique=False)

    # ==========================================================================
    # 9. omni_user_preferences - Browser storage replacement (NEW)
    # ==========================================================================
    # This table replaces localStorage for:
    # - omni_api_key -> session-based auth
    # - omni_setup_complete -> global_settings.setup_completed
    # - omni-theme -> stored here per session
    op.create_table(
        'omni_user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'key', name='uq_user_preferences_session_key')
    )
    op.create_index('ix_omni_user_preferences_id', 'omni_user_preferences', ['id'], unique=False)
    op.create_index('ix_omni_user_preferences_session_id', 'omni_user_preferences', ['session_id'], unique=False)
    op.create_index('ix_omni_user_preferences_key', 'omni_user_preferences', ['key'], unique=False)


def downgrade() -> None:
    """Drop all tables - this is a ground zero migration, no downgrade path."""
    # Drop in reverse order of creation (respecting foreign keys)
    op.drop_table('omni_user_preferences')
    op.drop_table('omni_trace_payloads')
    op.drop_table('omni_message_traces')
    op.drop_table('omni_access_rules')
    op.drop_table('omni_user_external_ids')
    op.drop_table('omni_users')
    op.drop_table('omni_instance_configs')
    op.drop_table('omni_setting_change_history')
    op.drop_table('omni_global_settings')
