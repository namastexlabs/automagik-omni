#!/usr/bin/env python3
"""
Apply comprehensive fixes to test_omni_endpoints.py to resolve the 8 test failures.
"""

def fix_omni_endpoints():
    import re
    
    test_file = '/home/cezar/automagik/automagik-omni/tests/test_omni_endpoints.py'
    
    # Read the file
    with open(test_file, 'r') as f:
        content = f.read()
    
    print(f"Original file size: {len(content):,} characters")
    
    # Define all fixes to apply
    fixes = [
        # Fix 1: Replace string channel_type values with ChannelType enum values
        ('channel_type = "whatsapp"', 'channel_type = ChannelType.WHATSAPP'),
        ('channel_type = "discord"', 'channel_type = ChannelType.DISCORD'),
        
        # Fix 2: Fix mock multiple instances 
        ('MagicMock(name="instance1", channel_type="whatsapp")',
         'MagicMock(name="instance1", channel_type=ChannelType.WHATSAPP)'),
        ('MagicMock(name="instance2", channel_type="discord")',
         'MagicMock(name="instance2", channel_type=ChannelType.DISCORD)'),
        
        # Fix 3: Fix handler method call assertions - contacts
        ('''mock_whatsapp_handler.get_contacts.assert_called_once_with(
            mock_instance_config, page=1, page_size=50, search_query=None
        )''',
         '''mock_whatsapp_handler.get_contacts.assert_called_once_with(
            instance=mock_instance_config, page=1, page_size=50, search_query=None, status_filter=None
        )'''),
        
        ('''handler.get_contacts.assert_called_once_with(
            mock_instance_config, page=1, page_size=50, search_query="Search"
        )''',
         '''handler.get_contacts.assert_called_once_with(
            instance=mock_instance_config, page=1, page_size=50, search_query="Search", status_filter=None
        )'''),
        
        # Fix 4: Fix handler method call assertions - chats
        ('''mock_discord_handler.get_chats.assert_called_once_with(
            mock_instance_config, page=1, page_size=50
        )''',
         '''mock_discord_handler.get_chats.assert_called_once_with(
            instance=mock_instance_config, page=1, page_size=50, chat_type_filter=None, archived=None
        )'''),
    ]
    
    # Apply fixes and count changes
    total_fixes = 0
    for old_str, new_str in fixes:
        count = content.count(old_str)
        if count > 0:
            content = content.replace(old_str, new_str)
            total_fixes += count
            print(f"✅ Applied {count} replacements: {old_str[:50]}...")
    
    print(f"\n📊 Applied {total_fixes} total fixes")
    print(f"New file size: {len(content):,} characters")
    
    # Write the file back
    with open(test_file, 'w') as f:
        f.write(content)
    
    print("✅ Successfully wrote updated file")
    
    # Verification
    print("\n🔍 Verification:")
    whatsapp_enums = content.count('ChannelType.WHATSAPP')
    discord_enums = content.count('ChannelType.DISCORD')
    status_filter = content.count('status_filter=None')
    chat_filter = content.count('chat_type_filter=None')
    
    print(f"  - ChannelType.WHATSAPP references: {whatsapp_enums}")
    print(f"  - ChannelType.DISCORD references: {discord_enums}")
    print(f"  - status_filter=None parameters: {status_filter}")
    print(f"  - chat_type_filter=None parameters: {chat_filter}")
    
    return total_fixes > 0

# Execute the function
if __name__ == "__main__":
    success = fix_omni_endpoints()
    print("\n🎉 Fix completed successfully!" if success else "\n⚠️  No fixes applied")