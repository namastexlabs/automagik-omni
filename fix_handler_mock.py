#!/usr/bin/env python3
"""
Fix the handler mock configuration specifically.
"""

# Read the file
with open("/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py", 'r') as f:
    content = f.read()

# Fix profilePicture -> profilePictureUrl
content = content.replace('"profilePicture":', '"profilePictureUrl":')

# Fix the mock configuration
old_config = '''        config.config = {
            "evolution_api_url": "https://api.evolution.test",
            "evolution_api_key": "test-api-key-123"
        }'''

new_config = '''        config.evolution_url = "https://api.evolution.test"
        config.evolution_key = "test-api-key-123"
        config.config = {}'''

content = content.replace(old_config, new_config)

# Write the file back
with open("/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py", 'w') as f:
    f.write(content)

print("Fixed handler test mock configuration!")