"""
SQLAlchemy models mapping to database tables.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Index, JSON, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=True)
    phone_number = Column(String(20), nullable=True)
    user_data = Column(JSON, nullable=True)  # Will store WhatsApp ID in user_data
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    sessions = relationship("Session", back_populates="user")
    memories = relationship("Memory", back_populates="user")
    messages = relationship("ChatMessage", back_populates="user")
    
    # Index
    __table_args__ = (
        Index("idx_users_email", email),
        Index("idx_users_phone_number", phone_number),
    )

class Session(Base):
    """Session model."""
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(String, nullable=False, default="whatsapp")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session")
    
    # Index
    __table_args__ = (
        Index("idx_sessions_user_id", user_id),
    )

class Memory(Base):
    """Memory model."""
    __tablename__ = "memories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="memories")
    
    # Index
    __table_args__ = (
        Index("idx_memories_user_id", user_id),
    )

class Agent(Base):
    """Agent model."""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(String, nullable=False, default="whatsapp")
    model = Column(String, nullable=False, default="builtin")
    version = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="agent")
    
    # Indexes
    __table_args__ = (
        Index("idx_agents_type", type),
        Index("idx_agents_active", active),
    )

class ChatMessage(Base):
    """Chat message model."""
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    text_content = Column(Text, nullable=True)
    media_url = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    message_type = Column(String, nullable=True)  # 'text', 'image', 'audio', etc.
    flagged = Column(String, nullable=True)
    user_feedback = Column(String, nullable=True)
    tool_calls = Column(JSON, nullable=True)
    tool_outputs = Column(JSON, nullable=True)
    raw_payload = Column(JSON, nullable=True)
    message_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    user = relationship("User", back_populates="messages")
    agent = relationship("Agent", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index("idx_chat_messages_session_id", session_id),
        Index("idx_chat_messages_user_id", user_id),
        Index("idx_chat_messages_agent_id", agent_id),
    ) 