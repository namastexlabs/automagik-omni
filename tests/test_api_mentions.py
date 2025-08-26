"""
API endpoint tests for WhatsApp mention functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.api.app import app
from src.db.models import InstanceConfig
# Import the messages module to enable proper mocking
from src.api.routes import messages


class TestApiMentions:
    """Test suite for mention functionality in API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_instance_config(self):
        """Mock instance configuration."""
        config = Mock(spec=InstanceConfig)
        config.name = "test-instance"
        config.channel_type = "whatsapp"  # CRITICAL: Set as string, not Mock
        config.evolution_url = "https://test-evolution.com"
        config.evolution_key = "test-key"
        config.whatsapp_instance = "test-instance"
        return config

    @pytest.fixture
    def api_headers(self):
        """Standard API headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": "Bearer namastex888"
        }

    @patch('src.api.deps.get_instance_by_name')
    @patch('src.channels.whatsapp.evolution_api_sender.EvolutionApiSender')
    @patch.object(messages, '_resolve_recipient')
    def test_send_text_with_auto_parse_mentions(
        self, mock_resolve, mock_sender_class, mock_get_instance, 
        client, mock_instance_config, api_headers
    ):
        """Test send-text endpoint with auto-parse mentions."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "5511777777777@s.whatsapp.net"
        
        mock_sender = Mock()
        mock_sender.send_text_message.return_value = True
        mock_sender_class.return_value = mock_sender
        
        # Test payload with @mentions in text
        payload = {
            "phone_number": "+5511777777777",
            "text": "Hello @5511999999999 and @5511888888888!",
            "auto_parse_mentions": True
        }
        
        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "sent"
        
        # Verify Evolution API sender was called with correct parameters
        assert mock_sender.send_text_message.called, "Mock should have been called"
        call_args = mock_sender.send_text_message.call_args
        
        assert call_args[1]["recipient"] == "5511777777777@s.whatsapp.net"
        assert call_args[1]["text"] == payload["text"]
        assert call_args[1]["auto_parse_mentions"] is True
        assert call_args[1]["mentioned"] is None  # Should be None for auto-parsing
        assert call_args[1]["mentions_everyone"] is False

    @patch('src.api.deps.get_instance_by_name')
    @patch('src.channels.whatsapp.evolution_api_sender.EvolutionApiSender')
    @patch.object(messages, '_resolve_recipient')
    @patch('src.channels.whatsapp.mention_parser.WhatsAppMentionParser.parse_explicit_mentions')
    def test_send_text_with_explicit_mentions(
        self, mock_parse_mentions, mock_resolve, mock_sender_class, 
        mock_get_instance, client, mock_instance_config, api_headers
    ):
        """Test send-text endpoint with explicit mentions."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "5511777777777@s.whatsapp.net"
        mock_parse_mentions.return_value = [
            "5511999999999@s.whatsapp.net",
            "5511888888888@s.whatsapp.net"
        ]
        
        mock_sender = Mock()
        mock_sender.send_text_message.return_value = True
        mock_sender_class.return_value = mock_sender
        
        # Test payload with explicit mentions
        payload = {
            "phone_number": "+5511777777777",
            "text": "Team meeting at 3pm",
            "mentioned": ["+5511999999999", "+5511888888888"],
            "auto_parse_mentions": False
        }
        
        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify mention parsing was called
        mock_parse_mentions.assert_called_once_with(["+5511999999999", "+5511888888888"])
        
        # Verify Evolution API sender was called with converted JIDs
        assert mock_sender.send_text_message.called, "Mock should have been called"
        call_args = mock_sender.send_text_message.call_args
        
        assert call_args[1]["mentioned"] == ["5511999999999@s.whatsapp.net", "5511888888888@s.whatsapp.net"]
        assert call_args[1]["auto_parse_mentions"] is False

    @patch('src.api.deps.get_instance_by_name')
    @patch('src.channels.whatsapp.evolution_api_sender.EvolutionApiSender')
    @patch.object(messages, '_resolve_recipient')
    def test_send_text_with_mentions_everyone(
        self, mock_resolve, mock_sender_class, mock_get_instance,
        client, mock_instance_config, api_headers
    ):
        """Test send-text endpoint with mentions everyone."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "group-id@g.us"
        
        mock_sender = Mock()
        mock_sender.send_text_message.return_value = True
        mock_sender_class.return_value = mock_sender
        
        # Test payload with mentions everyone
        payload = {
            "phone_number": "group-id@g.us",
            "text": "Important group announcement!",
            "mentions_everyone": True
        }
        
        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify Evolution API sender was called with mentions_everyone
        assert mock_sender.send_text_message.called, "Mock should have been called"
        call_args = mock_sender.send_text_message.call_args
        
        assert call_args[1]["mentions_everyone"] is True
        assert call_args[1]["mentioned"] is None

    @patch('src.api.deps.get_instance_by_name')
    @patch('src.channels.whatsapp.evolution_api_sender.EvolutionApiSender')
    @patch.object(messages, '_resolve_recipient')
    def test_send_text_no_mentions(
        self, mock_resolve, mock_sender_class, mock_get_instance,
        client, mock_instance_config, api_headers
    ):
        """Test send-text endpoint without any mentions."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "5511777777777@s.whatsapp.net"
        
        mock_sender = Mock()
        mock_sender.send_text_message.return_value = True
        mock_sender_class.return_value = mock_sender
        
        # Test payload without mentions
        payload = {
            "phone_number": "+5511777777777",
            "text": "Regular message without mentions"
        }
        
        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify Evolution API sender was called with default parameters
        assert mock_sender.send_text_message.called, "Mock should have been called"
        call_args = mock_sender.send_text_message.call_args
        
        assert call_args[1]["mentioned"] is None
        assert call_args[1]["mentions_everyone"] is False
        assert call_args[1]["auto_parse_mentions"] is True  # Default value

    @patch('src.api.deps.get_instance_by_name')
    @patch('src.channels.whatsapp.evolution_api_sender.EvolutionApiSender')
    @patch.object(messages, '_resolve_recipient')
    def test_send_text_sender_failure(
        self, mock_resolve, mock_sender_class, mock_get_instance,
        client, mock_instance_config, api_headers
    ):
        """Test send-text endpoint when sender fails."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "5511777777777@s.whatsapp.net"
        
        mock_sender = Mock()
        mock_sender.send_text_message.return_value = False  # Simulate failure
        mock_sender_class.return_value = mock_sender
        
        payload = {
            "phone_number": "+5511777777777",
            "text": "Test @5511999999999",
            "auto_parse_mentions": True
        }
        
        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "failed"

    def test_send_text_missing_api_key(self, client):
        """Test send-text endpoint without API key."""
        payload = {
            "phone_number": "+5511777777777",
            "text": "Test message"
        }
        
        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 403

    def test_send_text_invalid_instance(self, client, api_headers):
        """Test send-text endpoint with invalid instance."""
        payload = {
            "phone_number": "+5511777777777",
            "text": "Test message"
        }
        
        with patch('src.api.routes.messages.get_instance_by_name') as mock_get_instance:
            from fastapi import HTTPException, status
            mock_get_instance.side_effect = HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance 'invalid-instance' not found"
            )
            
            response = client.post(
                "/api/v1/instance/invalid-instance/send-text",
                json=payload,
                headers=api_headers
            )
            
            assert response.status_code == 404

    @pytest.mark.parametrize("payload,expected_auto_parse,expected_mentions_everyone", [
        # Default values
        ({"phone_number": "+5511777777777", "text": "test"}, True, False),
        
        # Explicit auto_parse_mentions
        ({"phone_number": "+5511777777777", "text": "test", "auto_parse_mentions": False}, False, False),
        
        # Explicit mentions_everyone
        ({"phone_number": "+5511777777777", "text": "test", "mentions_everyone": True}, True, True),
        
        # Both explicit
        ({"phone_number": "+5511777777777", "text": "test", "auto_parse_mentions": False, "mentions_everyone": True}, False, True),
    ])
    @patch('src.api.deps.get_instance_by_name')
    @patch('src.channels.whatsapp.evolution_api_sender.EvolutionApiSender')
    @patch.object(messages, '_resolve_recipient')
    def test_send_text_parameter_defaults(
        self, mock_resolve, mock_sender_class, mock_get_instance,
        client, mock_instance_config, api_headers,
        payload, expected_auto_parse, expected_mentions_everyone
    ):
        """Test that mention parameters have correct default values."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "5511777777777@s.whatsapp.net"
        
        mock_sender = Mock()
        mock_sender.send_text_message.return_value = True
        mock_sender_class.return_value = mock_sender
        
        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers
        )
        
        assert response.status_code == 200
        
        # Verify parameters were passed correctly
        assert mock_sender.send_text_message.called, "Mock should have been called"
        call_args = mock_sender.send_text_message.call_args
        
        assert call_args[1]["auto_parse_mentions"] == expected_auto_parse
        assert call_args[1]["mentions_everyone"] == expected_mentions_everyone

    def test_send_text_schema_validation(self, client, api_headers):
        """Test that the API validates mention-related fields correctly."""
        # Test valid payload
        valid_payload = {
            "phone_number": "+5511777777777",
            "text": "Test message",
            "auto_parse_mentions": True,
            "mentioned": ["+5511999999999"],
            "mentions_everyone": False
        }
        
        with patch('src.api.routes.messages.get_instance_by_name'), \
             patch('src.api.routes.messages.EvolutionApiSender'), \
             patch('src.api.routes.messages._resolve_recipient'):
            
            response = client.post(
                "/api/v1/instance/test-instance/send-text",
                json=valid_payload,
                headers=api_headers
            )
            
            # Should not fail validation
            assert response.status_code != 422

    def test_send_text_with_empty_mentioned_list(
        self, client, api_headers
    ):
        """Test send-text with empty mentioned list."""
        payload = {
            "phone_number": "+5511777777777",
            "text": "Test message",
            "mentioned": []  # Empty list
        }
        
        with patch('src.api.routes.messages.get_instance_by_name') as mock_get_instance, \
             patch('src.api.routes.messages.EvolutionApiSender') as mock_sender_class, \
             patch('src.api.routes.messages._resolve_recipient') as mock_resolve:
            
            mock_instance_config = Mock()
            mock_instance_config.channel_type = "whatsapp"  # CRITICAL: Set channel_type
            mock_get_instance.return_value = mock_instance_config
            mock_resolve.return_value = "5511777777777@s.whatsapp.net"
            
            mock_sender = Mock()
            mock_sender.send_text_message.return_value = True
            mock_sender_class.return_value = mock_sender
            
            response = client.post(
                "/api/v1/instance/test-instance/send-text",
                json=payload,
                headers=api_headers
            )
            
            assert response.status_code == 200
            
            # Should pass None to sender since empty list
            call_args = mock_sender.send_text_message.call_args
            assert call_args[1]["mentioned"] is None


if __name__ == "__main__":
    # Run basic tests manually
    pytest.main([__file__, "-v"])