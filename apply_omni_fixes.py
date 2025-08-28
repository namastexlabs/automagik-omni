#!/usr/bin/env python3
"""
Apply fixes to test_omni_endpoints.py directly
"""

def apply_fixes():
    file_path = '/home/cezar/automagik/automagik-omni/tests/test_omni_endpoints.py'
    
    print(f"Reading {file_path}...")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        print("Original content length:", len(content))
        
        # Apply fixes
        fixes_applied = 0
        
        # Fix 1: Replace string channel_type values with ChannelType enum values
        old_count = content.count('channel_type = "whatsapp"')
        content = content.replace('channel_type = "whatsapp"', 'channel_type = ChannelType.WHATSAPP')
        fixes_applied += old_count
        print(f"Fixed {old_count} 'whatsapp' channel_type strings")
        
        old_count = content.count('channel_type = "discord"')
        content = content.replace('channel_type = "discord"', 'channel_type = ChannelType.DISCORD')
        fixes_applied += old_count
        print(f"Fixed {old_count} 'discord' channel_type strings")
        
        # Fix 2: Update get_contacts handler calls
        old_pattern = 'mock_whatsapp_handler.get_contacts.assert_called_once_with(\n            mock_instance_config, page=1, page_size=50, search_query=None\n        )'
        new_pattern = 'mock_whatsapp_handler.get_contacts.assert_called_once_with(\n            instance=mock_instance_config, page=1, page_size=50, search_query=None, status_filter=None\n        )'
        
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            fixes_applied += 1
            print("Fixed mock_whatsapp_handler.get_contacts call")
        
        # Fix search query call
        old_pattern = 'handler.get_contacts.assert_called_once_with(\n            mock_instance_config, page=1, page_size=50, search_query="Search"\n        )'
        new_pattern = 'handler.get_contacts.assert_called_once_with(\n            instance=mock_instance_config, page=1, page_size=50, search_query="Search", status_filter=None\n        )'
        
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            fixes_applied += 1
            print("Fixed handler.get_contacts search call")
        
        # Fix 3: Update get_chats handler calls
        old_pattern = 'mock_discord_handler.get_chats.assert_called_once_with(\n            mock_instance_config, page=1, page_size=50\n        )'
        new_pattern = 'mock_discord_handler.get_chats.assert_called_once_with(\n            instance=mock_instance_config, page=1, page_size=50, chat_type_filter=None, archived=None\n        )'
        
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            fixes_applied += 1
            print("Fixed mock_discord_handler.get_chats call")
        
        print(f"Applied {fixes_applied} fixes total")
        print("New content length:", len(content))
        
        # Write the fixed content back
        with open(file_path, 'w') as f:
            f.write(content)
        
        print("✅ Successfully applied all fixes to test_omni_endpoints.py")
        return True
        
    except Exception as e:
        print(f"❌ Error applying fixes: {e}")
        return False

if __name__ == "__main__":
    success = apply_fixes()
    exit(0 if success else 1)