#!/usr/bin/env python3
"""
Mimic exactly how pytest would run the test imports
"""
import os
import sys
import importlib.util

# Change to project directory like pytest does
project_root = "/home/cezar/automagik/automagik-omni"
os.chdir(project_root)

# Add project root to path if not already there (pytest does this)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=== PYTEST IMPORT SIMULATION ===")
print(f"Working directory: {os.getcwd()}")
print(f"Project root in sys.path: {project_root in sys.path}")

# Test the exact import sequence from test_unified_transformers.py
print("\nTesting imports in the same order as test_unified_transformers.py:")

imports_to_test = [
    ("import pytest", lambda: __import__("pytest")),
    ("from datetime import datetime", lambda: __import__("datetime", fromlist=["datetime"])),
    ("from typing import Dict, Any", lambda: __import__("typing", fromlist=["Dict", "Any"])),
    ("from src.services.unified_transformers import WhatsAppTransformer, DiscordTransformer", 
     lambda: __import__("src.services.unified_transformers", fromlist=["WhatsAppTransformer", "DiscordTransformer"])),
    ("from src.api.schemas.unified import schemas", 
     lambda: __import__("src.api.schemas.unified", fromlist=["ChannelType", "UnifiedContactStatus", "UnifiedChatType", "UnifiedContact", "UnifiedChat", "UnifiedChannelInfo"])),
]

for description, import_func in imports_to_test:
    try:
        import_func()
        print(f"✅ {description}")
    except Exception as e:
        print(f"❌ {description}: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

# Additional diagnostics
print("\n=== DIAGNOSTICS ===")
print(f"src module location: {importlib.util.find_spec('src')}")
print(f"src.services module location: {importlib.util.find_spec('src.services') if importlib.util.find_spec('src') else 'src not found'}")
print(f"src.api.schemas module location: {importlib.util.find_spec('src.api.schemas') if importlib.util.find_spec('src.api') else 'src.api not found'}")

print("\n=== TEST COMPLETE ===")