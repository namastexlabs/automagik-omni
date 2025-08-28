#!/usr/bin/env python3
"""
Manual fix for enum values in test files
This creates corrected versions of the files by doing string replacements
"""
import sys

def fix_file(file_path):
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Track original content
        original = content
        
        # Apply all the fixes
        fixes = [
            ('UnifiedContactStatus.ACTIVE', 'UnifiedContactStatus.UNKNOWN'),
        ]
        
        for old, new in fixes:
            content = content.replace(old, new)
        
        # Write back if changed
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed: {file_path}")
            return True
        else:
            print(f"ℹ️  No changes: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

# Fix the files
files = [
    '/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py',
    '/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py'
]

total_fixed = 0
for file_path in files:
    if fix_file(file_path):
        total_fixed += 1

print(f"\n🎉 Successfully fixed {total_fixed} files!")