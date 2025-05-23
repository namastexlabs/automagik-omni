"""
Message Router Service
Handles routing messages to the appropriate agent system.
Uses the Automagik API for user and session management.
"""

import logging
from typing import Dict, Any, Optional, Union, List

from src.services.agent_api_client import agent_api_client
from src.services.automagik_api_client import automagik_api_client
from src.config import config

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
        session_name: str = None,
        message_type: str = "text",
        whatsapp_raw_payload: Optional[Dict[str, Any]] = None,
        session_origin: str = "whatsapp",
        agent_config: Optional[Dict[str, Any]] = None,
        media_contents: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Route a message to the appropriate handler.
        
        Args:
            message_text: Message text
            user_id: User ID (optional)
            session_name: Human-readable session name (required)
            message_type: Message type (default: "text")
            whatsapp_raw_payload: Raw WhatsApp payload (optional)
            session_origin: Session origin (default: "whatsapp")
            agent_config: Agent configuration (optional)
            media_contents: List of media content objects (optional)
            
        Returns:
            Response from the handler
        """
        # Use session_name if provided
        session_identifier = session_name 
        
        logger.info(f"Routing message to API for user {user_id}, session {session_identifier}")
        logger.info(f"Message text: {message_text}")
        logger.info(f"Session origin: {session_origin}")
        
        # Determine the agent name to use
        agent_name = config.agent_api.default_agent_name
        if agent_config and "name" in agent_config:
            agent_name = agent_config["name"]
        logger.info(f"Using agent name: {agent_name}")
        
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
                session_name=session_identifier,
                agent_name=agent_name,
                message_type=message_type,
                media_contents=media_contents,
                channel_payload=whatsapp_raw_payload
            )
            
            # Memory creation is handled by the Automagik Agents API, no need to create it here
            return response
        except Exception as e:
            logger.error(f"Error routing message: {e}", exc_info=True)
            return "Sorry, I encountered an error processing your message."

# Create a singleton instance
message_router = MessageRouter() 