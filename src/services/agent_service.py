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

            # Global API client disabled - using instance-specific configurations
            logger.debug(
                "Global API health check skipped - using instance-specific configurations"
            )

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

    def process_whatsapp_message(
        self, data: Dict[str, Any], instance_config=None, trace_context=None
    ) -> Optional[str]:
        """Process a WhatsApp message and generate a response.

        Args:
            data: WhatsApp message data
            instance_config: InstanceConfig object with per-instance configuration

        Returns:
            Optional response text
        """
        logger.info("Processing WhatsApp message")
        logger.debug(f"Message data: {data}")
        if instance_config:
            logger.info(
                f"Using instance configuration: {instance_config.name} -> Agent: {instance_config.default_agent}"
            )

        # Handle system messages
        if data.get("messageType") in ["systemMessage"]:
            logger.info(f"Ignoring system message: {data.get('messageType')}")
            return None

        # Import the WhatsApp handler here to avoid circular imports
        from src.channels.whatsapp.handlers import message_handler

        # Let the WhatsApp handler process the message
        # The handler will take care of transcribing audio, extracting text, etc.
        # and will send the response directly to the user
        # Pass trace context for message lifecycle tracking
        message_handler.handle_message(data, instance_config, trace_context)

        # Since the handler sends the response directly, we return None here
        return None


# Create a singleton instance
agent_service = AgentService()
