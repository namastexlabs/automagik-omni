#!/usr/bin/env python3
"""Test script to verify the import fix"""

import sys
import os

# Add the project root to Python path
project_root = "/home/cezar/automagik/automagik-omni"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("Testing the fixed import approach:")

try:
    from src.api.routes import messages
    print("✓ Successfully imported messages module")
    print("  Has _resolve_recipient:", hasattr(messages, '_resolve_recipient'))
    
    # Test the patch approach
    from unittest.mock import patch
    print("✓ unittest.mock imported")
    
    # Test if patch.object works
    with patch.object(messages, '_resolve_recipient', return_value="test") as mock_resolve:
        result = messages._resolve_recipient(None, None, None)
        print("✓ patch.object works, mock returned:", result)
        print("✓ Mock was called:", mock_resolve.called)
    
    print("\n🎉 Import fix appears to be working!")
    
except Exception as e:
    print("✗ Error:", e)
    import traceback
    traceback.print_exc()