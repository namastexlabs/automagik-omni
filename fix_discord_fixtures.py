#!/usr/bin/env python3
"""
Fix Discord test fixture issues by removing mock_get_bot parameters 
from function signatures where the corresponding fixtures don't exist.
"""

import re
import sys


def fix_discord_fixtures(file_path):
    """Fix Discord test fixture issues."""
    print(f"Fixing Discord fixtures in {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to find test functions with mock_get_bot parameter
    pattern = r'(\s+async def test_[^(]+\(\s*)(self,\s+mock_get_bot,\s+)([^)]+\)):'
    
    matches = re.findall(pattern, content)
    print(f"Found {len(matches)} functions with mock_get_bot parameter")
    
    if matches:
        # Replace the pattern by removing mock_get_bot parameter
        new_content = re.sub(pattern, r'\1\2\3):', content)
        # Now fix the replacement to remove the mock_get_bot properly
        new_content = re.sub(r'(\s+async def test_[^(]+\(\s*)(self,\s+mock_get_bot,\s+)', r'\1self, ', new_content)
        
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        print("✓ Fixed all Discord test function signatures")
        return True
    else:
        print("✗ No Discord fixture issues found")
        return False


def main():
    test_file = "tests/test_unified_handlers.py"
    
    try:
        success = fix_discord_fixtures(test_file)
        if success:
            print("\n✅ Discord fixture issues have been fixed!")
            print("The test functions no longer reference mock_get_bot parameters.")
        else:
            print("\n⚠️  No issues found to fix")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()