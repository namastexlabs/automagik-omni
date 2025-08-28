"""Immediate fix for test_omni_endpoints.py"""
import os

# Execute the fix directly
file_path = 'tests/test_omni_endpoints.py'

print(f"Fixing {file_path}...")

with open(file_path, 'r') as f:
    content = f.read()

# Track changes
changes = 0

# Fix 1: Channel type strings to enums  
old_content = content
content = content.replace('channel_type = "whatsapp"', 'channel_type = ChannelType.WHATSAPP')
changes += old_content.count('channel_type = "whatsapp"')

old_content = content
content = content.replace('channel_type = "discord"', 'channel_type = ChannelType.DISCORD')
changes += old_content.count('channel_type = "discord"')

# Fix 2: Handler method calls - get_contacts
old_str = '''mock_whatsapp_handler.get_contacts.assert_called_once_with(
            mock_instance_config, page=1, page_size=50, search_query=None
        )'''
new_str = '''mock_whatsapp_handler.get_contacts.assert_called_once_with(
            instance=mock_instance_config, page=1, page_size=50, search_query=None, status_filter=None
        )'''
if old_str in content:
    content = content.replace(old_str, new_str)
    changes += 1

# Fix 3: Handler method calls - get_contacts with search
old_str = '''handler.get_contacts.assert_called_once_with(
            mock_instance_config, page=1, page_size=50, search_query="Search"
        )'''
new_str = '''handler.get_contacts.assert_called_once_with(
            instance=mock_instance_config, page=1, page_size=50, search_query="Search", status_filter=None
        )'''
if old_str in content:
    content = content.replace(old_str, new_str)
    changes += 1

# Fix 4: Handler method calls - get_chats  
old_str = '''mock_discord_handler.get_chats.assert_called_once_with(
            mock_instance_config, page=1, page_size=50
        )'''
new_str = '''mock_discord_handler.get_chats.assert_called_once_with(
            instance=mock_instance_config, page=1, page_size=50, chat_type_filter=None, archived=None
        )'''
if old_str in content:
    content = content.replace(old_str, new_str)
    changes += 1

# Write back
with open(file_path, 'w') as f:
    f.write(content)

print(f"Applied {changes} fixes")
print("✅ Fix completed!")

# Verify the changes
print("\nVerifying changes...")
with open(file_path, 'r') as f:
    new_content = f.read()

whatsapp_enums = new_content.count('ChannelType.WHATSAPP')  
discord_enums = new_content.count('ChannelType.DISCORD')
status_filter_calls = new_content.count('status_filter=None')
chat_filter_calls = new_content.count('chat_type_filter=None')

print(f"✅ Found {whatsapp_enums} ChannelType.WHATSAPP references")
print(f"✅ Found {discord_enums} ChannelType.DISCORD references") 
print(f"✅ Found {status_filter_calls} status_filter=None parameters")
print(f"✅ Found {chat_filter_calls} chat_type_filter=None parameters")