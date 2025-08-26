#!/usr/bin/env python3
"""Verify the import fix works"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("Verifying import fix...")

success = True

try:
    # Test the import approach used in the fixed test
    from src.api.routes import messages
    print("✓ Successfully imported messages module")
    
    # Verify the function exists
    if hasattr(messages, '_resolve_recipient'):
        print("✓ _resolve_recipient function exists in messages module")
    else:
        print("✗ _resolve_recipient function NOT found in messages module")
        success = False
    
    # Test mock approach
    from unittest.mock import patch
    with patch.object(messages, '_resolve_recipient', return_value="mock_success") as mock_fn:
        # Call the function to see if mock works
        result = messages._resolve_recipient(None, None, None)
        if result == "mock_success" and mock_fn.called:
            print("✓ Mocking with patch.object works correctly")
        else:
            print("✗ Mocking failed")
            success = False
            
except Exception as e:
    print(f"✗ Import test failed: {e}")
    success = False

if success:
    print("\n🎉 Import fix verification PASSED! The test should now work.")
else:
    print("\n❌ Import fix verification FAILED. Need to investigate further.")

sys.exit(0 if success else 1)