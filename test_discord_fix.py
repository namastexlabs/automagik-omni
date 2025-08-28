#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test if we can import the modules
try:
    from services.unified_transformers import DiscordTransformer
    from api.schemas.unified import UnifiedContact, UnifiedContactStatus, ChannelType
    print("✓ Imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test the actual transformation with correct data format
discord_user = {
    "id": "987654321098765432",
    "username": "testuser",
    "discriminator": "1234", 
    "global_name": "Test User",  # Correct field name
    "avatar": "a1b2c3d4e5f6",
    "status": "online"
}

try:
    contact = DiscordTransformer.contact_to_unified(discord_user, "test-discord")
    print("✓ Transformation successful")
    print(f"  Name: {contact.name}")
    print(f"  Status: {contact.status}")
    print(f"  Channel data keys: {list(contact.channel_data.keys())}")
    print(f"  Avatar URL: {contact.avatar_url}")
    
    # Test status mapping
    for status in ["online", "idle", "dnd", "offline", "invisible"]:
        test_user = {"id": "123", "username": "test", "status": status}
        result = DiscordTransformer.contact_to_unified(test_user, "test")
        print(f"  Status '{status}' -> {result.status}")
        
except Exception as e:
    print(f"✗ Transformation error: {e}")
    import traceback
    traceback.print_exc()