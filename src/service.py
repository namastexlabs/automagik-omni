"""
Service layer for Stan application.
This handles the coordination between the WhatsApp client, agent, and database.
"""

import logging
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from src.channels.whatsapp.client import whatsapp_client
from src.agent.stan import StanAgent
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
logger = logging.getLogger("src.service")

class StanService:
    """Service layer for Stan application."""
    
    def __init__(self):
        """Initialize the service."""
        self.agent = StanAgent()
        self.lock = threading.Lock()
        # Track active sessions for simple caching
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def _initialize_default_agent(self):
        """Initialize the default WhatsApp agent if it doesn't exist."""
        logger.info("Checking for default WhatsApp agent...")
        
        with get_session() as db:
            agent_repo = AgentRepository(db)
            
            # Check if agent already exists
            existing_agent = agent_repo.get_active_agent(agent_type="whatsapp")
            if existing_agent:
                logger.info(f"Active WhatsApp agent already exists with ID: {existing_agent.id}")
                return existing_agent
            
            # Create new agent
            logger.info("No active WhatsApp agent found. Creating default agent...")
            agent = agent_repo.create(
                name="Stan WhatsApp Assistant",
                description="Default WhatsApp assistant for basic interactions",
                type="whatsapp",
                model="builtin",
                version="0.1.0",
                active=True,
                config={
                    "system_prompt": """
                    You are Stan, a friendly and helpful AI assistant on WhatsApp.
                    Your goal is to provide helpful, accurate, and friendly responses to user inquiries.
                    Be concise in your responses as this is a chat interface.
                    """
                }
            )
            
            logger.info(f"Created new WhatsApp agent with ID: {agent.id}")
            return agent
    
    def start(self):
        """Start the service."""
        logger.info("Starting Stan service...")
        
        # Initialize default agent
        self._initialize_default_agent()
        
        # Start the WhatsApp client
        success = whatsapp_client.start_async()
        if not success:
            logger.error("Failed to start WhatsApp client")
            return False
        
        logger.info("Stan service started successfully")
        return True
        
    def stop(self):
        """Stop the service."""
        logger.info("Stopping Stan service...")
        
        # Stop the WhatsApp client
        whatsapp_client.stop()
        
        logger.info("Stan service stopped successfully")

# Singleton instance
stan_service = StanService() 