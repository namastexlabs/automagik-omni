"""
Enhanced Message Router Service
Handles routing messages to the appropriate agent system.
Uses the Automagik API for user and session management.
Supports both traditional API routing and AutomagikHive streaming.
"""

import logging
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
            logger.info(f"Using user dict for automatic user creation: {user.get('phone_number', 'N/A')}")
            user_id = None  # Let the API handle user creation
        elif not user_id:
            # No user_id provided and no user dict - let the instance-specific agent handle user creation
            logger.info("No user_id provided - letting instance-specific agent API handle user creation")
            user_id = None

        # Process the message through the Agent API
        try:
            # Check if this is a Hive instance configuration
            is_hive = agent_config and agent_config.get("instance_type") == "hive"

            if is_hive and agent_config.get("instance_config"):
                # Use AutomagikHive client for Hive instances
                logger.info("Detected Hive instance configuration - using AutomagikHive client")
                from src.services.automagik_hive_client import AutomagikHiveClient

                instance_config = agent_config.get("instance_config")
                hive_client = AutomagikHiveClient(config_override=instance_config)

                # Determine if this is a team or agent
                agent_type = agent_config.get("agent_type", "agent")
                agent_id = agent_config.get("name")  # This should be the agent_id or team_id

                logger.info(f"Routing to Hive {agent_type}: {agent_id}")

                # Use synchronous wrapper for async Hive calls
                import asyncio

                async def call_hive():
                    try:
                        if agent_type == "team":
                            # Route to team
                            response = await hive_client.create_team_run(
                                team_id=agent_id,
                                message=message_text,
                                stream=agent_config.get("stream_mode", False),
                                session_id=session_identifier,
                                user_id=str(user_id) if user_id else None,
                                metadata={"user_data": user} if user else None,
                            )
                        else:
                            # Route to agent
                            response = await hive_client.create_agent_run(
                                agent_id=agent_id,
                                message=message_text,
                                stream=agent_config.get("stream_mode", False),
                                session_id=session_identifier,
                                user_id=str(user_id) if user_id else None,
                                metadata={"user_data": user} if user else None,
                            )

                        # Handle streaming vs non-streaming response
                        if agent_config.get("stream_mode", False):
                            # Stream response with newline-based chunking
                            logger.info("Processing Hive streaming response with real-time delivery...")
                            full_response = ""
                            event_count = 0
                            buffer = ""
                            responses = []

                            async for event in response:
                                event_count += 1
                                logger.info(
                                    f"Received streaming event #{event_count}: {type(event)} - {hasattr(event, 'content')}"
                                )
                                if hasattr(event, "content") and event.content:
                                    logger.info(f"Event content: {event.content[:100]}")
                                    buffer += event.content
                                    full_response += event.content

                                    # Check if buffer contains newline(s)
                                    while "\n" in buffer:
                                        # Split at the first newline
                                        line, buffer = buffer.split("\n", 1)
                                        if line.strip():  # Only send non-empty lines
                                            # Add the line to responses (will be sent as a chunk)
                                            responses.append(line)
                                            logger.info(f"Streaming chunk ready: {line[:100]}")

                            # Add any remaining buffer content
                            if buffer.strip():
                                responses.append(buffer)
                                logger.info(f"Final chunk: {buffer[:100]}")

                            logger.info(f"Streaming complete - {event_count} events received, {len(responses)} chunks")
                            logger.info(f"Final response length: {len(full_response)}")

                            # Return with streaming chunks for progressive sending
                            return {
                                "response": full_response,
                                "success": True,
                                "streaming_chunks": responses,
                            }
                        else:
                            # Non-streaming response
                            logger.info(f"Hive response received: {response}")
                            logger.info(f"Hive response type: {type(response)}")

                            # Hive API returns JSON with 'content' field
                            if isinstance(response, dict):
                                content = response.get("content", "")
                                if not content:
                                    # Fallback to raw response if no content field
                                    content = str(response)
                                    logger.warning(
                                        f"No 'content' field in Hive response, using fallback: {content[:100]}"
                                    )
                            else:
                                # Handle other response types
                                content = getattr(response, "content", str(response))

                            logger.info(f"Extracted content: {content[:200] if content else 'EMPTY'}")
                            return {"response": content, "success": True}
                    except Exception as e:
                        logger.error(f"Hive API error: {e}")
                        return {"response": str(e), "success": False}

                # Run the async function
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                response = loop.run_until_complete(call_hive())
                return response.get("response", "Error processing Hive request")

            elif agent_config and "api_url" in agent_config:
                # Use traditional Automagik API client
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
                instance_agent_client = AgentApiClient(config_override=instance_override)
                logger.info(f"Using instance-specific Automagik API client: {agent_config.get('api_url')}")
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
        from src.channels.whatsapp.streaming_integration_enhanced import (
            get_enhanced_streaming_instance,
        )
        from src.services.streaming_trace_context import StreamingTraceContext

        # Use session_name if provided
        session_identifier = session_name
        logger.info(
            f"Routing message to AutomagikHive streaming for user {user_id if user_id else 'new user'}, session {session_identifier}"
        )
        logger.info(f"Streaming to WhatsApp recipient: {recipient}")
        logger.info(f"Message text: {message_text}")

        try:
            # Convert trace_context to StreamingTraceContext if needed
            streaming_trace_context = trace_context
            if trace_context and not isinstance(trace_context, StreamingTraceContext):
                # Create a new streaming trace context with the same core data
                streaming_trace_context = StreamingTraceContext(
                    instance_name=trace_context.instance_name,
                    whatsapp_message_id=trace_context.whatsapp_message_id,
                    sender_phone=trace_context.sender_phone,
                    sender_name=trace_context.sender_name,
                    sender_jid=trace_context.sender_jid,
                    message_type=trace_context.message_type,
                    has_media=getattr(trace_context, "has_media", False),
                    has_quoted_message=getattr(trace_context, "has_quoted_message", False),
                    message_length=getattr(trace_context, "message_length", len(message_text)),
                    session_name=session_identifier,
                )
                logger.info("Converted standard trace context to streaming trace context")

            # Get the enhanced streaming instance for this configuration
            streaming_instance = get_enhanced_streaming_instance(instance_config)

            # Determine routing type based on instance configuration
            # First try unified schema
            if hasattr(instance_config, "is_hive") and instance_config.is_hive:
                if instance_config.agent_type == "team":
                    # Route to team streaming with enhanced tracing
                    logger.info(f"Streaming to AutomagikHive team: {instance_config.agent_id}")
                    success = await streaming_instance.stream_team_to_whatsapp_with_traces(
                        recipient=recipient,
                        team_id=instance_config.agent_id,
                        message=message_text,
                        trace_context=streaming_trace_context,
                        user_id=str(user_id) if user_id else None,
                    )
                else:
                    # Route to agent streaming with enhanced tracing
                    logger.info(f"Streaming to AutomagikHive agent: {instance_config.agent_id}")
                    success = await streaming_instance.stream_agent_to_whatsapp_with_traces(
                        recipient=recipient,
                        agent_id=instance_config.agent_id,
                        message=message_text,
                        trace_context=streaming_trace_context,
                        user_id=str(user_id) if user_id else None,
                    )
            # Backward compatibility with legacy fields
            elif hasattr(instance_config, "hive_agent_id") and instance_config.hive_agent_id:
                # Route to agent streaming with enhanced tracing
                logger.info(f"Streaming to AutomagikHive agent: {instance_config.hive_agent_id}")
                success = await streaming_instance.stream_agent_to_whatsapp_with_traces(
                    recipient=recipient,
                    agent_id=instance_config.hive_agent_id,
                    message=message_text,
                    trace_context=streaming_trace_context,
                    user_id=str(user_id) if user_id else None,
                )
            elif hasattr(instance_config, "hive_team_id") and instance_config.hive_team_id:
                # Route to team streaming with enhanced tracing
                logger.info(f"Streaming to AutomagikHive team: {instance_config.hive_team_id}")
                success = await streaming_instance.stream_team_to_whatsapp_with_traces(
                    recipient=recipient,
                    team_id=instance_config.hive_team_id,
                    message=message_text,
                    trace_context=streaming_trace_context,
                    user_id=str(user_id) if user_id else None,
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
        # Get agent config to check stream_mode (consistent with other streaming logic)
        agent_config = instance_config.get_agent_config()
        stream_mode = agent_config.get("stream_mode", False)

        logger.debug(f"Checking streaming for instance {instance_config.name}:")
        logger.debug(f"  - stream_mode from agent_config: {stream_mode}")
        logger.debug(f"  - agent_instance_type: {getattr(instance_config, 'agent_instance_type', None)}")
        logger.debug(f"  - is_hive property: {getattr(instance_config, 'is_hive', False)}")
        logger.debug(f"  - agent_api_url: {bool(getattr(instance_config, 'agent_api_url', None))}")
        logger.debug(f"  - agent_api_key: {bool(getattr(instance_config, 'agent_api_key', None))}")
        logger.debug(f"  - agent_id: {getattr(instance_config, 'agent_id', None)}")

        if not stream_mode:
            logger.debug("Streaming disabled: stream_mode is False")
            return False

        # For unified schema: check if this is a hive instance with streaming
        if hasattr(instance_config, "is_hive") and instance_config.is_hive:
            # Require API configuration
            if not instance_config.agent_api_url or not instance_config.agent_api_key:
                logger.debug("Streaming disabled: Missing API URL or key")
                return False
            # Require agent_id
            if not instance_config.agent_id:
                logger.debug("Streaming disabled: No agent_id configured")
                return False
            logger.debug("Streaming ENABLED for Hive instance")
            return True

        # Backward compatibility: check legacy hive fields
        if hasattr(instance_config, "hive_enabled") and instance_config.hive_enabled:
            if not instance_config.hive_api_url or not instance_config.hive_api_key:
                logger.debug("Streaming disabled (legacy): Missing Hive API URL or key")
                return False
            has_agent = hasattr(instance_config, "hive_agent_id") and instance_config.hive_agent_id
            has_team = hasattr(instance_config, "hive_team_id") and instance_config.hive_team_id
            if has_agent or has_team:
                logger.debug("Streaming ENABLED (legacy Hive fields)")
                return True
            logger.debug("Streaming disabled (legacy): No hive_agent_id or hive_team_id")
            return False

        logger.debug("Streaming disabled: Not a Hive instance")
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
            if hasattr(instance_config, "agent_api_url") and instance_config.agent_api_url:
                agent_config = {
                    "name": instance_config.name,
                    "api_url": instance_config.agent_api_url,
                    "api_key": instance_config.agent_api_key,
                    "timeout": getattr(instance_config, "agent_timeout", 60),
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
