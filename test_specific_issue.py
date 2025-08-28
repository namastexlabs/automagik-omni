#!/usr/bin/env python3
"""
Test specific issues to isolate the problems
"""
import os
import sys

# Set test environment first
os.environ["ENVIRONMENT"] = "test"
os.environ["AUTOMAGIK_OMNI_API_KEY"] = ""

# Add src to path
sys.path.insert(0, '/home/cezar/automagik/automagik-omni')

def test_basic_functionality():
    """Test basic functionality that might be failing"""
    try:
        print("=== TESTING BASIC IMPORTS ===")
        
        # Test 1: Basic schema imports
        from src.api.schemas.unified import ChannelType, UnifiedContactStatus
        print("✓ Schema imports work")
        
        # Test 2: Transformer imports 
        from src.services.unified_transformers import WhatsAppTransformer
        print("✓ Transformer imports work")
        
        # Test 3: Basic transformer functionality
        transformer = WhatsAppTransformer()
        test_contact = {
            "id": "5511999999999@c.us",
            "name": "Test Contact",
        }
        result = transformer.contact_to_unified(test_contact, "test-instance")
        print(f"✓ Transformer works: {result.name}")
        
        # Test 4: Handler imports
        from src.channels.handlers.whatsapp_chat_handler import WhatsAppChatHandler
        handler = WhatsAppChatHandler()
        print("✓ Handler instantiation works")
        
        print("\n=== ALL BASIC TESTS PASSED ===")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)