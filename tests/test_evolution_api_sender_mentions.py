"""
Unit tests for Evolution API sender mention functionality.
"""

import pytest
from unittest.mock import Mock, patch

from src.channels.whatsapp.evolution_api_sender import EvolutionApiSender


class TestEvolutionApiSenderMentions:
    """Test suite for Evolution API sender mention functionality."""

    @pytest.fixture
    def sender(self):
        """Create a configured Evolution API sender for testing."""
        sender = EvolutionApiSender()
        sender.server_url = "https://test-evolution-api.com"
        sender.api_key = "test-api-key"
        sender.instance_name = "test-instance"
        return sender

    @pytest.fixture
    def mock_response(self):
        """Mock successful HTTP response."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    @patch("src.channels.whatsapp.evolution_api_sender.requests.post")
    def test_send_text_message_with_auto_parsed_mentions(self, mock_post, sender, mock_response):
        """Test sending message with auto-parsed mentions."""
        mock_post.return_value = mock_response

        text = "Hello @5511999999999 and @5511888888888!"
        recipient = "5511777777777"

        result = sender.send_text_message(recipient=recipient, text=text, auto_parse_mentions=True)

        assert result is True
        mock_post.assert_called_once()

        # Verify the payload includes parsed mentions
        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        assert payload["number"] == recipient.replace("@g.us", "")
        assert payload["textMessage"]["text"] == text
        assert "mentioned" in payload
        assert len(payload["mentioned"]) == 2
        assert "5511999999999@s.whatsapp.net" in payload["mentioned"]
        assert "5511888888888@s.whatsapp.net" in payload["mentioned"]

    @patch("src.channels.whatsapp.evolution_api_sender.requests.post")
    def test_send_text_message_with_explicit_mentions(self, mock_post, sender, mock_response):
        """Test sending message with explicit mentions."""
        mock_post.return_value = mock_response

        text = "Team meeting at 3pm"
        recipient = "5511777777777"
        mentioned_jids = [
            "5511999999999@s.whatsapp.net",
            "5511888888888@s.whatsapp.net",
        ]

        result = sender.send_text_message(
            recipient=recipient,
            text=text,
            mentioned=mentioned_jids,
            auto_parse_mentions=False,
        )

        assert result is True
        mock_post.assert_called_once()

        # Verify the payload includes explicit mentions
        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        assert payload["number"] == recipient.replace("@g.us", "")
        assert payload["textMessage"]["text"] == text
        assert payload["mentioned"] == mentioned_jids

    @patch("src.channels.whatsapp.evolution_api_sender.requests.post")
    def test_send_text_message_with_mentions_everyone(self, mock_post, sender, mock_response):
        """Test sending message with mentions everyone."""
        mock_post.return_value = mock_response

        text = "Important announcement!"
        recipient = "group-id@g.us"

        result = sender.send_text_message(recipient=recipient, text=text, mentions_everyone=True)

        assert result is True
        mock_post.assert_called_once()

        # Verify the payload includes mentionsEveryOne
        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        assert payload["number"] == recipient.replace("@g.us", "")
        assert payload["textMessage"]["text"] == text
        assert payload["mentionsEveryOne"] is True

    @patch("src.channels.whatsapp.evolution_api_sender.requests.post")
    def test_send_text_message_no_mentions(self, mock_post, sender, mock_response):
        """Test sending message without mentions."""
        mock_post.return_value = mock_response

        text = "Regular message without mentions"
        recipient = "5511777777777"

        result = sender.send_text_message(recipient=recipient, text=text, auto_parse_mentions=True)

        assert result is True
        mock_post.assert_called_once()

        # Verify the payload does not include mention parameters
        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        assert payload["number"] == recipient.replace("@g.us", "")
        assert payload["textMessage"]["text"] == text
        assert "mentioned" not in payload
        assert "mentionsEveryOne" not in payload

    @patch("src.channels.whatsapp.evolution_api_sender.requests.post")
    def test_send_text_message_explicit_overrides_auto_parse(self, mock_post, sender, mock_response):
        """Test that explicit mentions override auto-parsing."""
        mock_post.return_value = mock_response

        text = "Hello @5511999999999!"  # This would be auto-parsed
        recipient = "5511777777777"
        explicit_mentions = ["5511888888888@s.whatsapp.net"]  # But we provide explicit mentions

        result = sender.send_text_message(
            recipient=recipient,
            text=text,
            mentioned=explicit_mentions,
            auto_parse_mentions=True,  # This should be ignored
        )

        assert result is True
        mock_post.assert_called_once()

        # Verify only explicit mentions are used
        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        assert payload["mentioned"] == explicit_mentions
        assert "5511999999999@s.whatsapp.net" not in payload["mentioned"]

    @patch("src.channels.whatsapp.evolution_api_sender.requests.post")
    def test_send_split_messages_with_mentions(self, mock_post, sender, mock_response):
        """Test split messages only mention in first message."""
        mock_post.return_value = mock_response

        text = "First part\n\nSecond part"
        recipient = "5511777777777"
        mentioned_jids = ["5511999999999@s.whatsapp.net"]

        result = sender.send_text_message(
            recipient=recipient,
            text=text,
            mentioned=mentioned_jids,
            mentions_everyone=True,
        )

        assert result is True
        assert mock_post.call_count == 2  # Two separate messages

        # First message should have mentions
        first_call_payload = mock_post.call_args_list[0][1]["json"]
        assert first_call_payload["mentioned"] == mentioned_jids
        assert first_call_payload["mentionsEveryOne"] is True
        assert first_call_payload["textMessage"]["text"] == "First part"

        # Second message should not have mentions
        second_call_payload = mock_post.call_args_list[1][1]["json"]
        assert "mentioned" not in second_call_payload
        assert "mentionsEveryOne" not in second_call_payload
        assert second_call_payload["textMessage"]["text"] == "Second part"

    def test_send_text_message_missing_config(self, sender):
        """Test sending message without proper configuration."""
        sender.server_url = None

        result = sender.send_text_message(
            recipient="5511777777777",
            text="Test message",
            mentioned=["5511999999999@s.whatsapp.net"],
        )

        assert result is False

    @patch("src.channels.whatsapp.evolution_api_sender.requests.post")
    def test_send_text_message_http_error(self, mock_post, sender):
        """Test handling HTTP errors during mention message sending."""
        import requests

        mock_post.side_effect = requests.RequestException("Network error")

        result = sender.send_text_message(
            recipient="5511777777777",
            text="Test @5511999999999",
            auto_parse_mentions=True,
        )

        assert result is False

    @patch("src.channels.whatsapp.evolution_api_sender.requests.post")
    def test_send_text_message_400_error_with_mentions(self, mock_post, sender):
        """Test handling 400 errors with mentions (known Evolution API issue)."""
        mock_resp = Mock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"message": "database schema issue"}
        mock_post.return_value = mock_resp

        result = sender.send_text_message(
            recipient="5511777777777",
            text="Test message",
            mentioned=["5511999999999@s.whatsapp.net"],
        )

        # Should return True despite 400 error (known issue handling)
        assert result is True

    @patch("src.channels.whatsapp.evolution_api_sender.WhatsAppMentionParser")
    def test_mention_parsing_integration(self, mock_parser, sender):
        """Test integration with mention parser."""
        # Mock the parser to return expected results
        mock_parser.extract_mentions.return_value = (
            "Hello @5511999999999!",
            ["5511999999999@s.whatsapp.net"],
        )

        with patch("src.channels.whatsapp.evolution_api_sender.requests.post") as mock_post:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_post.return_value = mock_resp

            result = sender.send_text_message(
                recipient="5511777777777",
                text="Hello @5511999999999!",
                auto_parse_mentions=True,
            )

            assert result is True
            mock_parser.extract_mentions.assert_called_once_with("Hello @5511999999999!")

    @pytest.mark.parametrize(
        "text,mentions,mentions_everyone,expected_mention_count",
        [
            ("Regular message", None, False, 0),
            ("Hello @5511999999999", None, False, 1),  # Auto-parsed
            ("Meeting", ["5511999999999@s.whatsapp.net"], False, 1),  # Explicit
            ("Announcement", None, True, 0),  # Everyone, no individual mentions
            (
                "Complex @5511111111111 @5511222222222",
                None,
                False,
                2,
            ),  # Multiple auto-parsed
        ],
    )
    @patch("src.channels.whatsapp.evolution_api_sender.requests.post")
    def test_mention_combinations(
        self,
        mock_post,
        sender,
        mock_response,
        text,
        mentions,
        mentions_everyone,
        expected_mention_count,
    ):
        """Test various mention combinations."""
        mock_post.return_value = mock_response

        result = sender.send_text_message(
            recipient="5511777777777",
            text=text,
            mentioned=mentions,
            mentions_everyone=mentions_everyone,
            auto_parse_mentions=True,
        )

        assert result is True

        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        if expected_mention_count > 0 or mentions:
            assert "mentioned" in payload
            if mentions:
                assert len(payload["mentioned"]) == len(mentions)
        else:
            if "mentioned" in payload:
                assert len(payload["mentioned"]) == expected_mention_count

        if mentions_everyone:
            assert payload.get("mentionsEveryOne") is True
        else:
            assert payload.get("mentionsEveryOne", False) is False


if __name__ == "__main__":
    # Run a basic test manually
    pytest.main([__file__, "-v"])
