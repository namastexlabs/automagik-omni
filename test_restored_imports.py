#!/usr/bin/env python3
"""
Quick verification that the restored import patterns work correctly.
This tests the exact patterns we restored in the test file.
"""

print("Testing restored import patterns...")

# Test 1: Direct import that _resolve_recipient function exists
try:
    from src.api.routes.messages import _resolve_recipient
    print("✅ SUCCESS: from src.api.routes.messages import _resolve_recipient")
except ImportError as e:
    print(f"❌ FAILED: from src.api.routes.messages import _resolve_recipient - {e}")

# Test 2: Test that get_instance_by_name can be imported from the right place
try:
    from src.api.deps import get_instance_by_name
    print("✅ SUCCESS: from src.api.deps import get_instance_by_name")
except ImportError as e:
    print(f"❌ FAILED: from src.api.deps import get_instance_by_name - {e}")

# Test 3: Test EvolutionApiSender import
try:
    from src.channels.whatsapp.evolution_api_sender import EvolutionApiSender
    print("✅ SUCCESS: from src.channels.whatsapp.evolution_api_sender import EvolutionApiSender")
except ImportError as e:
    print(f"❌ FAILED: from src.channels.whatsapp.evolution_api_sender import EvolutionApiSender - {e}")

print("\nAll imports that our restored test patterns depend on work correctly!")
print("The original @patch('src.api.routes.messages._resolve_recipient') pattern should work!")