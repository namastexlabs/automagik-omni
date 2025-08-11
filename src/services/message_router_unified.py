"""
Updated Message Router with Unified Agent Fields Support

This demonstrates how the message router works with the new unified schema that
supports both automagik and hive implementations through agent_instance_type.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Union, List
from src.services.agent_api_client import agent_api_client

# Configure logging
logger = logging.getLogger(__name__)


class UnifiedMessageRouter:
    """Message router that works with unified agent configuration fields."""
    
    def __init__(self):
        self.logger = logger

    async def process_message_unified(
        self,
        message_text: str,
        user_id: Optional[str] = None,
        user: Optional[Dict[str, Any]] = None,
        session_identifier: str = "default_session", 
        message_type: str = "text",
        whatsapp_raw_payload: Optional[Dict[str, Any]] = None,
        session_origin: str = "whatsapp",
        instance_config=None,  # Uses unified InstanceConfig
        media_contents: Optional[List[Dict[str, Any]]] = None,
        trace_context=None,
    ) -> Dict[str, Any]:
        """
        Process message using unified agent configuration.
        
        Args:
            instance_config: InstanceConfig with unified agent fields
            - agent_instance_type: "automagik" or "hive"
            - agent_api_url: API endpoint (works for both)
            - agent_api_key: API key (works for both)
            - agent_id: Agent name (automagik) or agent/team ID (hive)
            - agent_type: "agent" or "team" (hive-specific distinction)
            - agent_timeout: Timeout in seconds
            - agent_stream_mode: Whether to use streaming
        """
        
        if not instance_config:
            raise ValueError("instance_config is required for unified routing")
        
        # Determine routing type based on unified fields
        route_type = self._determine_route_type_unified(instance_config)
        
        self.logger.info(f"Using unified routing type: {route_type}")
        self.logger.info(f"Agent instance type: {instance_config.agent_instance_type}")
        self.logger.info(f"Agent type: {instance_config.agent_type}")
        self.logger.info(f"Agent ID: {instance_config.agent_id}")
        
        if route_type == "hive_streaming":
            return await self._process_hive_streaming(
                message_text=message_text,
                user_id=user_id,
                user=user,
                session_identifier=session_identifier,
                message_type=message_type,
                instance_config=instance_config,
                media_contents=media_contents,
                trace_context=trace_context
            )
        
        elif route_type == "hive_standard":
            return await self._process_hive_standard(
                message_text=message_text,
                user_id=user_id,
                user=user,
                session_identifier=session_identifier,
                message_type=message_type,
                instance_config=instance_config,
                media_contents=media_contents,
                trace_context=trace_context
            )
        
        else:  # automagik
            return await self._process_automagik_standard(
                message_text=message_text,
                user_id=user_id,
                user=user,
                session_identifier=session_identifier,
                message_type=message_type,
                instance_config=instance_config,
                media_contents=media_contents,
                trace_context=trace_context
            )

    def _determine_route_type_unified(self, instance_config) -> str:
        """
        Determine routing type based on unified configuration fields.
        
        Returns:
            "hive_streaming": AutomagikHive with streaming enabled
            "hive_standard": AutomagikHive without streaming  
            "automagik": Standard Automagik agent API
        """
        
        # Check if instance has complete configuration
        if not instance_config.has_complete_agent_config():
            self.logger.warning("Incomplete agent configuration, falling back to automagik")
            return "automagik"
        
        # Route based on instance type
        if instance_config.agent_instance_type == "hive":
            if instance_config.agent_stream_mode:
                return "hive_streaming"
            else:
                return "hive_standard"
        else:
            return "automagik"

    async def _process_hive_streaming(self, **kwargs) -> Dict[str, Any]:
        """Process message using AutomagikHive streaming."""
        instance_config = kwargs["instance_config"]
        
        try:
            from src.services.automagik_hive_client import AutomagikHiveClient
            
            # Create hive client using unified configuration
            hive_client = AutomagikHiveClient(instance_config=instance_config)
            
            # Determine target ID based on agent_type
            if instance_config.agent_type == "team":
                target_id = instance_config.agent_id  # team ID
                self.logger.info(f"Using team streaming with ID: {target_id}")
                response = await self._stream_team_conversation(hive_client, target_id, kwargs)
            else:
                target_id = instance_config.agent_id  # agent ID  
                self.logger.info(f"Using agent streaming with ID: {target_id}")
                response = await self._stream_agent_conversation(hive_client, target_id, kwargs)
            
            return self._normalize_hive_response(response)
            
        except Exception as e:
            self.logger.error(f"Hive streaming failed: {e}")
            # Fallback to standard processing
            return await self._process_automagik_standard(**kwargs)

    async def _process_hive_standard(self, **kwargs) -> Dict[str, Any]:
        """Process message using AutomagikHive without streaming."""
        instance_config = kwargs["instance_config"]
        
        try:
            from src.services.automagik_hive_client import AutomagikHiveClient
            
            # Create hive client using unified configuration
            hive_client = AutomagikHiveClient(instance_config=instance_config)
            
            # Use non-streaming methods based on agent_type
            if instance_config.agent_type == "team":
                response = await hive_client.run_team_conversation(
                    team_id=instance_config.agent_id,
                    message=kwargs["message_text"],
                    user_id=kwargs.get("user_id"),
                    session_id=kwargs.get("session_identifier", "default")
                )
            else:
                response = await hive_client.run_agent_conversation(
                    agent_id=instance_config.agent_id,
                    message=kwargs["message_text"],
                    user_id=kwargs.get("user_id"),
                    session_id=kwargs.get("session_identifier", "default")
                )
            
            return self._normalize_hive_response(response)
            
        except Exception as e:
            self.logger.error(f"Hive standard processing failed: {e}")
            # Fallback to automagik
            return await self._process_automagik_standard(**kwargs)

    async def _process_automagik_standard(self, **kwargs) -> Dict[str, Any]:
        """Process message using standard Automagik agent API."""
        instance_config = kwargs["instance_config"]
        
        # Create agent config for legacy compatibility
        agent_config = {
            "name": instance_config.agent_id,
            "api_url": instance_config.agent_api_url,
            "api_key": instance_config.agent_api_key,
            "timeout": instance_config.agent_timeout
        }
        
        # Use existing agent API client logic
        from src.services.agent_api_client import AgentApiClient
        
        class InstanceConfigAdapter:
            """Adapter to make unified config work with existing AgentApiClient."""
            def __init__(self, unified_config):
                self.name = unified_config.name if hasattr(unified_config, 'name') else 'unified'
                self.agent_api_url = unified_config.agent_api_url
                self.agent_api_key = unified_config.agent_api_key
                self.default_agent = unified_config.agent_id
                self.agent_timeout = unified_config.agent_timeout

        adapter = InstanceConfigAdapter(instance_config)
        agent_client = AgentApiClient(config_override=adapter)
        
        response = agent_client.process_message(
            message=kwargs["message_text"],
            user_id=kwargs.get("user_id"),
            user=kwargs.get("user"),
            session_name=kwargs.get("session_identifier", "default"),
            agent_name=instance_config.agent_id,
            message_type=kwargs.get("message_type", "text"),
            media_contents=kwargs.get("media_contents"),
            trace_context=kwargs.get("trace_context")
        )
        
        return response

    async def _stream_agent_conversation(self, hive_client, agent_id: str, kwargs: Dict) -> Dict[str, Any]:
        """Stream agent conversation and collect response."""
        collected_content = []
        
        async for event in hive_client.stream_agent_conversation(
            agent_id=agent_id,
            message=kwargs["message_text"],
            user_id=kwargs.get("user_id"),
            session_id=kwargs.get("session_identifier", "default")
        ):
            if event.event_type == "run.response.content":
                collected_content.append(event.data.get("content", ""))
        
        return {
            "message": "".join(collected_content),
            "agent_name": agent_id,
            "type": "hive_agent_streaming"
        }

    async def _stream_team_conversation(self, hive_client, team_id: str, kwargs: Dict) -> Dict[str, Any]:
        """Stream team conversation and collect response."""
        collected_content = []
        
        async for event in hive_client.stream_team_conversation(
            team_id=team_id,
            message=kwargs["message_text"],
            user_id=kwargs.get("user_id"),
            session_id=kwargs.get("session_identifier", "default")
        ):
            if event.event_type == "run.response.content":
                collected_content.append(event.data.get("content", ""))
        
        return {
            "message": "".join(collected_content),
            "team_name": team_id,
            "type": "hive_team_streaming"
        }

    def _normalize_hive_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize hive response to standard format."""
        return {
            "message": response.get("message", ""),
            "agent_name": response.get("agent_name", response.get("team_name", "unknown")),
            "type": response.get("type", "hive"),
            "metadata": {
                "source": "automagik_hive",
                "original_response": response
            }
        }

    def should_use_streaming_unified(self, instance_config) -> bool:
        """Check if streaming should be used based on unified config."""
        return (
            instance_config.agent_instance_type == "hive" and 
            instance_config.agent_stream_mode and
            instance_config.has_complete_agent_config()
        )


