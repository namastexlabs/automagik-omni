"""
Repositories for database operations have been removed.
This file exists as a placeholder to maintain imports in other files.
All repository methods now raise NotImplementedError when called.
"""

import logging
from typing import Optional, List, Dict, Any, TypeVar, Generic, Type

# Import models to maintain compatibility with existing code
from src.db.models import User, Session as DbSession, Memory, Agent, ChatMessage

# Configure logging
logger = logging.getLogger("src.db.repositories")

# Define a generic type for models
T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Base repository for database operations."""
    
    def __init__(self, db: Any, model: Type[T] = None):
        self.db = db
        self.model = model
        logger.warning("Database operations have been removed")
    
    def get(self, id: Any) -> Optional[T]:
        """Get entity by ID."""
        raise NotImplementedError("Database operations have been removed")
    
    def list(self, **filters) -> List[T]:
        """List entities with optional filters."""
        raise NotImplementedError("Database operations have been removed")
    
    def add(self, entity: T) -> T:
        """Add a new entity to the database."""
        raise NotImplementedError("Database operations have been removed")


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""
    
    def __init__(self, db: Any):
        super().__init__(db, User)
    
    def get_by_phone(self, phone_number: str) -> Optional[User]:
        """Get user by phone number."""
        raise NotImplementedError("Database operations have been removed")
    
    def create(self, **kwargs) -> User:
        """Create a new user."""
        raise NotImplementedError("Database operations have been removed")


class SessionRepository(BaseRepository[DbSession]):
    """Repository for Session operations."""
    
    def __init__(self, db: Any):
        super().__init__(db, DbSession)
    
    def create(self, **kwargs) -> DbSession:
        """Create a new session."""
        raise NotImplementedError("Database operations have been removed")
    
    def get_or_create_for_user(self, user_id: int, platform: str = "whatsapp") -> DbSession:
        """Get or create a session for a user."""
        raise NotImplementedError("Database operations have been removed")


class MemoryRepository(BaseRepository[Memory]):
    """Repository for Memory operations."""
    
    def __init__(self, db: Any):
        super().__init__(db, Memory)
    
    def create(self, **kwargs) -> Memory:
        """Create a new memory."""
        raise NotImplementedError("Database operations have been removed")
    
    def get_for_user(self, user_id: int, limit: int = 10) -> List[Memory]:
        """Get memories for a user."""
        raise NotImplementedError("Database operations have been removed")


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """Repository for ChatMessage operations."""
    
    def __init__(self, db: Any):
        super().__init__(db, ChatMessage)
    
    def create_from_whatsapp(self, session_id: str, user_id: int, data: Dict[str, Any], override_text: Optional[str] = None) -> ChatMessage:
        """Create a chat message from a WhatsApp message payload."""
        raise NotImplementedError("Database operations have been removed")
    
    def create(self, **kwargs) -> ChatMessage:
        """Create a new chat message."""
        raise NotImplementedError("Database operations have been removed")
    
    def get_session_messages(self, session_id: str, limit: int = 50) -> List[ChatMessage]:
        """Get messages for a session."""
        raise NotImplementedError("Database operations have been removed")


class AgentRepository(BaseRepository[Agent]):
    """Repository for Agent operations."""
    
    def __init__(self, db: Any):
        super().__init__(db, Agent)
    
    def get_active_agent(self, agent_type: str = "whatsapp", agent_name: Optional[str] = None) -> Optional[Agent]:
        """Get the active agent for a platform."""
        raise NotImplementedError("Database operations have been removed")
    
    def create_agent_response(self, session_id: str, user_id: int, agent_id: int, 
                        text_content: str, tool_calls=None, tool_outputs=None, message_type="text",
                        id: Optional[str] = None) -> ChatMessage:
        """Create a chat message from the agent."""
        raise NotImplementedError("Database operations have been removed") 