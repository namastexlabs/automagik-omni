#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

print("Testing schemas import...")

try:
    from src.api.schemas.unified import (
        ChannelType, UnifiedContactStatus, UnifiedChatType,
        UnifiedContact, UnifiedChat, UnifiedChannelInfo
    )
    print("✅ All schema imports successful")
    
    # Test creating instances
    contact = UnifiedContact(
        id="test",
        name="Test Contact",
        instance_name="test-instance",
        channel_type=ChannelType.WHATSAPP,
        status=UnifiedContactStatus.ACTIVE,
        channel_data={}
    )
    print("✅ UnifiedContact instance created successfully")
    
except Exception as e:
    import traceback
    print(f"❌ Schema import failed: {e}")
    print("Full traceback:")
    print(traceback.format_exc())
    
print("Test complete")