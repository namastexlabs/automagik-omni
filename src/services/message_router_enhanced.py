"""
Enhanced Message Router Service
Handles routing messages to the appropriate agent system.
Uses the Automagik API for user and session management.
Supports both traditional API routing and AutomagikHive streaming.
"""
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, Union, List
from src.services.agent_api_client import agent_api_client
from src.db.models import InstanceConfig

# Configure logging
logger = logging.getLogger("src.services.message_router")


class RouteType(Enum):
    """Route types for message routing."""
    AGENT = "agent"
    HIVE = "hive" 
    HYBRID = "hybrid"


class ResponseFormat(Enum):
    """Response format types."""
    DICT = "dict"
    STREAM = "stream"


class MessageRouter:
    """
    Routes messages to the appropriate agent system.
    Supports both traditional API routing and AutomagikHive streaming.
    """
    
    def __init__(self):
        """Initialize the MessageRouter."""
        logger.info("Enhanced message router initialized with AutomagikHive streaming support")
    
    def route_message(
        self,
        message_text: str,
        user_id: Optional[Union[str, int]] = None,
        user: Optional[Dict[str, Any]] = None,
        session_name: Optional[str] = None,
        message_type: str = "text",
        whatsapp_raw_payload: Optional[Dict[str, Any]] = None,
        session_origin: str = "whatsapp",
        agent_config: Optional[Dict[str, Any]] = None,
        media_contents: Optional[List[Dict[str, Any]]] = None,
        trace_context=None,
    ) -> Union[str, Dict[str, Any]]:
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
        agent_name = None
        if agent_config and "name" in agent_config:
            agent_name = agent_config["name"]
        
        # If no agent name is specified in the config, use a default
        if not agent_name:
            agent_name = "default"
        
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
    
    async def route_message_streaming(
        self,
        message_text: str,
        recipient: str,
        instance_config: InstanceConfig,
        user_id: Optional[Union[str, int]] = None,
        user: Optional[Dict[str, Any]] = None,
        session_name: Optional[str] = None,
        message_type: str = "text",
        whatsapp_raw_payload: Optional[Dict[str, Any]] = None,
        session_origin: str = "whatsapp",
        media_contents: Optional[List[Dict[str, Any]]] = None,
        trace_context=None,
    ) -> bool:
        """
        Route a message to AutomagikHive streaming for real-time WhatsApp delivery.
        
        Args:
            message_text: Message text
            recipient: WhatsApp recipient ID for streaming delivery
            instance_config: Instance configuration with AutomagikHive settings
            user_id: User ID (optional if user dict is provided)
            user: User data dict with email, phone_number, and user_data for auto-creation
            session_name: Human-readable session name (required)
            message_type: Message type (default: "text")
            whatsapp_raw_payload: Raw WhatsApp payload (optional)
            session_origin: Session origin (default: "whatsapp")
            media_contents: List of media content objects (optional)
            trace_context: TraceContext for message lifecycle tracking (optional)
            
        Returns:
            True if streaming was successful, False otherwise
        """
        # Import here to avoid circular imports
        from src.channels.whatsapp.streaming_integration import get_streaming_instance
        
        # Use session_name if provided
        session_identifier = session_name
        logger.info(
            f"Routing message to AutomagikHive streaming for user {user_id if user_id else 'new user'}, session {session_identifier}"
        )
        logger.info(f"Streaming to WhatsApp recipient: {recipient}")
        logger.info(f"Message text: {message_text}")
        
        try:
            # Get the streaming instance for this configuration
            streaming_instance = get_streaming_instance(instance_config)
            
            # Determine routing type based on instance configuration
            # First try unified schema
            if hasattr(instance_config, 'is_hive') and instance_config.is_hive:
                if instance_config.agent_type == 'team':
                    # Route to team streaming
                    logger.info(f"Streaming to AutomagikHive team: {instance_config.agent_id}")
                    success = await streaming_instance.stream_team_to_whatsapp(
                        recipient=recipient,
                        team_id=instance_config.agent_id,
                        message=message_text,
                        user_id=str(user_id) if user_id else None
                    )
                else:
                    # Route to agent streaming
                    logger.info(f"Streaming to AutomagikHive agent: {instance_config.agent_id}")
                    success = await streaming_instance.stream_agent_to_whatsapp(
                        recipient=recipient,
                        agent_id=instance_config.agent_id,
                        message=message_text,
                        user_id=str(user_id) if user_id else None
                    )
            # Backward compatibility with legacy fields
            elif hasattr(instance_config, 'hive_agent_id') and instance_config.hive_agent_id:
                # Route to agent streaming
                logger.info(f"Streaming to AutomagikHive agent: {instance_config.hive_agent_id}")
                success = await streaming_instance.stream_agent_to_whatsapp(
                    recipient=recipient,
                    agent_id=instance_config.hive_agent_id,
                    message=message_text,
                    user_id=str(user_id) if user_id else None
                )
            elif hasattr(instance_config, 'hive_team_id') and instance_config.hive_team_id:
                # Route to team streaming
                logger.info(f"Streaming to AutomagikHive team: {instance_config.hive_team_id}")
                success = await streaming_instance.stream_team_to_whatsapp(
                    recipient=recipient,
                    team_id=instance_config.hive_team_id,
                    message=message_text,
                    user_id=str(user_id) if user_id else None
                )
            else:
                logger.error("No AutomagikHive agent_id configured for streaming")
                return False
            
            if success:
                logger.info(f"AutomagikHive streaming completed successfully for {recipient}")
            else:
                logger.warning(f"AutomagikHive streaming failed for {recipient}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in AutomagikHive streaming for {recipient}: {e}", exc_info=True)
            return False
    
    def should_use_streaming(self, instance_config: InstanceConfig) -> bool:
        """
        Determine if streaming should be used for this instance.
        
        Args:
            instance_config: Instance configuration
            
        Returns:
            True if streaming should be used, False for traditional API routing
        """
        # Check if streaming is enabled (only Hive supports streaming)
        if not hasattr(instance_config, 'streaming_enabled') or not instance_config.streaming_enabled:
            return False
        
        # For unified schema: check if this is a hive instance with streaming
        if hasattr(instance_config, 'is_hive') and instance_config.is_hive:
            # Require API configuration
            if not instance_config.agent_api_url or not instance_config.agent_api_key:
                return False
            # Require agent_id
            if not instance_config.agent_id:
                return False
            return True
        
        # Backward compatibility: check legacy hive fields
        if hasattr(instance_config, 'hive_enabled') and instance_config.hive_enabled:
            if not instance_config.hive_api_url or not instance_config.hive_api_key:
                return False
            has_agent = hasattr(instance_config, 'hive_agent_id') and instance_config.hive_agent_id
            has_team = hasattr(instance_config, 'hive_team_id') and instance_config.hive_team_id
            return has_agent or has_team
        
        return False
    
    async def route_message_smart(
        self,
        message_text: str,
        recipient: str,
        instance_config: InstanceConfig,
        user_id: Optional[Union[str, int]] = None,
        user: Optional[Dict[str, Any]] = None,
        session_name: Optional[str] = None,
        message_type: str = "text",
        whatsapp_raw_payload: Optional[Dict[str, Any]] = None,
        session_origin: str = "whatsapp",
        media_contents: Optional[List[Dict[str, Any]]] = None,
        trace_context=None,
    ) -> Union[str, Dict[str, Any], bool]:
        """
        Smart routing that automatically chooses between traditional API and streaming.
        
        Args:
            message_text: Message text
            recipient: WhatsApp recipient ID for streaming delivery
            instance_config: Instance configuration
            user_id: User ID (optional if user dict is provided)
            user: User data dict with email, phone_number, and user_data for auto-creation
            session_name: Human-readable session name (required)
            message_type: Message type (default: "text")
            whatsapp_raw_payload: Raw WhatsApp payload (optional)
            session_origin: Session origin (default: "whatsapp")
            media_contents: List of media content objects (optional)
            trace_context: TraceContext for message lifecycle tracking (optional)
            
        Returns:
            For streaming: True if successful, False if failed
            For traditional API: Response string or dict from the handler
        """
        if self.should_use_streaming(instance_config):
            logger.info(f"Using AutomagikHive streaming for {recipient}")
            return await self.route_message_streaming(
                message_text=message_text,
                recipient=recipient,
                instance_config=instance_config,
                user_id=user_id,
                user=user,
                session_name=session_name,
                message_type=message_type,
                whatsapp_raw_payload=whatsapp_raw_payload,
                session_origin=session_origin,
                media_contents=media_contents,
                trace_context=trace_context,
            )
        else:
            logger.info(f"Using traditional API routing for {recipient}")
            # Convert instance_config to agent_config format for traditional routing
            agent_config = None
            if hasattr(instance_config, 'agent_api_url') and instance_config.agent_api_url:
                agent_config = {
                    "name": instance_config.name,
                    "api_url": instance_config.agent_api_url,
                    "api_key": instance_config.agent_api_key,
                    "timeout": getattr(instance_config, 'agent_timeout', 60),
                }
            
            return self.route_message(
                message_text=message_text,
                user_id=user_id,
                user=user,
                session_name=session_name,
                message_type=message_type,
                whatsapp_raw_payload=whatsapp_raw_payload,
                session_origin=session_origin,
                agent_config=agent_config,
                media_contents=media_contents,
                trace_context=trace_context,
            )


# Create a singleton instance
message_router = MessageRouter()