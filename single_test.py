#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

print("Testing single import...")

try:
    # Test the exact import that's failing
    from src.services.unified_transformers import WhatsAppTransformer, DiscordTransformer
    print("✅ Transformers imported successfully")
    
    # Test creating a transformer
    transformer = WhatsAppTransformer()
    print("✅ WhatsAppTransformer instantiated successfully")
    
    # Test the method exists
    print(f"✅ contact_to_unified method exists: {hasattr(WhatsAppTransformer, 'contact_to_unified')}")
    
except Exception as e:
    import traceback
    print(f"❌ Import failed: {e}")
    print("Full traceback:")
    print(traceback.format_exc())
    
print("Test complete")