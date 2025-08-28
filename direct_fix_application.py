#!/usr/bin/env python3

# Direct fix application
def apply_immediate_fix():
    file_path = '/home/cezar/automagik/automagik-omni/tests/test_omni_endpoints.py'
    
    # Read file
    with open(file_path, 'r') as f:
        content = f.read()
    
    print(f"Original file size: {len(content)} characters")
    
    # Count occurrences before fixing
    whatsapp_strings = content.count('channel_type = "whatsapp"')
    discord_strings = content.count('channel_type = "discord"')
    
    print(f"Found {whatsapp_strings} 'whatsapp' strings to fix")
    print(f"Found {discord_strings} 'discord' strings to fix")
    
    # Apply fixes
    content = content.replace('channel_type = "whatsapp"', 'channel_type = ChannelType.WHATSAPP')
    content = content.replace('channel_type = "discord"', 'channel_type = ChannelType.DISCORD')
    
    # Fix handler method calls
    fixes = [
        (
            'mock_whatsapp_handler.get_contacts.assert_called_once_with(\n            mock_instance_config, page=1, page_size=50, search_query=None\n        )',
            'mock_whatsapp_handler.get_contacts.assert_called_once_with(\n            instance=mock_instance_config, page=1, page_size=50, search_query=None, status_filter=None\n        )'
        ),
        (
            'handler.get_contacts.assert_called_once_with(\n            mock_instance_config, page=1, page_size=50, search_query="Search"\n        )',
            'handler.get_contacts.assert_called_once_with(\n            instance=mock_instance_config, page=1, page_size=50, search_query="Search", status_filter=None\n        )'
        ),
        (
            'mock_discord_handler.get_chats.assert_called_once_with(\n            mock_instance_config, page=1, page_size=50\n        )',
            'mock_discord_handler.get_chats.assert_called_once_with(\n            instance=mock_instance_config, page=1, page_size=50, chat_type_filter=None, archived=None\n        )'
        )
    ]
    
    method_fixes_applied = 0
    for old_pattern, new_pattern in fixes:
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            method_fixes_applied += 1
            print(f"✅ Applied method call fix: {old_pattern[:50]}...")
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Applied {whatsapp_strings + discord_strings + method_fixes_applied} total fixes")
    print("✅ File updated successfully!")
    
    # Verify
    with open(file_path, 'r') as f:
        new_content = f.read()
    
    enum_count = new_content.count('ChannelType.WHATSAPP') + new_content.count('ChannelType.DISCORD')
    print(f"✅ Verification: Found {enum_count} ChannelType enum references")

# Execute the fix
apply_immediate_fix()