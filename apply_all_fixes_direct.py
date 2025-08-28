#!/usr/bin/env python3
"""
Direct application of all comprehensive fixes
"""

import os
import sys

def main():
    print("🔧 Applying all test fixes directly...")
    
    # Fix 1: Discord test function signatures
    print("\n1. Fixing Discord test function signatures...")
    test_file = "tests/test_unified_handlers.py"
    
    if os.path.exists(test_file):
        with open(test_file, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Remove mock_get_bot parameter from Discord test methods
        content = content.replace(
            "self, mock_get_bot, handler, mock_instance_config, mock_discord_bot",
            "self, handler, mock_instance_config, mock_discord_bot"
        )
        
        content = content.replace(
            "self, mock_get_bot, handler, mock_instance_config",
            "self, handler, mock_instance_config"
        )
        
        if content != original_content:
            with open(test_file, 'w') as f:
                f.write(content)
            print("✅ Fixed Discord test function signatures")
        else:
            print("⚠️  No Discord signature issues found")
    else:
        print(f"❌ Test file not found: {test_file}")
    
    # Fix 2: WhatsApp transformer None handling  
    print("\n2. Fixing WhatsApp transformer None handling...")
    transformer_file = "src/services/unified_transformers.py"
    
    if os.path.exists(transformer_file):
        with open(transformer_file, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Add None checks if missing
        if "if not whatsapp_contact:" not in content:
            # Find contact_to_unified method and add None check
            contact_method = "def contact_to_unified(whatsapp_contact: Dict[str, Any], instance_name: str) -> UnifiedContact:"
            if contact_method in content:
                # Simple replacement - add None check after method definition line
                replacement = '''def contact_to_unified(whatsapp_contact: Dict[str, Any], instance_name: str) -> UnifiedContact:
        """Transform WhatsApp contact to unified format."""
        if not whatsapp_contact:
            return UnifiedContact(
                id="unknown",
                name="Unknown",
                channel_type=ChannelType.WHATSAPP,
                instance_name=instance_name
            )'''
                content = content.replace(
                    contact_method + '\n        """Transform WhatsApp contact to unified format."""',
                    replacement
                )
        
        if "if not whatsapp_chat:" not in content:
            # Find chat_to_unified method and add None check
            chat_method = "def chat_to_unified(whatsapp_chat: Dict[str, Any], instance_name: str) -> UnifiedChat:"
            if chat_method in content:
                replacement = '''def chat_to_unified(whatsapp_chat: Dict[str, Any], instance_name: str) -> UnifiedChat:
        """Transform WhatsApp chat to unified format."""
        if not whatsapp_chat:
            return UnifiedChat(
                id="unknown",
                name="Unknown",
                chat_type=UnifiedChatType.DIRECT,
                channel_type=ChannelType.WHATSAPP,
                instance_name=instance_name
            )'''
                content = content.replace(
                    chat_method + '\n        """Transform WhatsApp chat to unified format."""',
                    replacement
                )
        
        if content != original_content:
            with open(transformer_file, 'w') as f:
                f.write(content)
            print("✅ Added None handling to WhatsApp transformer")
        else:
            print("⚠️  WhatsApp transformer already has None handling")
    else:
        print(f"❌ Transformer file not found: {transformer_file}")
    
    # Fix 3: Discord channel_type handling
    print("\n3. Fixing Discord transformer channel_type...")
    if os.path.exists(transformer_file):
        with open(transformer_file, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Ensure channel_type is integer
        content = content.replace(
            'channel_type = discord_channel.get("type", 0)',
            'channel_type = int(discord_channel.get("type", 0))'
        )
        
        if content != original_content:
            with open(transformer_file, 'w') as f:
                f.write(content)
            print("✅ Fixed Discord channel_type handling")
        else:
            print("⚠️  Discord channel_type already handled correctly")
    
    print("\n🎉 All fixes applied!")
    print("\n🧪 Test the fixes:")
    print("python -m pytest tests/test_unified_handlers.py::TestDiscordChatHandler::test_get_contacts_success -v")

if __name__ == "__main__":
    main()