#!/usr/bin/env python3
"""Direct application of test fixes without subprocess calls."""

import os

def fix_unified_endpoints_test():
    """Fix the unified endpoints test file directly."""
    file_path = "/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py"
    
    print(f"Fixing {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: UnifiedContactStatus.ACTIVE -> ONLINE
    content = content.replace("UnifiedContactStatus.ACTIVE", "UnifiedContactStatus.ONLINE")
    
    # Fix 2: InstanceConfig parameter name
    content = content.replace("default_agent_name=", "default_agent=")
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✓ Fixed unified endpoints test")

def fix_unified_handlers_test():
    """Fix the unified handlers test file."""
    file_path = "/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py"
    
    if os.path.exists(file_path):
        print(f"Fixing {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix: Remove get_discord_bot patches
        lines = content.split('\n')
        fixed_lines = []
        skip_next_def = False
        
        for i, line in enumerate(lines):
            # Skip @patch lines for get_discord_bot
            if "@patch('src.channels.handlers.discord_chat_handler.get_discord_bot')" in line:
                continue
                
            # Fix function definitions that had mock_get_bot parameter
            if line.strip().startswith('def test_') and 'mock_get_bot' in line:
                line = line.replace(', mock_get_bot', '')
                line = line.replace('(self, mock_get_bot,', '(self,')
                
            # Skip mock_get_bot.return_value assignments
            if 'mock_get_bot.return_value' in line:
                continue
                
            fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print("✓ Fixed unified handlers test")

def fix_discord_transformer():
    """Fix potential Discord transformer issues."""
    file_path = "/home/cezar/automagik/automagik-omni/src/services/unified_transformers.py"
    
    if os.path.exists(file_path):
        print(f"Checking Discord transformer in {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for the potential issue where a dict is used as a dict key
        # The issue is likely in channel_data where channel_type (a dict) might be used as a key
        
        # Check if there's a problematic pattern
        original_content = content
        
        # Fix potential issue where channel_type dict is used as a dict key
        # Find and fix the Discord chat_to_unified method
        if '"type": channel_type' in content:
            # This suggests channel_type is being used as a value, which is correct
            pass
        
        # Check for actual problematic usage patterns
        if 'channel_type: channel_type' in content:
            # This would be problematic if channel_type is a dict
            content = content.replace('channel_type: channel_type', '"discord_channel_type": channel_type')
        
        # Ensure better error handling for Discord API calls
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print("✓ Fixed Discord transformer")
        else:
            print("✓ Discord transformer looks good")

def fix_whatsapp_transformer():
    """Improve WhatsApp transformer None handling."""
    file_path = "/home/cezar/automagik/automagik-omni/src/services/unified_transformers.py"
    
    if os.path.exists(file_path):
        print(f"Improving WhatsApp transformer None handling")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Improve name handling to prevent None concatenation issues
        old_name_pattern = 'whatsapp_contact.get("pushName") or whatsapp_contact.get("name", "Unknown")'
        new_name_pattern = 'whatsapp_contact.get("pushName") or whatsapp_contact.get("name") or "Unknown"'
        
        content = content.replace(old_name_pattern, new_name_pattern)
        
        # Improve phone number extraction to handle None
        old_phone_pattern = 'whatsapp_contact.get("id", "").replace("@c.us", "")'
        new_phone_pattern = '(whatsapp_contact.get("id") or "").replace("@c.us", "")'
        
        content = content.replace(old_phone_pattern, new_phone_pattern)
        
        # Improve chat name handling
        old_chat_name = 'whatsapp_chat.get("name") or whatsapp_chat.get("pushName", "Unknown")'
        new_chat_name = 'whatsapp_chat.get("name") or whatsapp_chat.get("pushName") or "Unknown"'
        
        content = content.replace(old_chat_name, new_chat_name)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print("✓ Improved WhatsApp None handling")

def main():
    """Apply all fixes."""
    print("🔧 Applying test fixes directly...")
    
    fix_unified_endpoints_test()
    fix_unified_handlers_test()
    fix_discord_transformer()
    fix_whatsapp_transformer()
    
    print("\n✅ All fixes applied!")
    print("Fixed issues:")
    print("1. ✓ UnifiedContactStatus.ACTIVE -> ONLINE")
    print("2. ✓ InstanceConfig default_agent_name -> default_agent")
    print("3. ✓ Removed get_discord_bot patches from handlers test")
    print("4. ✓ Checked Discord transformer for dict key issues")
    print("5. ✓ Improved WhatsApp None handling")

if __name__ == "__main__":
    main()