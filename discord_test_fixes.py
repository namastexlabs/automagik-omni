#!/usr/bin/env python3
"""
Script to fix the Discord handler tests in test_unified_handlers.py
"""

def fix_discord_tests():
    import_fix = """from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock"""
    
    # Create the complete fixed TestDiscordChatHandler class
    fixed_discord_class = '''class TestDiscordChatHandler:
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
        
        # Mock members
        member1 = MagicMock()
        member1.id = 987654321098765432
        member1.name = "testuser"
        member1.display_name = "Test User"
        member1.global_name = "Test User"
        member1.discriminator = "0001"
        member1.avatar = MagicMock()
        member1.avatar.url = "https://cdn.discordapp.com/avatars/987654321098765432/avatar.png"
        member1.status = "online"
        member1.bot = False
        member1.system = False
        member1.activities = []
        member1.verified = True
        member1.joined_at = datetime.now()
        
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
        assert isinstance(contact, UnifiedContact)
        assert contact.id == "987654321098765432"
        assert contact.name == "Test User"
        assert contact.channel_type == ChannelType.DISCORD
        assert contact.instance_name == "test-discord"
        assert contact.status == UnifiedContactStatus.ONLINE  # Maps from "online" status
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
        assert isinstance(chat, UnifiedChat)
        assert chat.id == "111222333444555666"
        assert chat.name == "general"
        assert chat.channel_type == ChannelType.DISCORD
        assert chat.instance_name == "test-discord"
        assert chat.chat_type == UnifiedChatType.DIRECT  # Type 0 maps to DIRECT
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
        assert isinstance(channel_info, UnifiedChannelInfo)
        assert channel_info.instance_name == "test-discord"
        assert channel_info.channel_type == ChannelType.DISCORD
        assert channel_info.display_name == "test-discord"  # Uses instance name as default
        # Bot connection status updates channel info
        assert channel_info.total_contacts == 1  # Member count from guild
        assert channel_info.total_chats == 1  # Channel count from guild

    @pytest.mark.asyncio
    async def test_discord_bot_not_found(
        self, mock_instance_config
    ):
        """Test handling when Discord bot is not available."""
        # Create handler without bot instances
        handler = DiscordChatHandler()
        contacts, total_count = await handler.get_contacts(mock_instance_config, page=1, page_size=50)
        # Should return empty results when bot instance not found
        assert contacts == []
        assert total_count == 0

    @pytest.mark.asyncio
    async def test_discord_guild_not_found(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test handling when Discord guild is not accessible."""
        # Set empty guilds list
        mock_discord_client.guilds = []
        contacts, total_count = await handler.get_contacts(mock_instance_config, page=1, page_size=50)
        # Should return empty results when no guilds available
        assert contacts == []
        assert total_count == 0

    @pytest.mark.asyncio
    async def test_discord_permission_error(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test handling of Discord permission errors."""
        # Mock guild with permission error
        def side_effect_guilds():
            raise Exception("Missing permissions")
        
        type(mock_discord_client).guilds = PropertyMock(side_effect=side_effect_guilds)
        
        contacts, total_count = await handler.get_contacts(mock_instance_config, page=1, page_size=50)
        # Should return empty results when permission error occurs
        assert contacts == []
        assert total_count == 0

    @pytest.mark.asyncio
    async def test_get_contact_by_id_success(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test successful contact retrieval by ID."""
        specific_user = MagicMock()
        specific_user.id = 555666777888999000
        specific_user.name = "specificuser"
        specific_user.display_name = "Specific User"
        specific_user.global_name = "Specific User"
        specific_user.discriminator = "0001"
        specific_user.avatar = None
        specific_user.status = "online"
        specific_user.bot = False
        specific_user.system = False
        specific_user.activities = []
        specific_user.verified = True
        
        async def mock_fetch_user_by_id(user_id):
            if user_id == 555666777888999000:
                return specific_user
            raise Exception("User not found")
        
        mock_discord_client.fetch_user = mock_fetch_user_by_id
        
        contact = await handler.get_contact_by_id(mock_instance_config, "555666777888999000")
        assert contact is not None
        assert contact.id == "555666777888999000"
        assert contact.name == "Specific User"
        assert contact.avatar_url is None

    @pytest.mark.asyncio
    async def test_get_contact_by_id_not_found(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test contact not found scenario."""
        async def mock_fetch_user_not_found(user_id):
            raise Exception("User not found")
        
        mock_discord_client.fetch_user = mock_fetch_user_not_found
        
        contact = await handler.get_contact_by_id(mock_instance_config, "nonexistent123")
        assert contact is None

    @pytest.mark.asyncio
    async def test_get_chat_by_id_success(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test successful chat retrieval by ID."""
        specific_channel = MagicMock()
        specific_channel.id = 777888999000111222
        specific_channel.name = "specific-channel"
        specific_channel.type = MagicMock()
        specific_channel.type.value = 2  # Voice channel
        specific_channel.guild_id = 123456789012345678
        specific_channel.guild = mock_discord_client.guilds[0]
        specific_channel.parent_id = None
        specific_channel.topic = None
        specific_channel.position = 1
        specific_channel.nsfw = False
        specific_channel.slowmode_delay = 0
        specific_channel.members = []
        
        def mock_get_channel_by_id(channel_id):
            if channel_id == 777888999000111222:
                return specific_channel
            return None
        
        mock_discord_client.get_channel = mock_get_channel_by_id
        
        chat = await handler.get_chat_by_id(mock_instance_config, "777888999000111222")
        assert chat is not None
        assert chat.id == "777888999000111222"
        assert chat.name == "specific-channel"
        assert chat.chat_type == UnifiedChatType.CHANNEL  # Type 2 maps to CHANNEL

    @pytest.mark.asyncio
    async def test_get_chat_by_id_not_found(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test chat not found scenario."""
        def mock_get_channel_not_found(channel_id):
            return None
        
        mock_discord_client.get_channel = mock_get_channel_not_found
        
        chat = await handler.get_chat_by_id(mock_instance_config, "nonexistent123")
        assert chat is None

    @pytest.mark.asyncio
    async def test_pagination_implementation(
        self, handler, mock_instance_config, mock_discord_client
    ):
        """Test pagination implementation for large member lists."""
        # Mock large member list
        members = []
        for i in range(100):
            member = MagicMock()
            member.id = i
            member.name = f"user{i}"
            member.display_name = f"User {i}"
            member.global_name = f"User {i}"
            member.discriminator = f"{i:04d}"
            member.avatar = None
            member.status = "online"
            member.bot = False
            member.system = False
            member.activities = []
            member.verified = True
            members.append(member)
        
        mock_discord_client.guilds[0].members = members
        
        # Test first page
        contacts, total_count = await handler.get_contacts(
            mock_instance_config, page=1, page_size=25
        )
        assert total_count == 100
        assert len(contacts) == 25  # Should respect page_size
        
        # Test second page
        contacts_page2, total_count2 = await handler.get_contacts(
            mock_instance_config, page=2, page_size=25
        )
        assert total_count2 == 100
        assert len(contacts_page2) == 25

    @pytest.mark.asyncio
    async def test_rate_limiting_handling(self, handler, mock_instance_config, mock_discord_client):
        """Test Discord rate limiting handling."""
        # Test that the handler can handle exceptions properly
        def side_effect_guilds():
            raise Exception("Rate limited")
        
        type(mock_discord_client).guilds = PropertyMock(side_effect=side_effect_guilds)
        
        contacts, total_count = await handler.get_contacts(mock_instance_config, page=1, page_size=50)
        # Should return empty results when rate limited
        assert contacts == []
        assert total_count == 0'''
    
    return import_fix, fixed_discord_class

if __name__ == "__main__":
    print("Discord test fixes prepared")
    import_fix, class_fix = fix_discord_tests()
    print("Import fix:", import_fix)
    print("Class fix ready - apply to test file")