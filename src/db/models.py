"""
SQLAlchemy models for multi-tenant instance configuration.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from .database import Base


class InstanceConfig(Base):
    """
    Instance configuration model for multi-tenant WhatsApp instances.
    Each instance can have different Evolution API and Agent API configurations.
    """
    __tablename__ = "instance_configs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Instance identification
    name = Column(String, unique=True, index=True, nullable=False)  # e.g., "flashinho_v2"
    
    # Evolution API configuration
    evolution_url = Column(String, nullable=False)
    evolution_key = Column(String, nullable=False)
    
    # WhatsApp instance configuration
    whatsapp_instance = Column(String, nullable=False)
    session_id_prefix = Column(String, nullable=True)
    
    # Agent API configuration
    agent_api_url = Column(String, nullable=False)
    agent_api_key = Column(String, nullable=False)
    default_agent = Column(String, nullable=False)
    agent_timeout = Column(Integer, default=60)
    
    # Default instance flag (for backward compatibility)
    is_default = Column(Boolean, default=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<InstanceConfig(name='{self.name}', is_default={self.is_default})>"