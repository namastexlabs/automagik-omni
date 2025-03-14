"""
Message Router Service
Handles routing messages to the appropriate agent system.
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional

from src.config import config
from src.services.agent_api_client import agent_api_client

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
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        message_type: str = "text",
        whatsapp_raw_payload: Optional[Dict[str, Any]] = None,
        session_origin: str = "whatsapp",
        agent_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Route a message to the appropriate handler.
        
        Args:
            message_text: Message text
            user_id: User ID (optional)
            session_id: Session ID (optional)
            message_type: Message type (default: "text")
            whatsapp_raw_payload: Raw WhatsApp payload (optional)
            session_origin: Session origin (default: "whatsapp")
            agent_config: Agent configuration (optional)
            
        Returns:
            Response from the handler
        """
        logger.info(f"Routing message to API for user {user_id}, session {session_id}")
        logger.info(f"Message text: {message_text}")
        logger.info(f"Session origin: {session_origin}")
        
        # Determine the agent name to use
        agent_name = "stan_agent"
        if agent_config and "name" in agent_config:
            agent_name = agent_config["name"]
        logger.info(f"Using agent name: {agent_name}")
        
        # If user_id is None, use a default value
        if user_id is None:
            logger.warning(f"Using default user_id=0 as no user_id was provided")
            user_id = "0"
        
        # Convert UUID to string for serialization
        if isinstance(session_id, uuid.UUID):
            session_id = str(session_id)
            
        try:
            # Get agent response from API
            result = agent_api_client.run_agent(
                agent_name=agent_name,
                message_content=message_text,
                user_id=user_id,
                session_id=session_id,
                message_type=message_type,
                session_origin=session_origin,
                channel_payload=whatsapp_raw_payload
            )
            
            # Extract the response from the result
            if isinstance(result, dict):
                if "error" in result:
                    return result.get("error", "I'm sorry, I encountered an error.")
                elif "response" in result:
                    return result.get("response", "")
                else:
                    return str(result)
            else:
                return str(result)
                
        except Exception as e:
            logger.error(f"Error routing message: {e}", exc_info=True)
            return "I'm sorry, I encountered an error processing your request."

# Create a singleton instance
message_router = MessageRouter() 