# Example usage patterns
async def example_unified_usage():
    """Demonstrate unified field usage patterns."""
    
    # Example 1: AutomagikHive Agent with Streaming
    class HiveAgentConfig:
        agent_instance_type = "hive"
        agent_api_url = "https://api.automagikhive.ai"
        agent_api_key = "hive_api_key_123"
        agent_id = "agent_abc123"
        agent_type = "agent"
        agent_timeout = 30
        agent_stream_mode = True
        
        def has_complete_agent_config(self) -> bool:
            return bool(self.agent_api_url and self.agent_api_key and self.agent_id)
    
    # Example 2: AutomagikHive Team with Streaming
    class HiveTeamConfig:
        agent_instance_type = "hive"
        agent_api_url = "https://api.automagikhive.ai"
        agent_api_key = "hive_api_key_123"
        agent_id = "team_xyz789"
        agent_type = "team"
        agent_timeout = 30
        agent_stream_mode = True
        
        def has_complete_agent_config(self) -> bool:
            return bool(self.agent_api_url and self.agent_api_key and self.agent_id)
    
    # Example 3: Standard Automagik Agent
    class AutomagikConfig:
        agent_instance_type = "automagik"
        agent_api_url = "https://api.automagik.ai"
        agent_api_key = "automagik_api_key_456"
        agent_id = "my_assistant"
        agent_type = "agent"
        agent_timeout = 60
        agent_stream_mode = False
        
        def has_complete_agent_config(self) -> bool:
            return bool(self.agent_api_url and self.agent_api_key and self.agent_id)
    
    router = UnifiedMessageRouter()
    
    # Test with different configurations
    configs = [
        ("Hive Agent Streaming", HiveAgentConfig()),
        ("Hive Team Streaming", HiveTeamConfig()),  
        ("Standard Automagik", AutomagikConfig())
    ]
    
    for name, config in configs:
        print(f"\n--- Testing {name} ---")
        route_type = router._determine_route_type_unified(config)
        streaming = router.should_use_streaming_unified(config)
        print(f"Route Type: {route_type}")
        print(f"Streaming Enabled: {streaming}")
        print(f"Agent Instance Type: {config.agent_instance_type}")
        print(f"Agent Type: {config.agent_type}")
        print(f"Agent ID: {config.agent_id}")


if __name__ == "__main__":
    asyncio.run(example_unified_usage())