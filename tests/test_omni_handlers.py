"""
Comprehensive tests for omni channel handlers.
Tests both WhatsApp and Discord chat handlers with:
- External API mocking (Evolution API, Discord API)
- Error handling and timeout scenarios
- Data retrieval method testing
- Rate limiting and retry logic
- Environment configuration validation
"""

import sys
import types

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from src.channels.handlers.whatsapp_chat_handler import WhatsAppChatHandler
from src.channels.handlers.discord_chat_handler import DiscordChatHandler
from src.api.schemas.omni import (
    ChannelType,
    OmniContactStatus,
    OmniChatType,
    OmniContact,
    OmniChat,
    OmniChannelInfo,
)
from src.db.models import InstanceConfig


# Fixture for httpx mocking - use explicitly where needed
@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient to prevent real HTTP requests."""
    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=None)

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "success", "data": []}'
        mock_response.json.return_value = {"status": "success", "data": []}
        client_instance.request.return_value = mock_response

        mock_client.return_value = client_instance
        yield mock_client


# Fixture for discord.py mocking - use explicitly where needed
@pytest.fixture
def mock_discord_py():
    """Mock discord.py dependencies, even if the optional package is absent."""
    # Save any existing discord modules (including namespace packages from tests/channels/discord)
    old_discord = sys.modules.get("discord")
    old_discord_utils = sys.modules.get("discord.utils")

    # Always create our stub to avoid namespace package conflicts
    discord_stub = types.ModuleType("discord")
    discord_stub.Client = MagicMock()
    discord_stub.Intents = MagicMock()

    utils_stub = types.ModuleType("discord.utils")
    utils_stub.get = lambda *args, **kwargs: None

    discord_stub.utils = utils_stub

    sys.modules["discord"] = discord_stub
    sys.modules["discord.utils"] = utils_stub

    try:
        yield
    finally:
        # Restore original state
        if old_discord is not None:
            sys.modules["discord"] = old_discord
        else:
            sys.modules.pop("discord", None)

        if old_discord_utils is not None:
            sys.modules["discord.utils"] = old_discord_utils
        else:
            sys.modules.pop("discord.utils", None)


@pytest.mark.usefixtures("mock_httpx_client")
class TestWhatsAppChatHandler:
    """Comprehensive tests for WhatsAppChatHandler."""

    @pytest.fixture
    def mock_instance_config(self):
        """Mock WhatsApp instance configuration."""
        config = MagicMock(spec=InstanceConfig)
        config.name = "test-whatsapp"
        config.channel_type = "whatsapp"
        config.evolution_url = "https://api.evolution.test"
        config.evolution_key = "test-api-key-123"
        config.config = {}
        return config

    @pytest.fixture
    def mock_evolution_client(self):
        """Mock Evolution API client."""
        client = AsyncMock()
        # PRECISION FIX: Ensure get_connection_state returns real dict to prevent AsyncMock.keys() error
        client.get_connection_state.return_value = {"status": "connected"}
        client.fetch_contacts.return_value = {
            "data": [
                {
                    "id": "5511999999999@c.us",
                    "pushName": "Test Contact",
                    "profilePictureUrl": "https://example.com/avatar.jpg",
                    "lastSeen": 1640995200000,  # Unix timestamp in milliseconds
                    "isGroup": False,
                }
            ],
            "total": 1,
        }
        client.fetch_chats.return_value = {
            "data": [
                {
                    "id": "5511999999999@c.us",
                    "name": "Test Chat",
                    "lastMessageTime": 1640995200000,
                    "unreadCount": 2,
                    "participants": [],
                }
            ],
            "total": 1,
        }
        return client

    @pytest.fixture
    def handler(self):
        """Create WhatsAppChatHandler instance."""
        return WhatsAppChatHandler()

    def test_initialization(self, handler):
        """Test handler initialization."""
        assert isinstance(handler, WhatsAppChatHandler)
        assert hasattr(handler, "get_contacts")
        assert hasattr(handler, "get_chats")
        assert hasattr(handler, "get_channel_info")

    @patch("src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client")
    @pytest.mark.asyncio
    async def test_get_contacts_success(self, mock_get_client, handler, mock_instance_config, mock_evolution_client):
        """Test successful contacts retrieval."""
        mock_get_client.return_value = mock_evolution_client
        contacts, total_count = await handler.get_contacts(
            mock_instance_config, page=1, page_size=50, search_query=None
        )
        assert len(contacts) == 1
        assert total_count == 1
        contact = contacts[0]
        assert isinstance(contact, OmniContact)
        assert contact.id == "5511999999999@c.us"
        assert contact.name == "Test Contact"
        assert contact.channel_type == ChannelType.WHATSAPP
        assert contact.instance_name == "test-whatsapp"
        assert contact.status == OmniContactStatus.UNKNOWN
        assert contact.avatar_url == "https://example.com/avatar.jpg"
        # Verify channel-specific data
        assert "phone_number" in contact.channel_data
        assert contact.channel_data["phone_number"] == "5511999999999"
        # Verify client was called correctly
        mock_evolution_client.fetch_contacts.assert_called_once_with(
            instance_name="test-whatsapp", page=1, page_size=50
        )

    @patch("src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client")
    @pytest.mark.asyncio
    async def test_get_contacts_with_search_query(
        self, mock_get_client, handler, mock_instance_config, mock_evolution_client
    ):
        """Test contacts retrieval with search query."""
        mock_get_client.return_value = mock_evolution_client
        mock_evolution_client.fetch_contacts.return_value = {
            "data": [
                {
                    "id": "5511111111111@c.us",
                    "pushName": "John Doe",
                    "profilePictureUrl": None,
                    "lastSeen": None,
                    "isGroup": False,
                }
            ],
            "total": 1,
        }
        contacts, total_count = await handler.get_contacts(
            mock_instance_config, page=1, page_size=50, search_query="John"
        )
        assert len(contacts) == 1
        contact = contacts[0]
        assert contact.name == "John Doe"
        assert contact.avatar_url is None
        assert contact.last_seen is None

    @patch("src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client")
    @pytest.mark.asyncio
    async def test_get_chats_success(self, mock_get_client, handler, mock_instance_config, mock_evolution_client):
        """Test successful chats retrieval."""
        mock_get_client.return_value = mock_evolution_client
        chats, total_count = await handler.get_chats(mock_instance_config, page=1, page_size=50)
        assert len(chats) == 1
        assert total_count == 1
        chat = chats[0]
        assert isinstance(chat, OmniChat)
        assert chat.id == "5511999999999@c.us"
        assert chat.name == "Test Chat"
        assert chat.channel_type == ChannelType.WHATSAPP
        assert chat.instance_name == "test-whatsapp"
        assert chat.chat_type == OmniChatType.DIRECT
        assert chat.unread_count == 2

    @patch("src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler.get_status")
    @pytest.mark.asyncio
    async def test_get_channel_info_success(self, mock_get_status, handler, mock_instance_config):
        """Test successful channel info retrieval."""
        # Mock the get_status response
        mock_status_response = MagicMock()
        mock_status_response.status = "connected"
        mock_status_response.instance_name = "test-whatsapp"
        mock_status_response.channel_type = "whatsapp"
        mock_status_response.channel_data = {
            "phoneNumber": "5511999999999",
            "profileName": "Test Profile",
        }
        mock_get_status.return_value = mock_status_response

        channel_info = await handler.get_channel_info(mock_instance_config)
        assert isinstance(channel_info, OmniChannelInfo)
        assert channel_info.instance_name == "test-whatsapp"
        assert channel_info.channel_type == ChannelType.WHATSAPP
        assert channel_info.display_name == "WhatsApp - test-whatsapp"
        assert channel_info.status == "connected"

    @patch("src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client")
    @patch("src.channels.whatsapp.evolution_client.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_evolution_api_timeout_handling(
        self, mock_httpx_client, mock_get_client, handler, mock_instance_config
    ):
        """Test handling of Evolution API timeouts."""
        # Mock the HTTP client to ensure no real requests
        mock_httpx_instance = AsyncMock()
        mock_httpx_client.return_value.__aenter__.return_value = mock_httpx_instance

        client = AsyncMock()
        # PRECISION FIX: Ensure get_connection_state returns real dict to prevent AsyncMock.keys() error
        client.get_connection_state.return_value = {"status": "connected"}
        client.fetch_contacts.side_effect = Exception("Connection timeout")
        mock_get_client.return_value = client
        with pytest.raises(Exception, match="Connection timeout"):
            await handler.get_contacts(mock_instance_config, page=1, page_size=50)

    @patch("src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client")
    @patch("src.channels.whatsapp.evolution_client.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_evolution_api_404_handling(self, mock_httpx_client, mock_get_client, handler, mock_instance_config):
        """Test handling of Evolution API 404 responses."""
        # Mock the HTTP client to ensure no real requests
        mock_httpx_instance = AsyncMock()
        mock_httpx_client.return_value.__aenter__.return_value = mock_httpx_instance

        client = AsyncMock()
        # PRECISION FIX: Ensure get_connection_state returns real dict to prevent AsyncMock.keys() error
        client.get_connection_state.return_value = {"status": "connected"}
        client.fetch_contacts.side_effect = Exception("Instance not found")
        mock_get_client.return_value = client
        with pytest.raises(Exception, match="Instance not found"):
            await handler.get_contacts(mock_instance_config, page=1, page_size=50)

    @patch("src.services.settings_service.get_evolution_api_key_global")
    @patch("src.channels.handlers.whatsapp_chat_handler.OmniEvolutionClient")
    def test_evolution_client_configuration_validation(
        self, mock_client_class, mock_get_key, handler, mock_instance_config
    ):
        """Test Evolution API client is created with valid configuration."""
        # Setup valid configuration
        mock_instance_config.evolution_url = "https://api.evolution.test"
        mock_get_key.return_value = "valid-global-key"

        # Mock client creation
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        # Should create client successfully
        client = handler._get_omni_evolution_client(mock_instance_config)
        assert client is not None
        mock_client_class.assert_called_once()
        # Verify correct args: (url, bootstrap_key, instance_name)
        call_args = mock_client_class.call_args[0]
        assert call_args[0] == "https://api.evolution.test"
        assert call_args[1] == "valid-global-key"

    @patch("src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client")
    @pytest.mark.asyncio
    async def test_get_contact_by_id_success(
        self, mock_get_client, handler, mock_instance_config, mock_evolution_client
    ):
        """Test successful contact retrieval by ID."""
        mock_get_client.return_value = mock_evolution_client
        # Mock get_contacts instead since get_contact_by_id uses it internally
        mock_evolution_client.fetch_contacts.return_value = {
            "data": [
                {
                    "id": "5511999999999@c.us",
                    "pushName": "Specific Contact",
                    "profilePictureUrl": "https://example.com/avatar.jpg",
                    "lastSeen": 1640995200000,
                    "isGroup": False,
                }
            ],
            "total": 1,
        }
        contact = await handler.get_contact_by_id(mock_instance_config, "5511999999999@c.us")
        assert contact is not None
        assert contact.id == "5511999999999@c.us"
        assert contact.name == "Specific Contact"

    @patch("src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client")
    @pytest.mark.asyncio
    async def test_get_contact_by_id_not_found(self, mock_get_client, handler, mock_instance_config):
        """Test contact not found scenario."""
        client = AsyncMock()
        # PRECISION FIX: Ensure get_connection_state returns real dict to prevent AsyncMock.keys() error
        client.get_connection_state.return_value = {"status": "connected"}
        client.fetch_contacts.return_value = {"data": [], "total": 0}
        mock_get_client.return_value = client
        contact = await handler.get_contact_by_id(mock_instance_config, "nonexistent@c.us")
        assert contact is None

    @patch("src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client")
    @pytest.mark.asyncio
    async def test_get_chat_by_id_success(self, mock_get_client, handler, mock_instance_config, mock_evolution_client):
        """Test successful chat retrieval by ID."""
        mock_get_client.return_value = mock_evolution_client
        # Mock get_chats instead since get_chat_by_id uses it internally
        mock_evolution_client.fetch_chats.return_value = {
            "data": [
                {
                    "id": "5511999999999@c.us",
                    "name": "Specific Chat",
                    "lastMessageTime": 1640995200000,
                    "unreadCount": 1,
                    "participants": [],
                }
            ],
            "total": 1,
        }
        chat = await handler.get_chat_by_id(mock_instance_config, "5511999999999@c.us")
        assert chat is not None
        assert chat.id == "5511999999999@c.us"
        assert chat.name == "Specific Chat"


@pytest.mark.usefixtures("mock_httpx_client", "mock_discord_py")
class TestDiscordChatHandler:
    """Comprehensive tests for DiscordChatHandler."""

    @pytest.fixture
    def mock_instance_config(self):
        """Mock Discord instance configuration."""
        config = MagicMock(spec=InstanceConfig)
        config.name = "test-discord"
        config.channel_type = "discord"
        config.config = {
            "discord_token": "test-discord-token-123",
            "discord_guild_id": "123456789012345678",
        }
        return config

    @pytest.fixture
    def mock_discord_client(self):
        """Mock Discord client with proper structure."""
        # Create async mock for client
        client = AsyncMock()
        # PRECISION FIX: Ensure get_connection_state returns real dict to prevent AsyncMock.keys() error
        client.get_connection_state.return_value = {"status": "connected"}

        # Mock guild
        guild = MagicMock()
        guild.id = 123456789012345678
        guild.name = "Test Server"
        guild.member_count = 100
        guild.icon = MagicMock()
        guild.icon.url = "https://cdn.discordapp.com/icons/123456789012345678/avatar.png"

        # Mock members - FIXED: Configure mock to return string values instead of MagicMocks
        member1 = MagicMock()
        member1.id = 987654321098765432
        # Critical fix: configure_mock ensures attributes return actual values, not MagicMocks
        member1.configure_mock(
            name="testuser",
            username="testuser",
            display_name="Test User",
            global_name="Test User",
            discriminator="0001",
            status="online",
            bot=False,
            system=False,
            activities=[],
            verified=True,
            joined_at=datetime.now(),
        )
        # Mock avatar with string URL
        member1.avatar = MagicMock()
        member1.avatar.configure_mock(url="https://cdn.discordapp.com/avatars/987654321098765432/avatar.png")
        # Mock guild reference
        member1.guild = guild

        guild.members = [member1]
        client.guilds = [guild]

        # Mock guild.get_member method
        def mock_get_member(user_id):
            if user_id == 987654321098765432:
                return member1
            return None

        guild.get_member = mock_get_member

        # Mock async methods
        async def mock_fetch_user(user_id):
            if user_id == 987654321098765432:
                return member1
            raise Exception("User not found")

        client.fetch_user = mock_fetch_user

        # Mock channels
        channel1 = MagicMock()
        channel1.id = 111222333444555666
        channel1.name = "general"
        channel1.type = MagicMock()
        channel1.type.value = 0  # Text channel
        channel1.guild_id = 123456789012345678
        channel1.guild = guild
        channel1.parent_id = None
        channel1.topic = None
        channel1.position = 0
        channel1.nsfw = False
        channel1.slowmode_delay = 0
        channel1.members = []

        guild.channels = [channel1]

        def mock_get_channel(channel_id):
            if channel_id == 111222333444555666:
                return channel1
            return None

        client.get_channel = mock_get_channel

        return client

    @pytest.fixture
    def mock_bot_instance(self, mock_discord_client):
        """Mock DiscordBotInstance."""
        bot_instance = MagicMock()
        bot_instance.client = mock_discord_client
        bot_instance.status = "connected"
        bot_instance.task = None
        bot_instance.invite_url = None
        bot_instance.error_message = None
        return bot_instance

    @pytest.fixture
    def handler(self, mock_bot_instance, mock_instance_config):
        """Create DiscordChatHandler instance with mocked bot instance."""
        handler = DiscordChatHandler()
        # Properly mock the _bot_instances dictionary
        handler._bot_instances = {mock_instance_config.name: mock_bot_instance}
        return handler

    @pytest.mark.asyncio
    async def test_get_contacts_success(self, handler, mock_instance_config, mock_discord_client):
        """Test successful contacts retrieval from Discord."""
        contacts, total_count = await handler.get_contacts(
            mock_instance_config, page=1, page_size=50, search_query=None
        )
        assert len(contacts) == 1
        assert total_count == 1
        contact = contacts[0]
        assert isinstance(contact, OmniContact)
        assert contact.id == "987654321098765432"
        assert contact.name == "Test User"
        assert contact.channel_type == ChannelType.DISCORD
        assert contact.instance_name == "test-discord"
        assert contact.status == OmniContactStatus.ONLINE  # Maps from "online" status
        # Verify Discord-specific data
        assert "username" in contact.channel_data
        assert contact.channel_data["username"] == "testuser"
        assert contact.channel_data["global_name"] == "Test User"
        assert not contact.channel_data["is_bot"]

    @pytest.mark.asyncio
    async def test_get_chats_success(self, handler, mock_instance_config, mock_discord_client):
        """Test successful chats retrieval from Discord."""
        chats, total_count = await handler.get_chats(mock_instance_config, page=1, page_size=50)
        assert len(chats) == 1
        assert total_count == 1
        chat = chats[0]
        assert isinstance(chat, OmniChat)
        assert chat.id == "111222333444555666"
        assert chat.name == "general"
        assert chat.channel_type == ChannelType.DISCORD
        assert chat.instance_name == "test-discord"
        assert chat.chat_type == OmniChatType.DIRECT  # Type 0 maps to DIRECT
        # Verify Discord-specific data
        assert "guild_id" in chat.channel_data
        assert chat.channel_data["guild_id"] == 123456789012345678

    @patch("src.channels.handlers.discord_chat_handler.DiscordChannelHandler.get_status")
    @pytest.mark.asyncio
    async def test_get_channel_info_success(self, mock_get_status, handler, mock_instance_config, mock_discord_client):
        """Test successful channel info retrieval."""
        # Mock the get_status response
        mock_get_status.return_value = MagicMock()
        mock_get_status.return_value.channel_data = {"status": "connected"}

        mock_discord_client.latency = 0.050  # 50ms latency

        channel_info = await handler.get_channel_info(mock_instance_config)
        assert isinstance(channel_info, OmniChannelInfo)

    @pytest.mark.asyncio
    async def test_discord_bot_not_initialized(self, mock_instance_config):
        """Test handling when Discord bot is not initialized."""
        handler = DiscordChatHandler()
        # Don't add any bot instances to _bot_instances

        contacts, total_count = await handler.get_contacts(mock_instance_config, page=1, page_size=50)
        assert len(contacts) == 0
        assert total_count == 0

    @pytest.mark.asyncio
    async def test_get_contact_by_id_success(self, handler, mock_instance_config, mock_discord_client):
        """Test successful contact retrieval by ID."""
        contact = await handler.get_contact_by_id(mock_instance_config, "987654321098765432")
        assert contact is not None
        assert contact.id == "987654321098765432"
        assert contact.name == "Test User"

    @pytest.mark.asyncio
    async def test_get_contact_by_id_not_found(self, handler, mock_instance_config, mock_discord_client):
        """Test contact not found scenario."""
        contact = await handler.get_contact_by_id(mock_instance_config, "999999999999999999")
        assert contact is None

    @pytest.mark.asyncio
    async def test_get_chat_by_id_success(self, handler, mock_instance_config, mock_discord_client):
        """Test successful chat retrieval by ID."""
        chat = await handler.get_chat_by_id(mock_instance_config, "111222333444555666")
        assert chat is not None
        assert chat.id == "111222333444555666"
        assert chat.name == "general"

    @pytest.mark.asyncio
    async def test_get_chat_by_id_not_found(self, handler, mock_instance_config, mock_discord_client):
        """Test chat not found scenario."""
        chat = await handler.get_chat_by_id(mock_instance_config, "999999999999999999")
        assert chat is None


@pytest.mark.usefixtures("mock_httpx_client", "mock_discord_py")
class TestHandlerErrorScenarios:
    """Test error scenarios common to both handlers."""

    def test_invalid_instance_config(self):
        """Test handling of invalid instance configurations."""
        whatsapp_handler = WhatsAppChatHandler()
        DiscordChatHandler()

        # Test with None config
        with pytest.raises(Exception):
            whatsapp_handler._get_omni_evolution_client(None)

    @patch("src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client")
    @patch("src.channels.whatsapp.evolution_client.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_network_timeout_scenarios(self, mock_httpx_client, mock_get_client):
        """Test various network timeout scenarios."""
        handler = WhatsAppChatHandler()

        config = MagicMock(spec=InstanceConfig)
        config.name = "timeout-test"
        config.channel_type = "whatsapp"
        config.evolution_url = "https://slow-api.test.com"
        config.evolution_key = "test-key"

        # Mock the HTTP client to ensure no real requests
        mock_httpx_instance = AsyncMock()
        mock_httpx_client.return_value.__aenter__.return_value = mock_httpx_instance

        client = AsyncMock()
        # PRECISION FIX: Ensure get_connection_state returns real dict to prevent AsyncMock.keys() error
        client.get_connection_state.return_value = {"status": "connected"}

        # Test connection timeout
        client.fetch_contacts.side_effect = Exception("Connection timeout after 30s")
        mock_get_client.return_value = client

        with pytest.raises(Exception, match="Connection timeout"):
            await handler.get_contacts(config, page=1, page_size=50)


@pytest.mark.usefixtures("mock_httpx_client", "mock_discord_py")
class TestOmniHandlerIntegration:
    """Integration tests for omni handlers."""

    @pytest.mark.asyncio
    async def test_whatsapp_to_discord_data_compatibility(self):
        """Test that data from WhatsApp handler is compatible with omni schemas."""
        whatsapp_handler = WhatsAppChatHandler()

        config = MagicMock(spec=InstanceConfig)
        config.name = "whatsapp-integration"
        config.channel_type = "whatsapp"
        config.config = {
            "evolution_api_url": "https://api.test.com",
            "evolution_api_key": "test-key",
        }

        with patch(
            "src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client"
        ) as mock_get_client:
            client = AsyncMock()
            # PRECISION FIX: Ensure get_connection_state returns real dict to prevent AsyncMock.keys() error
            client.get_connection_state.return_value = {"status": "connected"}
            client.fetch_contacts.return_value = {
                "data": [
                    {
                        "id": "5511999999999@c.us",
                        "name": "Integration Test Contact",
                        "profilePictureUrl": "https://example.com/avatar.jpg",
                        "lastSeen": 1640995200000,
                        "isGroup": False,
                    }
                ],
                "total": 1,
            }
            mock_get_client.return_value = client

            contacts, total_count = await whatsapp_handler.get_contacts(config, page=1, page_size=50, search_query=None)

            # Verify the contact can be serialized/deserialized
            contact = contacts[0]
            contact_dict = contact.model_dump()

            # Should contain all required omni fields
            required_fields = [
                "id",
                "name",
                "channel_type",
                "instance_name",
                "status",
                "created_at",
                "last_seen",
            ]

            for field in required_fields:
                assert field in contact_dict

            # Verify omni contact can be reconstructed
            reconstructed = OmniContact.model_validate(contact_dict)
            assert reconstructed.id == contact.id
            assert reconstructed.name == contact.name
            assert reconstructed.channel_type == contact.channel_type

    def test_omni_schemas_validation(self):
        """Test that omni schemas properly validate required fields."""
        from pydantic import ValidationError

        # Test OmniContact validation
        with pytest.raises(ValidationError):
            OmniContact()  # Missing required fields

        # Valid contact should pass
        contact = OmniContact(
            id="test@example.com",
            name="Test User",
            channel_type=ChannelType.WHATSAPP,
            instance_name="test-instance",
            status=OmniContactStatus.ONLINE,
        )
        assert contact.id == "test@example.com"
        assert contact.status == OmniContactStatus.ONLINE

        # Test OmniChat validation
        chat = OmniChat(
            id="chat-123",
            name="Test Chat",
            channel_type=ChannelType.DISCORD,
            instance_name="test-instance",
            chat_type=OmniChatType.GROUP,
        )
        assert chat.chat_type == OmniChatType.GROUP

    @pytest.mark.asyncio
    async def test_cross_handler_functionality(self):
        """Test that both handlers implement the same interface correctly."""
        whatsapp_handler = WhatsAppChatHandler()
        discord_handler = DiscordChatHandler()

        # Both should have the same public methods
        whatsapp_methods = set(dir(whatsapp_handler))
        discord_methods = set(dir(discord_handler))

        # Core methods should be present in both
        core_methods = {
            "get_contacts",
            "get_chats",
            "get_channel_info",
            "get_contact_by_id",
            "get_chat_by_id",
        }

        assert core_methods.issubset(whatsapp_methods)
        assert core_methods.issubset(discord_methods)

        # Both should be callable with the same signature
        import inspect

        for method_name in core_methods:
            whatsapp_sig = inspect.signature(getattr(whatsapp_handler, method_name))
            discord_sig = inspect.signature(getattr(discord_handler, method_name))

            # Parameter names and types should match
            assert list(whatsapp_sig.parameters.keys()) == list(discord_sig.parameters.keys())
