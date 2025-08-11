"""
Comprehensive tests for AutomagikHive client functionality.
Tests client initialization, HTTP calls, SSE streaming, and error handling.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from httpx import Response, ConnectTimeout, ReadTimeout, TimeoutException, HTTPError

from src.services.automagik_hive_client import (
    AutomagikHiveClient,
    AutomagikHiveError,
    AutomagikHiveAuthError,
    AutomagikHiveConnectionError,
    AutomagikHiveStreamError
)
from src.services.automagik_hive_models import (
    HiveEvent, HiveRunResponse, HiveEventType,
    RunStartedEvent, RunResponseContentEvent, RunCompletedEvent, ErrorEvent
)
from src.db.models import InstanceConfig


class TestAutomagikHiveClientInit:
    """Test client initialization and configuration."""
    
    def test_init_with_instance_config(self, test_db):
        """Test initialization with InstanceConfig object."""
        instance_config = InstanceConfig(
            instance_name="test-hive",
            instance_key="test-key",
            agent_instance_type="hive",
            agent_api_url="https://hive.example.com/api",
            agent_api_key="hive-api-key",
            agent_id="test-agent",
            agent_timeout=120
        )
        test_db.add(instance_config)
        test_db.commit()
        
        client = AutomagikHiveClient(config_override=instance_config)
        
        assert client.api_url == "https://hive.example.com/api"
        assert client.api_key == "hive-api-key"
        assert client.timeout == 120
        assert client.default_agent_id == "test-agent"
        assert client.default_team_id is None
    
    def test_init_with_dict_config(self):
        """Test initialization with dictionary configuration."""
        config_dict = {
            'api_url': 'https://hive.test.com/api',
            'api_key': 'test-api-key',
            'agent_id': 'dict-agent',
            'team_id': 'dict-team',
            'timeout': 90
        }
        
        client = AutomagikHiveClient(config_override=config_dict)
        
        assert client.api_url == 'https://hive.test.com/api'
        assert client.api_key == 'test-api-key'
        assert client.timeout == 90
        assert client.default_agent_id == 'dict-agent'
        assert client.default_team_id == 'dict-team'
    
    def test_init_with_legacy_hive_config(self, test_db):
        """Test initialization with legacy hive configuration."""
        instance_config = InstanceConfig(
            instance_name="legacy-hive",
            instance_key="legacy-key",
            agent_api_url="https://automagik.com",
            agent_api_key="automagik-key",
            # Legacy hive fields
            hive_api_url="https://legacy-hive.com",
            hive_api_key="legacy-hive-key",
            hive_agent_id="legacy-agent",
            hive_team_id="legacy-team",
            hive_timeout=150
        )
        test_db.add(instance_config)
        test_db.commit()
        
        client = AutomagikHiveClient(config_override=instance_config)
        
        # Should use legacy hive fields
        assert client.api_url == "https://legacy-hive.com"
        assert client.api_key == "legacy-hive-key"
        assert client.timeout == 150
        assert client.default_agent_id == "legacy-agent"
        assert client.default_team_id == "legacy-team"
    
    def test_init_no_config(self):
        """Test initialization without configuration (should raise error)."""
        with pytest.raises(AutomagikHiveError, match="No configuration provided"):
            AutomagikHiveClient()
    
    def test_init_missing_required_fields(self):
        """Test initialization with missing required fields."""
        # Missing api_key
        with pytest.raises(AutomagikHiveError, match="Missing required field: api_key"):
            AutomagikHiveClient(config_override={'api_url': 'https://test.com'})
        
        # Missing api_url
        with pytest.raises(AutomagikHiveError, match="Missing required field: api_url"):
            AutomagikHiveClient(config_override={'api_key': 'test-key'})


class TestAutomagikHiveClientHeaders:
    """Test header generation and management."""
    
    def test_make_headers_default(self):
        """Test default header generation."""
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-api-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        headers = client._make_headers()
        
        expected_headers = {
            'Authorization': 'Bearer test-api-key',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        assert headers == expected_headers
    
    def test_make_headers_sse(self):
        """Test SSE header generation."""
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-api-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        headers = client._make_headers(accept_sse=True)
        
        expected_headers = {
            'Authorization': 'Bearer test-api-key',
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache'
        }
        assert headers == expected_headers


class TestAutomagikHiveClientHTTPMethods:
    """Test HTTP method implementations."""
    
    @pytest.mark.asyncio
    async def test_get_client(self):
        """Test HTTP client creation."""
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-api-key',
            'timeout': 30
        }
        client = AutomagikHiveClient(config_override=config)
        
        http_client = await client._get_client()
        
        assert http_client is not None
        assert http_client.timeout.connect == 30
        assert http_client.timeout.read == 30
        assert http_client.timeout.write == 30
        assert http_client.timeout.pool == 30
    
    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test client cleanup."""
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-api-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        # Get a client first
        http_client = await client._get_client()
        assert client._client is not None
        
        # Close should clean up
        await client.close()
        assert client._client is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-api-key'
        }
        
        async with AutomagikHiveClient(config_override=config) as client:
            assert client is not None
            # Client should be available inside context
            http_client = await client._get_client()
            assert http_client is not None


