"""
API endpoint tests for WhatsApp mention functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.api.app import app
from src.db.models import InstanceConfig

# Import the messages module to enable proper mocking


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
            "Authorization": "Bearer namastex888",
        }

    @patch("src.api.routes.messages.get_instance_by_name")
    @patch("requests.post")
    @patch("src.api.routes.messages._resolve_recipient")
    def test_send_text_with_auto_parse_mentions(
        self,
        mock_resolve,
        mock_requests_post,
        mock_get_instance,
        client,
        mock_instance_config,
        api_headers,
    ):
        """Test send-text endpoint with auto-parse mentions."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "5511777777777@s.whatsapp.net"

        # Mock HTTP response for Evolution API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_requests_post.return_value = mock_response

        # Test payload with @mentions in text
        payload = {
            "phone_number": "+5511777777777",
            "text": "Hello @5511999999999 and @5511888888888!",
            "auto_parse_mentions": True,
        }

        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "sent"

        # Verify Evolution API HTTP request was made
        assert mock_requests_post.called, "HTTP request should have been made"
        call_args = mock_requests_post.call_args

        # Check URL was called correctly
        request_url = call_args[0][0]
        assert "test-evolution.com" in request_url
        assert "/message/sendText/" in request_url
        assert "test-instance" in request_url

        # Check headers
        request_headers = call_args[1]["headers"]
        assert request_headers["apikey"] == "test-key"
        assert request_headers["Content-Type"] == "application/json"

        # Check payload
        request_payload = call_args[1]["json"]
        assert request_payload["number"] == "5511777777777"
        assert request_payload["textMessage"]["text"] == payload["text"]

        # Should have auto-parsed mentions in the payload
        assert "mentioned" in request_payload
        mentions = request_payload["mentioned"]
        assert "5511999999999@s.whatsapp.net" in mentions
        assert "5511888888888@s.whatsapp.net" in mentions

    @patch("src.api.routes.messages.get_instance_by_name")
    @patch("requests.post")
    @patch("src.api.routes.messages._resolve_recipient")
    @patch("src.api.routes.messages.WhatsAppMentionParser.parse_explicit_mentions")
    def test_send_text_with_explicit_mentions(
        self,
        mock_parse_mentions,
        mock_resolve,
        mock_requests_post,
        mock_get_instance,
        client,
        mock_instance_config,
        api_headers,
    ):
        """Test send-text endpoint with explicit mentions."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "5511777777777@s.whatsapp.net"
        mock_parse_mentions.return_value = [
            "5511999999999@s.whatsapp.net",
            "5511888888888@s.whatsapp.net",
        ]

        # Mock HTTP response for Evolution API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_requests_post.return_value = mock_response

        # Test payload with explicit mentions
        payload = {
            "phone_number": "+5511777777777",
            "text": "Team meeting at 3pm",
            "mentioned": ["+5511999999999", "+5511888888888"],
            "auto_parse_mentions": False,
        }

        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify mention parsing was called
        mock_parse_mentions.assert_called_once_with(["+5511999999999", "+5511888888888"])

        # Verify Evolution API HTTP request was made
        assert mock_requests_post.called, "HTTP request should have been made"
        call_args = mock_requests_post.call_args

        # Check payload contains explicit mentions
        request_payload = call_args[1]["json"]
        assert "mentioned" in request_payload
        assert request_payload["mentioned"] == [
            "5511999999999@s.whatsapp.net",
            "5511888888888@s.whatsapp.net",
        ]

    @patch("src.api.routes.messages.get_instance_by_name")
    @patch("requests.post")
    @patch("src.api.routes.messages._resolve_recipient")
    def test_send_text_with_mentions_everyone(
        self,
        mock_resolve,
        mock_requests_post,
        mock_get_instance,
        client,
        mock_instance_config,
        api_headers,
    ):
        """Test send-text endpoint with mentions everyone."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "group-id@g.us"

        # Mock HTTP response for Evolution API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_requests_post.return_value = mock_response

        # Test payload with mentions everyone
        payload = {
            "phone_number": "group-id@g.us",
            "text": "Important group announcement!",
            "mentions_everyone": True,
        }

        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify Evolution API HTTP request was made
        assert mock_requests_post.called, "HTTP request should have been made"
        call_args = mock_requests_post.call_args

        # Check payload contains mentions everyone
        request_payload = call_args[1]["json"]
        assert "mentionsEveryOne" in request_payload
        assert request_payload["mentionsEveryOne"] is True

    @patch("src.api.routes.messages.get_instance_by_name")
    @patch("requests.post")
    @patch("src.api.routes.messages._resolve_recipient")
    def test_send_text_no_mentions(
        self,
        mock_resolve,
        mock_requests_post,
        mock_get_instance,
        client,
        mock_instance_config,
        api_headers,
    ):
        """Test send-text endpoint without any mentions."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "5511777777777@s.whatsapp.net"

        # Mock HTTP response for Evolution API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_requests_post.return_value = mock_response

        # Test payload without mentions
        payload = {
            "phone_number": "+5511777777777",
            "text": "Regular message without mentions",
        }

        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify Evolution API HTTP request was made
        assert mock_requests_post.called, "HTTP request should have been made"
        call_args = mock_requests_post.call_args

        # Check payload does not contain mentions (clean message)
        request_payload = call_args[1]["json"]
        assert "mentioned" not in request_payload or not request_payload.get("mentioned")
        assert "mentionsEveryOne" not in request_payload or not request_payload.get("mentionsEveryOne")

    @patch("src.api.routes.messages.get_instance_by_name")
    @patch("requests.post")
    @patch("src.api.routes.messages._resolve_recipient")
    def test_send_text_sender_failure(
        self,
        mock_resolve,
        mock_requests_post,
        mock_get_instance,
        client,
        mock_instance_config,
        api_headers,
    ):
        """Test send-text endpoint when sender fails."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "5511777777777@s.whatsapp.net"

        # Mock HTTP response for Evolution API failure
        mock_response = Mock()
        mock_response.status_code = 500  # Simulate HTTP error
        mock_response.raise_for_status.side_effect = Exception("Server error")
        mock_requests_post.return_value = mock_response

        payload = {
            "phone_number": "+5511777777777",
            "text": "Test @5511999999999",
            "auto_parse_mentions": True,
        }

        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "failed"

    def test_send_text_missing_api_key(self, client):
        """Test send-text endpoint without API key."""
        payload = {"phone_number": "+5511777777777", "text": "Test message"}

        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 403

    def test_send_text_invalid_instance(self, client, api_headers):
        """Test send-text endpoint with invalid instance."""
        payload = {"phone_number": "+5511777777777", "text": "Test message"}

        with patch("src.api.routes.messages.get_instance_by_name") as mock_get_instance:
            from fastapi import HTTPException, status

            mock_get_instance.side_effect = HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance 'invalid-instance' not found",
            )

            response = client.post(
                "/api/v1/instance/invalid-instance/send-text",
                json=payload,
                headers=api_headers,
            )

            assert response.status_code == 404

    @pytest.mark.parametrize(
        "payload,expected_auto_parse,expected_mentions_everyone",
        [
            # Default values
            ({"phone_number": "+5511777777777", "text": "test"}, True, False),
            # Explicit auto_parse_mentions
            (
                {
                    "phone_number": "+5511777777777",
                    "text": "test",
                    "auto_parse_mentions": False,
                },
                False,
                False,
            ),
            # Explicit mentions_everyone
            (
                {
                    "phone_number": "+5511777777777",
                    "text": "test",
                    "mentions_everyone": True,
                },
                True,
                True,
            ),
            # Both explicit
            (
                {
                    "phone_number": "+5511777777777",
                    "text": "test",
                    "auto_parse_mentions": False,
                    "mentions_everyone": True,
                },
                False,
                True,
            ),
        ],
    )
    @patch("src.api.routes.messages.get_instance_by_name")
    @patch("requests.post")
    @patch("src.api.routes.messages._resolve_recipient")
    def test_send_text_parameter_defaults(
        self,
        mock_resolve,
        mock_requests_post,
        mock_get_instance,
        client,
        mock_instance_config,
        api_headers,
        payload,
        expected_auto_parse,
        expected_mentions_everyone,
    ):
        """Test that mention parameters have correct default values."""
        # Setup mocks
        mock_get_instance.return_value = mock_instance_config
        mock_resolve.return_value = "5511777777777@s.whatsapp.net"

        # Mock HTTP response for Evolution API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_requests_post.return_value = mock_response

        response = client.post(
            "/api/v1/instance/test-instance/send-text",
            json=payload,
            headers=api_headers,
        )

        assert response.status_code == 200

        # Verify HTTP request was made
        assert mock_requests_post.called, "HTTP request should have been made"
        call_args = mock_requests_post.call_args

        # Check payload based on expected behavior
        request_payload = call_args[1]["json"]
        if expected_mentions_everyone:
            assert request_payload.get("mentionsEveryOne") is True
        else:
            assert not request_payload.get("mentionsEveryOne", False)

    def test_send_text_schema_validation(self, client, api_headers):
        """Test that the API validates mention-related fields correctly."""
        # Test valid payload
        valid_payload = {
            "phone_number": "+5511777777777",
            "text": "Test message",
            "auto_parse_mentions": True,
            "mentioned": ["+5511999999999"],
            "mentions_everyone": False,
        }

        with (
            patch("src.api.routes.messages.get_instance_by_name"),
            patch("src.api.routes.messages.OmniChannelMessageSender"),
            patch("src.api.routes.messages._resolve_recipient"),
        ):
            response = client.post(
                "/api/v1/instance/test-instance/send-text",
                json=valid_payload,
                headers=api_headers,
            )

            # Should not fail validation
            assert response.status_code != 422

    def test_send_text_with_empty_mentioned_list(self, client, api_headers):
        """Test send-text with empty mentioned list."""
        payload = {
            "phone_number": "+5511777777777",
            "text": "Test message",
            "mentioned": [],  # Empty list
        }

        with (
            patch("src.api.routes.messages.get_instance_by_name") as mock_get_instance,
            patch("requests.post") as mock_requests_post,
            patch("src.api.routes.messages._resolve_recipient") as mock_resolve,
        ):
            mock_instance_config = Mock()
            mock_instance_config.channel_type = "whatsapp"  # CRITICAL: Set channel_type
            mock_instance_config.evolution_url = "https://test-evolution.com"
            mock_instance_config.evolution_key = "test-key"
            mock_instance_config.whatsapp_instance = "test-instance"
            mock_get_instance.return_value = mock_instance_config
            mock_resolve.return_value = "5511777777777@s.whatsapp.net"

            # Mock HTTP response for Evolution API
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_requests_post.return_value = mock_response

            response = client.post(
                "/api/v1/instance/test-instance/send-text",
                json=payload,
                headers=api_headers,
            )

            assert response.status_code == 200

            # Should not have mentioned field or should be empty
            call_args = mock_requests_post.call_args
            request_payload = call_args[1]["json"]
            assert "mentioned" not in request_payload or not request_payload.get("mentioned")


if __name__ == "__main__":
    # Run basic tests manually
    pytest.main([__file__, "-v"])
