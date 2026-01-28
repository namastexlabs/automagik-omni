"""
SQLAlchemy models for multi-tenant instance configuration and user management.
"""

import uuid
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from .database import Base
from src.utils.datetime_utils import datetime_utcnow


class AgentProvider(Base):
    """
    Reusable Agent Provider configuration.
    Stores API credentials that can be shared across multiple instances.
    """

    __tablename__ = "omni_agent_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)  # Display name
    api_url = Column(Text, nullable=False)  # Base API URL
    api_key = Column(Text, nullable=False)  # API authentication key
    description = Column(Text, nullable=True)  # Optional description
    is_active = Column(Boolean, default=True, nullable=False)  # Enable/disable

    # Health check tracking
    last_health_check = Column(DateTime, nullable=True)
    last_health_status = Column(String(20), nullable=True)  # 'healthy', 'unhealthy', 'unknown'

    # Timestamps
    created_at = Column(DateTime, default=datetime_utcnow)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow)

    # Relationships
    instances = relationship("InstanceConfig", back_populates="agent_provider")

    def __repr__(self):
        return f"<AgentProvider(name='{self.name}', is_active={self.is_active})>"


class InstanceConfig(Base):
    """
    Instance configuration model for multi-tenant WhatsApp instances.
    Each instance can have different Evolution API and Agent API configurations.
    """

    __tablename__ = "omni_instance_configs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Instance identification
    name = Column(String, unique=True, index=True, nullable=False)  # e.g., "flashinho_v2"
    channel_type = Column(String, default="whatsapp", nullable=False)  # "whatsapp", "slack", "discord"

    # WhatsApp Web API configuration (via Evolution API)
    # Use whatsapp_web_url/whatsapp_web_key property aliases for new code
    evolution_url = Column(String, nullable=True)  # Alias: whatsapp_web_url
    evolution_key = Column(String, nullable=True)  # Alias: whatsapp_web_key

    # Channel-specific configuration
    whatsapp_instance = Column(String, nullable=True)  # WhatsApp: instance name
    session_id_prefix = Column(String, nullable=True)  # WhatsApp: session prefix
    webhook_base64 = Column(Boolean, default=True, nullable=False)  # WhatsApp: send base64 in webhooks

    # Discord-specific fields
    discord_bot_token = Column(String, nullable=True)  # Bot authentication token
    discord_client_id = Column(String, nullable=True)  # Application client ID
    discord_guild_id = Column(String, nullable=True)  # Optional specific guild/server
    discord_default_channel_id = Column(String, nullable=True)  # Default text channel
    discord_voice_enabled = Column(Boolean, default=False, nullable=True)  # Voice support flag
    discord_slash_commands_enabled = Column(Boolean, default=True, nullable=True)  # Slash commands
    discord_webhook_url = Column(String, nullable=True)  # Optional webhook for notifications
    discord_permissions = Column(Integer, nullable=True)  # Permission integer for bot

    # Future channel-specific fields (to be added as needed)
    # slack_bot_token = Column(String, nullable=True)
    # slack_workspace = Column(String, nullable=True)

    # Agent Provider relationship (optional - allows sharing credentials across instances)
    agent_provider_id = Column(
        Integer, ForeignKey("omni_agent_providers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_provider = relationship("AgentProvider", back_populates="instances")

    # Agno Agent API configuration
    # Made optional for wizard flow - can be configured later via settings
    # When agent_provider_id is set, these values are overridden by the provider
    agent_api_url = Column(String, nullable=True)  # Optional - configure later
    agent_api_key = Column(String, nullable=True)  # Optional - configure later
    agent_id = Column(
        String, default="default", nullable=True
    )  # Agent name/ID - defaults to "default" for backward compatibility
    agent_type = Column(String, default="agent", nullable=False)  # "agent" or "team"
    agent_timeout = Column(Integer, default=60)
    agent_stream_mode = Column(Boolean, default=False, nullable=False)  # Enable streaming

    # Profile information from Evolution API
    profile_name = Column(String, nullable=True)  # WhatsApp display name
    profile_pic_url = Column(String, nullable=True)  # Profile picture URL
    owner_jid = Column(String, nullable=True)  # WhatsApp JID (owner field from Evolution)

    # Default instance flag (for backward compatibility)
    is_default = Column(Boolean, default=False, index=True)

    # Instance status
    is_active = Column(Boolean, default=False, index=True)  # Evolution connection status

    # Message splitting control
    enable_auto_split = Column(Boolean, default=True, nullable=False)  # Auto-split messages on \n\n

    # Message debounce configuration (legacy field - kept for backward compatibility)
    message_debounce_seconds = Column(Integer, default=0, nullable=False)  # 0 = disabled

    # Randomized debounce configuration (new fields)
    # Mode: "disabled" (instant), "fixed" (use legacy seconds), "randomized" (min-max ms range)
    message_debounce_mode = Column(String(20), default="disabled", nullable=False)
    message_debounce_min_ms = Column(Integer, default=0, nullable=False)  # Min delay in milliseconds
    message_debounce_max_ms = Column(Integer, default=0, nullable=False)  # Max delay in milliseconds

    # Split message delay configuration
    # Mode: "disabled" (instant), "fixed" (fixed_ms), "randomized" (min-max ms range)
    # Default: "randomized" with 300-1000ms to preserve existing 0.3-1.0s behavior
    message_split_delay_mode = Column(String(20), default="randomized", nullable=False)
    message_split_delay_fixed_ms = Column(Integer, default=0, nullable=False)  # Fixed delay in ms
    message_split_delay_min_ms = Column(Integer, default=300, nullable=False)  # Min delay in ms (default: 300)
    message_split_delay_max_ms = Column(Integer, default=1000, nullable=False)  # Max delay in ms (default: 1000)

    # Disable username prefix on messages to agent
    disable_username_prefix = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime_utcnow)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow)

    # Relationships
    users = relationship(
        "User",
        back_populates="instance",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    access_rules = relationship(
        "AccessRule",
        back_populates="instance",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<InstanceConfig(name='{self.name}', is_default={self.is_default})>"

    # Helper properties
    @property
    def is_team(self) -> bool:
        """Check if configured for team mode."""
        return self.agent_type == "team"

    @property
    def streaming_enabled(self) -> bool:
        """Check if streaming is enabled."""
        return self.agent_stream_mode

    # WhatsApp Web API aliases (clean naming for evolution_* columns)
    @property
    def whatsapp_web_url(self) -> str | None:
        """Alias for evolution_url - WhatsApp Web API URL."""
        return self.evolution_url

    @whatsapp_web_url.setter
    def whatsapp_web_url(self, value: str | None) -> None:
        self.evolution_url = value

    @property
    def whatsapp_web_key(self) -> str | None:
        """Alias for evolution_key - WhatsApp Web API key."""
        return self.evolution_key

    @whatsapp_web_key.setter
    def whatsapp_web_key(self, value: str | None) -> None:
        self.evolution_key = value

    def get_agent_config(self) -> dict:
        """Get agent configuration as dictionary.

        If an agent_provider is linked, its credentials take precedence over
        the instance-level agent_api_url and agent_api_key.
        """
        agent_identifier = self.agent_id or "default"

        # Use provider credentials if available
        if self.agent_provider and self.agent_provider.is_active:
            api_url = self.agent_provider.api_url
            api_key = self.agent_provider.api_key
        else:
            api_url = self.agent_api_url
            api_key = self.agent_api_key

        config = {
            "api_url": api_url,
            "api_key": api_key,
            "agent_id": agent_identifier,
            "name": agent_identifier,
            "agent_type": self.agent_type or "agent",
            "timeout": self.agent_timeout or 60,
            "stream_mode": self.agent_stream_mode or False,
        }
        return config


class User(Base):
    """
    User model with stable identity and session tracking.

    This model provides a stable user identity across different sessions,
    agents, and interactions while tracking their most recent session info.
    """

    __tablename__ = "omni_users"

    # Stable primary identifier (never changes)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    # Channel type - identifies the source channel (whatsapp, discord, etc.)
    channel_type = Column(String(20), nullable=False, default="whatsapp", index=True)

    # User identification
    # For WhatsApp: phone_number and whatsapp_jid are the primary identifiers
    # For Discord: these can be null, use external_ids instead
    phone_number = Column(String, nullable=True, index=True)
    whatsapp_jid = Column(String, nullable=True, index=True)  # Formatted WhatsApp ID

    # Discord-specific fields (null for WhatsApp users)
    discord_user_id = Column(String, nullable=True, index=True)  # Discord snowflake ID
    discord_username = Column(String, nullable=True)  # Discord username#discriminator

    # Instance relationship
    instance_name = Column(String, ForeignKey("omni_instance_configs.name"), nullable=False, index=True)
    instance = relationship("InstanceConfig", back_populates="users")

    # User information
    display_name = Column(String, nullable=True)  # From pushName (WhatsApp) or global_name (Discord)

    # Session tracking (can change over time)
    last_session_name_interaction = Column(String, nullable=True, index=True)
    last_agent_user_id = Column(String, nullable=True)  # UUID from agent API, can change

    # Activity tracking
    last_seen_at = Column(DateTime, default=datetime_utcnow, index=True)
    message_count = Column(Integer, default=0)  # Total messages from this user

    # Timestamps
    created_at = Column(DateTime, default=datetime_utcnow)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow)

    def __repr__(self):
        if self.channel_type == "discord":
            return f"<User(id='{self.id}', discord='{self.discord_user_id}', instance='{self.instance_name}')>"
        return f"<User(id='{self.id}', phone='{self.phone_number}', instance='{self.instance_name}')>"

    @property
    def unique_key(self) -> str:
        """Generate unique key for phone + instance combination."""
        return f"{self.instance_name}:{self.phone_number}"


class UserExternalId(Base):
    """External identity linking for users across channels/platforms.

    Stores provider-specific identifiers (e.g., WhatsApp JID, Discord user ID)
    and links them to a stable local User.
    """

    __tablename__ = "omni_user_external_ids"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("omni_users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)  # e.g., 'whatsapp', 'discord'
    external_id = Column(String, nullable=False, index=True)
    instance_name = Column(String, ForeignKey("omni_instance_configs.name"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime_utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "external_id",
            "instance_name",
            name="uq_user_external_provider_instance",
        ),
    )

    user = relationship("User", backref="external_ids")

    def __repr__(self) -> str:
        scope = f"@{self.instance_name}" if self.instance_name else ""
        return f"<UserExternalId(provider='{self.provider}', external_id='{self.external_id}'{scope})>"


# Import trace models to ensure they're registered with SQLAlchemy


class AccessRuleType(str, Enum):
    """Enumeration of supported access rule types."""

    ALLOW = "allow"
    BLOCK = "block"


class AccessRule(Base):
    """Allow/block phone number rules optionally scoped to an instance."""

    __tablename__ = "omni_access_rules"
    __table_args__ = (
        UniqueConstraint(
            "instance_name",
            "phone_number",
            "rule_type",
            name="uq_access_rules_scope_phone_rule",
        ),
        CheckConstraint(
            "rule_type IN ('allow', 'block')",
            name="ck_access_rules_rule_type",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    instance_name = Column(
        String,
        ForeignKey("omni_instance_configs.name", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    phone_number = Column(String, nullable=False, index=True)
    rule_type = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime_utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow, nullable=False)

    instance = relationship("InstanceConfig", back_populates="access_rules")

    def __repr__(self) -> str:
        scope = self.instance_name or "global"
        return f"<AccessRule(scope='{scope}', phone='{self.phone_number}', type='{self.rule_type}')>"

    @property
    def rule_enum(self) -> AccessRuleType:
        """Return the rule type as an enum instance."""
        return AccessRuleType(self.rule_type)

    @property
    def is_allow(self) -> bool:
        """Convenience flag for allow rules."""
        return self.rule_enum is AccessRuleType.ALLOW


class SettingValueType(str, Enum):
    """Enumeration of supported setting value types."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    JSON = "json"
    SECRET = "secret"


class GlobalSetting(Base):
    """Global application settings with type safety and validation."""

    __tablename__ = "omni_global_settings"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Setting identification
    key = Column(String, unique=True, nullable=False, index=True)  # e.g., "evolution_api_key"
    value = Column(String, nullable=True)  # Stored as string, cast based on value_type
    value_type = Column(String(20), nullable=False, default="string")  # SettingValueType enum

    # Metadata
    category = Column(String, nullable=True, index=True)  # e.g., "api", "integration", "system"
    description = Column(String, nullable=True)  # Human-readable description
    is_secret = Column(Boolean, default=False, nullable=False)  # UI masking hint
    is_required = Column(Boolean, default=False, nullable=False)  # Validation flag
    default_value = Column(String, nullable=True)  # Default fallback

    # Validation rules (JSON stored as string)
    validation_rules = Column(String, nullable=True)  # JSON: min, max, pattern, etc.

    # Audit trail
    created_at = Column(DateTime, default=datetime_utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow, nullable=False)
    created_by = Column(String, nullable=True)  # API key identifier or user
    updated_by = Column(String, nullable=True)  # API key identifier or user

    # Relationships
    change_history = relationship(
        "SettingChangeHistory",
        back_populates="setting",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        masked_value = "***" if self.is_secret else self.value
        return f"<GlobalSetting(key='{self.key}', value='{masked_value}', type='{self.value_type}')>"


class SettingChangeHistory(Base):
    """Audit trail for global setting changes."""

    __tablename__ = "omni_setting_change_history"

    id = Column(Integer, primary_key=True, index=True)
    setting_id = Column(Integer, ForeignKey("omni_global_settings.id", ondelete="CASCADE"), nullable=False, index=True)

    # Change tracking
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    changed_by = Column(String, nullable=True)
    changed_at = Column(DateTime, default=datetime_utcnow, nullable=False, index=True)
    change_reason = Column(String, nullable=True)  # Optional user-provided reason

    # Relationship
    setting = relationship("GlobalSetting", back_populates="change_history")

    def __repr__(self):
        return f"<SettingChangeHistory(setting_id={self.setting_id}, changed_at='{self.changed_at}', changed_by='{self.changed_by}')>"


class UserPreference(Base):
    """User preferences synced to PostgreSQL (localStorage + sync pattern).

    This table provides persistent backup for localStorage preferences (API key, theme).
    Frontend uses localStorage for fast reads (0ms latency), syncs to PostgreSQL
    for persistence (survives browser cache clear).

    Replaces:
    - omni_api_key (localStorage) -> key='omni_api_key', value='sk-...'
    - omni_theme (localStorage) -> key='omni_theme', value='light'|'dark'|'system'
    """

    __tablename__ = "omni_user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)  # Identifier (stored session/API key)
    key = Column(String(100), nullable=False, index=True)  # Preference key (e.g., 'omni_theme')
    value = Column(String, nullable=True)  # Preference value

    # Timestamps
    created_at = Column(DateTime, default=datetime_utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("session_id", "key", name="uq_user_preferences_session_key"),)

    def __repr__(self):
        return f"<UserPreference(session='{self.session_id[:8]}...', key='{self.key}', value='{self.value}')>"


# =============================================================================
# Evolution API Tables (Read-Only Models)
# These models map to tables managed by Evolution API for direct database queries.
# DO NOT use these for writes - Evolution API manages these tables.
# =============================================================================


class EvolutionInstance(Base):
    """Read-only model for Evolution API instance table.

    Maps to evo_Instance table managed by Evolution API.
    Use for querying instance data directly from database.
    """

    __tablename__ = "evo_Instance"

    id = Column(String, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    connectionStatus = Column(String, default="close")  # open, close, connecting
    ownerJid = Column(String(100), nullable=True)
    profileName = Column(String(100), nullable=True)
    profilePicUrl = Column(String(500), nullable=True)
    integration = Column(String(100), nullable=True)
    number = Column(String(100), nullable=True)
    createdAt = Column(DateTime, nullable=True)
    updatedAt = Column(DateTime, nullable=True)

    # Relationships
    messages = relationship("EvolutionMessage", back_populates="instance", lazy="dynamic")
    chats = relationship("EvolutionChat", back_populates="instance", lazy="dynamic")

    def __repr__(self):
        return f"<EvolutionInstance(name='{self.name}', status='{self.connectionStatus}')>"


class EvolutionChat(Base):
    """Read-only model for Evolution API chat table.

    Maps to evo_Chat table managed by Evolution API.
    """

    __tablename__ = "evo_Chat"

    id = Column(String, primary_key=True)
    remoteJid = Column(String(100), nullable=False)
    name = Column(String(100), nullable=True)
    instanceId = Column(String, ForeignKey("evo_Instance.id", ondelete="CASCADE"), nullable=False)
    unreadMessages = Column(Integer, default=0)
    createdAt = Column(DateTime, nullable=True)
    updatedAt = Column(DateTime, nullable=True)

    # Relationships
    instance = relationship("EvolutionInstance", back_populates="chats")

    def __repr__(self):
        return f"<EvolutionChat(jid='{self.remoteJid}', unread={self.unreadMessages})>"


class EvolutionMessage(Base):
    """Read-only model for Evolution API message table.

    Maps to evo_Message table managed by Evolution API.
    Use for querying messages with delivery status directly from database.
    """

    __tablename__ = "evo_Message"

    id = Column(String, primary_key=True)
    key = Column(String, nullable=False)  # JSONB stored as string
    pushName = Column(String(100), nullable=True)
    participant = Column(String(100), nullable=True)
    messageType = Column(String(100), nullable=False)
    message = Column(String, nullable=False)  # JSONB stored as string
    contextInfo = Column(String, nullable=True)  # JSONB stored as string
    source = Column(String, nullable=False)  # DeviceMessage enum
    messageTimestamp = Column(Integer, nullable=False)
    instanceId = Column(String, ForeignKey("evo_Instance.id", ondelete="CASCADE"), nullable=False)
    webhookUrl = Column(String(500), nullable=True)
    status = Column(String(30), nullable=True)  # DELIVERY_ACK, READ, PLAYED, SERVER_ACK, PENDING

    # Relationships
    instance = relationship("EvolutionInstance", back_populates="messages")

    def __repr__(self):
        return f"<EvolutionMessage(id='{self.id}', status='{self.status}')>"
