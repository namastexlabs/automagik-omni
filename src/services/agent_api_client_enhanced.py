"""
Agent API Client - Enhanced with Async SSE Support
Handles interaction with the Automagik Agents API with both sync and async capabilities.
This file provides backward compatibility while adding streaming support for AutomagikHive.
"""

import logging
import uuid
import json
import asyncio
from typing import Dict, Any, Optional, List, Union, AsyncIterator
from contextlib import asynccontextmanager

import requests
from requests.exceptions import RequestException, Timeout

# Import httpx for async operations  
try:
    import httpx
    from httpx import ConnectTimeout, ReadTimeout, TimeoutException, HTTPError
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

# Configure logging
logger = logging.getLogger("src.services.agent_api_client")

# Custom JSON encoder that handles UUID objects
class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)

class AgentApiClient:
    """Synchronous client for interacting with the Automagik Agents API (original implementation)."""

    def __init__(self, config_override=None):
        """Initialize the API client."""
        if config_override:
            self.api_url = config_override.agent_api_url
            self.api_key = config_override.agent_api_key
            self.default_agent_name = config_override.default_agent
            self.timeout = config_override.agent_timeout
            logger.info(
                f"Agent API client initialized for instance '{config_override.name}' with URL: {self.api_url}"
            )
        else:
            self.api_url = ""
            self.api_key = ""
            self.default_agent_name = ""
            self.timeout = 60
            logger.debug(
                "Agent API client initialized without instance config - using default values"
            )

        # Configuration will be validated when actually needed

        self.is_healthy = False

    def _make_headers(self) -> Dict[str, str]:
        """Make headers for API requests."""
        headers = {"Content-Type": "application/json", "x-api-key": self.api_key}
        return headers

    def health_check(self) -> bool:
        """Check if the API is healthy."""
        try:
            url = f"{self.api_url}/health"
            response = requests.get(url, timeout=5)
            self.is_healthy = response.status_code == 200
            return self.is_healthy
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.is_healthy = False
            return False

    def run_agent(
        self,
        agent_name: str,
        message_content: str,
        message_type: Optional[str] = None,
        media_url: Optional[str] = None,
        mime_type: Optional[str] = None,
        media_contents: Optional[List[Dict[str, Any]]] = None,
        channel_payload: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        session_name: Optional[str] = None,
        user_id: Optional[Union[str, int]] = None,
        user: Optional[Dict[str, Any]] = None,
        message_limit: int = 100,
        session_origin: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        preserve_system_prompt: bool = False,
    ) -> Dict[str, Any]:
        """Run an agent with the provided parameters."""
        endpoint = f"{self.api_url}/api/v1/agent/{agent_name}/run"
        headers = self._make_headers()
        payload = {"message_content": message_content, "message_limit": message_limit}

        # Handle user identification - prefer user dict over user_id
        if user:
            payload["user"] = user
            logger.info(f"Using user dict for automatic user creation: {user.get('phone_number', 'N/A')}")
        elif user_id is not None:
            if isinstance(user_id, str):
                try:
                    uuid.UUID(user_id)
                    logger.debug(f"Using UUID string for user_id: {user_id}")
                except ValueError:
                    if user_id.isdigit():
                        user_id = int(user_id)
                    elif user_id.lower() == "anonymous":
                        user_id = 1
                    else:
                        logger.warning(f"Invalid user_id format: {user_id}, using default user ID 1")
                        user_id = 1
            elif not isinstance(user_id, int):
                logger.warning(f"Unexpected user_id type: {type(user_id)}, using default user ID 1")
                user_id = 1
            payload["user_id"] = user_id
        else:
            logger.warning("Neither user dict nor user_id provided, using default user ID 1")
            payload["user_id"] = 1

        # Add optional parameters
        if message_type:
            payload["message_type"] = message_type
        if media_url:
            payload["mediaUrl"] = media_url
        if mime_type:
            payload["mime_type"] = mime_type
        if media_contents:
            payload["media_contents"] = media_contents
        if channel_payload:
            payload["channel_payload"] = channel_payload
        if session_name:
            payload["session_name"] = session_name
        elif session_id:
            payload["session_id"] = session_id
        if context:
            payload["context"] = context
        if session_origin:
            payload["session_origin"] = session_origin
        payload["preserve_system_prompt"] = preserve_system_prompt

        logger.info(f"Making API request to {endpoint}")
        payload_summary = {
            "message_length": len(payload.get("message_content", "")),
            "user_id": payload.get("user_id"),
            "session_name": payload.get("session_name"),
            "message_type": payload.get("message_type"),
            "media_contents_count": len(payload.get("media_contents", [])),
            "has_context": bool(payload.get("context")),
        }
        logger.debug(f"Request payload summary: {json.dumps(payload_summary)}")

        try:
            logger.info(f"Sending request to agent API with timeout: {self.timeout}s")
            response = requests.post(endpoint, headers=headers, json=payload, timeout=self.timeout)
            logger.info(f"API response status: {response.status_code}")

            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict):
                        message_text = response_data.get("message", "")
                        session_id = response_data.get("session_id", "unknown")
                        success = response_data.get("success", True)
                        message_length = len(message_text) if isinstance(message_text, str) else "non-string message"
                        logger.info(f"Received response from agent ({message_length} chars), session: {session_id}, success: {success}")
                        return response_data
                    else:
                        logger.warning(f"Agent response is not a dict, wrapping: {type(response_data)}")
                        return {
                            "message": str(response_data),
                            "success": True,
                            "session_id": None,
                            "tool_calls": [],
                            "tool_outputs": [],
                            "usage": {},
                        }
                except json.JSONDecodeError:
                    text_response = response.text
                    logger.warning(f"Response was not valid JSON, using raw text: {text_response[:100]}...")
                    return {
                        "message": text_response,
                        "success": True,
                        "session_id": None,
                        "tool_calls": [],
                        "tool_outputs": [],
                        "usage": {},
                    }
            else:
                logger.error(f"Error from agent API: {response.status_code} (response: {len(response.text)} chars)")
                return {
                    "error": f"Desculpe, encontrei um erro (status {response.status_code}).",
                    "details": f"Response length: {len(response.text)} chars",
                }

        except Timeout:
            logger.error(f"Timeout calling agent API after {self.timeout}s")
            return {
                "error": "Desculpe, está demorando mais do que o esperado para responder. Por favor, tente novamente.",
                "success": False,
                "session_id": None,
                "tool_calls": [],
                "tool_outputs": [],
                "usage": {},
            }
        except RequestException as e:
            logger.error(f"Error calling agent API: {e}")
            return {
                "error": "Desculpe, encontrei um erro ao me comunicar com meu cérebro. Por favor, tente novamente.",
                "success": False,
                "session_id": None,
                "tool_calls": [],
                "tool_outputs": [],
                "usage": {},
            }
        except Exception as e:
            logger.error(f"Unexpected error calling agent API: {e}", exc_info=True)
            return {
                "error": "Desculpe, encontrei um erro inesperado. Por favor, tente novamente.",
                "success": False,
                "session_id": None,
                "tool_calls": [],
                "tool_outputs": [],
                "usage": {},
            }

    def get_session_info(self, session_name: str) -> Optional[Dict[str, Any]]:
        """Get session information from the agent API."""
        endpoint = f"{self.api_url}/api/v1/sessions/{session_name}"
        try:
            response = requests.get(endpoint, headers=self._make_headers(), timeout=self.timeout)
            if response.status_code == 200:
                session_data = response.json()
                logger.debug(f"Retrieved session info for {session_name}: user_id={session_data.get('user_id')}")
                return session_data
            elif response.status_code == 404:
                logger.warning(f"Session {session_name} not found")
                return None
            else:
                logger.warning(f"Unexpected response getting session {session_name}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting session info for {session_name}: {str(e)}")
            return None

    def list_agents(self) -> List[Dict[str, Any]]:
        """Get a list of available agents."""
        endpoint = f"{self.api_url}/api/v1/agent/list"
        try:
            response = requests.get(endpoint, headers=self._make_headers(), timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}", exc_info=True)
            return []

    def process_message(
        self,
        message: str,
        user_id: Optional[Union[str, int]] = None,
        user: Optional[Dict[str, Any]] = None,
        session_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        message_type: str = "text",
        media_url: Optional[str] = None,
        media_contents: Optional[List[Dict[str, Any]]] = None,
        mime_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        channel_payload: Optional[Dict[str, Any]] = None,
        session_origin: Optional[str] = None,
        preserve_system_prompt: bool = False,
        trace_context=None,
    ) -> Dict[str, Any]:
        """Process a message using the agent API."""
        if not agent_name:
            agent_name = self.default_agent_name

        # Log agent request if tracing enabled
        if trace_context:
            agent_request_payload = {
                "agent_name": agent_name,
                "message_content": message,
                "user_id": user_id,
                "user": user,
                "session_name": session_name,
                "message_type": message_type,
                "media_url": media_url,
                "media_contents": media_contents,
                "mime_type": mime_type,
                "context": context,
                "channel_payload": channel_payload,
                "session_origin": session_origin,
                "preserve_system_prompt": preserve_system_prompt,
            }
            trace_context.log_agent_request(agent_request_payload)

        import time
        start_time = time.time()

        result = self.run_agent(
            agent_name=agent_name,
            message_content=message,
            user_id=user_id,
            user=user,
            session_name=session_name,
            message_type=message_type,
            media_url=media_url,
            media_contents=media_contents,
            mime_type=mime_type,
            context=context,
            channel_payload=channel_payload,
            session_origin=session_origin,
            preserve_system_prompt=preserve_system_prompt,
        )

        processing_time = int((time.time() - start_time) * 1000)
        if trace_context:
            trace_context.log_agent_response(result, processing_time)

        # Fetch current session info
        current_user_id = None
        if session_name:
            try:
                session_info = self.get_session_info(session_name)
                if session_info and "user_id" in session_info:
                    current_user_id = session_info["user_id"]
                    logger.info(f"Session {session_name} current user_id: {current_user_id}")
            except Exception as e:
                logger.warning(f"Failed to fetch session info for {session_name}: {e}")
                current_user_id = None

        # Return response structure
        if isinstance(result, dict):
            if "error" in result:
                response = {
                    "message": result.get("error", "Desculpe, encontrei um erro."),
                    "success": False,
                    "session_id": None,
                    "tool_calls": [],
                    "tool_outputs": [],
                    "usage": {},
                    "error": result.get("details", ""),
                }
            else:
                response = result
        else:
            response = {
                "message": str(result),
                "success": True,
                "session_id": None,
                "tool_calls": [],
                "tool_outputs": [],
                "usage": {},
            }

        if current_user_id:
            response['current_user_id'] = current_user_id

        return response


