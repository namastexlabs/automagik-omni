"""
Message Router Service
Handles routing messages to the appropriate agent system.
Uses the Automagik API for user and session management.
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional, Union

from src.config import config
from src.services.agent_api_client import agent_api_client
from src.services.automagik_api_client import automagik_api_client

# Configure logging
logger = logging.getLogger("src.services.message_router")

class MessageRouter:
    """
    Routes messages to the appropriate agent system.
    Uses the Automagik Agent API to handle message processing.
    """
    
    def __init__(self):
        """Initialize the MessageRouter."""
        logger.info("Message router initialized")
    
    def route_message(
        self,
        message_text: str,
        user_id: Optional[Union[str, int]] = None,
        session_id: Optional[str] = None,
        session_name: Optional[str] = None,
        message_type: str = "text",
        whatsapp_raw_payload: Optional[Dict[str, Any]] = None,
        session_origin: str = "whatsapp",
        agent_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Route a message to the appropriate handler.
        
        Args:
            message_text: Message text
            user_id: User ID (optional)
            session_id: Session ID (optional, legacy)
            session_name: Human-readable session name (optional, preferred)
            message_type: Message type (default: "text")
            whatsapp_raw_payload: Raw WhatsApp payload (optional)
            session_origin: Session origin (default: "whatsapp")
            agent_config: Agent configuration (optional)
            
        Returns:
            Response from the handler
        """
        # Use session_name if provided, otherwise use session_id
        session_identifier = session_name or session_id
        
        logger.info(f"Routing message to API for user {user_id}, session {session_identifier}")
        logger.info(f"Message text: {message_text}")
        logger.info(f"Session origin: {session_origin}")
        
        # Determine the agent name to use
        agent_name = "stan_agent"
        if agent_config and "name" in agent_config:
            agent_name = agent_config["name"]
        logger.info(f"Using agent name: {agent_name}")
        
        # If no session identifier provided, generate one
        if not session_identifier:
            session_identifier = str(uuid.uuid4())
            logger.info(f"Generated new session identifier: {session_identifier}")
        
        # If no user ID provided, try to create a user or use default
        if not user_id:
            try:
                # Create an anonymous user with minimal information
                user_response = automagik_api_client.create_user(
                    user_data={"source": session_origin}
                )
                if user_response:
                    user_id = user_response["id"]
                    logger.info(f"Created new user with ID: {user_id}")
                else:
                    # Fallback to a default user ID (1 is typically admin/system user)
                    user_id = 1
                    logger.warning(f"Failed to create user, using default ID: {user_id}")
            except Exception as e:
                # If user creation fails, use default user ID
                user_id = 1
                logger.error(f"Error creating user: {e}")
        
        # Process the message through the Agent API
        try:
            response = agent_api_client.process_message(
                message=message_text,
                user_id=user_id,
                session_id=session_identifier,
                agent_name=agent_name
            )
            
            # Memory creation is handled by the Automagik Agents API, no need to create it here
            return response
        except Exception as e:
            logger.error(f"Error routing message: {e}", exc_info=True)
            return "Sorry, I encountered an error processing your message."

# Create a singleton instance
message_router = MessageRouter() 