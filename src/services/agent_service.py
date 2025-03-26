"""
Service layer for Agent application.
This handles the coordination between the WhatsApp client and the agent API.
Database operations have been removed and replaced with API calls.
"""

import logging
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union

# We no longer need to import the WhatsApp client that uses RabbitMQ
# from src.channels.whatsapp.client import whatsapp_client
from src.services.agent_api_client import agent_api_client
from src.services.automagik_api_client import automagik_api_client
from src.config import config

# Configure logging
logger = logging.getLogger("src.services.agent_service")

class AgentService:
    """Service layer for Agent application."""
    
    def __init__(self):
        """Initialize the service."""
        self.lock = threading.Lock()
        # Track active sessions for simple caching
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def start(self) -> bool:
        """Start the service."""
        logger.info("Starting agent service")
        
        try:
            # We no longer use the WhatsApp client with RabbitMQ
            # whatsapp_client.start()
            
            # Check if API is available
            if not automagik_api_client.health_check():
                logger.warning("Automagik API health check failed. Service may have limited functionality.")
            else:
                logger.info("Automagik API health check successful.")
            
            return True
        except Exception as e:
            logger.error(f"Error starting agent service: {e}", exc_info=True)
            return False
    
    def stop(self) -> None:
        """Stop the service."""
        logger.info("Stopping agent service")
        
        # We no longer use the WhatsApp client with RabbitMQ
        # whatsapp_client.stop()
        
        # No explicit cleanup needed for FastAPI-based service
        pass
    
    def process_whatsapp_message(self, data: Dict[str, Any]) -> Optional[str]:
        """Process a WhatsApp message and generate a response.
        
        Args:
            data: WhatsApp message data
            
        Returns:
            Optional response text
        """
        logger.info("Processing WhatsApp message")
        logger.debug(f"Message data: {data}")
        
        # Handle system messages
        if data.get("messageType") in ["systemMessage"]:
            logger.info(f"Ignoring system message: {data.get('messageType')}")
            return None
        
        # Extract the sender ID (WhatsApp phone number)
        sender = data.get("data", {}).get("key", {}).get("remoteJid", "")
        if not sender:
            logger.warning("Message missing remoteJid")
            return None
        
        # Remove @s.whatsapp.net suffix if present
        if "@" in sender:
            phone_number = sender.split("@")[0]
        else:
            phone_number = sender
            
        # Remove any + at the beginning
        if phone_number.startswith("+"):
            phone_number = phone_number[1:]
        
        logger.info(f"Extracted phone number: {phone_number}")
            
        # Get message content
        message_content = data.get("data", {}).get("message", {})
        if not message_content:
            logger.warning("Message missing content")
            return None
            
        # Extract text from various message types
        text_content = None
        
        if "conversation" in message_content:
            text_content = message_content.get("conversation", "")
        elif "extendedTextMessage" in message_content:
            text_content = message_content.get("extendedTextMessage", {}).get("text", "")
        elif "imageMessage" in message_content:
            # Handle image with caption
            text_content = message_content.get("imageMessage", {}).get("caption", "[Image]")
        elif "audioMessage" in message_content:
            # For audio messages, set a placeholder
            text_content = "[Audio]"
        
        # If we couldn't extract text, log and return
        if not text_content:
            logger.info("No text content found in message")
            text_content = "[Media message received]"
            
        logger.info(f"Extracted message text: {text_content}")
        
        # Handle empty messages
        if not text_content.strip():
            logger.info("Empty message received, ignoring")
            return None
            
        # Get or create user using the API
        user_info = automagik_api_client.get_or_create_user_by_phone(
            phone_number,
            user_data={
                "whatsapp_id": sender,
                "source": "whatsapp"
            }
        )
        
        if not user_info:
            logger.warning(f"Failed to get or create user for phone: {phone_number}, using default user")
            # Use default user ID instead of returning error
            user_id = 1 
        else:
            user_id = user_info["id"]
            logger.info(f"Using user ID: {user_id}")
        
        # Use session ID prefix from config + phone number
        session_id_prefix = config.whatsapp.session_id_prefix
        session_id = f"{session_id_prefix}{phone_number}"
        logger.info(f"Using session ID: {session_id}")
        
        # Process message through agent API
        try:
            # Process the message, ensuring user_id is passed correctly
            message_response = agent_api_client.process_message(
                message=text_content,
                user_id=user_id,
                session_name=session_id,
                session_origin="whatsapp",
                channel_payload=data
            )
            
            if message_response:
                logger.info(f"Agent response: {message_response}")
                # Memory creation is handled by the Automagik Agents API
                return message_response
            else:
                logger.warning("No response from agent")
                return None
                
        except Exception as e:
            logger.error(f"Error processing message with agent: {e}", exc_info=True)
            return "Sorry, I encountered an error processing your message."
            
        return None
        
# Create a singleton instance
agent_service = AgentService() 