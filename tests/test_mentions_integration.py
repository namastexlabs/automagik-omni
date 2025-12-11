"""
Integration tests for WhatsApp mention functionality end-to-end flow.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from src.api.app import app
from src.db.models import InstanceConfig
from src.channels.whatsapp.mention_parser import WhatsAppMentionParser
from src.channels.whatsapp.evolution_api_sender import EvolutionApiSender


class TestMentionsIntegration:
    """Integration tests for the complete mention flow."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def test_instance_config(self):
        """Create a test instance configuration."""
        config = Mock(spec=InstanceConfig)
        config.name = "test-instance"
        config.channel_type = "whatsapp"  # CRITICAL: Required for OmniChannelMessageSender routing
        config.evolution_url = "https://test-evolution.com"
        config.evolution_key = "test-evolution-key"
        # Property aliases used by EvolutionApiSender
        config.whatsapp_web_url = "https://test-evolution.com"
        config.whatsapp_web_key = "test-evolution-key"
        config.whatsapp_instance = "test-whatsapp-instance"
        config.agent_api_url = "https://test-agent.com"
        config.agent_api_key = "test-agent-key"
        config.default_agent = "test-agent"
        config.enable_auto_split = True
        return config

    @pytest.fixture
    def api_headers(self):
        """Standard API headers for testing."""
        return {
            "Content-Type": "application/json",
            "x-api-key": "namastex888",
        }

    def test_complete_mention_flow_auto_parse(self, client, test_instance_config, api_headers):
        """Test complete flow from API request to Evolution API call with auto-parsed mentions."""

        # Mock the entire flow
        with (
            patch("src.api.routes.messages.get_instance_by_name") as mock_get_instance,
            patch("src.api.routes.messages._resolve_recipient") as mock_resolve,
            patch("requests.post") as mock_http_post,
        ):
            # Setup mocks
            mock_get_instance.return_value = test_instance_config
            mock_resolve.return_value = "5511777777777@s.whatsapp.net"

            # Mock successful Evolution API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_http_post.return_value = mock_response

            # Test payload with mentions
            payload = {
                "phone_number": "+5511777777777",
                "text": "Hello @5511999999999 and @+55 11 888888888, meeting at 3pm!",
                "auto_parse_mentions": True,
            }

            # Make API request
            response = client.post(
                "/api/v1/instance/test-instance/send-text",
                json=payload,
                headers=api_headers,
            )

            # Verify API response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "sent"

            # Verify Evolution API was called
            mock_http_post.assert_called_once()

            # Check the Evolution API call details
            call_args = mock_http_post.call_args
            request_url = call_args[0][0]
            request_payload = call_args[1]["json"]
            request_headers = call_args[1]["headers"]

            # Verify URL structure
            assert "test-evolution.com" in request_url
            assert "/message/sendText/" in request_url
            assert "test-whatsapp-instance" in request_url

            # Verify headers
            assert request_headers["apikey"] == "test-evolution-key"
            assert request_headers["Content-Type"] == "application/json"

            # Verify payload structure
            assert request_payload["number"] == "5511777777777"
            assert request_payload["text"] == payload["text"]

            # Verify mentions were parsed correctly
            assert "mentioned" in request_payload
            mentions = request_payload["mentioned"]
            assert len(mentions) == 2
            assert "5511999999999@s.whatsapp.net" in mentions
            assert "5511888888888@s.whatsapp.net" in mentions

    def test_complete_mention_flow_explicit_mentions(self, client, test_instance_config, api_headers):
        """Test complete flow with explicit mentions."""

        with (
            patch("src.api.routes.messages.get_instance_by_name") as mock_get_instance,
            patch("src.api.routes.messages._resolve_recipient") as mock_resolve,
            patch("requests.post") as mock_http_post,
        ):
            # Setup mocks
            mock_get_instance.return_value = test_instance_config
            mock_resolve.return_value = "group-id@g.us"

            mock_response = Mock()
            mock_response.status_code = 200
            mock_http_post.return_value = mock_response

            # Test payload with explicit mentions
            payload = {
                "phone_number": "group-id@g.us",
                "text": "Team meeting canceled",
                "mentioned": ["+5511999999999", "5511888888888", "+55 11 777777777"],
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

            # Verify Evolution API payload
            call_args = mock_http_post.call_args
            request_payload = call_args[1]["json"]

            assert request_payload["number"] == "group-id"  # Stripped @g.us
            assert "mentioned" in request_payload

            mentions = request_payload["mentioned"]
            assert len(mentions) == 3
            assert "5511999999999@s.whatsapp.net" in mentions
            assert "5511888888888@s.whatsapp.net" in mentions
            assert "5511777777777@s.whatsapp.net" in mentions

    def test_complete_mention_flow_everyone(self, client, test_instance_config, api_headers):
        """Test complete flow with mention everyone."""

        with (
            patch("src.api.routes.messages.get_instance_by_name") as mock_get_instance,
            patch("src.api.routes.messages._resolve_recipient") as mock_resolve,
            patch("requests.post") as mock_http_post,
        ):
            mock_get_instance.return_value = test_instance_config
            mock_resolve.return_value = "group-id@g.us"

            mock_response = Mock()
            mock_response.status_code = 200
            mock_http_post.return_value = mock_response

            payload = {
                "phone_number": "group-id@g.us",
                "text": "🚨 URGENT: Server maintenance in 5 minutes!",
                "mentions_everyone": True,
            }

            response = client.post(
                "/api/v1/instance/test-instance/send-text",
                json=payload,
                headers=api_headers,
            )

            assert response.status_code == 200

            # Verify Evolution API payload includes mentionsEveryOne
            call_args = mock_http_post.call_args
            request_payload = call_args[1]["json"]

            assert request_payload["mentionsEveryOne"] is True
            assert request_payload["text"] == payload["text"]

    def test_mention_flow_with_split_messages(self, client, test_instance_config, api_headers):
        """Test mention flow when message gets split."""

        with (
            patch("src.api.routes.messages.get_instance_by_name") as mock_get_instance,
            patch("src.api.routes.messages._resolve_recipient") as mock_resolve,
            patch("requests.post") as mock_http_post,
        ):
            mock_get_instance.return_value = test_instance_config
            mock_resolve.return_value = "5511777777777@s.whatsapp.net"

            mock_response = Mock()
            mock_response.status_code = 200
            mock_http_post.return_value = mock_response

            # Long message that will be split
            payload = {
                "phone_number": "+5511777777777",
                "text": "First part with @5511999999999\n\nSecond part without mentions",
                "auto_parse_mentions": True,
            }

            response = client.post(
                "/api/v1/instance/test-instance/send-text",
                json=payload,
                headers=api_headers,
            )

            assert response.status_code == 200

            # Should have made 2 Evolution API calls (split message)
            assert mock_http_post.call_count == 2

            # First message should have mentions
            first_call = mock_http_post.call_args_list[0]
            first_payload = first_call[1]["json"]
            assert "mentioned" in first_payload
            assert "5511999999999@s.whatsapp.net" in first_payload["mentioned"]
            assert first_payload["text"] == "First part with @5511999999999"

            # Second message should not have mentions
            second_call = mock_http_post.call_args_list[1]
            second_payload = second_call[1]["json"]
            assert "mentioned" not in second_payload
            assert second_payload["text"] == "Second part without mentions"

    def test_mention_flow_error_handling(self, client, test_instance_config, api_headers):
        """Test mention flow with various error conditions."""

        with (
            patch("src.api.routes.messages.get_instance_by_name") as mock_get_instance,
            patch("src.api.routes.messages._resolve_recipient") as mock_resolve,
        ):
            mock_get_instance.return_value = test_instance_config
            mock_resolve.return_value = "5511777777777@s.whatsapp.net"

            # Test Evolution API failure
            with patch("requests.post") as mock_http_post:
                mock_http_post.side_effect = Exception("Network error")

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

    def test_mention_flow_400_error_handling(self, client, test_instance_config, api_headers):
        """Test mention flow with Evolution API 400 error (known issue)."""

        with (
            patch("src.api.routes.messages.get_instance_by_name") as mock_get_instance,
            patch("src.api.routes.messages._resolve_recipient") as mock_resolve,
            patch("requests.post") as mock_http_post,
        ):
            mock_get_instance.return_value = test_instance_config
            mock_resolve.return_value = "5511777777777@s.whatsapp.net"

            # Mock 400 error response (known Evolution API issue)
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"message": "database schema issue"}
            mock_http_post.return_value = mock_response

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

            # Should still report success (known issue handling)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_real_world_mention_scenarios(self, client, test_instance_config, api_headers):
        """Test realistic mention scenarios."""

        scenarios = [
            {
                "name": "Brazilian phone formats",
                "payload": {
                    "phone_number": "+5511777777777",
                    "text": "Reunião com @5511999999999, @+5511888888888 e @55 11 666666666 às 15h",
                    "auto_parse_mentions": True,
                },
                "expected_mentions": 3,
            },
            {
                "name": "Mixed mentions and emails",
                "payload": {
                    "phone_number": "+5511777777777",
                    "text": "Contato: @5511999999999 ou email@domain.com",
                    "auto_parse_mentions": True,
                },
                "expected_mentions": 1,
            },
            {
                "name": "Group announcement",
                "payload": {
                    "phone_number": "group-123@g.us",
                    "text": "🎉 Parabéns equipe! Reunião cancelada.",
                    "mentions_everyone": True,
                },
                "expected_mentions": 0,
                "expect_everyone": True,
            },
        ]

        for scenario in scenarios:
            with (
                patch("src.api.routes.messages.get_instance_by_name") as mock_get_instance,
                patch("src.api.routes.messages._resolve_recipient") as mock_resolve,
                patch("requests.post") as mock_http_post,
            ):
                mock_get_instance.return_value = test_instance_config
                mock_resolve.return_value = scenario["payload"]["phone_number"]

                mock_response = Mock()
                mock_response.status_code = 200
                mock_http_post.return_value = mock_response

                response = client.post(
                    "/api/v1/instance/test-instance/send-text",
                    json=scenario["payload"],
                    headers=api_headers,
                )

                assert response.status_code == 200, f"Failed scenario: {scenario['name']}"

                if scenario["expected_mentions"] > 0:
                    call_args = mock_http_post.call_args
                    request_payload = call_args[1]["json"]
                    assert len(request_payload.get("mentioned", [])) == scenario["expected_mentions"]

                if scenario.get("expect_everyone"):
                    call_args = mock_http_post.call_args
                    request_payload = call_args[1]["json"]
                    assert request_payload.get("mentionsEveryOne") is True

    def test_mention_parser_integration_with_sender(self):
        """Test direct integration between mention parser and sender."""

        # Test the integration without HTTP mocking
        parser = WhatsAppMentionParser()
        sender = EvolutionApiSender()

        # Configure sender
        sender.server_url = "https://test-evolution.com"
        sender.api_key = "test-key"
        sender.instance_name = "test-instance"

        test_text = "Meeting with @5511999999999 and @+55 11 888888888"

        # Parse mentions
        original, mentions = parser.extract_mentions(test_text)

        assert len(mentions) == 2
        assert "5511999999999@s.whatsapp.net" in mentions
        assert "5511888888888@s.whatsapp.net" in mentions

        # Test that sender can use parsed mentions
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = sender.send_text_message(
                recipient="5511777777777",
                text=test_text,
                mentioned=mentions,
                auto_parse_mentions=False,
            )

            assert result is True

            # Verify the payload
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["mentioned"] == mentions

    @pytest.mark.parametrize(
        "auto_parse,explicit_mentions,mentions_everyone,expected_api_calls",
        [
            (True, None, False, 1),  # Auto-parse only
            (False, ["5511999999999"], False, 1),  # Explicit mentions only
            (True, None, True, 1),  # Auto-parse + everyone
            (False, ["5511999999999"], True, 1),  # Explicit + everyone
            (True, None, False, 2),  # Auto-parse with split message
        ],
    )
    def test_mention_parameter_combinations(
        self,
        client,
        test_instance_config,
        api_headers,
        auto_parse,
        explicit_mentions,
        mentions_everyone,
        expected_api_calls,
    ):
        """Test various combinations of mention parameters."""

        with (
            patch("src.api.routes.messages.get_instance_by_name") as mock_get_instance,
            patch("src.api.routes.messages._resolve_recipient") as mock_resolve,
            patch("requests.post") as mock_http_post,
        ):
            mock_get_instance.return_value = test_instance_config
            mock_resolve.return_value = "5511777777777@s.whatsapp.net"

            mock_response = Mock()
            mock_response.status_code = 200
            mock_http_post.return_value = mock_response

            # Prepare payload
            payload = {
                "phone_number": "+5511777777777",
                "text": ("Test @5511999999999\n\nSecond part" if expected_api_calls == 2 else "Test @5511999999999"),
                "auto_parse_mentions": auto_parse,
                "mentions_everyone": mentions_everyone,
            }

            if explicit_mentions:
                payload["mentioned"] = explicit_mentions

            response = client.post(
                "/api/v1/instance/test-instance/send-text",
                json=payload,
                headers=api_headers,
            )

            assert response.status_code == 200
            assert mock_http_post.call_count == expected_api_calls


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
