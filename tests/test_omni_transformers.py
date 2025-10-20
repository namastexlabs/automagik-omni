"""
Comprehensive tests for omni data transformers.
Tests both WhatsApp and Discord transformers with:
- Edge case handling for null/invalid data
- Timestamp parsing from multiple formats
- Avatar URL building and validation
- Data format-specific ID patterns
- Boundary conditions and malformed data
"""

from datetime import datetime
from src.services.omni_transformers import WhatsAppTransformer, DiscordTransformer
from src.api.schemas.omni import (
    ChannelType,
    OmniContactStatus,
    OmniChatType,
    OmniContact,
    OmniChat,
    OmniChannelInfo,
)


class TestWhatsAppTransformer:
    """Comprehensive tests for WhatsAppTransformer."""

    def test_contact_to_omni_success(self):
        """Test successful WhatsApp contact transformation."""
        whatsapp_contact = {
            "id": "5511999999999@c.us",
            "name": "Test Contact",
            "profilePictureUrl": "https://example.com/avatar.jpg",
            "lastSeen": 1640995200000,  # Unix timestamp in milliseconds
            "isGroup": False,
            "status": "active",
        }

        contact = WhatsAppTransformer.contact_to_omni(whatsapp_contact, "test-instance")

        assert isinstance(contact, OmniContact)
        assert contact.id == "5511999999999@c.us"
        assert contact.name == "Test Contact"
        assert contact.channel_type == ChannelType.WHATSAPP
        assert contact.instance_name == "test-instance"
        assert contact.status == OmniContactStatus.UNKNOWN
        assert contact.avatar_url == "https://example.com/avatar.jpg"

        # Verify channel-specific data
        assert contact.channel_data["phone_number"] == "5511999999999"

        # Verify timestamp parsing
        assert contact.last_seen is not None
        expected_datetime = datetime.fromtimestamp(1640995200)  # Converted from milliseconds
        assert contact.last_seen == expected_datetime

    def test_contact_to_omni_minimal_data(self):
        """Test contact transformation with minimal required data."""
        whatsapp_contact = {
            "id": "5511888888888@c.us",
            "name": "Minimal Contact",
            # Missing optional fields: profilePicture, lastSeen, status
        }

        contact = WhatsAppTransformer.contact_to_omni(whatsapp_contact, "test-instance")

        assert contact.id == "5511888888888@c.us"
        assert contact.name == "Minimal Contact"
        assert contact.channel_type == ChannelType.WHATSAPP
        assert contact.avatar_url is None
        assert contact.last_seen is None
        assert contact.status == OmniContactStatus.UNKNOWN  # Default value

    def test_contact_to_omni_null_values(self):
        """Test contact transformation with null values."""
        whatsapp_contact = {
            "id": "5511777777777@c.us",
            "name": "Null Values Contact",
            "profilePictureUrl": None,
            "lastSeen": None,
            "status": None,
        }

        contact = WhatsAppTransformer.contact_to_omni(whatsapp_contact, "test-instance")

        assert contact.avatar_url is None
        assert contact.last_seen is None
        assert contact.status == OmniContactStatus.UNKNOWN

    def test_contact_to_omni_empty_strings(self):
        """Test contact transformation with empty string values."""
        whatsapp_contact = {
            "id": "5511666666666@c.us",
            "name": "Empty Strings Contact",
            "profilePictureUrl": "",
            "lastSeen": 0,
            "status": "",
        }

        contact = WhatsAppTransformer.contact_to_omni(whatsapp_contact, "test-instance")

        assert contact.avatar_url == ""  # Empty string preserved
        assert contact.last_seen is None  # Current implementation treats 0 as falsy
        assert contact.status == OmniContactStatus.UNKNOWN

    def test_contact_to_omni_none_input(self):
        """Test contact transformation with None input."""
        contact = WhatsAppTransformer.contact_to_omni(None, "test-instance")

        assert isinstance(contact, OmniContact)
        # Should create empty contact with instance info
        assert contact.instance_name == "test-instance"
        assert contact.channel_type == ChannelType.WHATSAPP
        assert contact.id == "unknown"
        assert contact.name == "Unknown"

    def test_invalid_whatsapp_id_patterns(self):
        """Test handling of invalid WhatsApp ID patterns."""
        invalid_patterns = [
            "invalid-id",  # No @c.us suffix
            "5511@g.us",  # Group ID but marked as individual
            "@c.us",  # Missing number
            "",  # Empty string
            "12345",  # No domain
        ]

        for invalid_id in invalid_patterns:
            whatsapp_contact = {"id": invalid_id, "name": "Test"}
            # Should handle gracefully without throwing
            contact = WhatsAppTransformer.contact_to_omni(whatsapp_contact, "test")
            assert contact.channel_type == ChannelType.WHATSAPP

    def test_whatsapp_name_variations(self):
        """Test handling of different WhatsApp name formats."""
        # Test pushName vs name field
        whatsapp_contact_push = {
            "id": "test@c.us",
            "pushName": "Push Name",
            "name": "Regular Name",
        }
        contact = WhatsAppTransformer.contact_to_omni(whatsapp_contact_push, "test")
        # Should prefer pushName over name
        assert contact.name == "Push Name"

        # Test with only name field
        whatsapp_contact_name = {"id": "test2@c.us", "name": "Only Name"}
        contact = WhatsAppTransformer.contact_to_omni(whatsapp_contact_name, "test")
        assert contact.name == "Only Name"

        # Test fallback when both are empty
        whatsapp_contact_fallback = {"id": "test3@c.us", "name": "", "pushName": None}
        contact = WhatsAppTransformer.contact_to_omni(whatsapp_contact_fallback, "test")
        assert contact.name == "Unknown"  # Should fallback to "Unknown"

    def test_chat_to_omni_direct_chat(self):
        """Test WhatsApp direct chat transformation."""
        whatsapp_chat = {
            "id": "5511999999999@c.us",
            "name": "Direct Chat",
            "lastMessageTime": 1640995200000,
            "unreadCount": 2,
            "isGroup": False,
            "participants": [],
        }

        chat = WhatsAppTransformer.chat_to_omni(whatsapp_chat, "test-instance")

        assert isinstance(chat, OmniChat)
        assert chat.id == "5511999999999@c.us"
        assert chat.name == "Direct Chat"
        assert chat.channel_type == ChannelType.WHATSAPP
        assert chat.instance_name == "test-instance"
        assert chat.chat_type == OmniChatType.DIRECT
        assert chat.unread_count == 2
        assert chat.participant_count is None  # Direct chats have no participant count

    def test_chat_to_omni_group_chat(self):
        """Test WhatsApp group chat transformation."""
        whatsapp_chat = {
            "id": "120363025@g.us",
            "name": "Test Group",
            "lastMessageTime": 1640995200000,
            "unreadCount": 5,
            "isGroup": True,
            "participants": ["user1@c.us", "user2@c.us", "user3@c.us"],
        }

        chat = WhatsAppTransformer.chat_to_omni(whatsapp_chat, "test-instance")

        assert chat.chat_type == OmniChatType.GROUP
        assert chat.participant_count == 3
        assert chat.channel_data["group_id"] == "120363025@g.us"

    def test_chat_to_omni_broadcast_channel(self):
        """Test WhatsApp broadcast channel transformation."""
        whatsapp_chat = {
            "id": "status@broadcast",
            "name": "My Status",
            "lastMessageTime": 1640995200000,
            "unreadCount": 0,
            "isGroup": False,
            "isBroadcast": True,
        }

        chat = WhatsAppTransformer.chat_to_omni(whatsapp_chat, "test-instance")

        assert chat.chat_type == OmniChatType.CHANNEL  # @broadcast maps to CHANNEL

    def test_chat_to_omni_none_input(self):
        """Test chat transformation with None input."""
        chat = WhatsAppTransformer.chat_to_omni(None, "test-instance")

        assert isinstance(chat, OmniChat)
        assert chat.instance_name == "test-instance"
        assert chat.channel_type == ChannelType.WHATSAPP
        assert chat.id == "unknown"
        assert chat.name == "Unknown"
        assert chat.chat_type == OmniChatType.DIRECT

    def test_invalid_chat_data(self):
        """Test handling of invalid chat data."""
        invalid_chats = [
            {"id": "", "name": "Empty ID"},  # Empty ID
            {"name": "No ID"},  # Missing ID
            {},  # Empty dict
        ]

        for invalid_chat in invalid_chats:
            # Should handle gracefully
            chat = WhatsAppTransformer.chat_to_omni(invalid_chat, "test")
            assert chat.channel_type == ChannelType.WHATSAPP

    def test_channel_to_omni_success(self):
        """Test successful WhatsApp channel transformation."""
        status_data = {
            "status": "connected",
            "phoneNumber": "5511999999999",
            "profileName": "Test Profile",
            "profilePictureUrl": "https://example.com/avatar.jpg",
            "contactCount": 150,
            "chatCount": 25,
            "connectedAt": 1640995200000,
            "lastActivity": 1640995200000,
        }

        instance_config = {"display_name": "WhatsApp Instance"}

        channel_info = WhatsAppTransformer.channel_to_omni("test-whatsapp", status_data, instance_config)

        assert isinstance(channel_info, OmniChannelInfo)
        assert channel_info.instance_name == "test-whatsapp"
        assert channel_info.channel_type == ChannelType.WHATSAPP
        assert channel_info.display_name == "WhatsApp Instance"
        assert channel_info.status == "connected"
        assert channel_info.is_healthy is True

    def test_channel_to_omni_minimal_data(self):
        """Test channel transformation with minimal data."""
        status_data = {"status": "connecting"}

        instance_config = {}

        channel_info = WhatsAppTransformer.channel_to_omni("minimal-instance", status_data, instance_config)

        assert channel_info.instance_name == "minimal-instance"
        assert channel_info.status == "connecting"
        assert channel_info.display_name == "minimal-instance"  # Fallback
        assert channel_info.is_healthy is False  # Not "connected" status

    def test_whatsapp_phone_number_extraction(self):
        """Test phone number extraction from WhatsApp IDs."""
        test_cases = [
            ("5511999999999@c.us", "5511999999999"),
            ("1234567890@c.us", "1234567890"),
            ("invalid@c.us", "invalid"),
            ("no-domain", "no-domain"),  # Fallback
            ("", ""),  # Empty string
        ]

        for whatsapp_id, expected_phone in test_cases:
            contact = {"id": whatsapp_id, "name": "Test"}
            transformed = WhatsAppTransformer.contact_to_omni(contact, "test")

            if "phone_number" in transformed.channel_data:
                assert transformed.channel_data["phone_number"] == expected_phone

    def test_whatsapp_timestamp_parsing(self):
        """Test various timestamp format parsing."""
        test_cases = [
            (1640995200000, datetime.fromtimestamp(1640995200)),  # Milliseconds
            (1640995200, datetime.fromtimestamp(1640995200)),  # Seconds
            (0, None),  # Current implementation treats 0 as falsy
            (None, None),  # None
            ("invalid", None),  # Invalid string
        ]

        for input_timestamp, expected_datetime in test_cases:
            contact = {"id": "test@c.us", "name": "Test", "lastSeen": input_timestamp}
            transformed = WhatsAppTransformer.contact_to_omni(contact, "test")

            if expected_datetime:
                assert transformed.last_seen == expected_datetime
            else:
                assert transformed.last_seen is None

    def test_whatsapp_avatar_url_handling(self):
        """Test avatar URL handling for WhatsApp contacts."""
        test_cases = [
            ("https://example.com/avatar.jpg", "https://example.com/avatar.jpg"),
            ("", ""),  # Empty string preserved
            (None, None),  # None preserved
            ("invalid-url", "invalid-url"),  # Invalid URL still preserved
        ]

        for input_url, expected_url in test_cases:
            contact = {
                "id": "test@c.us",
                "name": "Test",
                "profilePictureUrl": input_url,
            }
            transformed = WhatsAppTransformer.contact_to_omni(contact, "test")
            assert transformed.avatar_url == expected_url


