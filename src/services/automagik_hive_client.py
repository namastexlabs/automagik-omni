"""
AutomagikHive Client - Async HTTP client for AutomagikHive API integration.
This client provides streaming capabilities for real-time agent/team conversations
using Server-Sent Events (SSE) and supports authentication, error recovery,
and connection management.
"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any, AsyncIterator, Union, List
from contextlib import asynccontextmanager
import httpx
from httpx import ConnectTimeout, ReadTimeout, TimeoutException
from .automagik_hive_models import (
    HiveEvent, HiveContinueRequest, HiveRunResponse,
    parse_hive_event, HiveEventType, ErrorEvent
)
from ..db.models import InstanceConfig

logger = logging.getLogger(__name__)

class AutomagikHiveError(Exception):
    """Base exception for AutomagikHive client errors."""
    pass

class AutomagikHiveAuthError(AutomagikHiveError):
    """Authentication error with AutomagikHive API."""
    pass

class AutomagikHiveConnectionError(AutomagikHiveError):
    """Connection error with AutomagikHive API."""
    pass

class AutomagikHiveStreamError(AutomagikHiveError):
    """Streaming error with AutomagikHive API."""
    pass

class AutomagikHiveClient:
    """
    Async client for interacting with the AutomagikHive API.

    Provides streaming capabilities for real-time agent and team conversations,
    with robust error handling and connection management.
    """

    def __init__(self, config_override: Optional[Union[InstanceConfig, Dict[str, Any]]] = None):
        """
        Initialize the AutomagikHive client.

        Args:
            config_override: Optional configuration override (InstanceConfig or dict)
        """
        # Extract configuration from InstanceConfig or dict
        if isinstance(config_override, InstanceConfig):
            # Try legacy fields first for backward compatibility, then unified fields
            self.api_url = (
                getattr(config_override, 'hive_api_url', None) or
                getattr(config_override, 'agent_api_url', None)
            )
            self.api_key = (
                getattr(config_override, 'hive_api_key', None) or
                getattr(config_override, 'agent_api_key', None)
            )
            self.default_agent_id = (
                getattr(config_override, 'hive_agent_id', None) or
                getattr(config_override, 'agent_id', None)
            )
            self.default_team_id = (
                getattr(config_override, 'hive_team_id', None) or
                getattr(config_override, 'team_id', None)
            )
            self.timeout = (
                getattr(config_override, 'hive_timeout', None) or
                getattr(config_override, 'agent_timeout', None) or
                30
            )
            self.stream_mode = (
                getattr(config_override, 'hive_stream_mode', None) or
                getattr(config_override, 'agent_stream_mode', None) or
                True
            )
        elif isinstance(config_override, dict):
            self.api_url = config_override.get('api_url')
            self.api_key = config_override.get('api_key')
            self.default_agent_id = config_override.get('agent_id')
            self.default_team_id = config_override.get('team_id')
            self.timeout = config_override.get('timeout', 30)
            self.stream_mode = config_override.get('stream_mode', True)
        else:
            raise ValueError("config_override must be InstanceConfig instance or dictionary")

        # Validate required configuration
        if not self.api_url:
            raise ValueError("AutomagikHive API URL is required")
        if not self.api_key:
            raise ValueError("AutomagikHive API key is required")
        # Note: agent_id is not required for team operations, will be provided per-call

        # Clean up API URL
        self.api_url = self.api_url.rstrip('/')

        # Connection management
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

        # Connection pool settings
        self._connection_limits = httpx.Limits(
            max_keepalive_connections=5,
            max_connections=10,
            keepalive_expiry=30.0
        )

        # Timeout configuration
        self._timeout_config = httpx.Timeout(
            connect=10.0,
            read=float(self.timeout),
            write=10.0,
            pool=5.0
        )

        logger.info(f"AutomagikHive client initialized - URL: {self.api_url}")

    def _make_headers(self, accept_sse: bool = False) -> Dict[str, str]:
        """Make headers for API requests with Bearer token authentication."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "automagik-omni/1.0"
        }

        if accept_sse:
            headers.update({
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            })
        else:
            headers.update({
                "Content-Type": "application/json",
                "Accept": "application/json"
            })

        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create an async HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            async with self._client_lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        limits=self._connection_limits,
                        timeout=self._timeout_config,
                        follow_redirects=True
                        # Note: HTTP/2 disabled due to missing h2 package
                    )
        return self._client

    async def close(self):
        """Close the HTTP client and clean up resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def create_agent_run(
        self,
        agent_id: Optional[str] = None,
        message: str = "",
        stream: bool = True,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Union[HiveRunResponse, AsyncIterator[HiveEvent]]:
        """
        Create a new agent run.

        Args:
            agent_id: Agent ID to interact with
            message: Message to send to the agent
            stream: Whether to enable streaming responses
            user_id: Optional user identifier
            session_id: Optional session identifier
            metadata: Optional additional metadata

        Returns:
            HiveRunResponse if stream=False, AsyncIterator[HiveEvent] if stream=True

        Raises:
            AutomagikHiveAuthError: Authentication failed
            AutomagikHiveConnectionError: Connection failed
            AutomagikHiveStreamError: Streaming error
        """
        if not agent_id:
            agent_id = self.default_agent_id
            if not agent_id:
                raise AutomagikHiveError("agent_id is required")

        endpoint = f"{self.api_url}/playground/agents/{agent_id}/runs"

        request_data = {
            "message": message,
            "stream": stream,
            "user_id": user_id,
            "session_id": session_id,
        }
        # Note: metadata not supported in form-data API

        if stream:
            return self._create_streaming_run(endpoint, request_data)
        else:
            return await self._create_non_streaming_run(endpoint, request_data)

    async def create_team_run(
        self,
        team_id: Optional[str] = None,
        message: str = "",
        stream: bool = True,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Union[HiveRunResponse, AsyncIterator[HiveEvent]]:
        """
        Create a new team run.

        Args:
            team_id: Team ID to interact with
            message: Message to send to the team
            stream: Whether to enable streaming responses
            user_id: Optional user identifier
            session_id: Optional session identifier
            metadata: Optional additional metadata

        Returns:
            HiveRunResponse if stream=False, AsyncIterator[HiveEvent] if stream=True
        """
        if not team_id:
            team_id = self.default_team_id
            if not team_id:
                raise AutomagikHiveError("team_id is required")

        endpoint = f"{self.api_url}/playground/teams/{team_id}/runs"

        request_data = {
            "message": message,
            "stream": stream,
            "user_id": user_id,
            "session_id": session_id,
        }
        # Note: metadata not supported in form-data API

        if stream:
            return self._create_streaming_run(endpoint, request_data)
        else:
            return await self._create_non_streaming_run(endpoint, request_data)

    def continue_conversation(
        self,
        run_id: str,
        message: str,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[HiveEvent]:
        """
        Continue an existing conversation.

        Args:
            run_id: Run ID to continue
            message: Follow-up message
            agent_id: Agent ID (uses default if not provided)
            user_id: Optional user identifier
            metadata: Optional additional metadata

        Returns:
            AsyncIterator[HiveEvent]: Stream of events
        """
        if not agent_id:
            agent_id = self.default_agent_id

        endpoint = f"{self.api_url}/playground/agents/{agent_id}/runs/{run_id}/continue"

        request_data = HiveContinueRequest(
            message=message,
            user_id=user_id,
            metadata=metadata
        )

        return self._create_streaming_run(endpoint, request_data.model_dump())

    async def _create_non_streaming_run(self, endpoint: str, payload: dict) -> Dict[str, Any]:
        """Create a non-streaming run using multipart/form-data."""
        client = await self._get_client()
        headers = {"Authorization": f"Bearer {self.api_key}"}  # Don't set Content-Type for multipart

        try:
            # Convert payload to form data, filtering out None values
            form_data = {k: str(v) for k, v in payload.items() if v is not None}

            response = await client.post(endpoint, data=form_data, headers=headers)
            response.raise_for_status()

            data = response.json()
            return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AutomagikHiveAuthError(f"Authentication failed: {e.response.text}")
            elif e.response.status_code == 404:
                raise AutomagikHiveError(f"Endpoint not found: {endpoint}")
            else:
                raise AutomagikHiveError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except (ConnectTimeout, ReadTimeout, TimeoutException) as e:
            raise AutomagikHiveConnectionError(f"Connection timeout: {str(e)}")
        except Exception as e:
            raise AutomagikHiveError(f"Unexpected error: {str(e)}")

    async def _create_streaming_run(self, endpoint: str, payload: dict) -> AsyncIterator[HiveEvent]:
        """Create a streaming run and return event iterator using multipart/form-data."""
        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }

        try:
            # Convert payload to form data, filtering out None values
            form_data = {k: str(v) for k, v in payload.items() if v is not None}

            async with client.stream('POST', endpoint, data=form_data, headers=headers) as response:
                if response.status_code == 401:
                    raise AutomagikHiveAuthError("Authentication failed")
                elif response.status_code == 404:
                    raise AutomagikHiveError(f"Endpoint not found: {endpoint}")
                elif response.status_code != 200:
                    error_text = await response.aread()
                    raise AutomagikHiveError(f"HTTP error {response.status_code}: {error_text.decode()}")

                async for event in self.stream_events(response):
                    yield event

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AutomagikHiveAuthError("Authentication failed")
            else:
                raise AutomagikHiveError(f"HTTP error: {e}")
        except (ConnectTimeout, ReadTimeout, TimeoutException) as e:
            raise AutomagikHiveConnectionError(f"Connection timeout: {str(e)}")
        except Exception as e:
            if isinstance(e, (AutomagikHiveError, AutomagikHiveAuthError, AutomagikHiveConnectionError)):
                raise
            raise AutomagikHiveStreamError(f"Streaming error: {str(e)}")

    async def stream_events(self, response) -> AsyncIterator[HiveEvent]:
        """
        Parse JSON-per-line events from streaming response.

        Hive sends JSON objects split across multiple lines, not standard SSE format.

        Args:
            response: httpx streaming response

        Yields:
            HiveEvent: Parsed event objects
        """
        buffer = ""
        json_buffer = ""
        chunk_count = 0
        line_count = 0
        json_object_count = 0
        event_count = 0

        logger.info("Starting JSON-per-line stream parsing...")

        try:
            async for chunk in response.aiter_bytes():
                if not chunk:
                    continue

                chunk_count += 1
                logger.debug(f"Received chunk #{chunk_count}: {len(chunk)} bytes")
                logger.debug(f"Raw chunk data: {chunk!r}")

                # Decode chunk to text
                try:
                    text = chunk.decode('utf-8')
                    logger.debug(f"Decoded chunk text: {text!r}")
                except UnicodeDecodeError as e:
                    logger.warning(f"Failed to decode chunk: {e}")
                    continue

                # Special handling: Check if this looks like concatenated JSON without newlines
                # Hive sometimes sends all JSON objects concatenated on a single line
                if text.startswith('{') and text.count('}{') > 0 and '\n' not in text:
                    logger.debug("Detected concatenated JSON objects in single chunk without newlines")
                    # Process immediately without line splitting
                    json_objects = self._split_concatenated_json(text)
                    if json_objects:
                        logger.debug(f"Successfully split chunk into {len(json_objects)} JSON objects")
                        for json_obj_str in json_objects:
                            try:
                                event_data = json.loads(json_obj_str)
                                json_object_count += 1
                                logger.debug(f"Parsed JSON object #{json_object_count} from chunk")

                                event = self._create_event_from_data(event_data)
                                if event:
                                    event_count += 1
                                    logger.debug(f"Created event #{event_count}: {type(event).__name__}")
                                    yield event

                                    if event.event == HiveEventType.RUN_COMPLETED:
                                        logger.info(f"Run completed: {event.run_id}")
                                        return
                            except json.JSONDecodeError as e:
                                logger.debug(f"Failed to parse split JSON: {e}")
                            except Exception as e:
                                logger.error(f"Error processing split JSON: {e}")
                        continue  # Skip line-by-line processing for this chunk

                buffer += text
                logger.debug(f"Buffer length: {len(buffer)}")

                # Check if buffer contains concatenated JSON (not SSE format)
                # This handles the case where Hive sends raw concatenated JSON
                if buffer.strip().startswith('{') and '}{' in buffer:
                    logger.debug("Buffer contains concatenated JSON, processing without line splitting")
                    json_buffer = buffer
                    buffer = ""  # Clear the buffer

                    # Try to split and process concatenated JSON
                    if json_buffer.count('}{') > 0:
                        json_objects = self._split_concatenated_json(json_buffer)
                        if json_objects:
                            logger.debug(f"Successfully split buffer into {len(json_objects)} JSON objects")
                            for json_obj_str in json_objects:
                                try:
                                    event_data = json.loads(json_obj_str)
                                    json_object_count += 1
                                    logger.debug(f"Parsed JSON object #{json_object_count}")

                                    event = self._create_event_from_data(event_data)
                                    if event:
                                        event_count += 1
                                        logger.debug(f"Created event #{event_count}: {type(event).__name__}")
                                        yield event

                                        if event.event == HiveEventType.RUN_COMPLETED:
                                            logger.info(f"Run completed: {event.run_id}")
                                            return
                                except json.JSONDecodeError as e:
                                    logger.debug(f"Failed to parse JSON: {e}")
                                except Exception as e:
                                    logger.error(f"Error processing JSON: {e}")
                            json_buffer = ""  # Clear after processing
                    continue  # Skip line-by-line processing

                # Process complete lines for SSE format
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    line_count += 1

                    logger.debug(f"Processing line #{line_count}: {line!r}")

                    if not line:
                        logger.debug("Empty line - skipping")
                        continue

                    # Handle standard SSE format if present
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        logger.debug(f"Found SSE data line: {data}")

                        # Handle special SSE messages
                        if data == "[DONE]":
                            logger.info("AutomagikHive streaming response completed")
                            break

                        # Try to parse as complete JSON
                        try:
                            event_data = json.loads(data)
                            json_object_count += 1
                            logger.debug(f"Parsed complete SSE JSON #{json_object_count}: {event_data}")

                            event = self._create_event_from_data(event_data)
                            if event:
                                event_count += 1
                                logger.debug(f"Created event #{event_count}: {type(event).__name__} - {event}")
                                yield event

                                # Break on completion event
                                if event.event == HiveEventType.RUN_COMPLETED:
                                    logger.info(f"Run completed: {event.run_id}")
                                    break

                        except json.JSONDecodeError:
                            # Not complete JSON, add to json_buffer
                            json_buffer += data
                            logger.debug(f"SSE data not complete JSON, added to buffer: {len(json_buffer)} chars")
                        continue

                    # For non-SSE lines, accumulate in json_buffer
                    json_buffer += line

                    logger.debug(f"Added line to JSON buffer: {line!r}")
                    logger.debug(f"JSON buffer now contains: {len(json_buffer)} chars")

                    # Check if buffer has been corrupted (missing opening brace)
                    if json_buffer.strip() and not json_buffer.strip().startswith('{'):
                        if json_buffer.strip().startswith('"') and '}{' in json_buffer:
                            # Buffer is missing the opening brace, add it back
                            logger.debug("Detected missing opening brace in buffer, fixing...")
                            json_buffer = '{' + json_buffer
                            logger.debug(f"Fixed buffer now starts with: {json_buffer[:50]}...")

                    # Try to parse the accumulated JSON - handle concatenated objects
                    json_objects = []
                    remaining_buffer = json_buffer

                    # First check if we have concatenated objects
                    if remaining_buffer.count('}{') > 0:
                        logger.debug("Detected concatenated JSON objects in buffer, attempting to split...")
                        json_objects = self._split_concatenated_json(remaining_buffer)
                        if json_objects:
                            logger.debug(f"Successfully split into {len(json_objects)} JSON objects")
                            remaining_buffer = ""  # Clear buffer since we split successfully
                        else:
                            logger.warning(f"Failed to split concatenated JSON, buffer content: {remaining_buffer[:500]}{'...' if len(remaining_buffer) > 500 else ''}")
                    else:
                        # Try to parse as single JSON object
                        try:
                            event_data = json.loads(remaining_buffer)
                            json_objects = [remaining_buffer]
                            remaining_buffer = ""  # Clear buffer since we parsed successfully
                        except json.JSONDecodeError as e:
                            # Not complete JSON object yet, continue accumulating
                            logger.debug(f"JSON not complete yet ({str(e)}), buffer length: {len(remaining_buffer)}")
                            continue

                    # Process all parsed JSON objects
                    for json_obj_str in json_objects:
                        try:
                            event_data = json.loads(json_obj_str)
                            json_object_count += 1
                            logger.debug(f"Parsed JSON object #{json_object_count}: {event_data}")

                            event = self._create_event_from_data(event_data)
                            if event:
                                event_count += 1
                                logger.debug(f"Created event #{event_count}: {type(event).__name__} - {event}")
                                yield event

                                # Break on completion event
                                if event.event == HiveEventType.RUN_COMPLETED:
                                    logger.info(f"Run completed: {event.run_id}")
                                    json_buffer = remaining_buffer  # Update buffer
                                    return  # Exit the entire stream processing

                        except json.JSONDecodeError as split_error:
                            logger.debug(f"Failed to parse JSON object: {split_error}")
                            logger.debug(f"Problematic JSON: {json_obj_str}")
                        except Exception as split_error:
                            logger.error(f"Error processing JSON object: {split_error}")

                    # Update buffer with any remaining content
                    json_buffer = remaining_buffer

            # Handle any remaining JSON in buffer at end of stream
            if json_buffer.strip():
                try:
                    # Try to parse as single JSON object first
                    event_data = json.loads(json_buffer)
                    json_object_count += 1
                    logger.debug(f"Parsed final JSON object #{json_object_count}: {event_data}")

                    event = self._create_event_from_data(event_data)
                    if event:
                        event_count += 1
                        logger.debug(f"Created final event #{event_count}: {type(event).__name__} - {event}")
                        yield event

                except json.JSONDecodeError as e:
                    # Try to split concatenated JSON objects
                    if json_buffer.count('}{') > 0:
                        logger.debug("Detected concatenated JSON objects in final buffer, attempting to split...")
                        json_objects = self._split_concatenated_json(json_buffer)

                        if json_objects:
                            logger.debug(f"Successfully split final buffer into {len(json_objects)} JSON objects")

                            # Process each JSON object
                            for json_obj_str in json_objects:
                                try:
                                    event_data = json.loads(json_obj_str)
                                    json_object_count += 1
                                    logger.debug(f"Parsed final split JSON object #{json_object_count}: {event_data}")

                                    event = self._create_event_from_data(event_data)
                                    if event:
                                        event_count += 1
                                        logger.debug(f"Created final event #{event_count}: {type(event).__name__} - {event}")
                                        yield event

                                except json.JSONDecodeError as split_error:
                                    logger.debug(f"Failed to parse final split JSON object: {split_error}")
                                    logger.debug(f"Problematic JSON: {json_obj_str}")
                                except Exception as split_error:
                                    logger.error(f"Error processing final split JSON object: {split_error}")
                        else:
                            logger.warning(f"Failed to parse final JSON buffer: {json_buffer} - Error: {e}")
                    else:
                        logger.warning(f"Failed to parse final JSON buffer: {json_buffer} - Error: {e}")
                except Exception as e:
                    logger.error(f"Failed to process final JSON object: {e}")

            logger.info(f"JSON stream parsing completed. Stats: {chunk_count} chunks, {line_count} lines, {json_object_count} JSON objects, {event_count} events created")

        except Exception as e:
            logger.error(f"Error processing JSON stream: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Yield final error event
            error_event = ErrorEvent(
                error_message=f"Stream processing error: {e}",
                error_details={"error_type": type(e).__name__}
            )
            yield error_event
            raise AutomagikHiveStreamError(f"Stream processing failed: {e}")

    def _split_concatenated_json(self, json_text: str) -> List[str]:
        """
        Split concatenated JSON objects into individual JSON strings.

        Handles cases where multiple JSON objects are concatenated without separators:
        {"event":"A"}{"event":"B"} -> ["{"event":"A"}", "{"event":"B"}"]

        Args:
            json_text: String potentially containing concatenated JSON objects

        Returns:
            List of individual JSON object strings
        """
        json_objects = []
        if not json_text.strip():
            return json_objects

        i = 0
        while i < len(json_text):
            # Skip whitespace
            while i < len(json_text) and json_text[i].isspace():
                i += 1

            if i >= len(json_text):
                break

            # Must start with opening brace
            if json_text[i] != '{':
                logger.warning(f"Expected '{{' at position {i}, found '{json_text[i]}' in: {json_text[i:i+50]}...")
                break

            # Find the matching closing brace
            brace_count = 0
            start = i
            in_string = False
            escape_next = False

            while i < len(json_text):
                char = json_text[i]

                if escape_next:
                    escape_next = False
                    i += 1
                    continue

                if char == '\\':
                    escape_next = True
                elif char == '"' and not escape_next:
                    in_string = not in_string
                elif not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # Found complete JSON object
                            json_obj = json_text[start:i+1]
                            json_objects.append(json_obj)
                            i += 1
                            break

                i += 1
            else:
                # Reached end without closing brace - treat as incomplete
                if brace_count > 0:
                    incomplete_json = json_text[start:]
                    logger.debug(f"Incomplete JSON object at end: {incomplete_json[:100]}...")

        return json_objects

    def _create_event_from_data(self, event_data: dict) -> Optional[HiveEvent]:
        """
        Create HiveEvent from parsed JSON data with event type mapping.

        Args:
            event_data: Parsed JSON event data

        Returns:
            HiveEvent instance or None if creation failed
        """
        try:
            # Handle TeamRunResponseContent -> RunResponseContent mapping
            if "event" in event_data:
                event_type = event_data["event"]
                if event_type == "TeamRunResponseContent":
                    event_data["event"] = "RunResponseContent"
                    logger.debug("Mapped event type 'TeamRunResponseContent' to 'RunResponseContent'")
                elif event_type == "TeamRunStarted":
                    event_data["event"] = "RunStarted"
                    logger.debug("Mapped event type 'TeamRunStarted' to 'RunStarted'")
                elif event_type == "TeamRunCompleted":
                    event_data["event"] = "RunCompleted"
                    logger.debug("Mapped event type 'TeamRunCompleted' to 'RunCompleted'")

            event = parse_hive_event(event_data)
            return event

        except Exception as e:
            logger.error(f"Failed to create event from data: {e}")
            logger.error(f"Event data: {event_data}")
            # Return error event instead of None
            error_event = ErrorEvent(
                error_message=f"Event creation failed: {e}",
                error_details={"raw_data": event_data}
            )
            return error_event

    @asynccontextmanager
    async def stream_agent_conversation(
        self,
        agent_id: Optional[str] = None,
        message: str = "",
        **kwargs
    ):
        """
        Context manager for streaming agent conversations.

        Usage:
            async with client.stream_agent_conversation("agent-id", "Hello") as stream:
                async for event in stream:
                    if event.event == HiveEventType.RUN_RESPONSE_CONTENT:
                        print(event.content)
        """
        if not agent_id:
            agent_id = self.default_agent_id

        try:
            stream = await self.create_agent_run(
                agent_id=agent_id,
                message=message,
                stream=True,
                **kwargs
            )
            yield stream
        except Exception as e:
            logger.error(f"Error in agent conversation stream: {e}")
            raise
        finally:
            # Cleanup is handled by the client's context manager
            pass

    @asynccontextmanager
    async def stream_team_conversation(
        self,
        team_id: Optional[str] = None,
        message: str = "",
        **kwargs
    ):
        """
        Context manager for streaming team conversations.

        Usage:
            async with client.stream_team_conversation("team-id", "Hello") as stream:
                async for event in stream:
                    if event.event == HiveEventType.RUN_RESPONSE_CONTENT:
                        print(event.content)
        """
        if not team_id:
            team_id = self.default_team_id
            if not team_id:
                raise ValueError("No team_id provided and no default team_id configured")

        try:
            stream = await self.create_team_run(
                team_id=team_id,
                message=message,
                stream=True,
                **kwargs
            )
            yield stream
        except Exception as e:
            logger.error(f"Error in team conversation stream: {e}")
            raise
        finally:
            # Cleanup is handled by the client's context manager
            pass

    async def health_check(self) -> bool:
        """
        Check if the AutomagikHive API is accessible.

        Returns:
            bool: True if API is accessible, False otherwise
        """
        try:
            client = await self._get_client()
            headers = self._make_headers()

            # Try a simple endpoint (adjust based on actual API)
            health_url = f"{self.api_url}/health"
            response = await client.get(health_url, headers=headers)

            return response.status_code == 200

        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    def __repr__(self) -> str:
        """String representation of the client without exposing sensitive data."""
        return f"<AutomagikHiveClient(api_url='{self.api_url}', agent_id='{self.default_agent_id}')>"

    def __str__(self) -> str:
        """String representation of the client."""
        return f"AutomagikHiveClient({self.api_url})"
