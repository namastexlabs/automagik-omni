#!/usr/bin/env python3
"""
Quick test to check if our Pydantic fixes work
"""

import sys
import os

# Add the source directory to path 
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from unittest.mock import MagicMock
from src.api.schemas.omni import OmniContact, ChannelType, OmniContactStatus

def test_discord_mock_validation():
    """Test if our Discord mock setup creates valid OmniContact objects."""
    print("Testing Discord mock validation...")
    
    # Create mock Discord user data like in our test
    mock_user = MagicMock()
    mock_user.id = 987654321098765432
    mock_user.name = "testuser"
    mock_user.username = "testuser"  # Our fix
    mock_user.global_name = "Test User"
    mock_user.discriminator = "0001"
    mock_user.status = "online"
    
    # Simulate what Discord handler does
    user_data = {
        "id": mock_user.id,
        "username": mock_user.name,  # This was causing issues
        "global_name": getattr(mock_user, 'global_name', None),
        "discriminator": getattr(mock_user, 'discriminator', None),
        "avatar": getattr(mock_user, 'avatar', None),
        "bot": getattr(mock_user, 'bot', False),
        "system": getattr(mock_user, 'system', False),
        "status": str(getattr(mock_user, 'status', 'unknown')),
        "activities": [],
        "verified": getattr(mock_user, 'verified', None)
    }
    
    print(f"User data: {user_data}")
    
    # Simulate what DiscordTransformer.contact_to_omni() does
    try:
        status_map = {
            "online": OmniContactStatus.ONLINE,
            "idle": OmniContactStatus.AWAY, 
            "dnd": OmniContactStatus.DND,
            "offline": OmniContactStatus.OFFLINE,
        }
        
        contact = OmniContact(
            id=str(user_data.get("id", "")),
            name=user_data.get("global_name") or user_data.get("username", "Unknown"),
            channel_type=ChannelType.DISCORD,
            instance_name="test-instance",
            status=status_map.get(user_data.get("status"), OmniContactStatus.UNKNOWN),
            channel_data={
                "username": user_data.get("username"),
                "discriminator": user_data.get("discriminator"),
                "global_name": user_data.get("global_name"),
            }
        )
        print(f"✓ Successfully created OmniContact: {contact.name}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create OmniContact: {e}")
        return False

def test_enum_values():
    """Test if enum values are correct."""
    print("\nTesting enum values...")
    
    # Test that ACTIVE doesn't exist (it was causing errors)
    try:
        active = OmniContactStatus.ACTIVE
        print(f"✗ ERROR: OmniContactStatus.ACTIVE should not exist but got {active}")
        return False
    except AttributeError:
        print("✓ Confirmed: OmniContactStatus.ACTIVE does not exist (good)")
    
    # Test that valid enum values exist
    valid_values = ["ONLINE", "OFFLINE", "AWAY", "DND", "UNKNOWN"]
    for value in valid_values:
        try:
            enum_val = getattr(OmniContactStatus, value)
            print(f"✓ {value}: {enum_val}")
        except AttributeError:
            print(f"✗ ERROR: Missing enum value {value}")
            return False
    
    return True

if __name__ == "__main__":
    print("Running Pydantic validation fix test...\n")
    
    success1 = test_discord_mock_validation()
    success2 = test_enum_values()
    
    if success1 and success2:
        print("\n🎉 All tests passed! Pydantic fixes should work.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the fixes.")
        sys.exit(1)