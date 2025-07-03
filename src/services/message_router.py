"""
Message Router Service
Handles routing messages to the appropriate agent system.
Uses the Automagik API for user and session management.
"""

import logging
from typing import Dict, Any, Optional, Union, List

from src.services.agent_api_client import agent_api_client
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
        user: Optional[Dict[str, Any]] = None,
        session_name: str = None,
        message_type: str = "text",
        whatsapp_raw_payload: Optional[Dict[str, Any]] = None,
        session_origin: str = "whatsapp",
        agent_config: Optional[Dict[str, Any]] = None,
        media_contents: Optional[List[Dict[str, Any]]] = None,
        trace_context=None,
    ) -> str:
        """Route a message to the appropriate handler.

        Args:
            message_text: Message text
            user_id: User ID (optional if user dict is provided)
            user: User data dict with email, phone_number, and user_data for auto-creation
            session_name: Human-readable session name (required)
            message_type: Message type (default: "text")
            whatsapp_raw_payload: Raw WhatsApp payload (optional)
            session_origin: Session origin (default: "whatsapp")
            agent_config: Agent configuration (optional)
            media_contents: List of media content objects (optional)
            trace_context: TraceContext for message lifecycle tracking (optional)

        Returns:
            Response from the handler
        """
        # Use session_name if provided
        session_identifier = session_name

        logger.info(
            f"Routing message to API for user {user_id if user_id else 'new user'}, session {session_identifier}"
        )
        logger.info(f"Message text: {message_text}")
        logger.info(f"Session origin: {session_origin}")

        # Determine the agent name to use
        agent_name = config.agent_api.default_agent_name
        if agent_config and "name" in agent_config:
            agent_name = agent_config["name"]
        logger.info(f"Using agent name: {agent_name}")

        # If user_id is provided, prioritize it over user dict
        if user_id:
            logger.info(f"Using provided user_id: {user_id}")
            # Clear user dict to avoid confusion - we have a specific user ID
            user = None
        elif user:
            logger.info(
                f"Using user dict for automatic user creation: {user.get('phone_number', 'N/A')}"
            )
            user_id = None  # Let the API handle user creation
        elif not user_id:
            # No user_id provided and no user dict - let the instance-specific agent handle user creation
            logger.info(
                "No user_id provided - letting instance-specific agent API handle user creation"
            )
            user_id = None

        # Process the message through the Agent API
        try:
            # Use instance-specific API client if agent_config contains API details
            if agent_config and "api_url" in agent_config:
                # Create a per-instance agent API client
                from src.services.agent_api_client import AgentApiClient

                class InstanceConfig:
                    def __init__(
                        self,
                        name,
                        agent_api_url,
                        agent_api_key,
                        default_agent,
                        agent_timeout,
                    ):
                        self.name = name
                        self.agent_api_url = agent_api_url
                        self.agent_api_key = agent_api_key
                        self.default_agent = default_agent
                        self.agent_timeout = agent_timeout

                instance_override = InstanceConfig(
                    name=agent_config.get("name", "unknown"),
                    agent_api_url=agent_config.get("api_url"),
                    agent_api_key=agent_config.get("api_key"),
                    default_agent=agent_config.get("name"),
                    agent_timeout=agent_config.get("timeout", 60),
                )

                instance_agent_client = AgentApiClient(
                    config_override=instance_override
                )
                logger.info(
                    f"Using instance-specific agent API client: {agent_config.get('api_url')}"
                )

                response = instance_agent_client.process_message(
                    message=message_text,
                    user_id=user_id,
                    user=user,
                    session_name=session_identifier,
                    agent_name=agent_name,
                    message_type=message_type,
                    media_contents=media_contents,
                    channel_payload=whatsapp_raw_payload,
                    trace_context=trace_context,
                )
            else:
                # Use global agent API client
                logger.info(
                    f"Using global agent API client: {agent_api_client.api_url if agent_api_client else 'not configured'}"
                )
                response = agent_api_client.process_message(
                    message=message_text,
                    user_id=user_id,
                    user=user,
                    session_name=session_identifier,
                    agent_name=agent_name,
                    message_type=message_type,
                    media_contents=media_contents,
                    channel_payload=whatsapp_raw_payload,
                    trace_context=trace_context,
                )

            # Memory creation is handled by the Automagik Agents API, no need to create it here
            return response
        except Exception as e:
            logger.error(f"Error routing message: {e}", exc_info=True)
            return "Sorry, I encountered an error processing your message."


# Create a singleton instance
message_router = MessageRouter()
