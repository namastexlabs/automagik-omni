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
        
        # If no session ID provided, generate one
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"Generated new session ID: {session_id}")
        
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
                session_id=session_id,
                agent_name=agent_name
            )
            
            # Store the message and response as a memory
            try:
                # Convert user_id to int if it's a string digit, otherwise pass None for the user_id
                memory_user_id = None
                if user_id:
                    if isinstance(user_id, int):
                        memory_user_id = user_id
                    elif isinstance(user_id, str) and user_id.isdigit():
                        memory_user_id = int(user_id)
                    # If it's not a digit string or int, try to convert
                    elif isinstance(user_id, str):
                        try:
                            memory_user_id = int(user_id)
                        except (ValueError, TypeError):
                            # If conversion fails, use default
                            memory_user_id = 1
                    # If all else fails, use 1 as default
                    if memory_user_id is None:
                        memory_user_id = 1
                
                automagik_api_client.create_memory(
                    name=f"Message from {session_origin}",
                    content=f"User: {message_text}\nAgent: {response}",
                    user_id=memory_user_id,
                    session_id=session_id,
                    metadata={
                        "source": session_origin,
                        "message_type": message_type
                    }
                )
            except Exception as mem_err:
                logger.warning(f"Failed to create memory: {mem_err}")
                
            return response
        except Exception as e:
            logger.error(f"Error routing message: {e}", exc_info=True)
            return "Sorry, I encountered an error processing your message."

# Create a singleton instance
message_router = MessageRouter() 