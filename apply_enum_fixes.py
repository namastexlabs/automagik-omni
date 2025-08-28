#!/usr/bin/env python3
"""Apply enum fixes to test files"""

import os

# Files to fix and their content
files_to_fix = [
    "/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py",
    "/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py"
]

for file_path in files_to_fix:
    if os.path.exists(file_path):
        # Read content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply replacements
        original_content = content
        content = content.replace('UnifiedContactStatus.ACTIVE', 'UnifiedContactStatus.UNKNOWN')
        
        if content != original_content:
            # Write back the fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {file_path}")
        else:
            print(f"No changes needed in {file_path}")
    else:
        print(f"File not found: {file_path}")

print("Enum fixes completed!")