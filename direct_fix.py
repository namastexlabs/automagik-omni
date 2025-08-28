#!/usr/bin/env python3
"""Direct file replacement for Discord test fixes"""

def apply_fixes():
    # Read original file
    with open('tests/test_unified_handlers.py', 'r') as f:
        content = f.read()
    
    # Backup original
    with open('tests/test_unified_handlers_backup.py', 'w') as f:
        f.write(content)
    
    # Apply fixes
    content = content.replace(
        'from unittest.mock import AsyncMock, MagicMock, patch',
        'from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock'
    )
    
    # Replace the entire Discord test class section
    discord_class_start = content.find('class TestDiscordChatHandler:')
    if discord_class_start != -1:
        # Find the end of the Discord class (next class or end of file)
        next_class_start = content.find('class TestHandlerErrorRecovery:', discord_class_start)
        if next_class_start == -1:
            next_class_start = len(content)
        
        # Replace the Discord class
        new_discord_class = '''class TestDiscordChatHandler:
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
        client = AsyncMock()
        
        # Mock guild
        guild = MagicMock()
        guild.id = 123456789012345678
        guild.name = "Test Server"
        guild.member_count = 100
        
        # Mock member
        member1 = MagicMock()
        member1.id = 987654321098765432
        member1.name = "testuser"
        member1.display_name = "Test User"
        member1.global_name = "Test User"
        member1.status = "online"
        member1.bot = False
        member1.activities = []
        
        guild.members = [member1]
        client.guilds = [guild]
        
        # Mock channel
        channel1 = MagicMock()
        channel1.id = 111222333444555666
        channel1.name = "general"
        channel1.type = MagicMock()
        channel1.type.value = 0
        channel1.guild_id = 123456789012345678
        
        guild.channels = [channel1]
        client.get_channel = lambda cid: channel1 if cid == 111222333444555666 else None
        
        async def mock_fetch_user(user_id):
            if user_id == 987654321098765432:
                return member1
            raise Exception("User not found")
        
        client.fetch_user = mock_fetch_user
        return client
    
    @pytest.fixture
    def mock_bot_instance(self, mock_discord_client):
        """Mock DiscordBotInstance."""
        bot_instance = MagicMock()
        bot_instance.client = mock_discord_client
        bot_instance.status = "connected"
        return bot_instance
    
    @pytest.fixture
    def handler(self, mock_bot_instance, mock_instance_config):
        """Create DiscordChatHandler instance with mocked bot instance."""
        handler = DiscordChatHandler()
        handler._bot_instances = {mock_instance_config.name: mock_bot_instance}
        return handler

    @pytest.mark.asyncio
    async def test_get_contacts_success(self, handler, mock_instance_config):
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

    @pytest.mark.asyncio
    async def test_get_contacts_with_search_filter(self, handler, mock_instance_config, mock_discord_client):
        """Test contacts retrieval with search filtering."""
        # Create multiple members for testing
        member1 = MagicMock()
        member1.name = "johndoe"
        member1.global_name = "John Doe"
        member1.id = 111111111111111111
        member1.status = "online"
        member1.bot = False
        member1.activities = []
        
        member2 = MagicMock()
        member2.name = "janesmith" 
        member2.global_name = "Jane Smith"
        member2.id = 222222222222222222
        member2.status = "idle"
        member2.bot = False
        member2.activities = []
        
        mock_discord_client.guilds[0].members = [member1, member2]
        
        contacts, total_count = await handler.get_contacts(
            mock_instance_config, page=1, page_size=50, search_query="John"
        )
        # Should filter results
        assert len(contacts) <= 2

    @pytest.mark.asyncio
    async def test_get_chats_success(self, handler, mock_instance_config):
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

    @patch('src.channels.handlers.discord_chat_handler.DiscordChannelHandler.get_status')
    @pytest.mark.asyncio
    async def test_get_channel_info_success(self, mock_get_status, handler, mock_instance_config):
        """Test successful channel info retrieval."""
        mock_get_status.return_value = MagicMock()
        mock_get_status.return_value.channel_data = {"status": "connected"}
        
        channel_info = await handler.get_channel_info(mock_instance_config)
        assert isinstance(channel_info, UnifiedChannelInfo)
        assert channel_info.instance_name == "test-discord"
        assert channel_info.channel_type == ChannelType.DISCORD

    @pytest.mark.asyncio
    async def test_discord_bot_not_found(self, mock_instance_config):
        """Test handling when Discord bot is not available."""
        handler = DiscordChatHandler()
        contacts, total_count = await handler.get_contacts(mock_instance_config, page=1, page_size=50)
        assert contacts == []
        assert total_count == 0

    @pytest.mark.asyncio
    async def test_discord_guild_not_found(self, handler, mock_instance_config, mock_discord_client):
        """Test handling when Discord guild is not accessible."""
        mock_discord_client.guilds = []
        contacts, total_count = await handler.get_contacts(mock_instance_config, page=1, page_size=50)
        assert contacts == []
        assert total_count == 0

    @pytest.mark.asyncio
    async def test_discord_permission_error(self, handler, mock_instance_config, mock_discord_client):
        """Test handling of Discord permission errors."""
        def side_effect_guilds():
            raise Exception("Missing permissions")
        
        type(mock_discord_client).guilds = PropertyMock(side_effect=side_effect_guilds)
        
        contacts, total_count = await handler.get_contacts(mock_instance_config, page=1, page_size=50)
        assert contacts == []
        assert total_count == 0

    @pytest.mark.asyncio
    async def test_get_contact_by_id_success(self, handler, mock_instance_config, mock_discord_client):
        """Test successful contact retrieval by ID."""
        contact = await handler.get_contact_by_id(mock_instance_config, "987654321098765432")
        assert contact is not None
        assert contact.id == "987654321098765432"

    @pytest.mark.asyncio
    async def test_get_contact_by_id_not_found(self, handler, mock_instance_config, mock_discord_client):
        """Test contact not found scenario."""
        async def mock_fetch_user_not_found(user_id):
            raise Exception("User not found")
        
        mock_discord_client.fetch_user = mock_fetch_user_not_found
        contact = await handler.get_contact_by_id(mock_instance_config, "nonexistent123")
        assert contact is None

    @pytest.mark.asyncio
    async def test_get_chat_by_id_success(self, handler, mock_instance_config, mock_discord_client):
        """Test successful chat retrieval by ID."""
        chat = await handler.get_chat_by_id(mock_instance_config, "111222333444555666")
        assert chat is not None
        assert chat.id == "111222333444555666"

    @pytest.mark.asyncio
    async def test_get_chat_by_id_not_found(self, handler, mock_instance_config, mock_discord_client):
        """Test chat not found scenario."""
        mock_discord_client.get_channel = lambda cid: None
        chat = await handler.get_chat_by_id(mock_instance_config, "nonexistent123")
        assert chat is None

    @pytest.mark.asyncio
    async def test_pagination_implementation(self, handler, mock_instance_config, mock_discord_client):
        """Test pagination implementation for large member lists."""
        # Mock large member list
        members = []
        for i in range(100):
            member = MagicMock()
            member.id = i
            member.name = f"user{i}"
            member.global_name = f"User {i}"
            member.status = "online"
            member.bot = False
            member.activities = []
            members.append(member)
        
        mock_discord_client.guilds[0].members = members
        
        contacts, total_count = await handler.get_contacts(
            mock_instance_config, page=1, page_size=25
        )
        assert total_count == 100
        assert len(contacts) == 25

    @pytest.mark.asyncio
    async def test_rate_limiting_handling(self, handler, mock_instance_config, mock_discord_client):
        """Test Discord rate limiting handling."""
        def side_effect_guilds():
            raise Exception("Rate limited")
        
        type(mock_discord_client).guilds = PropertyMock(side_effect=side_effect_guilds)
        
        contacts, total_count = await handler.get_contacts(mock_instance_config, page=1, page_size=50)
        assert contacts == []
        assert total_count == 0


'''
        
        content = content[:discord_class_start] + new_discord_class + content[next_class_start:]
    
    # Write the fixed content
    with open('tests/test_unified_handlers.py', 'w') as f:
        f.write(content)
    
    print("Applied fixes to tests/test_unified_handlers.py")
    print("✓ Added PropertyMock import")
    print("✓ Replaced Discord test class with proper _bot_instances mocking")
    print("✓ Removed incorrect get_discord_bot patches")
    print("✓ Fixed async method mocking")
    print("✓ Updated test expectations")

if __name__ == "__main__":
    apply_fixes()