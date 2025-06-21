"""
Service layer for Agent application.
This handles the coordination between the WhatsApp client and the agent API.
Database operations have been removed and replaced with API calls.
"""

import logging
import threading
from typing import Dict, Any, Optional

# We no longer need to import the WhatsApp client that uses RabbitMQ
# from src.channels.whatsapp.client import whatsapp_client
from src.services.automagik_api_client import automagik_api_client

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
        
        # Import the WhatsApp handler here to avoid circular imports
        from src.channels.whatsapp.handlers import message_handler
        
        # Let the WhatsApp handler process the message
        # The handler will take care of transcribing audio, extracting text, etc.
        # and will send the response directly to the user
        message_handler.handle_message(data)
        
        # Since the handler sends the response directly, we return None here
        return None
        
# Create a singleton instance
agent_service = AgentService() 