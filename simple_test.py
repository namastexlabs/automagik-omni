#!/usr/bin/env python3
"""
Simple test to verify imports work exactly like in the test files
"""
import os
import sys

# Change to project directory like pytest would
os.chdir("/home/cezar/automagik/automagik-omni")

# Test the exact imports from the test files
print("Testing imports from test_unified_transformers.py...")

try:
    # This is the exact import from the failing test
    from src.services.unified_transformers import WhatsAppTransformer, DiscordTransformer
    print("✅ SUCCESS: WhatsAppTransformer, DiscordTransformer imported")
    
    # Test that we can access their methods  
    print(f"WhatsAppTransformer.contact_to_unified exists: {hasattr(WhatsAppTransformer, 'contact_to_unified')}")
    print(f"DiscordTransformer.contact_to_unified exists: {hasattr(DiscordTransformer, 'contact_to_unified')}")
    
except ImportError as e:
    print(f"❌ IMPORT ERROR: {e}")
except Exception as e:
    print(f"❌ OTHER ERROR: {e}")
    import traceback
    traceback.print_exc()

try:
    # This is the exact import from the failing test
    from src.api.schemas.unified import (
        ChannelType, UnifiedContactStatus, UnifiedChatType,
        UnifiedContact, UnifiedChat, UnifiedChannelInfo
    )
    print("✅ SUCCESS: All unified schema classes imported")
    
except ImportError as e:
    print(f"❌ SCHEMA IMPORT ERROR: {e}")
except Exception as e:
    print(f"❌ SCHEMA OTHER ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\nTest complete!")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path contains: {'/home/cezar/automagik/automagik-omni' in sys.path}")