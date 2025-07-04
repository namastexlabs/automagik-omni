"""
Tests for telemetry functionality.
"""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.core.telemetry import TelemetryClient, telemetry_client


class TestTelemetryClient:
    """Test the TelemetryClient class."""

    def test_telemetry_disabled_by_env_var(self):
        """Test that telemetry is disabled by environment variable."""
        with patch.dict(os.environ, {"AUTOMAGIK_OMNI_DISABLE_TELEMETRY": "true"}):
            client = TelemetryClient()
            assert not client.is_enabled()

    def test_telemetry_disabled_by_opt_out_file(self):
        """Test that telemetry is disabled by opt-out file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            opt_out_file = Path(temp_dir) / ".automagik-omni-no-telemetry"
            opt_out_file.touch()
            
            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                client = TelemetryClient()
                assert not client.is_enabled()

    def test_telemetry_disabled_in_ci(self):
        """Test that telemetry is auto-disabled in CI environments."""
        with patch.dict(os.environ, {"CI": "true"}):
            client = TelemetryClient()
            assert not client.is_enabled()

    def test_telemetry_enabled_by_default(self):
        """Test that telemetry is enabled by default in normal environments."""
        # Clear any CI environment variables
        ci_vars = ["CI", "GITHUB_ACTIONS", "TRAVIS", "JENKINS", "GITLAB_CI"]
        env_without_ci = {k: v for k, v in os.environ.items() if k not in ci_vars}
        env_without_ci.pop("AUTOMAGIK_OMNI_DISABLE_TELEMETRY", None)
        
        with patch.dict(os.environ, env_without_ci, clear=True):
            with tempfile.TemporaryDirectory() as temp_dir:
                with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                    client = TelemetryClient()
                    assert client.is_enabled()

    def test_user_id_persistence(self):
        """Test that user ID is persisted across sessions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                client1 = TelemetryClient()
                user_id_1 = client1.user_id
                
                client2 = TelemetryClient()
                user_id_2 = client2.user_id
                
                assert user_id_1 == user_id_2
                assert len(user_id_1) == 36  # UUID length

    def test_disable_telemetry(self):
        """Test disabling telemetry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                client = TelemetryClient()
                assert client.is_enabled()
                
                client.disable()
                assert not client.is_enabled()
                
                # Check that opt-out file was created
                opt_out_file = Path(temp_dir) / ".automagik-omni-no-telemetry"
                assert opt_out_file.exists()

    def test_enable_telemetry(self):
        """Test enabling telemetry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            opt_out_file = Path(temp_dir) / ".automagik-omni-no-telemetry"
            opt_out_file.touch()
            
            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                client = TelemetryClient()
                assert not client.is_enabled()
                
                client.enable()
                assert client.is_enabled()
                
                # Check that opt-out file was removed
                assert not opt_out_file.exists()

    def test_track_command_disabled(self):
        """Test that tracking does nothing when disabled."""
        with patch.dict(os.environ, {"AUTOMAGIK_OMNI_DISABLE_TELEMETRY": "true"}):
            client = TelemetryClient()
            
            # Mock the _send_event method to ensure it's not called
            with patch.object(client, '_send_event') as mock_send:
                client.track_command("test_command", success=True)
                mock_send.assert_not_called()

    @patch('urllib.request.urlopen')
    def test_track_command_enabled(self, mock_urlopen):
        """Test that tracking works when enabled."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = mock_response
        
        # Clear CI environment variables
        ci_vars = ["CI", "GITHUB_ACTIONS", "TRAVIS", "JENKINS", "GITLAB_CI"]
        env_without_ci = {k: v for k, v in os.environ.items() if k not in ci_vars}
        env_without_ci.pop("AUTOMAGIK_OMNI_DISABLE_TELEMETRY", None)
        
        with patch.dict(os.environ, env_without_ci, clear=True):
            with tempfile.TemporaryDirectory() as temp_dir:
                with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                    client = TelemetryClient()
                    client.track_command("test_command", success=True, duration_ms=100)
                    
                    # Verify that urlopen was called
                    mock_urlopen.assert_called_once()

    def test_get_status(self):
        """Test getting telemetry status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                client = TelemetryClient()
                status = client.get_status()
                
                assert isinstance(status, dict)
                assert "enabled" in status
                assert "user_id" in status
                assert "session_id" in status
                assert "project_name" in status
                assert "project_version" in status
                assert "endpoint" in status
                assert status["project_name"] == "automagik-omni"
                assert status["project_version"] == "0.2.0"

    def test_system_info_collection(self):
        """Test that system information is collected correctly."""
        client = TelemetryClient()
        system_info = client._get_system_info()
        
        assert "os" in system_info
        assert "python_version" in system_info
        assert "architecture" in system_info
        assert "project_name" in system_info
        assert system_info["project_name"] == "automagik-omni"

    def test_attributes_creation(self):
        """Test OTLP attribute creation."""
        client = TelemetryClient()
        data = {
            "string_value": "test",
            "int_value": 42,
            "float_value": 3.14,
            "bool_value": True,
            "long_string": "x" * 600  # Should be truncated
        }
        
        attributes = client._create_attributes(data)
        
        # Check that all attributes are present
        event_attrs = [attr for attr in attributes if attr["key"].startswith("event.")]
        assert len(event_attrs) == len(data)
        
        # Check truncation of long strings
        long_string_attr = next(attr for attr in event_attrs if attr["key"] == "event.long_string")
        assert len(long_string_attr["value"]["stringValue"]) == 500

    @patch('urllib.request.urlopen')
    def test_network_error_handling(self, mock_urlopen):
        """Test that network errors are handled gracefully."""
        from urllib.error import URLError
        
        # Setup mock to raise network error
        mock_urlopen.side_effect = URLError("Network error")
        
        # Clear CI environment variables
        ci_vars = ["CI", "GITHUB_ACTIONS", "TRAVIS", "JENKINS", "GITLAB_CI"]
        env_without_ci = {k: v for k, v in os.environ.items() if k not in ci_vars}
        env_without_ci.pop("AUTOMAGIK_OMNI_DISABLE_TELEMETRY", None)
        
        with patch.dict(os.environ, env_without_ci, clear=True):
            with tempfile.TemporaryDirectory() as temp_dir:
                with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                    client = TelemetryClient()
                    
                    # This should not raise an exception
                    client.track_command("test_command", success=True)
                    
                    # Verify that urlopen was called (and failed)
                    mock_urlopen.assert_called_once()


class TestTelemetryFunctions:
    """Test the convenience functions."""

    def test_global_telemetry_client_exists(self):
        """Test that global telemetry client exists."""
        assert telemetry_client is not None
        assert isinstance(telemetry_client, TelemetryClient)

    def test_convenience_functions_exist(self):
        """Test that all convenience functions are available."""
        from src.core.telemetry import (
            track_command,
            track_api_request,
            track_webhook_processed,
            track_instance_operation,
            track_feature_usage,
            enable_telemetry,
            disable_telemetry,
            is_telemetry_enabled,
            get_telemetry_status
        )
        
        # Just check that they're callable
        assert callable(track_command)
        assert callable(track_api_request)
        assert callable(track_webhook_processed)
        assert callable(track_instance_operation)
        assert callable(track_feature_usage)
        assert callable(enable_telemetry)
        assert callable(disable_telemetry)
        assert callable(is_telemetry_enabled)
        assert callable(get_telemetry_status)