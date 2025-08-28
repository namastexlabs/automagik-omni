#!/usr/bin/env python3
"""
Basic test verification to check imports and basic functionality.
"""
import sys
import os
import traceback

# Add the source path
sys.path.insert(0, "/home/cezar/automagik/automagik-omni/src")
os.chdir("/home/cezar/automagik/automagik-omni")

print("Testing basic imports and functionality...")

try:
    # Test basic imports
    print("1. Testing environment setup...")
    os.environ["ENVIRONMENT"] = "test"
    os.environ["AUTOMAGIK_OMNI_API_KEY"] = ""
    print("   Environment set up successfully")

    print("2. Testing imports...")
    # Import schemas first
    from src.api.schemas.omni import OmniContact, OmniChat, OmniChannelInfo, ChannelType, OmniContactStatus, OmniChatType
    print("   Schemas imported successfully")
    
    # Import models
    from src.db.models import InstanceConfig
    print("   Models imported successfully")
    
    print("3. Testing schema creation...")
    # Test creating a basic OmniContact
    contact = OmniContact(
        id="test-id",
        name="Test Contact",
        channel_type=ChannelType.WHATSAPP,
        instance_name="test-instance",
        status=OmniContactStatus.ONLINE
    )
    print(f"   Created OmniContact: {contact.id} - {contact.name}")
    
    # Test creating a basic OmniChat
    chat = OmniChat(
        id="test-chat-id",
        name="Test Chat",
        chat_type=OmniChatType.DIRECT,
        channel_type=ChannelType.WHATSAPP,
        instance_name="test-instance"
    )
    print(f"   Created OmniChat: {chat.id} - {chat.name}")
    
    # Test creating a basic OmniChannelInfo
    channel_info = OmniChannelInfo(
        instance_name="test-instance",
        channel_type=ChannelType.WHATSAPP,
        display_name="Test Instance",
        status="connected",
        is_healthy=True
    )
    print(f"   Created OmniChannelInfo: {channel_info.instance_name}")
    
    print("4. Testing route imports...")
    from src.api.routes.omni import router, get_omni_handler
    print("   Route imports successful")
    
    print("5. Testing app creation...")
    from src.api.app import app
    print("   App creation successful")
    
    print("\n✅ All basic checks passed!")
    
    # Now let's test the actual failing test components
    print("\n6. Testing test fixtures...")
    from unittest.mock import AsyncMock, MagicMock, patch
    from fastapi.testclient import TestClient
    
    # Create test client
    client = TestClient(app)
    print("   Test client created successfully")
    
    # Test basic endpoint access
    print("7. Testing basic endpoint access...")
    response = client.get("/health", timeout=10)
    print(f"   Health check response: {response.status_code}")
    
    print("\n✅ Test infrastructure is working!")
    
except Exception as e:
    print(f"\n❌ Error occurred: {e}")
    print(f"   Error type: {type(e).__name__}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)