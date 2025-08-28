#!/usr/bin/env python3

# Make the minimal essential fix
with open('tests/test_unified_transformers.py', 'r') as f:
    content = f.read()

# The most important fix - change display_name to global_name
if '"display_name": "Test User",' in content:
    content = content.replace('"display_name": "Test User",', '"global_name": "Test User",')
    print("✓ Fixed: display_name -> global_name")
else:
    print("✗ display_name not found")

if '"display_name": "No Avatar User",' in content:
    content = content.replace('"display_name": "No Avatar User",', '"global_name": "No Avatar User",')
    print("✓ Fixed: display_name -> global_name (avatar test)")
else:
    print("✗ display_name (avatar) not found")

# Write back
with open('tests/test_unified_transformers.py', 'w') as f:
    f.write(content)

print("Minimal fix applied!")

# Quick test
test_cmd = """
import sys, os
sys.path.insert(0, 'src')
try:
    from services.unified_transformers import DiscordTransformer
    user = {"id": "123", "username": "test", "global_name": "Test", "status": "online"}
    result = DiscordTransformer.contact_to_unified(user, "test")
    print(f"Test successful: {result.name}, {result.status}")
except Exception as e:
    print(f"Test failed: {e}")
"""

exec(test_cmd)