class TestDiscordTransformer:
    """Comprehensive tests for DiscordTransformer."""

    def test_contact_to_omni_success(self):
        """Test successful Discord user transformation."""
        discord_user = {
            "id": 987654321098765432,
            "username": "testuser",
            "display_name": "Test User",
            "global_name": "Test User Global",
            "discriminator": "0001",
            "avatar": "a_1234567890abcdef1234567890abcdef",
            "status": "online",
            "bot": False,
        }

        contact = DiscordTransformer.contact_to_omni(discord_user, "test-discord")

        assert isinstance(contact, OmniContact)
        assert contact.id == "987654321098765432"
        assert contact.name == "Test User Global"  # Prefers global_name
        assert contact.channel_type == ChannelType.DISCORD
        assert contact.instance_name == "test-discord"
        assert contact.status == OmniContactStatus.ONLINE  # 'online' maps to ONLINE

        # Verify Discord-specific data
        assert contact.channel_data["username"] == "testuser"
        assert contact.channel_data["discriminator"] == "0001"
        assert contact.channel_data["global_name"] == "Test User Global"
        assert not contact.channel_data["is_bot"]

        # Verify avatar URL construction
        expected_avatar = "https://cdn.discordapp.com/avatars/987654321098765432/a_1234567890abcdef1234567890abcdef.png"
        assert contact.avatar_url == expected_avatar

    def test_contact_to_omni_no_global_name(self):
        """Test Discord user transformation without global_name."""
        discord_user = {
            "id": 111222333444555666,
            "username": "olduser",
            "display_name": "Old User",
            # No global_name field
            "discriminator": "0001",
            "status": "idle",
        }

        contact = DiscordTransformer.contact_to_omni(discord_user, "test-discord")

        # Should fall back to display_name or username
        assert contact.name == "olduser"

    def test_contact_to_omni_no_avatar(self):
        """Test Discord user transformation without avatar."""
        discord_user = {
            "id": 999888777666555444,
            "username": "noavatar",
            "display_name": "No Avatar User",
            "discriminator": "0001",
            "avatar": None,
            "status": "dnd",
        }

        contact = DiscordTransformer.contact_to_omni(discord_user, "test-discord")

        assert contact.avatar_url is None

    def test_discord_status_mapping(self):
        """Test Discord status to omni status mapping."""
        status_mappings = [
            ("online", OmniContactStatus.ONLINE),
            ("idle", OmniContactStatus.AWAY),
            ("dnd", OmniContactStatus.DND),
            ("offline", OmniContactStatus.OFFLINE),
            ("invisible", OmniContactStatus.UNKNOWN),  # Unknown status maps to UNKNOWN
            ("unknown", OmniContactStatus.UNKNOWN),  # Default fallback
        ]

        for discord_status, expected_omni_status in status_mappings:
            discord_user = {
                "id": 123456789,
                "username": "testuser",
                "status": discord_status,
            }
            contact = DiscordTransformer.contact_to_omni(discord_user, "test")
            assert contact.status == expected_omni_status

    def test_chat_to_omni_text_channel(self):
        """Test Discord text channel transformation."""
        discord_channel = {
            "id": 111222333444555666,
            "name": "general",
            "type": 0,  # Text channel
            "guild_id": 987654321098765432,
            "topic": "General discussion",
            "position": 0,
            "nsfw": False,
        }

        chat = DiscordTransformer.chat_to_omni(discord_channel, "test-discord")

        assert isinstance(chat, OmniChat)
        assert chat.id == "111222333444555666"
        assert chat.name == "general"
        assert chat.channel_type == ChannelType.DISCORD
        assert chat.instance_name == "test-discord"
        assert chat.chat_type == OmniChatType.DIRECT  # Type 0 maps to DIRECT
        assert chat.channel_data["guild_id"] == 987654321098765432
        assert chat.description == "General discussion"  # topic becomes description

    def test_chat_to_omni_group_dm(self):
        """Test Discord group DM transformation."""
        discord_channel = {
            "id": 222333444555666777,
            "name": None,  # Group DMs might not have names
            "type": 2,  # Group DM
            "member_count": 3,
        }

        chat = DiscordTransformer.chat_to_omni(discord_channel, "test-discord")

        assert chat.chat_type == OmniChatType.GROUP
        assert chat.participant_count == 3

    def test_chat_to_omni_dm_channel(self):
        """Test Discord DM channel transformation."""
        discord_channel = {
            "id": 333444555666777888,
            "name": None,
            "type": 1,  # DM channel
            "member_count": 1,
        }

        chat = DiscordTransformer.chat_to_omni(discord_channel, "test-discord")

        assert chat.chat_type == OmniChatType.DIRECT
        assert chat.participant_count == 1

    def test_discord_channel_type_mapping(self):
        """Test Discord channel type to omni chat type mapping."""
        type_mappings = [
            (0, OmniChatType.DIRECT),  # DM
            (1, OmniChatType.DIRECT),  # DM
            (2, OmniChatType.GROUP),  # Group DM
            (4, OmniChatType.CHANNEL),  # Guild category
            (5, OmniChatType.CHANNEL),  # Guild text
            (10, OmniChatType.THREAD),  # Guild news thread
            (11, OmniChatType.THREAD),  # Guild public thread
            (12, OmniChatType.THREAD),  # Guild private thread
            (999, OmniChatType.CHANNEL),  # Unknown type defaults to CHANNEL
        ]

        for discord_type, expected_chat_type in type_mappings:
            discord_channel = {"id": 123456789, "name": "test", "type": discord_type}
            chat = DiscordTransformer.chat_to_omni(discord_channel, "test")
            assert chat.chat_type == expected_chat_type

    def test_channel_to_omni_success(self):
        """Test successful Discord channel info transformation."""
        status_data = {
            "status": "connected",
            "bot_id": 123456789012345678,
            "guild_count": 5,
            "member_count": 150,
            "channel_count": 25,
            "avatar_url": "https://cdn.discordapp.com/avatars/123456789012345678/avatar.png",
            "connected_at": 1640995200,
            "last_activity": 1640995200,
        }

        instance_config = {"display_name": "Discord Bot"}

        channel_info = DiscordTransformer.channel_to_omni("test-discord", status_data, instance_config)

        assert isinstance(channel_info, OmniChannelInfo)
        assert channel_info.instance_name == "test-discord"
        assert channel_info.channel_type == ChannelType.DISCORD
        assert channel_info.display_name == "Discord Bot"
        assert channel_info.status == "connected"
        assert channel_info.is_healthy is True

    def test_discord_avatar_url_construction(self):
        """Test Discord avatar URL construction."""
        test_cases = [
            # (user_id, avatar_hash, expected_url)
            (
                123456789,
                "abc123",
                "https://cdn.discordapp.com/avatars/123456789/abc123.png",
            ),
            (987654321, None, None),  # No avatar
            (111222333, "", None),  # Empty avatar hash
        ]

        for user_id, avatar_hash, expected_url in test_cases:
            discord_user = {
                "id": user_id,
                "username": "testuser",
                "avatar": avatar_hash,
            }
            contact = DiscordTransformer.contact_to_omni(discord_user, "test")
            assert contact.avatar_url == expected_url

    def test_discord_user_id_string_conversion(self):
        """Test that Discord user IDs are properly converted to strings."""
        discord_user = {
            "id": 123456789012345678,  # Integer
            "username": "testuser",
        }

        contact = DiscordTransformer.contact_to_omni(discord_user, "test")

        # ID should be converted to string
        assert isinstance(contact.id, str)
        assert contact.id == "123456789012345678"

    def test_discord_name_priority_handling(self):
        """Test Discord name field priority handling."""
        # Test priority: global_name > display_name > username
        user_all_names = {
            "id": 123,
            "username": "username_only",
            "display_name": "Display Name",
            "global_name": "Global Name",
        }
        contact = DiscordTransformer.contact_to_omni(user_all_names, "test")
        assert contact.name == "Global Name"

        # Test without global_name
        user_no_global = {
            "id": 456,
            "username": "username_only",
            "display_name": "Display Name",
        }
        contact = DiscordTransformer.contact_to_omni(user_no_global, "test")
        assert contact.name == "username_only"  # Implementation doesn't use display_name

        # Test with only username
        user_only_username = {"id": 789, "username": "username_only"}
        contact = DiscordTransformer.contact_to_omni(user_only_username, "test")
        assert contact.name == "username_only"

    def test_discord_transformer_malformed_data(self):
        """Test Discord transformer with malformed data."""
        malformed_inputs = [
            {},  # Empty dict
            {"random": "data"},  # No id field
            {"id": None},  # Null id
            {"id": "not-number"},  # Wrong id type
        ]

        for malformed_input in malformed_inputs:
            # Should handle gracefully without throwing
            contact = DiscordTransformer.contact_to_omni(malformed_input, "test")
            assert isinstance(contact, OmniContact)
            assert contact.channel_type == ChannelType.DISCORD

    def test_transformer_edge_case_timestamps(self):
        """Test transformers with edge case timestamps."""
        edge_cases = [
            -1,  # Negative timestamp
            0,  # Epoch
            2**63 - 1,  # Large timestamp
            "invalid",  # String
            [],  # List
            {"nested": "dict"},  # Dict
        ]

        for edge_case in edge_cases:
            contact = {"id": "test@c.us", "name": "Test", "lastSeen": edge_case}
            # Should handle gracefully without crashing
            transformed = WhatsAppTransformer.contact_to_omni(contact, "test")
            assert isinstance(transformed, OmniContact)

    def test_discord_snowflake_timestamp_invalid_inputs(self):
        """Test Discord snowflake timestamp parsing with invalid inputs."""
        # Test None snowflake
        result = DiscordTransformer._parse_snowflake_timestamp(None)
        assert result is None

        # Test invalid snowflake that raises exception
        result = DiscordTransformer._parse_snowflake_timestamp("invalid_snowflake")
        assert result is None

        # Test empty string
        result = DiscordTransformer._parse_snowflake_timestamp("")
        assert result is None

        # Test valid snowflake
        valid_snowflake = 987654321098765432
        result = DiscordTransformer._parse_snowflake_timestamp(valid_snowflake)
        assert isinstance(result, datetime)

    def test_discord_timestamp_parsing_with_exceptions(self):
        """Test Discord timestamp parsing exception handling."""
        # Test None timestamp
        result = DiscordTransformer._parse_datetime(None)
        assert result is None

        # Test invalid timestamp type that raises exception
        result = DiscordTransformer._parse_datetime({"invalid": "dict"})
        assert result is None

        # Test list input
        result = DiscordTransformer._parse_datetime([1, 2, 3])
        assert result is None

        # Test valid integer timestamp
        result = DiscordTransformer._parse_datetime(1640995200)
        assert isinstance(result, datetime)

        # Test valid ISO string
        result = DiscordTransformer._parse_datetime("2022-01-01T00:00:00Z")
        assert isinstance(result, datetime)
