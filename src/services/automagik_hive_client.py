"""
AutomagikHive Client - Async HTTP client for AutomagikHive API integration.

This client provides streaming capabilities for real-time agent/team conversations
using Server-Sent Events (SSE) and supports authentication, error recovery,
and connection management.
"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any, AsyncIterator, Union
from contextlib import asynccontextmanager

import httpx
from httpx import ConnectTimeout, ReadTimeout, TimeoutException, HTTPError

from .automagik_hive_models import (
    HiveEvent, HiveRunRequest, HiveContinueRequest, HiveRunResponse,
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
            self.api_url = config_override.hive_api_url
            self.api_key = config_override.hive_api_key
            self.default_agent_id = config_override.hive_agent_id
            self.default_team_id = config_override.hive_team_id
            self.timeout = config_override.hive_timeout
            self.stream_mode = config_override.hive_stream_mode
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
        if not self.default_agent_id:
            raise ValueError("AutomagikHive agent ID is required")
            
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
                        follow_redirects=True,
                        http2=True  # Enable HTTP/2 for better streaming
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
        agent_id: str,
        message: str,
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
        endpoint = f"{self.api_url}/playground/agents/{agent_id}/runs"
        
        request_data = HiveRunRequest(
            message=message,
            stream=stream,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata
        )
        
        if stream:
            return self._create_streaming_run(endpoint, request_data.dict())
        else:
            return await self._create_non_streaming_run(endpoint, request_data.dict())
    
    async def create_team_run(
        self,
        team_id: str,
        message: str,
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
        endpoint = f"{self.api_url}/playground/teams/{team_id}/runs"
        
        request_data = HiveRunRequest(
            message=message,
            stream=stream,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata
        )
        
        if stream:
            return self._create_streaming_run(endpoint, request_data.dict())
        else:
            return await self._create_non_streaming_run(endpoint, request_data.dict())
    
    async def continue_conversation(
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
        
        return self._create_streaming_run(endpoint, request_data.dict())
    
    async def _create_non_streaming_run(self, endpoint: str, payload: dict) -> HiveRunResponse:
        """Create a non-streaming run."""
        client = await self._get_client()
        headers = self._make_headers(accept_sse=False)
        
        try:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return HiveRunResponse(**data)
            
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
        """Create a streaming run and return event iterator."""
        client = await self._get_client()
        headers = self._make_headers(accept_sse=True)
        
        try:
            async with client.stream('POST', endpoint, json=payload, headers=headers) as response:
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
        Parse SSE events from streaming response.
        
        Args:
            response: httpx streaming response
            
        Yields:
            HiveEvent: Parsed event objects
        """
        buffer = ""
        
        try:
            async for chunk in response.aiter_bytes():
                if not chunk:
                    continue
                
                # Decode chunk to text
                try:
                    text = chunk.decode('utf-8')
                except UnicodeDecodeError as e:
                    logger.warning(f"Failed to decode chunk: {e}")
                    continue
                
                buffer += text
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    # Parse SSE format
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        
                        # Handle special SSE messages
                        if data == "[DONE]":
                            logger.info("AutomagikHive streaming response completed")
                            break
                        
                        # Parse JSON data
                        try:
                            event_data = json.loads(data)
                            event = parse_hive_event(event_data)
                            yield event
                            
                            # Break on completion event
                            if event.event == HiveEventType.RUN_COMPLETED:
                                logger.info(f"Run completed: {event.run_id}")
                                break
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSON event data: {data} - Error: {e}")
                            # Yield error event
                            error_event = ErrorEvent(
                                error_message=f"Failed to parse event data: {e}",
                                error_details={"raw_data": data}
                            )
                            yield error_event
                        except Exception as e:
                            logger.error(f"Failed to parse event: {e}")
                            # Yield error event
                            error_event = ErrorEvent(
                                error_message=f"Event parsing error: {e}",
                                error_details={"raw_data": data}
                            )
                            yield error_event
                    
                    elif line.startswith("event: "):
                        # Handle event type lines (could be used for more complex parsing)
                        event_type = line[7:]  # Remove "event: " prefix
                        logger.debug(f"Received event type: {event_type}")
                    
                    elif line.startswith("id: "):
                        # Handle event ID lines
                        event_id = line[4:]  # Remove "id: " prefix
                        logger.debug(f"Received event ID: {event_id}")
                    
                    elif line.startswith("retry: "):
                        # Handle retry time
                        retry_time = line[7:]  # Remove "retry: " prefix
                        logger.debug(f"Received retry time: {retry_time}")
                    
                    else:
                        logger.debug(f"Unknown SSE line format: {line}")
                        
        except Exception as e:
            logger.error(f"Error processing SSE stream: {e}")
            # Yield final error event
            error_event = ErrorEvent(
                error_message=f"Stream processing error: {e}",
                error_details={"error_type": type(e).__name__}
            )
            yield error_event
            raise AutomagikHiveStreamError(f"Stream processing failed: {e}")
    
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