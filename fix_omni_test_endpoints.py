#!/usr/bin/env python3
"""
Fix test_omni_endpoints.py to resolve the 8 remaining test failures.

Issues to fix:
1. Mock channel_type using strings instead of ChannelType enum values
2. Handler method call assertions missing required parameters
3. Mock objects not providing valid enum values for schema validation
"""

def fix_omni_endpoints_tests():
    file_path = '/home/cezar/automagik/automagik-omni/tests/test_omni_endpoints.py'
    
    # Read the current content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Replace string channel_type values with ChannelType enum values
    replacements = [
        # Authentication test class fixtures
        ('instance.channel_type = "whatsapp"', 'instance.channel_type = ChannelType.WHATSAPP'),
        ('instance.channel_type = "discord"', 'instance.channel_type = ChannelType.DISCORD'),
        
        # Fix handler method call assertions - add missing parameters
        # get_contacts calls - add status_filter parameter
        (
            'mock_whatsapp_handler.get_contacts.assert_called_once_with(\n            mock_instance_config, page=1, page_size=50, search_query=None\n        )',
            'mock_whatsapp_handler.get_contacts.assert_called_once_with(\n            instance=mock_instance_config, page=1, page_size=50, search_query=None, status_filter=None\n        )'
        ),
        (
            'handler.get_contacts.assert_called_once_with(\n            mock_instance_config, page=1, page_size=50, search_query="Search"\n        )',
            'handler.get_contacts.assert_called_once_with(\n            instance=mock_instance_config, page=1, page_size=50, search_query="Search", status_filter=None\n        )'
        ),
        
        # get_chats calls - add chat_type_filter and archived parameters
        (
            'mock_discord_handler.get_chats.assert_called_once_with(\n            mock_instance_config, page=1, page_size=50\n        )',
            'mock_discord_handler.get_chats.assert_called_once_with(\n            instance=mock_instance_config, page=1, page_size=50, chat_type_filter=None, archived=None\n        )'
        ),
        
        # Fix multiple instances mock for channels endpoint
        ('instances = [\n            MagicMock(name="instance1", channel_type="whatsapp"),\n            MagicMock(name="instance2", channel_type="discord")\n        ]',
         'instances = [\n            MagicMock(name="instance1", channel_type=ChannelType.WHATSAPP),\n            MagicMock(name="instance2", channel_type=ChannelType.DISCORD)\n        ]'),
        
        # Fix inline instance creations in test methods
        ('whatsapp_instance.channel_type = "whatsapp"', 'whatsapp_instance.channel_type = ChannelType.WHATSAPP'),
        ('instance.channel_type = "whatsapp"', 'instance.channel_type = ChannelType.WHATSAPP'),
    ]
    
    # Apply all replacements
    for old, new in replacements:
        content = content.replace(old, new)
    
    # Write the fixed content back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed test_omni_endpoints.py:")
    print("  - Replaced string channel_type values with ChannelType enum values")
    print("  - Added missing status_filter parameter to get_contacts calls")  
    print("  - Added missing chat_type_filter and archived parameters to get_chats calls")
    print("  - Fixed all mock instance configurations")
    print("  - Changed positional arguments to keyword arguments where needed")

if __name__ == "__main__":
    fix_omni_endpoints_tests()