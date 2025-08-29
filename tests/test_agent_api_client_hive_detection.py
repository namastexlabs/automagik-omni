"""
Test suite for Agent API Client Hive API detection feature.

This test suite covers the PR #3 fix for Hive API detection that was causing
incorrect endpoint usage. The fix ensures proper port-based detection:
- Hive API instances (port 8000) use `/playground/agents/{agent_name}/runs`
- Automagik Core instances (port 8881) use `/api/v1/agent/{agent_name}/run`
"""

import pytest
from unittest.mock import Mock, patch
from src.services.agent_api_client import AgentApiClient


class TestHiveApiDetection:
    """Test cases for Hive API detection logic."""

    def test_hive_api_detection_port_8000(self):
        """Test that port 8000 is correctly detected as Hive API instance."""
        # Test with port 8000 in URL
        client = AgentApiClient()
        client.api_url = "http://localhost:8000"
        client.instance_config = None
        
        assert client._is_hive_api_mode() is True

    def test_hive_api_detection_port_8000_with_path(self):
        """Test that port 8000 with path is correctly detected as Hive API instance."""
        client = AgentApiClient()
        client.api_url = "http://localhost:8000/some/path"
        client.instance_config = None
        
        assert client._is_hive_api_mode() is True

    def test_automagik_core_detection_port_8881(self):
        """Test that port 8881 is correctly detected as Automagik Core instance (not Hive)."""
        client = AgentApiClient()
        client.api_url = "http://localhost:8881"
        client.instance_config = None
        
        assert client._is_hive_api_mode() is False

    def test_automagik_core_detection_port_8881_with_path(self):
        """Test that port 8881 with path is correctly detected as Automagik Core instance."""
        client = AgentApiClient()
        client.api_url = "http://localhost:8881/api/v1"
        client.instance_config = None
        
        assert client._is_hive_api_mode() is False

    def test_remote_hive_api_detection(self):
        """Test that remote Hive API instances on port 8000 are correctly detected."""
        client = AgentApiClient()
        client.api_url = "https://my-hive-instance.com:8000"
        client.instance_config = None
        
        assert client._is_hive_api_mode() is True

    def test_remote_automagik_core_detection(self):
        """Test that remote Automagik Core instances on port 8881 are correctly detected."""
        client = AgentApiClient()
        client.api_url = "https://my-core-instance.com:8881"
        client.instance_config = None
        
        assert client._is_hive_api_mode() is False

    def test_default_port_detection(self):
        """Test that URLs without explicit ports default to non-Hive mode."""
        client = AgentApiClient()
        client.api_url = "http://localhost"
        client.instance_config = None
        
        assert client._is_hive_api_mode() is False

    def test_other_ports_not_hive(self):
        """Test that other ports are not detected as Hive API instances."""
        test_ports = [80, 443, 3000, 5000, 8080, 8090, 9000]
        
        for port in test_ports:
            client = AgentApiClient()
            client.api_url = f"http://localhost:{port}"
            client.instance_config = None
            
            assert client._is_hive_api_mode() is False, f"Port {port} should not be detected as Hive API"

    def test_instance_config_overrides_port_detection(self):
        """Test that instance config is_hive flag overrides port-based detection."""
        # Mock instance config with is_hive=True
        mock_config = Mock()
        mock_config.is_hive = True
        
        client = AgentApiClient()
        client.api_url = "http://localhost:8881"  # Normally would be Core
        client.instance_config = mock_config
        
        assert client._is_hive_api_mode() is True

    def test_instance_config_overrides_port_detection_false(self):
        """Test that instance config is_hive=False overrides port-based detection."""
        # Mock instance config with is_hive=False
        mock_config = Mock()
        mock_config.is_hive = False
        
        client = AgentApiClient()
        client.api_url = "http://localhost:8000"  # Normally would be Hive
        client.instance_config = mock_config
        
        assert client._is_hive_api_mode() is False

    def test_no_api_url_returns_false(self):
        """Test that missing API URL returns False for Hive detection."""
        client = AgentApiClient()
        client.api_url = None
        client.instance_config = None
        
        assert client._is_hive_api_mode() is False


