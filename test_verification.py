#!/usr/bin/env python3
"""
Quick verification script to test if the fixed unified_transformers tests pass.
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/cezar/automagik/automagik-omni')

from datetime import datetime
from src.services.unified_transformers import WhatsAppTransformer, DiscordTransformer
from src.api.schemas.unified import (
    ChannelType, UnifiedContactStatus, UnifiedChatType,
    UnifiedContact, UnifiedChat, UnifiedChannelInfo
)

def test_whatsapp_basic():
    """Test basic WhatsApp functionality."""
    print("Testing WhatsApp transformer...")
    
    # Test with None input
    contact = WhatsAppTransformer.contact_to_unified(None, "test-instance")
    assert contact.id == "unknown"
    assert contact.name == "Unknown"
    print("✓ WhatsApp None input handling works")
    
    # Test contact transformation
    whatsapp_contact = {
        "id": "5511999999999@c.us",
        "name": "Test Contact",
        "profilePictureUrl": "https://example.com/avatar.jpg",
        "lastSeen": 1640995200000,
    }
    
    contact = WhatsAppTransformer.contact_to_unified(whatsapp_contact, "test-instance")
    assert contact.id == "5511999999999@c.us"
    assert contact.name == "Test Contact"
    assert contact.channel_data["phone_number"] == "5511999999999"
    print("✓ WhatsApp contact transformation works")

def test_discord_basic():
    """Test basic Discord functionality."""
    print("Testing Discord transformer...")
    
    # Test Discord contact with global_name
    discord_user = {
        "id": "987654321098765432",
        "username": "testuser",
        "discriminator": "1234",
        "global_name": "Test User",
        "avatar": "a1b2c3d4e5f6",
        "status": "online",
    }
    
    contact = DiscordTransformer.contact_to_unified(discord_user, "test-discord")
    assert contact.id == "987654321098765432"
    assert contact.name == "Test User"  # Should use global_name
    assert contact.status == UnifiedContactStatus.ONLINE  # online maps to ONLINE
    print("✓ Discord contact transformation works")
    
    # Test Discord channel type mapping
    discord_channel = {
        "id": "123456789012345678",
        "name": "general",
        "type": 5,  # Guild text channel
        "guild_id": "987654321098765432",
    }
    
    chat = DiscordTransformer.chat_to_unified(discord_channel, "test-discord")
    assert chat.chat_type == UnifiedChatType.CHANNEL  # Type 5 maps to CHANNEL
    print("✓ Discord channel type mapping works")

def test_datetime_parsing():
    """Test datetime parsing functionality."""
    print("Testing datetime parsing...")
    
    # Test WhatsApp millisecond timestamp
    result = WhatsAppTransformer._parse_datetime(1640995200000)
    expected = datetime.fromtimestamp(1640995200)
    assert result == expected
    print("✓ WhatsApp datetime parsing works")
    
    # Test None values
    assert WhatsAppTransformer._parse_datetime(None) is None
    assert WhatsAppTransformer._parse_datetime("") is None
    print("✓ Invalid datetime handling works")

if __name__ == "__main__":
    try:
        test_whatsapp_basic()
        test_discord_basic()
        test_datetime_parsing()
        print("\n🎉 All basic functionality tests passed!")
        print("The fixed test file should now work correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)