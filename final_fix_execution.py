#!/usr/bin/env python3

# Execute fix inline
def apply_fix():
    test_file = '/home/cezar/automagik/automagik-omni/tests/test_omni_endpoints.py'
    
    # Read file
    with open(test_file, 'r') as f:
        content = f.read()
    
    print(f"Reading {test_file} ({len(content):,} chars)")
    
    # Apply fixes
    changes = 0
    
    # Fix channel_type strings
    old_whatsapp = content.count('channel_type = "whatsapp"')
    content = content.replace('channel_type = "whatsapp"', 'channel_type = ChannelType.WHATSAPP')
    changes += old_whatsapp
    print(f"Fixed {old_whatsapp} whatsapp strings")
    
    old_discord = content.count('channel_type = "discord"')  
    content = content.replace('channel_type = "discord"', 'channel_type = ChannelType.DISCORD')
    changes += old_discord
    print(f"Fixed {old_discord} discord strings")
    
    # Fix MagicMock constructor calls
    if 'MagicMock(name="instance1", channel_type="whatsapp")' in content:
        content = content.replace('MagicMock(name="instance1", channel_type="whatsapp")',
                                'MagicMock(name="instance1", channel_type=ChannelType.WHATSAPP)')
        changes += 1
        print("Fixed instance1 mock")
    
    if 'MagicMock(name="instance2", channel_type="discord")' in content:
        content = content.replace('MagicMock(name="instance2", channel_type="discord")',
                                'MagicMock(name="instance2", channel_type=ChannelType.DISCORD)')
        changes += 1
        print("Fixed instance2 mock")
    
    # Fix method call assertions
    contacts_fix = '''mock_whatsapp_handler.get_contacts.assert_called_once_with(
            mock_instance_config, page=1, page_size=50, search_query=None
        )'''
    if contacts_fix in content:
        new_contacts = '''mock_whatsapp_handler.get_contacts.assert_called_once_with(
            instance=mock_instance_config, page=1, page_size=50, search_query=None, status_filter=None
        )'''
        content = content.replace(contacts_fix, new_contacts)
        changes += 1
        print("Fixed contacts handler call")
    
    search_fix = '''handler.get_contacts.assert_called_once_with(
            mock_instance_config, page=1, page_size=50, search_query="Search"
        )'''
    if search_fix in content:
        new_search = '''handler.get_contacts.assert_called_once_with(
            instance=mock_instance_config, page=1, page_size=50, search_query="Search", status_filter=None
        )'''
        content = content.replace(search_fix, new_search)
        changes += 1
        print("Fixed contacts search handler call")
    
    chats_fix = '''mock_discord_handler.get_chats.assert_called_once_with(
            mock_instance_config, page=1, page_size=50
        )'''
    if chats_fix in content:
        new_chats = '''mock_discord_handler.get_chats.assert_called_once_with(
            instance=mock_instance_config, page=1, page_size=50, chat_type_filter=None, archived=None
        )'''
        content = content.replace(chats_fix, new_chats)
        changes += 1
        print("Fixed chats handler call")
    
    # Write back
    with open(test_file, 'w') as f:
        f.write(content)
    
    print(f"\n✅ Applied {changes} fixes and wrote file")
    
    # Verify
    enum_count = content.count('ChannelType.')
    param_count = content.count('status_filter=') + content.count('chat_type_filter=')
    print(f"✅ Verified: {enum_count} enum refs, {param_count} parameter fixes")

# Run the fix
apply_fix()