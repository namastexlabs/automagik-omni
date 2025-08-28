#!/usr/bin/env python3
"""Direct application of test fixes"""

import os

def apply_discord_fixture_fixes():
    """Apply Discord fixture fixes directly."""
    file_path = "tests/test_unified_handlers.py"
    
    print(f"🔧 Fixing Discord test fixtures in {file_path}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    changes_made = 0
    
    # Process each line to remove mock_get_bot from Discord test function signatures
    for i, line in enumerate(lines):
        if 'self, mock_get_bot, handler, mock_instance_config, mock_discord_bot' in line:
            lines[i] = line.replace('self, mock_get_bot, handler, mock_instance_config, mock_discord_bot', 
                                  'self, handler, mock_instance_config, mock_discord_bot')
            changes_made += 1
            print(f"   Fixed line {i+1}: {line.strip()}")
        elif 'self, mock_get_bot, handler, mock_instance_config' in line and 'mock_discord_bot' not in line:
            lines[i] = line.replace('self, mock_get_bot, handler, mock_instance_config', 
                                  'self, handler, mock_instance_config')
            changes_made += 1
            print(f"   Fixed line {i+1}: {line.strip()}")
    
    # Write the modified content back
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Fixed {changes_made} Discord test function signatures")
    return changes_made > 0

def apply_whatsapp_transformer_fixes():
    """Apply WhatsApp transformer None handling fixes."""
    file_path = "src/services/unified_transformers.py"
    
    if not os.path.exists(file_path):
        print(f"⚠️  {file_path} not found")
        return False
    
    print(f"🔧 Adding None handling to WhatsApp transformer in {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    # Add None check to contact_to_unified method if not already present
    if 'if not whatsapp_contact:' not in content:
        # Find WhatsApp contact method
        contact_method = 'def contact_to_unified(whatsapp_contact: Dict[str, Any], instance_name: str) -> UnifiedContact:'
        if contact_method in content:
            # Find the method and add None check
            method_start = content.find(contact_method)
            if method_start != -1:
                # Find end of docstring
                docstring_end = content.find('"""', method_start)
                if docstring_end != -1:
                    docstring_end = content.find('"""', docstring_end + 3) + 3
                    # Add None check after docstring
                    none_check = '''
        if not whatsapp_contact:
            return UnifiedContact(
                id="unknown",
                name="Unknown", 
                channel_type=ChannelType.WHATSAPP,
                instance_name=instance_name
            )
        '''
                    content = content[:docstring_end] + none_check + content[docstring_end:]
                    changes_made += 1
                    print("   Added None check to WhatsApp contact_to_unified")
    
    # Add None check to chat_to_unified method if not already present
    if 'if not whatsapp_chat:' not in content:
        # Find WhatsApp chat method
        chat_method = 'def chat_to_unified(whatsapp_chat: Dict[str, Any], instance_name: str) -> UnifiedChat:'
        if chat_method in content:
            # Find the method and add None check
            method_start = content.find(chat_method)
            if method_start != -1:
                # Find end of docstring
                docstring_end = content.find('"""', method_start)
                if docstring_end != -1:
                    docstring_end = content.find('"""', docstring_end + 3) + 3
                    # Add None check after docstring
                    none_check = '''
        if not whatsapp_chat:
            return UnifiedChat(
                id="unknown",
                name="Unknown",
                chat_type=UnifiedChatType.DIRECT,
                channel_type=ChannelType.WHATSAPP,
                instance_name=instance_name
            )
        '''
                    content = content[:docstring_end] + none_check + content[docstring_end:]
                    changes_made += 1
                    print("   Added None check to WhatsApp chat_to_unified")
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✅ Added {changes_made} None checks to WhatsApp transformer")
        return True
    else:
        print("✗ WhatsApp transformer already has proper None handling")
        return False

def apply_discord_channel_type_fix():
    """Fix Discord channel_type to be integer."""
    file_path = "src/services/unified_transformers.py"
    
    if not os.path.exists(file_path):
        print(f"⚠️  {file_path} not found")
        return False
    
    print(f"🔧 Fixing Discord channel_type handling in {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Fix channel_type to ensure it's an integer
    if 'channel_type = discord_channel.get("type", 0)' in content:
        content = content.replace(
            'channel_type = discord_channel.get("type", 0)',
            'channel_type = int(discord_channel.get("type", 0))'
        )
        
        with open(file_path, 'w') as f:
            f.write(content)
        print("✅ Fixed Discord channel_type to be integer")
        return True
    else:
        print("✗ Discord channel_type already handled as integer or not found")
        return False

def main():
    """Apply all fixes in sequence."""
    print("🚀 Applying direct test fixes...\n")
    
    fixes_applied = []
    
    # Apply Discord fixture fixes
    if apply_discord_fixture_fixes():
        fixes_applied.append("Discord fixture parameters")
    
    print()
    
    # Apply WhatsApp transformer fixes
    if apply_whatsapp_transformer_fixes():
        fixes_applied.append("WhatsApp None handling")
    
    print()
    
    # Apply Discord channel_type fixes
    if apply_discord_channel_type_fix():
        fixes_applied.append("Discord channel_type")
    
    print()
    
    if fixes_applied:
        print(f"🎉 Successfully applied fixes for: {', '.join(fixes_applied)}")
        print("\n🧪 Test the fixes:")
        print("   python -m pytest tests/test_unified_handlers.py::TestDiscordChatHandler::test_get_contacts_success -v")
        print("   python -m pytest tests/test_unified_transformers.py -v")
    else:
        print("⚠️  No fixes were applied - issues may already be resolved")

if __name__ == "__main__":
    main()