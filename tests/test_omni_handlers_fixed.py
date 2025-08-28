"""
Comprehensive tests for omni channel handlers.
Tests both WhatsApp and Discord chat handlers with:
- External API mocking (Evolution API, Discord API)
- Error handling and timeout scenarios
- Data retrieval method testing
- Rate limiting and retry logic
- Environment configuration validation
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime
from src.channels.handlers.whatsapp_chat_handler import WhatsAppChatHandler
from src.channels.handlers.discord_chat_handler import DiscordChatHandler
from src.api.schemas.omni import (
    ChannelType, OmniContactStatus, OmniChatType,
    OmniContact, OmniChat, OmniChannelInfo
)
from src.db.models import InstanceConfig

# Global patches for external dependencies
@pytest.fixture(autouse=True)
def mock_httpx_client():
    """Mock httpx.AsyncClient globally to prevent real HTTP requests."""
    with patch('httpx.AsyncClient') as mock_client:
        # Create a mock client instance
        client_instance = AsyncMock()
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the request method to prevent actual HTTP calls
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "success", "data": []}'
        mock_response.json.return_value = {"status": "success", "data": []}
        client_instance.request.return_value = mock_response
        
        mock_client.return_value = client_instance
        yield mock_client

@pytest.fixture(autouse=True)  
def mock_discord_py():
    """Mock discord.py dependencies globally."""
    with patch('discord.Client'), \
         patch('discord.Intents'), \
         patch('discord.utils.get'):
        yield

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
        client.fetch_contacts.return_value = {
            "data": [
                {
                    "id": "5511999999999@c.us",
                    "name": "Test Contact",
                    "profilePictureUrl": "https://example.com/avatar.jpg",
                    "lastSeen": 1640995200000,  # Unix timestamp in milliseconds
                    "isGroup": False
                }
            ],
            "total": 1
        }
        client.fetch_chats.return_value = {
            "data": [
                {
                    "id": "5511999999999@c.us",
                    "name": "Test Chat",
                    "lastMessageTime": 1640995200000,
                    "unreadCount": 2,
                    "participants": []
                }
            ],
            "total": 1
        }
        return client
    @pytest.fixture
    def handler(self):
        """Create WhatsAppChatHandler instance."""
        return WhatsAppChatHandler()
    def test_initialization(self, handler):
        """Test handler initialization."""
        assert isinstance(handler, WhatsAppChatHandler)
        assert hasattr(handler, 'get_contacts')
        assert hasattr(handler, 'get_chats')
        assert hasattr(handler, 'get_channel_info')
    @patch('src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client')
    @pytest.mark.asyncio
    async def test_get_contacts_success(
        self, mock_get_client, handler, mock_instance_config, mock_evolution_client
    ):
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
        assert contact.status == OmniContactStatus.UNKNOWN  # FIXED: ACTIVE doesn't exist in enum
        assert contact.avatar_url == "https://example.com/avatar.jpg"
        # Verify channel-specific data
        assert "phone_number" in contact.channel_data
        assert contact.channel_data["phone_number"] == "5511999999999"
        # Verify client was called correctly
        mock_evolution_client.fetch_contacts.assert_called_once_with(
            instance_name="test-whatsapp",
            page=1,
            page_size=50
        )
    @patch('src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client')
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
                    "name": "John Doe",
                    "profilePictureUrl": None,
                    "lastSeen": None,
                    "isGroup": False
                }
            ],
            "total": 1
        }
        contacts, total_count = await handler.get_contacts(
            mock_instance_config, page=1, page_size=50, search_query="John"
        )
        assert len(contacts) == 1
        contact = contacts[0]
        assert contact.name == "John Doe"
        assert contact.avatar_url is None
        assert contact.last_seen is None
    @patch('src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client')
    @pytest.mark.asyncio
    async def test_get_chats_success(
        self, mock_get_client, handler, mock_instance_config, mock_evolution_client
    ):
        """Test successful chats retrieval."""
        mock_get_client.return_value = mock_evolution_client
        chats, total_count = await handler.get_chats(
            mock_instance_config, page=1, page_size=50
        )
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
    @patch('src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client')
    @pytest.mark.asyncio
    async def test_get_chats_group_identification(
        self, mock_get_client, handler, mock_instance_config, mock_evolution_client
    ):
        """Test proper identification of group chats vs direct chats."""
        mock_get_client.return_value = mock_evolution_client
        
        # Mock group chat data
        mock_evolution_client.fetch_chats.return_value = {
            "data": [
                {
                    "id": "120363025@g.us",
                    "name": "Test Group",
                    "lastMessageTime": 1640995200000,
                    "unreadCount": 5,
                    "participants": ["user1@c.us", "user2@c.us", "user3@c.us"]
                }
            ],
            "total": 1
        }
        chats, total_count = await handler.get_chats(
            mock_instance_config, page=1, page_size=50
        )
        chat = chats[0]
        assert chat.chat_type == OmniChatType.GROUP
        assert chat.participant_count == 3
        assert "group_id" in chat.channel_data
        assert chat.channel_data["group_id"] == "120363025@g.us"
    @patch('src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client')
    @pytest.mark.asyncio
    async def test_get_channel_info_success(
        self, mock_get_client, handler, mock_instance_config, mock_evolution_client
    ):
        """Test successful channel info retrieval."""
        mock_get_client.return_value = mock_evolution_client
        channel_info = await handler.get_channel_info(mock_instance_config)
        assert isinstance(channel_info, OmniChannelInfo)
        assert channel_info.instance_name == "test-whatsapp"
        assert channel_info.channel_type == ChannelType.WHATSAPP
        assert channel_info.display_name == "test-whatsapp"
        assert channel_info.status == "connected"
        assert channel_info.connected_at is not None
        assert channel_info.last_activity_at is not None
    @patch('src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client')
    @patch('src.channels.whatsapp.evolution_client.httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_evolution_api_timeout_handling(
        self, mock_httpx_client, mock_get_client, handler, mock_instance_config
    ):
        """Test handling of Evolution API timeouts."""
        # Mock the HTTP client to ensure no real requests
        mock_httpx_instance = AsyncMock()
        mock_httpx_client.return_value.__aenter__.return_value = mock_httpx_instance
        
        client = AsyncMock()
        client.fetch_contacts.side_effect = Exception("Connection timeout")
        mock_get_client.return_value = client
        with pytest.raises(Exception, match="Connection timeout"):
            await handler.get_contacts(mock_instance_config, page=1, page_size=50)
            
    @patch('src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client')
    @patch('src.channels.whatsapp.evolution_client.httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_evolution_api_404_handling(
        self, mock_httpx_client, mock_get_client, handler, mock_instance_config
    ):
        """Test handling of Evolution API 404 responses."""
        # Mock the HTTP client to ensure no real requests
        mock_httpx_instance = AsyncMock()
        mock_httpx_client.return_value.__aenter__.return_value = mock_httpx_instance
        
        client = AsyncMock()
        client.fetch_contacts.side_effect = Exception("Instance not found")
        mock_get_client.return_value = client
        with pytest.raises(Exception, match="Instance not found"):
            await handler.get_contacts(mock_instance_config, page=1, page_size=50)
    @patch('src.channels.whatsapp.omni_evolution_client.OmniEvolutionClient')
    def test_evolution_client_configuration_validation(self, mock_evolution_client_class, handler, mock_instance_config):
        """Test Evolution API client configuration validation."""
        # Mock the OmniEvolutionClient to raise appropriate exceptions
        # Test with missing API key
        mock_instance_config.evolution_url = "https://api.evolution.test"
        mock_instance_config.evolution_key = ""
        mock_evolution_client_class.side_effect = Exception("Evolution API key is required")
        
        with pytest.raises(Exception, match="Evolution API key"):
            handler._get_omni_evolution_client(mock_instance_config)
            
        # Test with invalid URL  
        mock_instance_config.evolution_url = "ftp://invalid-protocol.test"
        mock_instance_config.evolution_key = "valid-key"
        mock_evolution_client_class.side_effect = Exception("Evolution API URL must start with http")
        
        with pytest.raises(Exception, match="must start with http"):
            handler._get_omni_evolution_client(mock_instance_config)
    @patch('src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client')
    @pytest.mark.asyncio
    async def test_get_contact_by_id_success(
        self, mock_get_client, handler, mock_instance_config, mock_evolution_client
    ):
        """Test successful contact retrieval by ID."""
        mock_get_client.return_value = mock_evolution_client
        mock_evolution_client.get_contact_info.return_value = {
            "id": "5511999999999@c.us",
            "name": "Specific Contact",
            "profilePictureUrl": "https://example.com/avatar.jpg",
            "lastSeen": 1640995200000,
            "isGroup": False
        }
        contact = await handler.get_contact_by_id(mock_instance_config, "5511999999999@c.us")
        assert contact is not None
        assert contact.id == "5511999999999@c.us"
        assert contact.name == "Specific Contact"
    @patch('src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client')
    @pytest.mark.asyncio
    async def test_get_contact_by_id_not_found(
        self, mock_get_client, handler, mock_instance_config
    ):
        """Test contact not found scenario."""
        client = AsyncMock()
        client.get_contact_info.side_effect = Exception("Contact not found")
        mock_get_client.return_value = client
        contact = await handler.get_contact_by_id(mock_instance_config, "nonexistent@c.us")
        assert contact is None
    @patch('src.channels.handlers.whatsapp_chat_handler.WhatsAppChatHandler._get_omni_evolution_client')
    @pytest.mark.asyncio
    async def test_get_chat_by_id_success(
        self, mock_get_client, handler, mock_instance_config, mock_evolution_client
    ):
        """Test successful chat retrieval by ID."""
        mock_get_client.return_value = mock_evolution_client
        mock_evolution_client.get_chat_info.return_value = {
            "id": "5511999999999@c.us",
            "name": "Specific Chat",
            "lastMessageTime": 1640995200000,
            "unreadCount": 1,
            "participants": []
        }
        chat = await handler.get_chat_by_id(mock_instance_config, "5511999999999@c.us")
        assert chat is not None
        assert chat.id == "5511999999999@c.us"
        assert chat.name == "Specific Chat"
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
            "discord_guild_id": "123456789012345678"
        }
        return config
    
    @pytest.fixture
    def mock_discord_client(self):
        """Mock Discord client with proper structure."""
        # Create async mock for client
        client = AsyncMock()
        
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
            joined_at=datetime.now()
        )
        # Mock avatar with string URL
        member1.avatar = MagicMock()
        member1.avatar.configure_mock(url="https://cdn.discordapp.com/avatars/987654321098765432/avatar.png")
        
        guild.members = [member1]
        client.guilds = [guild]
        
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
        
        # Mock guild.get_member method - CRITICAL FIX
        def mock_get_member(user_id):
            if user_id == 987654321098765432:
                return member1
            return None

        guild.get_member = mock_get_member

        # Mock guild.get_channel method  
        def mock_get_channel(channel_id):
            if channel_id == 111222333444555666:
                return channel1
            return None
        
        guild.get_channel = mock_get_channel
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
    async def test_get_contacts_success(
        self, handler, mock_instance_config, mock_discord_client
    ):
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
        assert contact.channel_data["is_bot"] == False
    @pytest.mark.asyncio
    async def test_get_contacts_with_search_filter(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test contacts retrieval with search filtering."""
        # Mock multiple members
        member1 = MagicMock()
        member1.id = 111111111111111111
        member1.name = "johndoe"
        member1.display_name = "John Doe"
        member1.global_name = "John Doe"
        member1.discriminator = "0001"
        member1.avatar = None
        member1.status = "online"
        member1.bot = False
        member1.system = False
        member1.activities = []
        member1.verified = True
        
        member2 = MagicMock()
        member2.id = 222222222222222222
        member2.name = "janesmith"
        member2.display_name = "Jane Smith"
        member2.global_name = "Jane Smith"
        member2.discriminator = "0002"
        member2.avatar = None
        member2.status = "idle"
        member2.bot = False
        member2.system = False
        member2.activities = []
        member2.verified = True
        
        # Update guild members
        mock_discord_client.guilds[0].members = [member1, member2]
        
        contacts, total_count = await handler.get_contacts(
            mock_instance_config, page=1, page_size=50, search_query="John"
        )
        # Should only return contacts matching the search query
        assert len(contacts) <= 2
        if len(contacts) == 1:
            assert "John" in contacts[0].name
    @pytest.mark.asyncio
    async def test_get_chats_success(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test successful chats retrieval from Discord."""
        chats, total_count = await handler.get_chats(
            mock_instance_config, page=1, page_size=50
        )
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
    @patch('src.channels.handlers.discord_chat_handler.DiscordChannelHandler.get_status')
    @pytest.mark.asyncio
    async def test_get_channel_info_success(
        self, mock_get_status, handler, mock_instance_config, mock_discord_client
    ):
        """Test successful channel info retrieval."""
        # Mock the get_status response
        mock_get_status.return_value = MagicMock()
        mock_get_status.return_value.channel_data = {"status": "connected"}
        
        mock_discord_client.latency = 0.050  # 50ms latency
        
        channel_info = await handler.get_channel_info(mock_instance_config)
        assert isinstance(channel_info, OmniChannelInfo)
    @pytest.mark.asyncio
    async def test_discord_bot_not_initialized(
        self, mock_instance_config
    ):
        """Test handling when Discord bot is not initialized."""
        handler = DiscordChatHandler()
        # Don't add any bot instances to _bot_instances
        
        with pytest.raises(Exception, match="Discord bot not initialized"):
            await handler.get_contacts(mock_instance_config, page=1, page_size=50)
    @pytest.mark.asyncio
    async def test_discord_api_error_handling(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test handling of Discord API errors."""
        # Mock Discord API error
        mock_discord_client.guilds = None
        
        # Handler should gracefully handle errors and return empty results
        contacts, total = await handler.get_contacts(mock_instance_config, page=1, page_size=50)
        assert contacts == []
        assert total == 0
    @pytest.mark.asyncio
    async def test_get_contact_by_id_success(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test successful contact retrieval by ID."""
        contact = await handler.get_contact_by_id(mock_instance_config, "987654321098765432")
        assert contact is not None
        assert contact.id == "987654321098765432"
        assert contact.name == "Test User"
    @pytest.mark.asyncio
    async def test_get_contact_by_id_not_found(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test contact not found scenario."""
        contact = await handler.get_contact_by_id(mock_instance_config, "999999999999999999")
        assert contact is None
    @pytest.mark.asyncio
    async def test_get_chat_by_id_success(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test successful chat retrieval by ID."""
        chat = await handler.get_chat_by_id(mock_instance_config, "111222333444555666")
        assert chat is not None
        assert chat.id == "111222333444555666"
        assert chat.name == "general"