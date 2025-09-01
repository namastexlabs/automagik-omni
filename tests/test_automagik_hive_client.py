"""
Comprehensive tests for AutomagikHive client functionality.
Tests client initialization, HTTP calls, SSE streaming, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch
from httpx import ConnectTimeout, ReadTimeout, HTTPError, HTTPStatusError

from src.services.automagik_hive_client import (
    AutomagikHiveClient,
    AutomagikHiveError,
    AutomagikHiveAuthError,
    AutomagikHiveConnectionError,
    AutomagikHiveStreamError
)
from src.services.automagik_hive_models import (
    HiveEventType,
    RunStartedEvent, RunResponseContentEvent, RunCompletedEvent
)
from src.db.models import InstanceConfig


class TestAutomagikHiveClientInit:
    """Test client initialization and configuration."""

    def test_init_with_instance_config(self, test_db):
        """Test initialization with InstanceConfig object."""
        instance_config = InstanceConfig(
            name="test-hive",
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
            name="legacy-hive",
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
        with pytest.raises(ValueError, match="config_override must be InstanceConfig instance or dictionary"):
            AutomagikHiveClient()

    def test_init_missing_required_fields(self):
        """Test initialization with missing required fields."""
        # Missing api_key
        with pytest.raises(ValueError, match="AutomagikHive API key is required"):
            AutomagikHiveClient(config_override={'api_url': 'https://test.com'})

        # Missing api_url
        with pytest.raises(ValueError, match="AutomagikHive API URL is required"):
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
            'User-Agent': 'automagik-omni/1.0',
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
            'User-Agent': 'automagik-omni/1.0',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
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
        assert http_client.timeout.connect == 10.0
        assert http_client.timeout.read == 30.0
        assert http_client.timeout.write == 10.0
        assert http_client.timeout.pool == 5.0

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
        mock_response.raise_for_status.return_value = None  # No exception raised
        mock_post.return_value = mock_response

        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)

        response = await client.create_agent_run(
            agent_id='test-agent',
            message='Test prompt',
            stream=False
        )

        # Verify request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args is not None, "Mock was not called"
        assert call_args[0][0] == 'https://hive.test.com/playground/agents/test-agent/runs'

        # Check payload (now form data)
        assert call_args[1] is not None, "No keyword arguments passed to mock"
        assert 'data' in call_args[1], "No 'data' key in call arguments"
        form_data = call_args[1]['data']
        assert form_data['message'] == 'Test prompt'
        assert form_data['stream'] == 'False'

        # Check response type (implementation returns dict, not HiveRunResponse)
        assert isinstance(response, dict)
        assert response['id'] == 'run_123'

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.stream')
    async def test_create_agent_run_streaming(self, mock_stream):
        """Test streaming agent run creation."""
        # Mock streaming response with JSON-per-line data
        json_data = [
            b'{"event": "run_started", "timestamp": "2024-01-01T00:00:00Z", "run_id": "run_123"}\n',
            b'{"event": "run_response_content", "timestamp": "2024-01-01T00:00:01Z", "content": "Hello"}\n',
            b'{"event": "run_completed", "timestamp": "2024-01-01T00:00:02Z", "status": "completed"}\n'
        ]

        async def async_iter_mock():
            for chunk in json_data:
                yield chunk

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.aiter_bytes.return_value = async_iter_mock()
        mock_stream.return_value.__aenter__.return_value = mock_response

        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)

        events = []
        async for event in await client.create_agent_run(
            agent_id='test-agent',
            message='Test prompt',
            stream=True
        ):
            events.append(event)

        # Verify request
        mock_stream.assert_called_once()
        call_args = mock_stream.call_args
        assert call_args is not None, "Mock was not called"
        assert call_args[0][0] == 'POST'
        assert call_args[0][1] == 'https://hive.test.com/playground/agents/test-agent/runs'

        # Check payload (now form data)
        assert call_args[1] is not None, "No keyword arguments passed to mock"
        assert 'data' in call_args[1], "No 'data' key in call arguments"
        form_data = call_args[1]['data']
        assert form_data['stream'] == 'True'

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

            await client.create_agent_run(message='Test prompt', stream=False)

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
            message='Team prompt',
            stream=False
        )

        # Verify request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://hive.test.com/playground/teams/test-team/runs'

        # Check response (implementation returns dict, not HiveRunResponse)
        assert isinstance(response, dict)
        assert response['id'] == 'team_run_123'

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

            await client.create_team_run(message='Team prompt', stream=False)

            # Should use default team ID
            call_args = mock_post.call_args
            assert 'default-team' in call_args[0][0]


class TestAutomagikHiveClientContinueConversation:
    """Test conversation continuation functionality."""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.stream')
    async def test_continue_conversation(self, mock_stream):
        """Test continuing a conversation."""
        # Mock streaming response
        async def mock_aiter_bytes():
            yield b'data: {"event": "run_started", "run_id": "continue_123"}\n\n'
            yield b'data: {"event": "run_response_content", "content": "Continued response"}\n\n'
            yield b'data: {"event": "run_completed"}\n\n'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.aiter_bytes.return_value = mock_aiter_bytes()

        mock_stream.return_value.__aenter__.return_value = mock_response

        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)

        # continue_conversation always streams
        events = []
        async for event in client.continue_conversation(
            run_id='original_run_123',
            message='Continue prompt'
        ):
            events.append(event)

        # Verify we got events
        assert len(events) >= 1
        assert events[0].event in [HiveEventType.RUN_STARTED, HiveEventType.RUN_RESPONSE_CONTENT]


class TestAutomagikHiveClientStreaming:
    """Test streaming functionality and SSE parsing."""

    @pytest.mark.asyncio
    async def test_stream_events_valid_json(self):
        """Test streaming valid JSON-per-line events."""
        json_chunks = [
            b'{"event": "RunStarted", "timestamp": "2024-01-01T00:00:00Z", "run_id": "run_123"}\n',
            b'{"event": "RunResponseContent", "timestamp": "2024-01-01T00:00:01Z", "content": "Hello"}\n',
            b'{"event": "RunCompleted", "timestamp": "2024-01-01T00:00:02Z", "status": "completed"}\n'
        ]

        async def async_iter_mock():
            for chunk in json_chunks:
                yield chunk

        mock_response = MagicMock()
        mock_response.aiter_bytes.return_value = async_iter_mock()

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
        assert hasattr(events[1], 'content') and events[1].content == "Hello"
        assert events[2].event == HiveEventType.RUN_COMPLETED

    @pytest.mark.asyncio
    async def test_stream_events_invalid_json(self):
        """Test handling of invalid JSON in stream."""
        json_chunks = [
            b'{"invalid": json}\n'  # Invalid JSON
        ]

        async def async_iter_mock():
            for chunk in json_chunks:
                yield chunk

        mock_response = MagicMock()
        mock_response.aiter_bytes.return_value = async_iter_mock()

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
    async def test_stream_events_empty_chunks(self):
        """Test handling of empty chunks in stream."""
        json_chunks = [b'', b'  ', b'\n', b'\t']

        async def async_iter_mock():
            for chunk in json_chunks:
                yield chunk

        mock_response = MagicMock()
        mock_response.aiter_bytes.return_value = async_iter_mock()

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

        async with client.stream_agent_conversation(
            agent_id='test-agent',
            message='Test prompt'
        ) as stream:
            # Collect all events from the stream
            events = []
            async for event in stream:
                events.append(event)

            # Check that we got the expected events
            assert len(events) == 3
            assert events[0].event == HiveEventType.RUN_STARTED
            assert events[1].event == HiveEventType.RUN_RESPONSE_CONTENT
            assert events[2].event == HiveEventType.RUN_COMPLETED

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

        async with client.stream_team_conversation(
            team_id='test-team',
            message='Team prompt'
        ) as stream:
            # Collect all events from the stream
            events = []
            async for event in stream:
                events.append(event)

            # Check that we got the expected events
            assert len(events) == 3
            assert events[0].event == HiveEventType.RUN_STARTED
            assert events[1].event == HiveEventType.RUN_RESPONSE_CONTENT
            assert events[2].event == HiveEventType.RUN_COMPLETED


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
        mock_get.assert_called_once_with('https://hive.test.com/health', headers={'Authorization': 'Bearer test-key', 'User-Agent': 'automagik-omni/1.0', 'Content-Type': 'application/json', 'Accept': 'application/json'})

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
            await client.create_agent_run(agent_id='test', message='test', stream=False)

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
            await client.create_agent_run(agent_id='test', message='test', stream=False)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_http_401_error(self, mock_post):
        """Test HTTP 401 authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        # Mock raise_for_status to raise HTTPStatusError
        http_error = HTTPStatusError("401 Unauthorized", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response

        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)

        with pytest.raises(AutomagikHiveAuthError, match="Authentication failed"):
            await client.create_agent_run(agent_id='test', message='test', stream=False)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_http_500_error(self, mock_post):
        """Test HTTP 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        # Mock raise_for_status to raise HTTPStatusError
        http_error = HTTPStatusError("500 Internal Server Error", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response

        config = {
            'api_url': 'https://hive.test.com',
            'api_key': 'test-key'
        }
        client = AutomagikHiveClient(config_override=config)

        with pytest.raises(AutomagikHiveError, match="HTTP error 500"):
            await client.create_agent_run(agent_id='test', message='test', stream=False)

    @pytest.mark.asyncio
    async def test_stream_error_handling(self):
        """Test error handling in streaming."""
        mock_response = MagicMock()
        mock_response.aiter_bytes.side_effect = Exception("Stream error")

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
            await client.create_agent_run(message='test')

        with pytest.raises(AutomagikHiveError, match="team_id is required"):
            await client.create_team_run(message='test')

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
            mock_response.raise_for_status.return_value = None  # No exception raised
            mock_post.return_value = mock_response

            # Should still work with empty prompt
            await client.create_agent_run(agent_id='test', message='', stream=False)

            # Verify empty message was sent
            call_args = mock_post.call_args
            assert call_args is not None, "Mock was not called"
            assert call_args[1] is not None, "No keyword arguments passed to mock"
            assert 'data' in call_args[1], "No 'data' key in call arguments"
            form_data = call_args[1]['data']
            assert form_data['message'] == ''

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
            mock_response.raise_for_status.return_value = None  # No exception raised
            mock_post.return_value = mock_response

            # Should handle long prompt
            await client.create_agent_run(agent_id='test', message=long_prompt, stream=False)

            # Verify long message was sent
            call_args = mock_post.call_args
            assert call_args is not None, "Mock was not called"
            assert call_args[1] is not None, "No keyword arguments passed to mock"
            assert 'data' in call_args[1], "No 'data' key in call arguments"
            form_data = call_args[1]['data']
            assert len(form_data['message']) == 10000

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