class TestEndpointSelection:
    """Test cases for endpoint selection based on Hive API detection."""

    @patch('src.services.agent_api_client.AgentApiClient._call_hive_api')
    def test_hive_api_endpoint_selection(self, mock_hive_api):
        """Test that Hive API instances use the playground endpoint."""
        mock_hive_api.return_value = {"response": "hive_response", "success": True}
        
        client = AgentApiClient()
        client.api_url = "http://localhost:8000"
        client.instance_config = None
        
        response = client.run_agent(
            agent_name="test_agent",
            message_content="test message"
        )
        
        # Should call _call_hive_api method
        mock_hive_api.assert_called_once()
        assert response == {"response": "hive_response", "success": True}

    @patch('requests.post')
    def test_automagik_core_endpoint_selection(self, mock_post):
        """Test that Automagik Core instances use the standard API endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "core_response", "success": True}
        mock_post.return_value = mock_response
        
        client = AgentApiClient()
        client.api_url = "http://localhost:8881"
        client.instance_config = None
        
        # Mock the headers method
        client._make_headers = Mock(return_value={"Content-Type": "application/json"})
        
        response = client.run_agent(
            agent_name="test_agent",
            message_content="test message"
        )
        
        # Should make POST request to /api/v1/agent/{agent_name}/run
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8881/api/v1/agent/test_agent/run"

    @patch('requests.post')
    def test_hive_playground_endpoint_format(self, mock_post):
        """Test the correct playground endpoint format for Hive API calls."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "hive_response", "success": True}
        mock_post.return_value = mock_response
        
        client = AgentApiClient()
        client.api_url = "http://localhost:8000"
        client.instance_config = None
        
        # Mock the headers method
        client._make_headers = Mock(return_value={"Content-Type": "application/json"})
        
        # Call the _call_hive_api method directly
        response = client._call_hive_api(
            agent_name="test_agent",
            message_content="test message"
        )
        
        # Should make POST request to /playground/agents/{agent_name}/runs
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8000/playground/agents/test_agent/runs"


class TestRegressionPrevention:
    """Test cases to prevent regression of the original bug."""

    def test_original_bug_hive_instances_dont_use_wrong_endpoints(self):
        """Test that Hive instances don't mistakenly use Core endpoints (the original bug)."""
        client = AgentApiClient()
        client.api_url = "http://localhost:8000"  # Hive API port
        client.instance_config = None
        
        # Should detect as Hive API
        assert client._is_hive_api_mode() is True
        
        # Should NOT use the /api/v1/agent/ endpoints that caused 404s
        with patch('src.services.agent_api_client.AgentApiClient._call_hive_api') as mock_hive:
            mock_hive.return_value = {"response": "success", "success": True}
            
            client.run_agent(
                agent_name="test_agent",
                message_content="test"
            )
            
            # Verify _call_hive_api was called (not the regular API path)
            mock_hive.assert_called_once()

    def test_original_bug_core_instances_dont_use_wrong_endpoints(self):
        """Test that Core instances don't mistakenly use Hive playground endpoints."""
        client = AgentApiClient()
        client.api_url = "http://localhost:8881"  # Core API port
        client.instance_config = None
        
        # Should detect as Core (not Hive)
        assert client._is_hive_api_mode() is False
        
        # Should use the regular /api/v1/agent/ endpoints
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "success", "success": True}
            mock_post.return_value = mock_response
            
            client._make_headers = Mock(return_value={"Content-Type": "application/json"})
            
            client.run_agent(
                agent_name="test_agent",
                message_content="test"
            )
            
            # Verify the correct endpoint was used
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "/api/v1/agent/" in call_args[0][0]
            assert "/playground/" not in call_args[0][0]

    def test_backward_compatibility_no_config(self):
        """Test that the fix maintains backward compatibility when no instance config is available."""
        # This tests the fallback logic that was fixed
        
        # Test Hive API detection without config
        hive_client = AgentApiClient()
        hive_client.api_url = "http://localhost:8000"
        hive_client.instance_config = None
        
        assert hive_client._is_hive_api_mode() is True
        
        # Test Core API detection without config
        core_client = AgentApiClient()
        core_client.api_url = "http://localhost:8881"
        core_client.instance_config = None
        
        assert core_client._is_hive_api_mode() is False

    def test_different_url_formats(self):
        """Test various URL formats to ensure robust detection."""
        test_cases = [
            # Hive API cases (port 8000)
            ("http://localhost:8000", True),
            ("https://localhost:8000", True),
            ("http://127.0.0.1:8000", True),
            ("https://api.example.com:8000", True),
            ("http://localhost:8000/", True),
            ("http://localhost:8000/some/path", True),
            
            # Core API cases (port 8881)
            ("http://localhost:8881", False),
            ("https://localhost:8881", False),
            ("http://127.0.0.1:8881", False),
            ("https://api.example.com:8881", False),
            ("http://localhost:8881/", False),
            ("http://localhost:8881/api/v1", False),
            
            # Other cases
            ("http://localhost", False),
            ("http://localhost:80", False),
            ("http://localhost:443", False),
            ("https://example.com", False),
        ]
        
        for url, expected_is_hive in test_cases:
            client = AgentApiClient()
            client.api_url = url
            client.instance_config = None
            
            result = client._is_hive_api_mode()
            assert result == expected_is_hive, f"URL {url} should return {expected_is_hive}, got {result}"


if __name__ == "__main__":
    pytest.main([__file__])