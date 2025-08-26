"""
Updated AutomagikHive Client - Works with Unified Agent Fields

This client has been updated to work with the new unified field schema where
both automagik and hive configurations use the same field names.
"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any, AsyncIterator

import httpx
from httpx import ConnectTimeout, ReadTimeout, TimeoutException, HTTPError

from .automagik_hive_models import (
    HiveEvent, HiveRunRequest, HiveRunResponse,
    parse_hive_event, ErrorEvent
)

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


class UnifiedAutomagikHiveClient:
    """
    Updated AutomagikHive client that works with unified agent fields.
    
    Uses the new schema where both automagik and hive instances share the same field names:
    - agent_instance_type: "automagik" or "hive" 
    - agent_api_url: API endpoint
    - agent_api_key: API key
    - agent_id: Agent name (automagik) or agent/team ID (hive)
    - agent_type: "agent" or "team" (hive distinction)
    - agent_timeout: Request timeout
    - agent_stream_mode: Whether streaming is enabled
    """
    
    def __init__(self, instance_config, timeout_override: Optional[int] = None):
        """
        Initialize client with unified instance configuration.
        
        Args:
            instance_config: InstanceConfig with unified agent fields
            timeout_override: Override the configured timeout
        """
        
        # Validate that this is a hive instance
        if instance_config.agent_instance_type != "hive":
            raise ValueError(f"This client only works with hive instances, got: {instance_config.agent_instance_type}")
        
        if not instance_config.has_complete_agent_config():
            raise ValueError("Incomplete hive configuration")
        
        self.config = instance_config
        self.api_url = instance_config.agent_api_url.rstrip('/')
        self.api_key = instance_config.agent_api_key
        self.timeout = timeout_override or instance_config.agent_timeout
        self.stream_mode = instance_config.agent_stream_mode
        
        # Log configuration for debugging
        logger.info("Initialized UnifiedAutomagikHiveClient:")
        logger.info(f"  API URL: {self.api_url}")
        logger.info(f"  Agent Type: {instance_config.agent_type}")
        logger.info(f"  Agent ID: {instance_config.agent_id}")
        logger.info(f"  Timeout: {self.timeout}s")
        logger.info(f"  Stream Mode: {self.stream_mode}")
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def get_agent_config(self) -> Dict[str, Any]:
        """Get unified agent configuration."""
        return {
            "instance_type": self.config.agent_instance_type,
            "api_url": self.config.agent_api_url,
            "agent_id": self.config.agent_id,
            "agent_type": self.config.agent_type,
            "timeout": self.config.agent_timeout,
            "stream_mode": self.config.agent_stream_mode
        }
    
    async def run_agent_conversation(
        self, 
        message: str,
        user_id: Optional[str] = None,
        session_id: str = "default",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> HiveRunResponse:
        """
        Run a single agent conversation (non-streaming).
        
        Args:
            message: User message
            user_id: Optional user identifier
            session_id: Session identifier
            additional_context: Additional context for the conversation
            
        Returns:
            HiveRunResponse with the agent's response
        """
        
        if self.config.agent_type != "agent":
            raise ValueError("This method only works with agent instances, not teams")
        
        agent_id = self.config.agent_id
        
        request = HiveRunRequest(
            message=message,
            user_id=user_id,
            session_id=session_id,
            additional_context=additional_context or {}
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/agents/{agent_id}/run",
                    headers=self.headers,
                    json=request.dict(exclude_none=True)
                )
                response.raise_for_status()
                
                return HiveRunResponse(**response.json())
                
        except HTTPError as e:
            if e.response.status_code == 401:
                raise AutomagikHiveAuthError(f"Authentication failed: {e}")
            raise AutomagikHiveError(f"HTTP error: {e}")
        except (ConnectTimeout, ReadTimeout, TimeoutException) as e:
            raise AutomagikHiveConnectionError(f"Connection error: {e}")
        except Exception as e:
            raise AutomagikHiveError(f"Unexpected error: {e}")
    
    async def run_team_conversation(
        self,
        message: str,
        user_id: Optional[str] = None,
        session_id: str = "default",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> HiveRunResponse:
        """
        Run a team conversation (non-streaming).
        
        Args:
            message: User message
            user_id: Optional user identifier  
            session_id: Session identifier
            additional_context: Additional context for the conversation
            
        Returns:
            HiveRunResponse with the team's response
        """
        
        if self.config.agent_type != "team":
            raise ValueError("This method only works with team instances, not individual agents")
        
        team_id = self.config.agent_id
        
        request = HiveRunRequest(
            message=message,
            user_id=user_id,
            session_id=session_id,
            additional_context=additional_context or {}
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/teams/{team_id}/run",
                    headers=self.headers,
                    json=request.dict(exclude_none=True)
                )
                response.raise_for_status()
                
                return HiveRunResponse(**response.json())
                
        except HTTPError as e:
            if e.response.status_code == 401:
                raise AutomagikHiveAuthError(f"Authentication failed: {e}")
            raise AutomagikHiveError(f"HTTP error: {e}")
        except (ConnectTimeout, ReadTimeout, TimeoutException) as e:
            raise AutomagikHiveConnectionError(f"Connection error: {e}")
        except Exception as e:
            raise AutomagikHiveError(f"Unexpected error: {e}")
    
    async def stream_agent_conversation(
        self,
        message: str,
        user_id: Optional[str] = None,
        session_id: str = "default",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[HiveEvent]:
        """
        Stream an agent conversation.
        
        Args:
            message: User message
            user_id: Optional user identifier
            session_id: Session identifier
            additional_context: Additional context for the conversation
            
        Yields:
            HiveEvent objects from the streaming response
        """
        
        if not self.stream_mode:
            raise AutomagikHiveError("Streaming is not enabled for this instance")
        
        if self.config.agent_type != "agent":
            raise ValueError("This method only works with agent instances, not teams")
        
        agent_id = self.config.agent_id
        
        request = HiveRunRequest(
            message=message,
            user_id=user_id,
            session_id=session_id,
            additional_context=additional_context or {}
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_url}/agents/{agent_id}/stream",
                    headers={**self.headers, "Accept": "text/event-stream"},
                    json=request.dict(exclude_none=True)
                ) as response:
                    response.raise_for_status()
                    
                    async for event in self._parse_sse_stream(response):
                        yield event
                        
        except HTTPError as e:
            if e.response.status_code == 401:
                raise AutomagikHiveAuthError(f"Authentication failed: {e}")
            raise AutomagikHiveError(f"HTTP error: {e}")
        except (ConnectTimeout, ReadTimeout, TimeoutException) as e:
            raise AutomagikHiveConnectionError(f"Connection error: {e}")
        except Exception as e:
            raise AutomagikHiveStreamError(f"Streaming error: {e}")
    
    async def stream_team_conversation(
        self,
        message: str,
        user_id: Optional[str] = None,
        session_id: str = "default",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[HiveEvent]:
        """
        Stream a team conversation.
        
        Args:
            message: User message
            user_id: Optional user identifier
            session_id: Session identifier
            additional_context: Additional context for the conversation
            
        Yields:
            HiveEvent objects from the streaming response
        """
        
        if not self.stream_mode:
            raise AutomagikHiveError("Streaming is not enabled for this instance")
        
        if self.config.agent_type != "team":
            raise ValueError("This method only works with team instances, not individual agents")
        
        team_id = self.config.agent_id
        
        request = HiveRunRequest(
            message=message,
            user_id=user_id,
            session_id=session_id,
            additional_context=additional_context or {}
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_url}/teams/{team_id}/stream",
                    headers={**self.headers, "Accept": "text/event-stream"},
                    json=request.dict(exclude_none=True)
                ) as response:
                    response.raise_for_status()
                    
                    async for event in self._parse_sse_stream(response):
                        yield event
                        
        except HTTPError as e:
            if e.response.status_code == 401:
                raise AutomagikHiveAuthError(f"Authentication failed: {e}")
            raise AutomagikHiveError(f"HTTP error: {e}")
        except (ConnectTimeout, ReadTimeout, TimeoutException) as e:
            raise AutomagikHiveConnectionError(f"Connection error: {e}")
        except Exception as e:
            raise AutomagikHiveStreamError(f"Streaming error: {e}")
    
    async def _parse_sse_stream(self, response) -> AsyncIterator[HiveEvent]:
        """Parse Server-Sent Events stream."""
        try:
            async for line in response.aiter_lines():
                line = line.strip()
                
                if not line or line.startswith(':'):
                    continue
                
                if line.startswith('data: '):
                    event_data = line[6:]  # Remove 'data: ' prefix
                    
                    if event_data.strip() == '[DONE]':
                        logger.debug("Received [DONE] marker, ending stream")
                        break
                    
                    try:
                        event_json = json.loads(event_data)
                        event = parse_hive_event(event_json)
                        
                        if event:
                            yield event
                        else:
                            logger.warning(f"Could not parse event: {event_data}")
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON in event data: {event_data}, error: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error parsing SSE stream: {e}")
            yield ErrorEvent(
                event_type="error",
                data={"error": str(e), "source": "sse_parser"}
            )


# Legacy compatibility class
class AutomagikHiveClient(UnifiedAutomagikHiveClient):
    """
    Legacy compatibility wrapper for the old AutomagikHiveClient.
    
    This allows existing code to continue working while gradually migrating
    to the unified field approach.
    """
    
    def __init__(self, instance_config, timeout_override: Optional[int] = None):
        """Initialize with backward compatibility for old hive_ field names."""
        
        # Check if this is an old-style config with hive_ fields
        if hasattr(instance_config, 'hive_enabled') and instance_config.hive_enabled:
            # Convert old hive_ fields to unified format
            class UnifiedAdapter:
                def __init__(self, old_config):
                    self.agent_instance_type = "hive"
                    self.agent_api_url = old_config.hive_api_url
                    self.agent_api_key = old_config.hive_api_key
                    self.agent_timeout = getattr(old_config, 'hive_timeout', 30)
                    self.agent_stream_mode = getattr(old_config, 'hive_stream_mode', True)
                    
                    # Determine agent_id and agent_type from old fields
                    if hasattr(old_config, 'hive_team_id') and old_config.hive_team_id:
                        self.agent_id = old_config.hive_team_id
                        self.agent_type = "team"
                    elif hasattr(old_config, 'hive_agent_id') and old_config.hive_agent_id:
                        self.agent_id = old_config.hive_agent_id
                        self.agent_type = "agent"
                    else:
                        raise ValueError("Missing agent or team ID in hive configuration")
                
                def has_complete_agent_config(self) -> bool:
                    return bool(self.agent_api_url and self.agent_api_key and self.agent_id)
            
            adapted_config = UnifiedAdapter(instance_config)
            super().__init__(adapted_config, timeout_override)
        else:
            # Use the new unified config directly
            super().__init__(instance_config, timeout_override)


# Example usage
async def example_unified_client_usage():
    """Example of how to use the unified client."""
    
    # Example unified configuration
    class UnifiedHiveConfig:
        agent_instance_type = "hive"
        agent_api_url = "https://api.automagikhive.ai"
        agent_api_key = "your_api_key_here"
        agent_id = "agent_123456"  # or team_123456 for teams
        agent_type = "agent"  # or "team"
        agent_timeout = 30
        agent_stream_mode = True
        
        def has_complete_agent_config(self) -> bool:
            return bool(self.agent_api_url and self.agent_api_key and self.agent_id)
    
    config = UnifiedHiveConfig()
    
    try:
        client = UnifiedAutomagikHiveClient(config)
        
        print(f"Client initialized for {config.agent_type}: {config.agent_id}")
        print(f"Configuration: {client.get_agent_config()}")
        
        # Example: Non-streaming conversation
        if config.agent_type == "agent":
            response = await client.run_agent_conversation(
                message="Hello, how are you?",
                user_id="user123",
                session_id="session456"
            )
            print(f"Agent response: {response.message}")
        
        # Example: Streaming conversation (if enabled)
        if client.stream_mode:
            print("\n--- Streaming Example ---")
            if config.agent_type == "agent":
                async for event in client.stream_agent_conversation(
                    message="Tell me a short story",
                    user_id="user123"
                ):
                    if event.event_type == "run.response.content":
                        print(f"Streaming content: {event.data.get('content', '')}")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(example_unified_client_usage())