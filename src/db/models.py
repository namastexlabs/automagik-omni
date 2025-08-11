"""
SQLAlchemy models for multi-tenant instance configuration and user management.
"""

import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from src.utils.datetime_utils import datetime_utcnow


class InstanceConfig(Base):
    """
    Instance configuration model for multi-tenant WhatsApp instances.
    Each instance can have different Evolution API and Agent API configurations.
    """

    __tablename__ = "instance_configs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Instance identification
    name = Column(
        String, unique=True, index=True, nullable=False
    )  # e.g., "flashinho_v2"
    channel_type = Column(
        String, default="whatsapp", nullable=False
    )  # "whatsapp", "slack", "discord"

    # Evolution API configuration (WhatsApp-specific)
    evolution_url = Column(String, nullable=True)  # Made nullable for other channels
    evolution_key = Column(String, nullable=True)  # Made nullable for other channels

    # Channel-specific configuration
    whatsapp_instance = Column(String, nullable=True)  # WhatsApp: instance name
    session_id_prefix = Column(String, nullable=True)  # WhatsApp: session prefix
    webhook_base64 = Column(
        Boolean, default=True, nullable=False
    )  # WhatsApp: send base64 in webhooks

    # Future channel-specific fields (to be added as needed)
    # slack_bot_token = Column(String, nullable=True)
    # slack_workspace = Column(String, nullable=True)
    # discord_token = Column(String, nullable=True)
    # discord_guild_id = Column(String, nullable=True)

    # Unified Agent API configuration (works for both Automagik and Hive)
    agent_instance_type = Column(String, default="automagik", nullable=False)  # "automagik" or "hive"
    agent_api_url = Column(String, nullable=False)
    agent_api_key = Column(String, nullable=False)
    agent_id = Column(String, default="default", nullable=True)  # Agent name/ID - defaults to "default" for backward compatibility
    agent_type = Column(String, default="agent", nullable=False)  # "agent" or "team" (team only for hive)
    agent_timeout = Column(Integer, default=60)
    agent_stream_mode = Column(Boolean, default=False, nullable=False)  # Enable streaming (mainly for hive)
    
    # Legacy field for backward compatibility (will be migrated to agent_id)
    default_agent = Column(String, nullable=True)  # Deprecated - use agent_id instead
    
    # Legacy AutomagikHive fields (deprecated - kept for migration)
    hive_enabled = Column(Boolean, default=False, nullable=True)  # Deprecated - use agent_instance_type
    hive_api_url = Column(String, nullable=True)  # Deprecated - use agent_api_url
    hive_api_key = Column(String, nullable=True)  # Deprecated - use agent_api_key
    hive_agent_id = Column(String, nullable=True)  # Deprecated - use agent_id with agent_type="agent"
    hive_team_id = Column(String, nullable=True)  # Deprecated - use agent_id with agent_type="team"
    hive_timeout = Column(Integer, nullable=True)  # Deprecated - use agent_timeout
    hive_stream_mode = Column(Boolean, nullable=True)  # Deprecated - use agent_stream_mode

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
    is_active = Column(
        Boolean, default=False, index=True
    )  # Evolution connection status

    # Timestamps
    created_at = Column(DateTime, default=datetime_utcnow)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow)

    # Relationships
    users = relationship("User", back_populates="instance")

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
        agent_identifier = self.agent_id or self.default_agent or "default"
        
        config = {
            "instance_type": self.agent_instance_type or "automagik",
            "api_url": self.agent_api_url,
            "api_key": self.agent_api_key,
            "agent_id": agent_identifier,
            "agent_type": self.agent_type or "agent",
            "timeout": self.agent_timeout or 60,
            "stream_mode": self.agent_stream_mode or False
        }
        return config
    
    # Backward compatibility methods
    def has_hive_config(self) -> bool:
        """Legacy: Check if instance has complete AutomagikHive configuration."""
        # Check new unified fields
        if self.is_hive:
            return bool(self.agent_api_url) and bool(self.agent_api_key) and bool(self.agent_id)
        # Fall back to legacy fields if they exist
        return (
            self.hive_enabled and 
            bool(self.hive_api_url) and 
            bool(self.hive_api_key) and
            (bool(self.hive_agent_id) or bool(self.hive_team_id))
        )
    
    def get_hive_config(self) -> dict:
        """Legacy: Get AutomagikHive configuration as dictionary."""
        # Use new unified fields if this is a hive instance
        if self.is_hive:
            return self.get_agent_config()
        # Fall back to legacy fields
        return {
            "api_url": self.hive_api_url,
            "api_key": self.hive_api_key,
            "agent_id": self.hive_agent_id,
            "team_id": self.hive_team_id,
            "timeout": self.hive_timeout,
            "stream_mode": self.hive_stream_mode
        }


class User(Base):
    """
    User model with stable identity and session tracking.

    This model provides a stable user identity across different sessions,
    agents, and interactions while tracking their most recent session info.
    """

    __tablename__ = "users"

    # Stable primary identifier (never changes)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    # User identification (most stable identifier from WhatsApp)
    phone_number = Column(String, nullable=False, index=True)
    whatsapp_jid = Column(String, nullable=False, index=True)  # Formatted WhatsApp ID

    # Instance relationship
    instance_name = Column(
        String, ForeignKey("instance_configs.name"), nullable=False, index=True
    )
    instance = relationship("InstanceConfig", back_populates="users")

    # User information
    display_name = Column(String, nullable=True)  # From pushName, can change

    # Session tracking (can change over time)
    last_session_name_interaction = Column(String, nullable=True, index=True)
    last_agent_user_id = Column(
        String, nullable=True
    )  # UUID from agent API, can change

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


# Import trace models to ensure they're registered with SQLAlchemy
