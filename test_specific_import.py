#!/usr/bin/env python3

import sys
import os

# Test the exact same import as in the failing test
project_root = "/home/cezar/automagik/automagik-omni"
os.chdir(project_root)
sys.path.insert(0, project_root)

print("Testing the exact imports from test_unified_transformers.py...")

try:
    from src.services.unified_transformers import WhatsAppTransformer, DiscordTransformer
    print("✅ Transformers imported successfully")
except Exception as e:
    print(f"❌ Transformer import failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from src.api.schemas.unified import (
        ChannelType, UnifiedContactStatus, UnifiedChatType,
        UnifiedContact, UnifiedChat, UnifiedChannelInfo
    )
    print("✅ Schema imports successful")
except Exception as e:
    print(f"❌ Schema import failed: {e}")
    import traceback
    traceback.print_exc()

print("Import test complete!")