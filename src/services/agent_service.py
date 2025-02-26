"""
Service layer for Agent application.
This handles the coordination between the WhatsApp client, agent, and database.
"""

import logging
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from src.channels.whatsapp.client import whatsapp_client
from src.services.agent_api_client import agent_api_client
from src.db.engine import get_session
from src.db.repositories import (
    UserRepository,
    SessionRepository,
    ChatMessageRepository,
    AgentRepository,
    MemoryRepository
)
from src.db.models import User, Session, ChatMessage, Agent, Memory
from sqlalchemy.orm import Session as DbSession

# Configure logging
logger = logging.getLogger("src.services.agent_service")

class AgentService:
    """Service layer for Agent application."""
    
    def __init__(self):
        """Initialize the service."""
        self.lock = threading.Lock()
        # Track active sessions for simple caching
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def _initialize_default_agent(self):
        """Initialize the default WhatsApp agent if it doesn't exist."""
        logger.info("Checking for default WhatsApp agent...")
        
        with get_session() as db:
            agent_repo = AgentRepository(db)
            
            # Check if agent already exists
            existing_agent = agent_repo.get_active_agent(agent_name=agent_api_client.default_agent_name)
            if existing_agent:
                logger.info(f"Active WhatsApp agent already exists with ID: {existing_agent.id}")
                return existing_agent
            
            # Create new agent
            logger.info("No active WhatsApp agent found. Creating default agent...")
            if not existing_agent:
                logger.error("Failed to create default WhatsApp agent")
                raise RuntimeError("Failed to create default WhatsApp agent")
            
    
    def start(self):
        """Start the service."""
        logger.info("Starting Agent service...")
        
        # Initialize default agent
        self._initialize_default_agent()
        
        # Start the WhatsApp client
        success = whatsapp_client.start_async()
        if not success:
            logger.error("Failed to start WhatsApp client")
            return False
        
        logger.info("Agent service started successfully")
        return True
        
    def stop(self):
        """Stop the service."""
        logger.info("Stopping Agent service...")
        
        # Stop the WhatsApp client
        whatsapp_client.stop()
        
        logger.info("Agent service stopped successfully")

# Singleton instance
agent_service = AgentService() 