"""
SQLAlchemy models for multi-tenant instance configuration and user management.

Supports dual database architecture:
- SQLite: Global settings (bootstrap safety, always available)
- PostgreSQL: Runtime data with omni_ prefix (shared with Evolution API)
"""

import os
import uuid
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Text,
)
from sqlalchemy.orm import relationship
from .database import Base
from src.utils.datetime_utils import datetime_utcnow


def _get_table_prefix() -> str:
    """Get table prefix based on database type (evaluated at import time)."""
    db_type = os.getenv("AUTOMAGIK_OMNI_DB_TYPE", "sqlite").lower()
    if db_type == "postgresql":
        return os.getenv("AUTOMAGIK_OMNI_TABLE_PREFIX", "omni_")
    return ""


def _prefixed_table(name: str) -> str:
    """Return table name with prefix for runtime tables."""
    return f"{_get_table_prefix()}{name}"


# Table prefix for runtime data (entities, instances, users, etc.)
# Global settings tables are NOT prefixed (they stay in SQLite)
_TABLE_PREFIX = _get_table_prefix()


class Entity(Base):
    """
    Entity represents a person or company that owns multiple channel integrations.

    This enables omnichannel presence where one AI assistant can be present
    across all networks (WhatsApp, Discord, Telegram, etc.) for the same entity.
    """

    __tablename__ = f"{_TABLE_PREFIX}entities"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Entity identification
    name = Column(String, nullable=False, index=True)  # e.g., "John Doe", "Acme Corp"
    entity_type = Column(String, default="person", nullable=False)  # "person" | "company"
    description = Column(Text, nullable=True)  # Optional description

    # Timestamps
    created_at = Column(DateTime, default=datetime_utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow, nullable=False)

    # Relationships
    instances = relationship("InstanceConfig", back_populates="entity")

    def __repr__(self):
        return f"<Entity(id={self.id}, name='{self.name}', type='{self.entity_type}')>"


class InstanceConfig(Base):
    """
    Instance configuration model for multi-tenant WhatsApp instances.
    Each instance can have different Evolution API and Agent API configurations.
    """

    __tablename__ = f"{_TABLE_PREFIX}instance_configs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Instance identification
    name = Column(String, unique=True, index=True, nullable=False)  # e.g., "flashinho_v2"
    channel_type = Column(String, default="whatsapp", nullable=False)  # "whatsapp", "slack", "discord"

    # Evolution API configuration (WhatsApp-specific)
    evolution_url = Column(String, nullable=True)  # Made nullable for other channels
    evolution_key = Column(String, nullable=True)  # Made nullable for other channels

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

    # Unified Agent API configuration (supports Automagik and Hive via agent_* fields)
    agent_instance_type = Column(String, default="automagik", nullable=False)  # "automagik" or "hive"
    agent_api_url = Column(String, nullable=False)
    agent_api_key = Column(String, nullable=False)
    agent_id = Column(
        String, default="default", nullable=True
    )  # Agent name/ID - defaults to "default" for backward compatibility
    agent_type = Column(String, default="agent", nullable=False)  # "agent" or "team" (team only for hive)
    agent_timeout = Column(Integer, default=60)
    agent_stream_mode = Column(Boolean, default=False, nullable=False)  # Enable streaming (mainly for hive)

    # Legacy field for backward compatibility (will be migrated to agent_id)
    default_agent = Column(String, nullable=True)  # Deprecated - use agent_id instead

    # Automagik instance identification (for UI display)
    automagik_instance_id = Column(String, nullable=True)
    automagik_instance_name = Column(String, nullable=True)

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

    # Entity relationship (for omnichannel grouping)
    entity_id = Column(Integer, ForeignKey(f"{_TABLE_PREFIX}entities.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime_utcnow)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="instances")
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

    # Helper properties for unified schema
    @property
    def is_hive(self) -> bool:
        """Check if this is a Hive instance."""
        return self.agent_instance_type == "hive"

    @property
    def is_automagik(self) -> bool:
        """Check if this is an Automagik instance."""
        return self.agent_instance_type == "automagik"

    @property
    def is_team(self) -> bool:
        """Check if configured for team mode (Hive only)."""
        return self.agent_type == "team" and self.is_hive

    @property
    def streaming_enabled(self) -> bool:
        """Check if streaming is enabled."""
        return self.agent_stream_mode and self.is_hive

    def get_agent_config(self) -> dict:
        """Get unified agent configuration as dictionary."""
        # Use default_agent if agent_id is not set (backward compatibility)
        # Check if agent_id is meaningful (not the default value)
        if self.agent_id and self.agent_id != "default":
            agent_identifier = self.agent_id
        elif self.default_agent:
            agent_identifier = self.default_agent
        else:
            agent_identifier = "default"

        config = {
            "instance_type": self.agent_instance_type or "automagik",
            "api_url": self.agent_api_url,
            "api_key": self.agent_api_key,
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

    __tablename__ = f"{_TABLE_PREFIX}users"

    # Stable primary identifier (never changes)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    # User identification (most stable identifier from WhatsApp)
    phone_number = Column(String, nullable=False, index=True)
    whatsapp_jid = Column(String, nullable=False, index=True)  # Formatted WhatsApp ID

    # Instance relationship
    instance_name = Column(String, ForeignKey(f"{_TABLE_PREFIX}instance_configs.name"), nullable=False, index=True)
    instance = relationship("InstanceConfig", back_populates="users")

    # User information
    display_name = Column(String, nullable=True)  # From pushName, can change

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

    __tablename__ = f"{_TABLE_PREFIX}user_external_ids"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey(f"{_TABLE_PREFIX}users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)  # e.g., 'whatsapp', 'discord'
    external_id = Column(String, nullable=False, index=True)
    instance_name = Column(String, ForeignKey(f"{_TABLE_PREFIX}instance_configs.name"), nullable=True, index=True)

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

    __tablename__ = f"{_TABLE_PREFIX}access_rules"
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
        ForeignKey(f"{_TABLE_PREFIX}instance_configs.name", ondelete="CASCADE"),
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

    __tablename__ = "global_settings"

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

    __tablename__ = "setting_change_history"

    id = Column(Integer, primary_key=True, index=True)
    setting_id = Column(Integer, ForeignKey("global_settings.id", ondelete="CASCADE"), nullable=False, index=True)

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
