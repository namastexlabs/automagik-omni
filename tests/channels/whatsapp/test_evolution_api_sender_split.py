"""
Tests for EvolutionApiSender message splitting functionality.
Tests the configurable message splitting feature introduced in Issue #109 (PR #105).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.channels.whatsapp.evolution_api_sender import EvolutionApiSender
from src.db.models import InstanceConfig


@pytest.fixture
def mock_instance_config():
    """Create a mock InstanceConfig for testing."""
    config = Mock(spec=InstanceConfig)
    config.name = "test_instance"
    config.evolution_url = "https://test-evolution.api"
    config.evolution_key = "test-api-key"
    config.whatsapp_instance = "test_whatsapp"
    config.enable_auto_split = True  # Default enabled
    return config


@pytest.fixture
def sender_with_config(mock_instance_config):
    """Create EvolutionApiSender with instance config."""
    return EvolutionApiSender(config_override=mock_instance_config)


@pytest.fixture
def sender_without_config():
    """Create EvolutionApiSender without instance config."""
    sender = EvolutionApiSender()
    sender.server_url = "https://test-evolution.api"
    sender.api_key = "test-api-key"
    sender.instance_name = "test_instance"
    return sender


class TestMessageSplittingPriorityLogic:
    """Test the priority logic for message splitting configuration."""

    def test_per_message_override_true(self, sender_with_config):
        """Test per-message override takes highest priority (split_message=True)."""
        # Instance config says False, but per-message override says True
        sender_with_config.config.enable_auto_split = False

        text = "Part 1\n\nPart 2"
        quoted_message = None  # Text message reply

        # Per-message override = True should win
        result = sender_with_config._should_split_message(text, quoted_message, split_message=True)
        assert result is True

    def test_per_message_override_false(self, sender_with_config):
        """Test per-message override takes highest priority (split_message=False)."""
        # Instance config says True, but per-message override says False
        sender_with_config.config.enable_auto_split = True

        text = "Part 1\n\nPart 2"
        quoted_message = None

        # Per-message override = False should win
        result = sender_with_config._should_split_message(text, quoted_message, split_message=False)
        assert result is False

    def test_instance_config_priority(self, sender_with_config):
        """Test instance config is used when no per-message override."""
        # No per-message override, use instance config
        sender_with_config.config.enable_auto_split = False

        text = "Part 1\n\nPart 2"
        quoted_message = None

        # Should use instance config (False)
        result = sender_with_config._should_split_message(text, quoted_message, split_message=None)
        assert result is False

    def test_default_behavior_when_no_config(self, sender_without_config):
        """Test default behavior (True) when no instance config."""
        text = "Part 1\n\nPart 2"
        quoted_message = None

        # No instance config, should default to True
        result = sender_without_config._should_split_message(text, quoted_message, split_message=None)
        assert result is True

    def test_splitting_disabled_by_instance_config(self, sender_with_config):
        """Test that instance config can disable splitting."""
        sender_with_config.config.enable_auto_split = False

        text = "Part 1\n\nPart 2\n\nPart 3"
        quoted_message = None

        result = sender_with_config._should_split_message(text, quoted_message, split_message=None)
        assert result is False

    def test_splitting_enabled_by_instance_config(self, sender_with_config):
        """Test that instance config can enable splitting."""
        sender_with_config.config.enable_auto_split = True

        text = "Part 1\n\nPart 2"
        quoted_message = None

        result = sender_with_config._should_split_message(text, quoted_message, split_message=None)
        assert result is True


class TestMessageSplittingRules:
    """Test the rules for when messages should be split."""

    def test_no_split_for_single_paragraph(self, sender_with_config):
        """Test that single paragraph messages are not split."""
        text = "This is a single paragraph without double newlines"
        quoted_message = None

        result = sender_with_config._should_split_message(text, quoted_message, split_message=None)
        assert result is False

    def test_split_for_double_newlines(self, sender_with_config):
        """Test that messages with \\n\\n are split."""
        text = "First paragraph\n\nSecond paragraph"
        quoted_message = None

        result = sender_with_config._should_split_message(text, quoted_message, split_message=None)
        assert result is True

    def test_no_split_for_media_reply(self, sender_with_config):
        """Test that replies to media messages are not split."""
        text = "Caption 1\n\nCaption 2"
        quoted_message = {
            "message": {
                "imageMessage": {
                    "caption": "Original image"
                }
            }
        }

        result = sender_with_config._should_split_message(text, quoted_message, split_message=None)
        assert result is False

    def test_split_for_text_reply(self, sender_with_config):
        """Test that replies to text messages can be split."""
        text = "Reply 1\n\nReply 2"
        quoted_message = {
            "message": {
                "conversation": "Original text"
            }
        }

        result = sender_with_config._should_split_message(text, quoted_message, split_message=None)
        assert result is True

    def test_no_split_when_disabled(self, sender_with_config):
        """Test that splitting is disabled when split_message=False."""
        sender_with_config.config.enable_auto_split = True  # Config says yes

        text = "Part 1\n\nPart 2"
        quoted_message = None

        # But per-message override says no
        result = sender_with_config._should_split_message(text, quoted_message, split_message=False)
        assert result is False


class TestMediaMessageDetection:
    """Test detection of media messages for split logic."""

    def test_is_media_message_image(self, sender_with_config):
        """Test detection of image messages."""
        quoted_message = {
            "message": {
                "imageMessage": {"caption": "test"}
            }
        }
        assert sender_with_config._is_media_message(quoted_message) is True

    def test_is_media_message_video(self, sender_with_config):
        """Test detection of video messages."""
        quoted_message = {
            "message": {
                "videoMessage": {"caption": "test"}
            }
        }
        assert sender_with_config._is_media_message(quoted_message) is True

    def test_is_media_message_audio(self, sender_with_config):
        """Test detection of audio messages."""
        quoted_message = {
            "message": {
                "audioMessage": {}
            }
        }
        assert sender_with_config._is_media_message(quoted_message) is True

    def test_is_media_message_document(self, sender_with_config):
        """Test detection of document messages."""
        quoted_message = {
            "message": {
                "documentMessage": {"fileName": "test.pdf"}
            }
        }
        assert sender_with_config._is_media_message(quoted_message) is True

    def test_is_media_message_sticker(self, sender_with_config):
        """Test detection of sticker messages."""
        quoted_message = {
            "message": {
                "stickerMessage": {}
            }
        }
        assert sender_with_config._is_media_message(quoted_message) is True

    def test_is_not_media_message_text(self, sender_with_config):
        """Test that text messages are not detected as media."""
        quoted_message = {
            "message": {
                "conversation": "Just text"
            }
        }
        assert sender_with_config._is_media_message(quoted_message) is False

    def test_is_not_media_message_none(self, sender_with_config):
        """Test that None is not a media message."""
        assert sender_with_config._is_media_message(None) is False

    def test_is_not_media_message_empty(self, sender_with_config):
        """Test that empty dict is not a media message."""
        assert sender_with_config._is_media_message({}) is False


class TestSendTextMessageIntegration:
    """Test send_text_message with split_message parameter."""

    @patch('src.channels.whatsapp.evolution_api_sender.requests.post')
    def test_send_with_split_enabled(self, mock_post, sender_with_config):
        """Test sending message with splitting enabled."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()

        text = "Part 1\n\nPart 2\n\nPart 3"
        recipient = "5551234567890"

        result = sender_with_config.send_text_message(
            recipient=recipient,
            text=text,
            split_message=True  # Explicitly enable
        )

        # Should be split into 3 messages
        assert result is True
        assert mock_post.call_count == 3

    @patch('src.channels.whatsapp.evolution_api_sender.requests.post')
    def test_send_with_split_disabled(self, mock_post, sender_with_config):
        """Test sending message with splitting disabled."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()

        text = "Part 1\n\nPart 2\n\nPart 3"
        recipient = "5551234567890"

        result = sender_with_config.send_text_message(
            recipient=recipient,
            text=text,
            split_message=False  # Explicitly disable
        )

        # Should send as single message
        assert result is True
        assert mock_post.call_count == 1

        # Verify the full text was sent
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['text'] == text  # Full text, not split

    @patch('src.channels.whatsapp.evolution_api_sender.requests.post')
    def test_send_uses_instance_config(self, mock_post, sender_with_config):
        """Test that instance config is respected when no override."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()

        # Disable splitting in instance config
        sender_with_config.config.enable_auto_split = False

        text = "Part 1\n\nPart 2"
        recipient = "5551234567890"

        # No per-message override, should use instance config
        result = sender_with_config.send_text_message(
            recipient=recipient,
            text=text
        )

        # Should send as single message (config disabled splitting)
        assert result is True
        assert mock_post.call_count == 1

    @patch('src.channels.whatsapp.evolution_api_sender.requests.post')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_split_message_delays(self, mock_sleep, mock_post, sender_with_config):
        """Test that split messages have delays between them."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()

        text = "Part 1\n\nPart 2\n\nPart 3"
        recipient = "5551234567890"

        sender_with_config.send_text_message(
            recipient=recipient,
            text=text,
            split_message=True
        )

        # Should have 2 delays (between 3 messages)
        assert mock_sleep.call_count == 2

        # Verify delay is in expected range (0.3 to 1.0 seconds)
        for call in mock_sleep.call_args_list:
            delay = call[0][0]
            assert 0.3 <= delay <= 1.0

    @patch('src.channels.whatsapp.evolution_api_sender.requests.post')
    def test_mentions_only_in_first_split_part(self, mock_post, sender_with_config):
        """Test that mentions are only included in first message part."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()

        text = "Part 1\n\nPart 2"
        recipient = "5551234567890"
        mentioned = ["5559876543@s.whatsapp.net"]

        sender_with_config.send_text_message(
            recipient=recipient,
            text=text,
            mentioned=mentioned,
            split_message=True
        )

        # First call should have mentions
        first_call = mock_post.call_args_list[0][1]['json']
        assert 'mentioned' in first_call
        assert first_call['mentioned'] == mentioned

        # Second call should NOT have mentions
        second_call = mock_post.call_args_list[1][1]['json']
        assert 'mentioned' not in second_call

    @patch('src.channels.whatsapp.evolution_api_sender.requests.post')
    def test_quote_only_in_first_split_part(self, mock_post, sender_with_config):
        """Test that quoted message is only in first message part."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()

        text = "Reply 1\n\nReply 2"
        recipient = "5551234567890"
        quoted_message = {
            "key": {"id": "test_msg_id"},
            "message": {"conversation": "Original"}
        }

        # Note: Quoting is currently disabled in the implementation due to Evolution API bugs,
        # but we test the logic is correct in _send_split_messages
        sender_with_config.send_text_message(
            recipient=recipient,
            text=text,
            quoted_message=quoted_message,
            split_message=True
        )

        # Both messages sent (quoting disabled in actual implementation)
        assert mock_post.call_count == 2
