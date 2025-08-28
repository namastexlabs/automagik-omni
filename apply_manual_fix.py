#!/usr/bin/env python3
"""Apply the fixes manually to the test files."""

import shutil
import os

def apply_fixes():
    """Apply all the necessary fixes to the test files."""
    
    # Read the original file
    with open("/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py", "r") as f:
        content = f.read()
    
    # Apply fixes
    print("Applying fixes...")
    
    # Fix 1: UnifiedContactStatus.ACTIVE -> ONLINE
    content = content.replace("UnifiedContactStatus.ACTIVE", "UnifiedContactStatus.ONLINE")
    print("✓ Fixed UnifiedContactStatus.ACTIVE -> ONLINE")
    
    # Fix 2: InstanceConfig parameter name
    content = content.replace("default_agent_name=", "default_agent=")
    print("✓ Fixed InstanceConfig parameter: default_agent_name -> default_agent")
    
    # Write back the fixed content
    with open("/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py", "w") as f:
        f.write(content)
    
    print("✅ Applied fixes to test_unified_endpoints.py")
    
    # Fix the transformers file
    fix_transformers()

def fix_transformers():
    """Fix the transformers file for better None handling."""
    transformer_file = "/home/cezar/automagik/automagik-omni/src/services/unified_transformers.py"
    
    with open(transformer_file, "r") as f:
        content = f.read()
    
    original_content = content
    
    # Improve WhatsApp name handling
    content = content.replace(
        'whatsapp_contact.get("pushName") or whatsapp_contact.get("name", "Unknown")',
        'whatsapp_contact.get("pushName") or whatsapp_contact.get("name") or "Unknown"'
    )
    
    # Improve phone number handling
    content = content.replace(
        'whatsapp_contact.get("id", "").replace("@c.us", "")',
        '(whatsapp_contact.get("id") or "").replace("@c.us", "")'
    )
    
    # Improve chat name handling  
    content = content.replace(
        'whatsapp_chat.get("name") or whatsapp_chat.get("pushName", "Unknown")',
        'whatsapp_chat.get("name") or whatsapp_chat.get("pushName") or "Unknown"'
    )
    
    if content != original_content:
        with open(transformer_file, "w") as f:
            f.write(content)
        print("✓ Improved WhatsApp transformer None handling")
    else:
        print("✓ WhatsApp transformer already has good None handling")

if __name__ == "__main__":
    apply_fixes()
    print("\n🎉 All fixes applied successfully!")
    print("\nFixed issues:")
    print("1. ✓ UnifiedContactStatus.ACTIVE -> ONLINE")
    print("2. ✓ InstanceConfig default_agent_name -> default_agent") 
    print("3. ✓ Improved WhatsApp transformer None handling")
    print("\n🧪 Tests should now pass!")