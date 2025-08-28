#!/usr/bin/env python3
"""
Final verification test to ensure all imports work and basic functionality operates
"""
import os
import sys

# Change to project directory
os.chdir("/home/cezar/automagik/automagik-omni")

print("=== FINAL VERIFICATION TEST ===")
print(f"Working directory: {os.getcwd()}")
print(f"Python version: {sys.version}")

# Test 1: Import transformers
print("\n1. Testing transformer imports...")
try:
    from src.services.unified_transformers import WhatsAppTransformer, DiscordTransformer
    print("✅ Transformers imported successfully")
    
    # Test transformer methods exist
    whatsapp_methods = [method for method in dir(WhatsAppTransformer) if not method.startswith('_')]
    discord_methods = [method for method in dir(DiscordTransformer) if not method.startswith('_')]
    
    print(f"   WhatsApp methods: {whatsapp_methods}")
    print(f"   Discord methods: {discord_methods}")
    
except Exception as e:
    print(f"❌ Transformer import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Import schemas
print("\n2. Testing schema imports...")
try:
    from src.api.schemas.unified import (
        ChannelType, UnifiedContactStatus, UnifiedChatType,
        UnifiedContact, UnifiedChat, UnifiedChannelInfo
    )
    print("✅ All schema classes imported successfully")
    
    # Test enum values
    print(f"   ChannelType options: {[e.value for e in ChannelType]}")
    print(f"   UnifiedContactStatus options: {[e.value for e in UnifiedContactStatus]}")
    
except Exception as e:
    print(f"❌ Schema import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Create a sample transformer operation
print("\n3. Testing basic transformer functionality...")
try:
    # Create a sample WhatsApp contact data
    sample_whatsapp_contact = {
        "id": "5511999999999@c.us",
        "name": "Test Contact",
        "profilePicture": "https://example.com/avatar.jpg",
        "lastSeen": 1640995200000,
        "isGroup": False,
        "status": "active"
    }
    
    # Transform it
    unified_contact = WhatsAppTransformer.contact_to_unified(sample_whatsapp_contact, "test-instance")
    print("✅ WhatsApp contact transformation successful")
    print(f"   Result: {unified_contact.id}, {unified_contact.name}, {unified_contact.instance_name}")
    
except Exception as e:
    print(f"❌ Transformer functionality test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Verify CORS config imports
print("\n4. Testing config imports...")
try:
    from src.config import config
    print("✅ Config imported successfully")
    print(f"   CORS origins: {config.cors.allowed_origins}")
    print(f"   CORS credentials: {config.cors.allow_credentials}")
    
except Exception as e:
    print(f"❌ Config import failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== VERIFICATION COMPLETE ===")