class TestAutomagikHiveClientAgentRuns:
    """Test agent run creation and management."""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_create_agent_run_non_streaming(self, mock_post):
        """Test non-streaming agent run creation."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'run_123',
            'status': 'completed',
            'response': 'Test response'
        }
        mock_post.return_value = mock_response
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        response = await client.create_agent_run(
            agent_id='test-agent',
            prompt='Test prompt',
            stream=False
        )
        
        # Verify request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://hive.test.com/agents/test-agent/run'
        
        # Check payload
        payload = json.loads(call_args[1]['content'])
        assert payload['prompt'] == 'Test prompt'
        assert payload['stream'] is False
        
        # Check response type
        assert isinstance(response, HiveRunResponse)
        assert response.id == 'run_123'
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_create_agent_run_streaming(self, mock_post):
        """Test streaming agent run creation."""
        # Mock streaming response with SSE data
        sse_data = [
            'event: run_started\ndata: {"event": "run_started", "timestamp": "2024-01-01T00:00:00Z", "run_id": "run_123"}\n\n',
            'event: run_response_content\ndata: {"event": "run_response_content", "timestamp": "2024-01-01T00:00:01Z", "content": "Hello"}\n\n',
            'event: run_completed\ndata: {"event": "run_completed", "timestamp": "2024-01-01T00:00:02Z", "status": "completed"}\n\n'
        ]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.aiter_lines.return_value = iter(sse_data)
        mock_post.return_value = mock_response
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        events = []
        async for event in await client.create_agent_run(
            agent_id='test-agent',
            prompt='Test prompt',
            stream=True
        ):
            events.append(event)
        
        # Verify request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://hive.test.com/agents/test-agent/run'
        
        # Check payload
        payload = json.loads(call_args[1]['content'])
        assert payload['stream'] is True
        
        # Verify events
        assert len(events) == 3
        assert events[0].event == HiveEventType.RUN_STARTED
        assert events[1].event == HiveEventType.RUN_RESPONSE_CONTENT
        assert events[2].event == HiveEventType.RUN_COMPLETED
    
    @pytest.mark.asyncio
    async def test_create_agent_run_default_agent(self):
        """Test agent run with default agent ID."""
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key',
            'agent_id': 'default-agent'
        }
        client = AutomagikHiveClient(config_override=config)
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'id': 'run_123', 'status': 'completed'}
            mock_post.return_value = mock_response
            
            await client.create_agent_run(prompt='Test prompt')
            
            # Should use default agent ID
            call_args = mock_post.call_args
            assert 'default-agent' in call_args[0][0]


class TestAutomagikHiveClientTeamRuns:
    """Test team run creation and management."""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_create_team_run_non_streaming(self, mock_post):
        """Test non-streaming team run creation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'team_run_123',
            'status': 'completed',
            'response': 'Team response'
        }
        mock_post.return_value = mock_response
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        response = await client.create_team_run(
            team_id='test-team',
            prompt='Team prompt',
            stream=False
        )
        
        # Verify request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://hive.test.com/teams/test-team/run'
        
        # Check response
        assert isinstance(response, HiveRunResponse)
        assert response.id == 'team_run_123'
    
    @pytest.mark.asyncio
    async def test_create_team_run_default_team(self):
        """Test team run with default team ID."""
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key',
            'team_id': 'default-team'
        }
        client = AutomagikHiveClient(config_override=config)
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'id': 'run_123', 'status': 'completed'}
            mock_post.return_value = mock_response
            
            await client.create_team_run(prompt='Team prompt')
            
            # Should use default team ID
            call_args = mock_post.call_args
            assert 'default-team' in call_args[0][0]


