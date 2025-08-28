#!/usr/bin/env python3
"""
Fix UnifiedContactStatus enum values in test files.
Replace incorrect enum values with correct ones.
"""
import re

files_to_fix = [
    '/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py',
    '/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py'
]

# Replacements to make
replacements = [
    (r'UnifiedContactStatus\.ACTIVE', 'UnifiedContactStatus.UNKNOWN'),
]

for file_path in files_to_fix:
    print(f"Fixing {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ Fixed {file_path}")
    else:
        print(f"  ℹ️  No changes needed in {file_path}")

print("Done!")