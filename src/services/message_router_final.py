"""
Message Router Service - Enhanced Version
Handles routing messages to the appropriate agent system.
Supports multiple routing backends: Agent API and AutomagikHive.
Provides intelligent routing with fallback capabilities.
"""
import logging
import asyncio
from typing import Dict, Any, Optional, Union, List, AsyncIterator
from enum import Enum
from src.services.agent_api_client import agent_api_client
from src.services.automagik_hive_client import AutomagikHiveClient
from src.services.async_http_client import HiveEvent, HiveRunResponse

# Configure logging
logger = logging.getLogger("src.services.message_router")

class RouteType(Enum):
    """Supported routing types."""
    AGENT = "agent"      # Route to Agent API only
    HIVE = "hive"        # Route to AutomagikHive only
    HYBRID = "hybrid"    # Try AutomagikHive first, fallback to Agent API

class ResponseFormat(Enum):
    """Response format types."""
    STREAMING = "streaming"       # Async streaming response
    NON_STREAMING = "non_streaming"  # Standard dict response

class MessageRouter:
    """
    Routes messages to the appropriate agent system.
    Supports Agent API and AutomagikHive backends with intelligent routing.
    """

    def __init__(self):
        """Initialize the MessageRouter."""
        self._hive_clients: Dict[str, AutomagikHiveClient] = {}  # Cache for hive clients
        logger.info("Enhanced message router initialized with AutomagikHive support")

    def _get_hive_client(self, instance_config) -> AutomagikHiveClient:
        """Get or create a cached AutomagikHive client for the instance."""
        if not instance_config or not hasattr(instance_config, 'has_hive_config'):
            raise ValueError("Instance configuration missing or invalid")
        
        if not instance_config.has_hive_config():
            raise ValueError("Instance does not have complete AutomagikHive configuration")
        
        # Use instance name/id as cache key
        cache_key = getattr(instance_config, 'name', str(id(instance_config)))
        
        if cache_key not in self._hive_clients:
            logger.info(f"Creating new AutomagikHive client for instance: {cache_key}")
            self._hive_clients[cache_key] = AutomagikHiveClient(config_override=instance_config)
        
        return self._hive_clients[cache_key]

    def _determine_route_type(self, route_type: Optional[str], instance_config, agent_config: Optional[Dict[str, Any]]) -> RouteType:
        """Determine the appropriate route type based on configuration."""
        if route_type:
            try:
                return RouteType(route_type)
            except ValueError:
                logger.warning(f"Invalid route_type '{route_type}', falling back to auto-detection")
        
        # Auto-detection logic
        has_hive = instance_config and hasattr(instance_config, 'has_hive_config') and instance_config.has_hive_config()
        has_agent = agent_config or (agent_api_client and hasattr(agent_api_client, 'api_url'))
        
        if has_hive and has_agent:
            return RouteType.HYBRID  # Both available - use hybrid for best reliability
        elif has_hive:
            return RouteType.HIVE    # Only hive available
        else:
            return RouteType.AGENT   # Default to agent API
    
    async def _route_to_hive(
        self,
        instance_config,
        message_text: str,
        user_id: Optional[Union[str, int]],
        session_name: Optional[str],
        stream: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Union[Dict[str, Any], AsyncIterator[HiveEvent]]:
        """Route message to AutomagikHive."""
        try:
            hive_client = self._get_hive_client(instance_config)
            
            # Prepare AutomagikHive parameters
            hive_agent_id = instance_config.hive_agent_id
            hive_user_id = str(user_id) if user_id else None
            hive_session_id = session_name
            
            logger.info(f"Routing to AutomagikHive - Agent: {hive_agent_id}, User: {hive_user_id}, Session: {hive_session_id}, Stream: {stream}")
            
            response = await hive_client.create_agent_run(
                agent_id=hive_agent_id,
                message=message_text,
                stream=stream,
                user_id=hive_user_id,
                session_id=hive_session_id,
                metadata=metadata
            )
            
            if stream:
                # Return streaming response directly
                return response
            else:
                # Normalize non-streaming response to Agent API format
                return self._normalize_hive_response(response)
                
        except Exception as e:
            logger.error(f"Error routing to AutomagikHive: {e}", exc_info=True)
            raise

    def _route_to_agent(
        self,
        message_text: str,
        user_id: Optional[Union[str, int]],
        user: Optional[Dict[str, Any]],
        session_name: Optional[str],
        message_type: str,
        whatsapp_raw_payload: Optional[Dict[str, Any]],
        agent_config: Optional[Dict[str, Any]],
        media_contents: Optional[List[Dict[str, Any]]],
        trace_context
    ) -> Dict[str, Any]:
        """Route message to Agent API (existing logic)."""
        session_identifier = session_name
        
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
            user = None
        elif user:
            logger.info(f"Using user dict for automatic user creation: {user.get('phone_number', 'N/A')}")
            user_id = None
        elif not user_id:
            logger.info("No user_id provided - letting instance-specific agent API handle user creation")
            user_id = None
        
        # Process the message through the Agent API
        if agent_config and "api_url" in agent_config:
            # Create a per-instance agent API client
            from src.services.agent_api_client import AgentApiClient
            
            class InstanceConfig:
                def __init__(self, name, agent_api_url, agent_api_key, default_agent, agent_timeout):
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
            instance_agent_client = AgentApiClient(config_override=instance_override)
            logger.info(f"Using instance-specific agent API client: {agent_config.get('api_url')}")
            
            return instance_agent_client.process_message(
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
            logger.info(f"Using global agent API client: {agent_api_client.api_url if agent_api_client else 'not configured'}")
            
            return agent_api_client.process_message(
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

    def _normalize_hive_response(self, hive_response: Union[HiveRunResponse, Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize AutomagikHive response to Agent API format."""
        if isinstance(hive_response, dict):
            # Already in dict format
            response_dict = hive_response
        elif hasattr(hive_response, 'to_dict'):
            response_dict = hive_response.to_dict()
        else:
            # Fallback - convert to dict
            response_dict = {
                "content": str(hive_response),
                "source": "automagik_hive",
                "status": "success"
            }
        
        # Ensure consistent structure with Agent API response
        normalized = {
            "response": response_dict.get("content", response_dict.get("message", str(hive_response))),
            "source": "automagik_hive",
            "metadata": response_dict.get("metadata", {}),
            "status": response_dict.get("status", "success")
        }
        
        return normalized

    async def route_message(
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
        route_type: Optional[str] = None,
        instance_config=None,
        stream: bool = True,
    ) -> Union[str, Dict[str, Any], AsyncIterator[HiveEvent]]:
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
            route_type: Routing type ("agent", "hive", "hybrid") - auto-detected if not provided
            instance_config: Instance configuration object with hive settings
            stream: Enable streaming responses for supported backends

        Returns:
            Response from the handler - can be string, dict, or async iterator for streaming
        """
        session_identifier = session_name
        logger.info(f"Routing message to handler - User: {user_id if user_id else 'new user'}, Session: {session_identifier}")
        logger.info(f"Message text: {message_text}")
        logger.info(f"Session origin: {session_origin}")
        
        try:
            # Determine route type
            determined_route_type = self._determine_route_type(route_type, instance_config, agent_config)
            logger.info(f"Determined route type: {determined_route_type.value}")
            
            # Prepare metadata for hive calls
            hive_metadata = {
                "message_type": message_type,
                "session_origin": session_origin,
                "whatsapp_payload": whatsapp_raw_payload,
                "media_contents": media_contents,
                "trace_context_id": getattr(trace_context, 'trace_id', None) if trace_context else None
            }
            
            # Route based on determined type
            if determined_route_type == RouteType.HIVE:
                logger.info("Routing to AutomagikHive")
                return await self._route_to_hive(
                    instance_config, message_text, user_id, session_name, stream, hive_metadata
                )
                
            elif determined_route_type == RouteType.HYBRID:
                logger.info("Attempting hybrid routing - AutomagikHive first, Agent API fallback")
                try:
                    return await self._route_to_hive(
                        instance_config, message_text, user_id, session_name, stream, hive_metadata
                    )
                except Exception as hive_error:
                    logger.warning(f"AutomagikHive routing failed: {hive_error}, falling back to Agent API")
                    # Fallback to Agent API (non-streaming)
                    return self._route_to_agent(
                        message_text, user_id, user, session_name, message_type,
                        whatsapp_raw_payload, agent_config, media_contents, trace_context
                    )
                    
            else:  # RouteType.AGENT
                logger.info("Routing to Agent API")
                return self._route_to_agent(
                    message_text, user_id, user, session_name, message_type,
                    whatsapp_raw_payload, agent_config, media_contents, trace_context
                )
                
        except Exception as e:
            logger.error(f"Error in message routing: {e}", exc_info=True)
            return "Sorry, I encountered an error processing your message."

    # Backward compatibility method - wraps async route_message
    def route_message_sync(
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
        """Synchronous wrapper for backward compatibility."""
        logger.info("Using synchronous routing wrapper - streaming disabled")
        
        # Force non-streaming mode and Agent API routing for sync calls
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Force agent routing for sync calls to maintain compatibility
        result = loop.run_until_complete(
            self.route_message(
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
                route_type="agent",  # Force agent routing for sync
                stream=False
            )
        )
        
        return result

    # LEGACY METHOD: Maintain exact backward compatibility
    def route_message_legacy(
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
        """Legacy synchronous method - maintains exact original signature."""
        return self.route_message_sync(
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