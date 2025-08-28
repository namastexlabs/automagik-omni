#!/usr/bin/env python3
import sys
import os

# Direct execution to fix the files
files_to_fix = [
    "/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py",
    "/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py"
]

for file_path in files_to_fix:
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Apply the fix
        fixed_content = content.replace('UnifiedContactStatus.ACTIVE', 'UnifiedContactStatus.UNKNOWN')
        
        # Write it back
        with open(file_path, 'w') as f:
            f.write(fixed_content)
            
        print(f"Fixed: {file_path}")
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")

print("Enum fixes applied!")

# Now let's run this immediately
if __name__ == "__main__":
    exec(open(__file__).read())