#!/usr/bin/env python3

import sys
import os

# Add project root to Python path
project_root = "/home/cezar/automagik/automagik-omni"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"Python path: {sys.path[:3]}")  # Show first 3 entries
print(f"Working directory: {os.getcwd()}")

# Test 1: Basic import
print("\n=== TEST 1: Basic imports ===")
try:
    print("Attempting src.services.unified_transformers import...")
    from src.services.unified_transformers import WhatsAppTransformer, DiscordTransformer
    print("✅ SUCCESS: unified_transformers imported")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    print(traceback.format_exc())

# Test 2: Schemas import  
print("\n=== TEST 2: Schemas import ===")
try:
    print("Attempting src.api.schemas.unified import...")
    from src.api.schemas.unified import (
        ChannelType, UnifiedContactStatus, UnifiedChatType,
        UnifiedContact, UnifiedChat, UnifiedChannelInfo
    )
    print("✅ SUCCESS: unified schemas imported")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    print(traceback.format_exc())

# Test 3: Test if we can create instances
print("\n=== TEST 3: Create instances ===")
try:
    transformer = WhatsAppTransformer()
    print("✅ SUCCESS: WhatsAppTransformer instantiated")
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 4: Check what files exist
print("\n=== TEST 4: File existence checks ===")
files_to_check = [
    "src/services/unified_transformers.py",
    "src/api/schemas/unified.py",
    "src/services/__init__.py",
    "src/api/schemas/__init__.py",
    "src/api/__init__.py",
    "src/__init__.py"
]

for file_path in files_to_check:
    full_path = os.path.join(project_root, file_path)
    exists = os.path.exists(full_path)
    print(f"{'✅' if exists else '❌'} {file_path}: {'EXISTS' if exists else 'MISSING'}")

print("\n=== TEST COMPLETE ===")