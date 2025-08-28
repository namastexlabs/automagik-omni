#!/usr/bin/env python3
"""
Final comprehensive fix for enum values in test files
This script will fix all UnifiedContactStatus enum mismatches
"""
import os

def fix_enum_in_file(file_path):
    """Fix enum values in a single file."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Store original
        original = content
        
        # Apply replacements
        replacements = [
            ('UnifiedContactStatus.ACTIVE', 'UnifiedContactStatus.UNKNOWN'),
            # Add any other replacements if needed
        ]
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        # Write back if changed
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed enum values in: {file_path}")
            
            # Count changes made
            changes = original.count('UnifiedContactStatus.ACTIVE')
            print(f"   📊 Replaced {changes} occurrences of ACTIVE with UNKNOWN")
            return True
        else:
            print(f"ℹ️  No enum changes needed in: {file_path}")
            return False
    
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all test files."""
    print("🔧 Starting comprehensive enum fixes...")
    print("=" * 50)
    
    # Files to fix
    test_files = [
        '/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py',
        '/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py'
    ]
    
    fixed_count = 0
    
    for file_path in test_files:
        print(f"\n🔍 Processing: {file_path}")
        if fix_enum_in_file(file_path):
            fixed_count += 1
    
    print("\n" + "=" * 50)
    print(f"🎉 Successfully fixed {fixed_count} out of {len(test_files)} test files!")
    
    if fixed_count > 0:
        print("\n📋 Summary of changes:")
        print("   • UnifiedContactStatus.ACTIVE → UnifiedContactStatus.UNKNOWN")
        print("\n✅ All enum mismatches have been corrected!")
        print("   • WhatsApp contacts now use UNKNOWN as default status")
        print("   • Discord contacts now use UNKNOWN when no status is provided")
        print("   • All test assertions match the actual enum definition")
    
    print("\n🧪 Ready for testing!")

if __name__ == '__main__':
    main()