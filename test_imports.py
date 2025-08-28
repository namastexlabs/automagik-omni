#!/usr/bin/env python3
"""
Test basic imports to see what fails
"""

try:
    print("Testing basic imports...")
    
    print("1. Testing unified transformers import...")
    from src.services.unified_transformers import WhatsAppTransformer, DiscordTransformer
    print("   ✓ Transformer imports successful")
    
    print("2. Testing unified schemas import...")
    from src.api.schemas.unified import (
        ChannelType, UnifiedContactStatus, UnifiedChatType,
        UnifiedContact, UnifiedChat, UnifiedChannelInfo
    )
    print("   ✓ Schema imports successful")
    
    print("3. Testing handler imports...")
    from src.channels.handlers.whatsapp_chat_handler import WhatsAppChatHandler
    from src.channels.handlers.discord_chat_handler import DiscordChatHandler
    print("   ✓ Handler imports successful")
    
    print("4. Testing database models...")
    from src.db.models import InstanceConfig
    print("   ✓ Database model imports successful")
    
    print("\n✓ All imports successful!")
    
except Exception as e:
    print(f"\n✗ Import failed: {e}")
    import traceback
    traceback.print_exc()