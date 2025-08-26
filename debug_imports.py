#!/usr/bin/env python3
"""Debug script to test imports"""

import sys
import os

# Add the project root to Python path
project_root = "/home/cezar/automagik/automagik-omni"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("Python path:", sys.path[:3])
print("Current working directory:", os.getcwd())

# Test various import patterns
try:
    print("Testing: import src")
    import src
    print("✓ src imported successfully")
except Exception as e:
    print("✗ Failed to import src:", e)

try:
    print("Testing: import src.api")
    import src.api
    print("✓ src.api imported successfully")
except Exception as e:
    print("✗ Failed to import src.api:", e)

try:
    print("Testing: import src.api.routes")
    import src.api.routes
    print("✓ src.api.routes imported successfully")
except Exception as e:
    print("✗ Failed to import src.api.routes:", e)

try:
    print("Testing: import src.api.routes.messages")
    import src.api.routes.messages
    print("✓ src.api.routes.messages imported successfully")
    print("  Messages module has _resolve_recipient:", hasattr(src.api.routes.messages, '_resolve_recipient'))
except Exception as e:
    print("✗ Failed to import src.api.routes.messages:", e)

try:
    print("Testing: from src.api.routes.messages import _resolve_recipient")
    from src.api.routes.messages import _resolve_recipient
    print("✓ _resolve_recipient imported successfully")
except Exception as e:
    print("✗ Failed to import _resolve_recipient:", e)

# Test accessing via attribute chain
try:
    print("Testing: src.api.routes.messages after importing")
    import src.api.routes.messages
    print("  src.api.routes:", dir(src.api.routes))
    print("  hasattr(src.api.routes, 'messages'):", hasattr(src.api.routes, 'messages'))
except Exception as e:
    print("✗ Error testing attribute access:", e)