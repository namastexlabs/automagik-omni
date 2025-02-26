"""
Message Router Service
Handles routing messages to the appropriate agent system.
"""

import logging
from typing import Dict, Any, List, Optional

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
        pass
    
    def route_message(self, 
                      user_id: str, 
                      session_id: str, 
                      message_text: str, 
                      message_type: str,
                      conversation_history=None,  # Not used anymore with the API approach
                      agent_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Route a message to the agent API service and get a response.
        
        Args:
            user_id: The user ID
            session_id: The session ID
            message_text: The message text
            message_type: The message type (text, audio, etc.)
            conversation_history: List of previous messages (not used with API approach)
            agent_config: Optional configuration from the agent in the database
            
        Returns:
            The agent's response as a string
        """
        try:
            logger.info(f"Routing message to API for user {user_id}, session {session_id}")
            logger.info(f"Message text: {message_text}")
            logger.info(f"Message type: {message_type}")
            
            # Get agent name from config if available
            agent_name = agent_config.get("name", agent_api_client.default_agent_name) if agent_config else agent_api_client.default_agent_name
            
            # Use API client to call the agent API
            result = agent_api_client.run_agent(
                agent_name=agent_name,
                message_content=message_text,
                message_type=message_type,
                session_id=session_id,
                user_id=user_id,
                context={
                    "agent_config": agent_config or {}
                }
            )
            
            # Check for errors
            if "error" in result and result["error"] is not None:
                logger.error(f"Error from agent API: {result['error']}")
                if "details" in result:
                    logger.error(f"Error details: {result['details']}")
                return "I'm sorry, I encountered an error processing your request. Please try again later."
            
            # Extract the response text from the result
            # The API format might vary, so adjust this based on the actual response structure
            if isinstance(result, dict):
                # Try to find the response in the standard formats
                if "response" in result:
                    return result["response"]
                elif "message" in result:
                    return result["message"]
                elif "content" in result:
                    return result["content"]
                elif "text" in result:
                    return result["text"]
                else:
                    # If we can't find a standard format, return the raw response
                    logger.warning(f"Unexpected response format: {result}")
                    return str(result)
            else:
                # If it's not a dict, just convert to string and return
                return str(result)
            
        except Exception as e:
            logger.error(f"Error routing message: {e}", exc_info=True)
            return "I'm sorry, I encountered an error processing your request. Please try again later."


# Singleton instance
message_router = MessageRouter() 