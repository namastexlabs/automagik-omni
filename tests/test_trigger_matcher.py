"""Unit tests for TriggerMatcher service."""

from unittest.mock import Mock

from src.services.trigger_matcher import TriggerMatcher, trigger_matcher
from src.db.models import InstanceConfig


class TestTriggerMatcher:
    """Unit tests for TriggerMatcher service."""

    def test_missing_instance_config_fails_open(self):
        """Returns True when instance_config is missing (backward compatibility)."""
        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hello",
            instance_config=None,
            channel_type="whatsapp",
        )
        assert result is True

    def test_keyword_match_case_insensitive(self):
        """Returns True when message contains configured keyword (case-insensitive)."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = '["jack", "bot"]'
        instance.owner_jid = None

        matcher = TriggerMatcher()

        # Test exact match
        result = matcher.should_respond(
            message_text="hey jack, can you help?",
            instance_config=instance,
            channel_type="whatsapp",
        )
        assert result is True

        # Test case insensitivity
        result = matcher.should_respond(
            message_text="HEY JACK!",
            instance_config=instance,
            channel_type="whatsapp",
        )
        assert result is True

    def test_keyword_no_match(self):
        """Returns False when no keywords match and no mention."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = '["jack", "bot"]'
        instance.owner_jid = "1234567890@s.whatsapp.net"

        # Provide group payload with no mentions
        channel_payload = {
            "data": {
                "key": {"remoteJid": "group123@g.us"},
                "message": {"extendedTextMessage": {"contextInfo": {"mentionedJid": []}}},
            }
        }

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hello there, how are you?",
            instance_config=instance,
            channel_payload=channel_payload,
            channel_type="whatsapp",
        )
        assert result is False

    def test_keyword_malformed_json_fails_open(self):
        """Ignores keywords when JSON is invalid (mention-only fallback)."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = "not valid json"
        instance.owner_jid = "1234567890@s.whatsapp.net"

        # Provide group payload with no mentions
        channel_payload = {
            "data": {
                "key": {"remoteJid": "group123@g.us"},
                "message": {"extendedTextMessage": {"contextInfo": {"mentionedJid": []}}},
            }
        }

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hello jack",
            instance_config=instance,
            channel_payload=channel_payload,
            channel_type="whatsapp",
        )
        # Should return False since keywords are invalid and no mention
        assert result is False

    def test_keyword_not_a_list(self):
        """Returns False when trigger_keywords is valid JSON but not a list."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = '{"keyword": "jack"}'
        instance.owner_jid = "1234567890@s.whatsapp.net"

        # Provide group payload with no mentions
        channel_payload = {
            "data": {
                "key": {"remoteJid": "group123@g.us"},
                "message": {"extendedTextMessage": {"contextInfo": {"mentionedJid": []}}},
            }
        }

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hello jack",
            instance_config=instance,
            channel_payload=channel_payload,
            channel_type="whatsapp",
        )
        assert result is False

    def test_no_keywords_configured(self):
        """Returns False when no keywords are configured and no mention."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = None
        instance.owner_jid = "1234567890@s.whatsapp.net"

        # Provide group payload with no mentions
        channel_payload = {
            "data": {
                "key": {"remoteJid": "group123@g.us"},
                "message": {"extendedTextMessage": {"contextInfo": {"mentionedJid": []}}},
            }
        }

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hello there",
            instance_config=instance,
            channel_payload=channel_payload,
            channel_type="whatsapp",
        )
        assert result is False

    def test_whatsapp_group_mention_detected(self):
        """Detects mention via WhatsApp group payload."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = None
        instance.owner_jid = "1234567890@s.whatsapp.net"

        channel_payload = {
            "data": {
                "key": {"remoteJid": "group123@g.us"},
                "message": {
                    "extendedTextMessage": {
                        "contextInfo": {"mentionedJid": ["1234567890@s.whatsapp.net", "9876543210@s.whatsapp.net"]}
                    }
                },
            }
        }

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hey @bot check this",
            instance_config=instance,
            channel_payload=channel_payload,
            channel_type="whatsapp",
        )
        assert result is True

    def test_whatsapp_group_no_mention(self):
        """Returns False when WhatsApp group message lacks mention and keyword."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = None
        instance.owner_jid = "1234567890@s.whatsapp.net"

        channel_payload = {
            "data": {
                "key": {"remoteJid": "group123@g.us"},
                "message": {"extendedTextMessage": {"contextInfo": {"mentionedJid": ["9876543210@s.whatsapp.net"]}}},
            }
        }

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hey there",
            instance_config=instance,
            channel_payload=channel_payload,
            channel_type="whatsapp",
        )
        assert result is False

    def test_whatsapp_dm_bypasses_triggers(self):
        """WhatsApp DM bypasses triggers and returns True."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = '["jack"]'
        instance.owner_jid = "1234567890@s.whatsapp.net"

        # DM payload (remoteJid does NOT end with @g.us)
        channel_payload = {"data": {"key": {"remoteJid": "9876543210@s.whatsapp.net"}, "message": {}}}

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hello there",  # No keyword match
            instance_config=instance,
            channel_payload=channel_payload,
            channel_type="whatsapp",
        )
        assert result is True  # DMs bypass triggers

    def test_whatsapp_missing_owner_jid(self):
        """Returns False when owner_jid is not configured (keyword-only fallback)."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = None
        instance.owner_jid = None

        channel_payload = {
            "data": {
                "key": {"remoteJid": "group123@g.us"},
                "message": {"extendedTextMessage": {"contextInfo": {"mentionedJid": ["1234567890@s.whatsapp.net"]}}},
            }
        }

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hey",
            instance_config=instance,
            channel_payload=channel_payload,
            channel_type="whatsapp",
        )
        # No keywords and no owner_jid -> can't check mentions
        assert result is False

    def test_discord_guild_mention_detected(self):
        """Detects mention via Discord metadata (guild)."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = None

        channel_metadata = {
            "mentions": [{"id": "bot123", "username": "MyBot"}, {"id": "user456", "username": "Alice"}],
            "is_dm": False,
            "bot_id": "bot123",
            "guild_id": "guild789",
        }

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hey @bot check this",
            instance_config=instance,
            channel_metadata=channel_metadata,
            channel_type="discord",
        )
        assert result is True

    def test_discord_guild_no_mention(self):
        """Returns False when Discord guild message lacks mention and keyword."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = None

        channel_metadata = {
            "mentions": [{"id": "user456", "username": "Alice"}],
            "is_dm": False,
            "bot_id": "bot123",
            "guild_id": "guild789",
        }

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hey there",
            instance_config=instance,
            channel_metadata=channel_metadata,
            channel_type="discord",
        )
        assert result is False

    def test_discord_dm_bypasses_triggers(self):
        """Discord DM bypasses triggers and returns True."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = '["jack"]'

        channel_metadata = {"mentions": [], "is_dm": True, "bot_id": "bot123", "guild_id": None}

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hello there",  # No keyword match
            instance_config=instance,
            channel_metadata=channel_metadata,
            channel_type="discord",
        )
        assert result is True  # DMs bypass triggers

    def test_discord_missing_bot_id(self):
        """Returns False when bot_id is not in metadata (keyword-only fallback)."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = None

        channel_metadata = {
            "mentions": [{"id": "bot123", "username": "MyBot"}],
            "is_dm": False,
            "bot_id": None,  # Missing bot ID
            "guild_id": "guild789",
        }

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hey @bot",
            instance_config=instance,
            channel_metadata=channel_metadata,
            channel_type="discord",
        )
        # No keywords and no bot_id -> can't check mentions
        assert result is False

    def test_keyword_or_mention_logic(self):
        """Returns True when EITHER keyword OR mention matches."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = '["jack"]'

        channel_metadata = {
            "mentions": [{"id": "bot123", "username": "MyBot"}],
            "is_dm": False,
            "bot_id": "bot123",
            "guild_id": "guild789",
        }

        matcher = TriggerMatcher()

        # Test keyword match without mention
        result = matcher.should_respond(
            message_text="hey jack are you there?",
            instance_config=instance,
            channel_metadata={"mentions": [], "is_dm": False, "bot_id": "bot123", "guild_id": "guild789"},
            channel_type="discord",
        )
        assert result is True

        # Test mention without keyword match
        result = matcher.should_respond(
            message_text="@bot hello",
            instance_config=instance,
            channel_metadata=channel_metadata,
            channel_type="discord",
        )
        assert result is True

    def test_unknown_channel_type_fails_open(self):
        """Returns True for unknown channel type (fail-open)."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = None

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hello",
            instance_config=instance,
            channel_type="unknown_channel",
        )
        assert result is True

    def test_whatsapp_payload_exception_fails_open(self):
        """Returns True when WhatsApp payload parsing raises exception."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = None
        instance.owner_jid = "1234567890@s.whatsapp.net"

        # Malformed payload that will cause exception
        channel_payload = "not a dict"

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hello",
            instance_config=instance,
            channel_payload=channel_payload,
            channel_type="whatsapp",
        )
        assert result is True  # Fail open on exception

    def test_discord_metadata_exception_fails_open(self):
        """Returns True when Discord metadata parsing raises exception."""
        instance = Mock(spec=InstanceConfig)
        instance.trigger_keywords = None

        # Malformed metadata that will cause exception
        channel_metadata = "not a dict"

        matcher = TriggerMatcher()
        result = matcher.should_respond(
            message_text="hello",
            instance_config=instance,
            channel_metadata=channel_metadata,
            channel_type="discord",
        )
        assert result is True  # Fail open on exception

    def test_singleton_instance(self):
        """Verify trigger_matcher singleton is properly initialized."""
        assert trigger_matcher is not None
        assert isinstance(trigger_matcher, TriggerMatcher)