class TestAutomagikHiveClientContinueConversation:
    """Test conversation continuation functionality."""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_continue_conversation(self, mock_post):
        """Test continuing a conversation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'continue_123',
            'status': 'completed',
            'response': 'Continued response'
        }
        mock_post.return_value = mock_response
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        response = await client.continue_conversation(
            run_id='original_run_123',
            prompt='Continue prompt',
            stream=False
        )
        
        # Verify request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://hive.test.com/continue'
        
        # Check payload
        payload = json.loads(call_args[1]['content'])
        assert payload['run_id'] == 'original_run_123'
        assert payload['prompt'] == 'Continue prompt'
        
        # Check response
        assert isinstance(response, HiveRunResponse)


class TestAutomagikHiveClientStreaming:
    """Test streaming functionality and SSE parsing."""
    
    @pytest.mark.asyncio
    async def test_stream_events_valid_sse(self):
        """Test streaming valid SSE events."""
        sse_lines = [
            'event: run_started',
            'data: {"event": "run_started", "timestamp": "2024-01-01T00:00:00Z", "run_id": "run_123"}',
            '',
            'event: run_response_content',
            'data: {"event": "run_response_content", "timestamp": "2024-01-01T00:00:01Z", "content": "Hello"}',
            '',
            'event: run_completed',
            'data: {"event": "run_completed", "timestamp": "2024-01-01T00:00:02Z", "status": "completed"}',
            ''
        ]
        
        mock_response = MagicMock()
        mock_response.aiter_lines.return_value = iter(sse_lines)
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        events = []
        async for event in client.stream_events(mock_response):
            events.append(event)
        
        assert len(events) == 3
        assert events[0].event == HiveEventType.RUN_STARTED
        assert events[1].event == HiveEventType.RUN_RESPONSE_CONTENT
        assert events[1].content == "Hello"
        assert events[2].event == HiveEventType.RUN_COMPLETED
    
    @pytest.mark.asyncio
    async def test_stream_events_invalid_json(self):
        """Test handling of invalid JSON in SSE stream."""
        sse_lines = [
            'event: run_started',
            'data: {"invalid": json}',  # Invalid JSON
            ''
        ]
        
        mock_response = MagicMock()
        mock_response.aiter_lines.return_value = iter(sse_lines)
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        events = []
        async for event in client.stream_events(mock_response):
            events.append(event)
        
        # Should skip invalid JSON and continue
        assert len(events) == 0
    
    @pytest.mark.asyncio
    async def test_stream_events_empty_lines(self):
        """Test handling of empty lines in SSE stream."""
        sse_lines = ['', '  ', '\n', '\t']
        
        mock_response = MagicMock()
        mock_response.aiter_lines.return_value = iter(sse_lines)
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        events = []
        async for event in client.stream_events(mock_response):
            events.append(event)
        
        # Should handle empty lines gracefully
        assert len(events) == 0


class TestAutomagikHiveClientConversationStreaming:
    """Test high-level conversation streaming methods."""
    
    @pytest.mark.asyncio
    @patch('src.services.automagik_hive_client.AutomagikHiveClient.create_agent_run')
    async def test_stream_agent_conversation(self, mock_create_run):
        """Test streaming agent conversation."""
        # Mock events
        mock_events = [
            RunStartedEvent(event=HiveEventType.RUN_STARTED, timestamp="2024-01-01T00:00:00Z", run_id="run_123"),
            RunResponseContentEvent(event=HiveEventType.RUN_RESPONSE_CONTENT, timestamp="2024-01-01T00:00:01Z", content="Hello"),
            RunCompletedEvent(event=HiveEventType.RUN_COMPLETED, timestamp="2024-01-01T00:00:02Z", status="completed")
        ]
        
        async def mock_stream():
            for event in mock_events:
                yield event
        
        mock_create_run.return_value = mock_stream()
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        result = await client.stream_agent_conversation(
            agent_id='test-agent',
            prompt='Test prompt'
        )
        
        assert 'full_response' in result
        assert 'run_id' in result
        assert 'status' in result
        assert result['run_id'] == 'run_123'
        assert result['status'] == 'completed'
        assert 'Hello' in result['full_response']
    
    @pytest.mark.asyncio
    @patch('src.services.automagik_hive_client.AutomagikHiveClient.create_team_run')
    async def test_stream_team_conversation(self, mock_create_run):
        """Test streaming team conversation."""
        mock_events = [
            RunStartedEvent(event=HiveEventType.RUN_STARTED, timestamp="2024-01-01T00:00:00Z", run_id="team_run_123"),
            RunResponseContentEvent(event=HiveEventType.RUN_RESPONSE_CONTENT, timestamp="2024-01-01T00:00:01Z", content="Team response"),
            RunCompletedEvent(event=HiveEventType.RUN_COMPLETED, timestamp="2024-01-01T00:00:02Z", status="completed")
        ]
        
        async def mock_stream():
            for event in mock_events:
                yield event
        
        mock_create_run.return_value = mock_stream()
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        result = await client.stream_team_conversation(
            team_id='test-team',
            prompt='Team prompt'
        )
        
        assert result['run_id'] == 'team_run_123'
        assert result['status'] == 'completed'
        assert 'Team response' in result['full_response']


class TestAutomagikHiveClientHealthCheck:
    """Test health check functionality."""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_health_check_success(self, mock_get):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        is_healthy = await client.health_check()
        
        assert is_healthy is True
        mock_get.assert_called_once_with('https://hive.test.com/health')
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_health_check_failure(self, mock_get):
        """Test failed health check."""
        mock_get.side_effect = HTTPError("Connection failed")
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        is_healthy = await client.health_check()
        
        assert is_healthy is False


class TestAutomagikHiveClientErrorHandling:
    """Test error handling and exception cases."""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_connection_timeout(self, mock_post):
        """Test connection timeout handling."""
        mock_post.side_effect = ConnectTimeout("Connection timeout")
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        with pytest.raises(AutomagikHiveConnectionError, match="Connection timeout"):
            await client.create_agent_run(agent_id='test', prompt='test')
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_read_timeout(self, mock_post):
        """Test read timeout handling."""
        mock_post.side_effect = ReadTimeout("Read timeout")
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        with pytest.raises(AutomagikHiveConnectionError, match="Read timeout"):
            await client.create_agent_run(agent_id='test', prompt='test')
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_http_401_error(self, mock_post):
        """Test HTTP 401 authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        with pytest.raises(AutomagikHiveAuthError, match="Authentication failed"):
            await client.create_agent_run(agent_id='test', prompt='test')
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_http_500_error(self, mock_post):
        """Test HTTP 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        with pytest.raises(AutomagikHiveError, match="HTTP 500"):
            await client.create_agent_run(agent_id='test', prompt='test')
    
    @pytest.mark.asyncio
    async def test_stream_error_handling(self):
        """Test error handling in streaming."""
        mock_response = MagicMock()
        mock_response.aiter_lines.side_effect = Exception("Stream error")
        
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        with pytest.raises(AutomagikHiveStreamError, match="Stream error"):
            async for event in client.stream_events(mock_response):
                pass


class TestAutomagikHiveClientEdgeCases:
    """Test edge cases and unusual scenarios."""
    
    @pytest.mark.asyncio
    async def test_missing_agent_and_team_id(self):
        """Test behavior when both agent_id and team_id are missing."""
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        with pytest.raises(AutomagikHiveError, match="agent_id is required"):
            await client.create_agent_run(prompt='test')
        
        with pytest.raises(AutomagikHiveError, match="team_id is required"):
            await client.create_team_run(prompt='test')
    
    @pytest.mark.asyncio
    async def test_empty_prompt(self):
        """Test behavior with empty prompt."""
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'id': 'run_123', 'status': 'completed'}
            mock_post.return_value = mock_response
            
            # Should still work with empty prompt
            await client.create_agent_run(agent_id='test', prompt='')
            
            # Verify empty prompt was sent
            call_args = mock_post.call_args
            payload = json.loads(call_args[1]['content'])
            assert payload['prompt'] == ''
    
    @pytest.mark.asyncio
    async def test_very_long_prompt(self):
        """Test behavior with very long prompt."""
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        long_prompt = 'x' * 10000  # Very long prompt
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'id': 'run_123', 'status': 'completed'}
            mock_post.return_value = mock_response
            
            # Should handle long prompt
            await client.create_agent_run(agent_id='test', prompt=long_prompt)
            
            # Verify long prompt was sent
            call_args = mock_post.call_args
            payload = json.loads(call_args[1]['content'])
            assert len(payload['prompt']) == 10000
    
    def test_repr_and_str_methods(self):
        """Test string representation methods."""
        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)
        
        # Should not expose API key in string representation
        repr_str = repr(client)
        str_str = str(client)
        
        assert 'test-key' not in repr_str
        assert 'test-key' not in str_str
        assert 'hive.test.com' in repr_str
        assert 'hive.test.com' in str_str