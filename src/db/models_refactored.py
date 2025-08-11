"""
SQLAlchemy models for multi-tenant instance configuration and user management.
Updated with unified field names for both automagik and hive agent implementations.
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

    # Unified Agent Configuration (supports both automagik and hive implementations)
    agent_instance_type = Column(String, default="automagik", nullable=False)  # "automagik" or "hive"
    agent_api_url = Column(String, nullable=False)  # Works for both automagik and hive
    agent_api_key = Column(String, nullable=False)  # Works for both automagik and hive
    agent_id = Column(String, nullable=False)  # For automagik: agent name, for hive: agent/team ID
    agent_type = Column(String, default="agent", nullable=False)  # "agent" or "team" (hive-specific distinction)
    agent_timeout = Column(Integer, default=60, nullable=False)  # Works for both (hive uses 30, automagik 60)
    agent_stream_mode = Column(Boolean, default=False, nullable=False)  # Works for both (automagik: False, hive: True)
    
    # Legacy field for backward compatibility (will be removed in future migration)
    default_agent = Column(String, nullable=True)  # Deprecated, use agent_id instead

    # Automagik instance identification (for UI display)
    automagik_instance_id = Column(String, nullable=True)
    automagik_instance_name = Column(String, nullable=True)

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

    def is_hive_enabled(self) -> bool:
        """Check if this instance is configured for AutomagikHive."""
        return self.agent_instance_type == "hive"
    
    def is_automagik_enabled(self) -> bool:
        """Check if this instance is configured for standard Automagik."""
        return self.agent_instance_type == "automagik"

    def has_complete_agent_config(self) -> bool:
        """Check if instance has complete agent configuration (works for both types)."""
        return (
            bool(self.agent_api_url) and 
            bool(self.agent_api_key) and
            bool(self.agent_id)
        )
    
    @property
    def streaming_enabled(self) -> bool:
        """Property for compatibility with message router streaming logic."""
        return self.is_hive_enabled() and self.agent_stream_mode
    
    def get_agent_config(self) -> dict:
        """Get agent configuration as dictionary (unified for both types)."""
        return {
            "instance_type": self.agent_instance_type,
            "api_url": self.agent_api_url,
            "api_key": self.agent_api_key,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "timeout": self.agent_timeout,
            "stream_mode": self.agent_stream_mode
        }

    # Legacy methods for backward compatibility
    def has_hive_config(self) -> bool:
        """Legacy method for backward compatibility."""
        return self.is_hive_enabled() and self.has_complete_agent_config()
    
    def get_hive_config(self) -> dict:
        """Legacy method for backward compatibility."""
        if not self.is_hive_enabled():
            return {}
        
        return {
            "api_url": self.agent_api_url,
            "api_key": self.agent_api_key,
            "agent_id": self.agent_id if self.agent_type == "agent" else None,
            "team_id": self.agent_id if self.agent_type == "team" else None,
            "timeout": self.agent_timeout,
            "stream_mode": self.agent_stream_mode
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