# ASYNC EXTENSIONS FOR SSE STREAMING SUPPORT
if HTTPX_AVAILABLE:
    
    class AsyncAgentApiClient:
        """
        Async version of AgentApiClient with SSE streaming support.
        
        This client provides the async functionality needed for AutomagikHive integration,
        including Server-Sent Events streaming for real-time agent responses.
        """
        
        def __init__(self, config_override=None):
            """Initialize async client with same configuration as sync version."""
            if config_override:
                self.api_url = config_override.agent_api_url
                self.api_key = config_override.agent_api_key
                self.default_agent_name = config_override.default_agent
                self.timeout = config_override.agent_timeout
                logger.info(f"Async Agent API client initialized for instance '{config_override.name}'")
            else:
                self.api_url = ""
                self.api_key = ""
                self.default_agent_name = ""
                self.timeout = 60
                logger.warning("Async Agent API client initialized without config")
            
            if not self.api_key:
                logger.warning("Agent API key not set for async client")
            
            self.is_healthy = False
            self._client: Optional[httpx.AsyncClient] = None
            self._client_lock = asyncio.Lock()
            
            # High-performance connection pool settings
            self._connection_limits = httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0
            )
            
            # Robust timeout configuration with retry logic
            self._timeout_config = httpx.Timeout(
                connect=10.0,      # Connection timeout
                read=float(self.timeout),  # Read timeout (configurable)
                write=10.0,        # Write timeout
                pool=5.0           # Pool timeout
            )
        
        def _make_headers(self, accept_sse: bool = False) -> Dict[str, str]:
            """Create headers for API requests with optional SSE support."""
            headers = {"x-api-key": self.api_key}
            
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
            """Get or create async HTTP client with connection pooling."""
            if self._client is None or self._client.is_closed:
                async with self._client_lock:
                    if self._client is None or self._client.is_closed:
                        self._client = httpx.AsyncClient(
                            limits=self._connection_limits,
                            timeout=self._timeout_config,
                            follow_redirects=True,
                            verify=True
                        )
            return self._client
        
        async def close(self):
            """Clean up HTTP client resources."""
            if self._client and not self._client.is_closed:
                await self._client.aclose()
                logger.debug("Async HTTP client closed")
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.close()
        
        async def health_check(self) -> bool:
            """Async health check with proper error handling."""
            try:
                url = f"{self.api_url}/health"
                client = await self._get_client()
                response = await client.get(url, timeout=5.0)
                self.is_healthy = response.status_code == 200
                logger.debug(f"Async health check result: {self.is_healthy}")
                return self.is_healthy
            except Exception as e:
                logger.error(f"Async health check failed: {e}")
                self.is_healthy = False
                return False
        
        async def run_agent_stream(
            self,
            agent_name: str,
            message_content: str,
            message_type: Optional[str] = None,
            media_url: Optional[str] = None,
            mime_type: Optional[str] = None,
            media_contents: Optional[List[Dict[str, Any]]] = None,
            channel_payload: Optional[Dict[str, Any]] = None,
            session_id: Optional[str] = None,
            session_name: Optional[str] = None,
            user_id: Optional[Union[str, int]] = None,
            user: Optional[Dict[str, Any]] = None,
            message_limit: int = 100,
            session_origin: Optional[str] = None,
            context: Optional[Dict[str, Any]] = None,
            preserve_system_prompt: bool = False,
        ) -> AsyncIterator[Dict[str, Any]]:
            """
            Stream agent responses using Server-Sent Events.
            
            This is the core streaming functionality for AutomagikHive integration.
            Yields real-time chunks of agent responses as they are generated.
            
            Args:
                All the same arguments as run_agent plus streaming-specific behavior
                
            Yields:
                Dict[str, Any]: Streaming response chunks with metadata:
                    - chunk_number: Sequential chunk identifier
                    - stream_active: Boolean indicating if stream is still active
                    - stream_ended: Boolean indicating if stream has completed
                    - error: Error message if something went wrong
                    - success: Boolean indicating success/failure
            """
            endpoint = f"{self.api_url}/api/v1/agent/{agent_name}/stream"
            
            # Prepare SSE headers
            headers = self._make_headers(accept_sse=True)
            
            # Build payload with same structure as sync version
            payload = {"message_content": message_content, "message_limit": message_limit}
            
            # Handle user identification (same logic as sync version)
            if user:
                payload["user"] = user
                logger.info(f"Streaming with user dict: {user.get('phone_number', 'N/A')}")
            elif user_id is not None:
                if isinstance(user_id, str):
                    try:
                        uuid.UUID(user_id)
                        logger.debug(f"Using UUID string: {user_id}")
                    except ValueError:
                        if user_id.isdigit():
                            user_id = int(user_id)
                        elif user_id.lower() == "anonymous":
                            user_id = 1
                        else:
                            logger.warning(f"Invalid user_id: {user_id}, using default")
                            user_id = 1
                elif not isinstance(user_id, int):
                    logger.warning(f"Unexpected user_id type: {type(user_id)}")
                    user_id = 1
                payload["user_id"] = user_id
            else:
                logger.warning("No user identification provided for streaming")
                payload["user_id"] = 1
            
            # Add all optional parameters
            if message_type:
                payload["message_type"] = message_type
            if media_url:
                payload["mediaUrl"] = media_url
            if mime_type:
                payload["mime_type"] = mime_type
            if media_contents:
                payload["media_contents"] = media_contents
            if channel_payload:
                payload["channel_payload"] = channel_payload
            if session_name:
                payload["session_name"] = session_name
            elif session_id:
                payload["session_id"] = session_id
            if context:
                payload["context"] = context
            if session_origin:
                payload["session_origin"] = session_origin
            payload["preserve_system_prompt"] = preserve_system_prompt
            
            logger.info(f"Starting streaming request to {endpoint}")
            
            try:
                client = await self._get_client()
                
                # Begin streaming request
                async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                    
                    if response.status_code != 200:
                        logger.error(f"Streaming failed: HTTP {response.status_code}")
                        yield {
                            "error": f"Streaming request failed (HTTP {response.status_code})",
                            "success": False,
                            "stream_ended": True
                        }
                        return
                    
                    logger.info("Streaming response started successfully")
                    
                    # Process Server-Sent Events
                    buffer = ""
                    chunk_count = 0
                    
                    async for chunk in response.aiter_text():
                        buffer += chunk
                        
                        # Process complete lines from buffer
                        while "\\n" in buffer:
                            line, buffer = buffer.split("\\n", 1)
                            line = line.strip()
                            
                            if not line:
                                continue
                            
                            # Handle SSE format
                            if line.startswith("data: "):
                                data = line[6:]  # Remove "data: " prefix
                                
                                # Check for stream completion
                                if data == "[DONE]":
                                    logger.info(f"Stream completed after {chunk_count} chunks")
                                    yield {"stream_ended": True, "success": True, "total_chunks": chunk_count}
                                    return
                                
                                # Parse JSON data
                                try:
                                    event_data = json.loads(data)
                                    chunk_count += 1
                                    
                                    # Add streaming metadata
                                    event_data.update({
                                        "chunk_number": chunk_count,
                                        "stream_active": True,
                                        "timestamp": int(asyncio.get_event_loop().time() * 1000)
                                    })
                                    
                                    yield event_data
                                    
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Invalid JSON in stream data: {e}")
                                    continue
                                    
                            elif line.startswith(("event: ", "id: ", "retry: ")):
                                # Handle other SSE fields for potential reconnection logic
                                continue
                
            except (ConnectTimeout, ReadTimeout, TimeoutException) as e:
                logger.error(f"Streaming timeout: {e}")
                yield {
                    "error": "Streaming request timed out. Please try again.",
                    "success": False,
                    "stream_ended": True,
                    "error_type": "timeout"
                }
            except HTTPError as e:
                logger.error(f"HTTP error during streaming: {e}")
                yield {
                    "error": "Network error during streaming. Please check connection.",
                    "success": False,
                    "stream_ended": True,
                    "error_type": "http_error"
                }
            except Exception as e:
                logger.error(f"Unexpected streaming error: {e}", exc_info=True)
                yield {
                    "error": "Unexpected error during streaming. Please try again.",
                    "success": False,
                    "stream_ended": True,
                    "error_type": "unexpected"
                }
        
        @asynccontextmanager
        async def stream_agent_messages(
            self, agent_name: str, message_content: str, **kwargs
        ) -> AsyncIterator[AsyncIterator[Dict[str, Any]]]:
            """
            Context manager for streaming agent responses with automatic cleanup.
            
            Usage:
                async with client.stream_agent_messages("agent", "Hello") as stream:
                    async for chunk in stream:
                        print(chunk)
            """
            try:
                stream = self.run_agent_stream(
                    agent_name=agent_name,
                    message_content=message_content,
                    **kwargs
                )
                yield stream
            except Exception as e:
                logger.error(f"Streaming context manager error: {e}")
                raise
            finally:
                logger.debug("Streaming context manager cleanup completed")
        
        # TODO: Implement fully async versions of these methods
        # For now, these use sync fallback but should be async in production
        
        async def run_agent(self, *args, **kwargs) -> Dict[str, Any]:
            """Async version of run_agent (currently uses sync fallback)."""
            # TODO: Implement fully async version
            sync_client = AgentApiClient()
            sync_client.api_url = self.api_url
            sync_client.api_key = self.api_key
            sync_client.default_agent_name = self.default_agent_name
            sync_client.timeout = self.timeout
            
            logger.debug("Using sync fallback for async run_agent")
            return sync_client.run_agent(*args, **kwargs)
        
        async def get_session_info(self, session_name: str) -> Optional[Dict[str, Any]]:
            """Async version of get_session_info."""
            endpoint = f"{self.api_url}/api/v1/sessions/{session_name}"
            
            try:
                client = await self._get_client()
                response = await client.get(endpoint, headers=self._make_headers())
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"Session {session_name} not found")
                    return None
                else:
                    logger.warning(f"Session lookup failed: HTTP {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error getting session info: {e}")
                return None
        
        async def list_agents(self) -> List[Dict[str, Any]]:
            """Async version of list_agents."""
            endpoint = f"{self.api_url}/api/v1/agent/list"
            
            try:
                client = await self._get_client()
                response = await client.get(endpoint, headers=self._make_headers())
                response.raise_for_status()
                return response.json()
                
            except Exception as e:
                logger.error(f"Error listing agents: {e}")
                return []

    # Create async client instance
    async_agent_api_client = AsyncAgentApiClient()
    logger.info("✅ Async Agent API client initialized with SSE streaming support")

else:
    # Create a dummy async client for compatibility when httpx is not available
    class AsyncAgentApiClient:
        def __init__(self, *args, **kwargs):
            logger.error("❌ AsyncAgentApiClient requires httpx - install with: pip install httpx>=0.28.0")
            raise ImportError("httpx required for async functionality")
    
    async_agent_api_client = None
    logger.warning("⚠️  Async functionality disabled - httpx not available")


# SINGLETON INSTANCES
# Original sync client (maintains backward compatibility)
agent_api_client = AgentApiClient()

# New async client for streaming operations (if available)
if HTTPX_AVAILABLE:
    async_agent_api_client = AsyncAgentApiClient()