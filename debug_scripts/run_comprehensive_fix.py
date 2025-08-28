#!/usr/bin/env python3
"""
Run comprehensive fixes directly using file operations
"""

import re

def fix_discord_test_signatures():
    """Fix all Discord test method signatures by removing mock_get_bot parameter."""
    file_path = "tests/test_unified_handlers.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Track changes
    changes_made = 0
    
    # Fix all occurrences of mock_get_bot parameter in Discord test methods
    patterns = [
        # Pattern 1: self, mock_get_bot, handler, mock_instance_config, mock_discord_bot
        (r'(\s+)(self, mock_get_bot, handler, mock_instance_config, mock_discord_bot)', r'\1self, handler, mock_instance_config, mock_discord_bot'),
        # Pattern 2: self, mock_get_bot, handler, mock_instance_config (no mock_discord_bot)
        (r'(\s+)(self, mock_get_bot, handler, mock_instance_config)(\s*)', r'\1self, handler, mock_instance_config\3'),
    ]
    
    original_content = content
    for pattern, replacement in patterns:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes_made += content.count('mock_get_bot') - new_content.count('mock_get_bot')
            content = new_content
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✓ Fixed {changes_made} Discord test function signatures")
        return True
    else:
        print("✗ No Discord fixture issues found")
        return False

def fix_whatsapp_none_handling():
    """Fix WhatsApp transformer None handling."""
    file_path = "src/services/unified_transformers.py"
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"⚠️  {file_path} not found")
        return False
    
    original_content = content
    changes_made = 0
    
    # Add None check for WhatsApp contact transformation
    if 'if not whatsapp_contact:' not in content and 'WhatsAppTransformer' in content:
        # Find the contact_to_unified method and add None check
        pattern = r'(def contact_to_unified\(whatsapp_contact: Dict\[str, Any\], instance_name: str\) -> UnifiedContact:\s+"""Transform WhatsApp contact to unified format\."""\s+)'
        replacement = r'\1if not whatsapp_contact:\n            return UnifiedContact(\n                id="unknown",\n                name="Unknown",\n                channel_type=ChannelType.WHATSAPP,\n                instance_name=instance_name\n            )\n        '
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        if content != original_content:
            changes_made += 1
    
    # Add None check for WhatsApp chat transformation
    if 'if not whatsapp_chat:' not in content and 'WhatsAppTransformer' in content:
        pattern = r'(def chat_to_unified\(whatsapp_chat: Dict\[str, Any\], instance_name: str\) -> UnifiedChat:\s+"""Transform WhatsApp chat to unified format\."""\s+)'
        replacement = r'\1if not whatsapp_chat:\n            return UnifiedChat(\n                id="unknown",\n                name="Unknown",\n                chat_type=UnifiedChatType.DIRECT,\n                channel_type=ChannelType.WHATSAPP,\n                instance_name=instance_name\n            )\n        '
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        if content != original_content:
            changes_made += 1
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✓ Added {changes_made} None checks to WhatsApp transformer")
        return True
    else:
        print("✗ WhatsApp transformer already has proper None handling")
        return False

def fix_discord_channel_type():
    """Fix Discord transformer channel_type handling."""
    file_path = "src/services/unified_transformers.py"
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"⚠️  {file_path} not found")
        return False
    
    original_content = content
    
    # Ensure channel_type is handled as integer
    content = re.sub(
        r'channel_type = discord_channel\.get\("type", 0\)',
        r'channel_type = int(discord_channel.get("type", 0))',
        content
    )
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print("✓ Fixed Discord transformer channel_type handling")
        return True
    else:
        print("✗ Discord transformer channel_type already handled correctly")
        return False

def main():
    """Apply all fixes."""
    print("🔧 Applying comprehensive test fixes...\n")
    
    fixes_applied = []
    
    try:
        print("1. Fixing Discord test fixture issues...")
        if fix_discord_test_signatures():
            fixes_applied.append("Discord fixture parameters")
        
        print("\n2. Fixing WhatsApp transformer None handling...")
        if fix_whatsapp_none_handling():
            fixes_applied.append("WhatsApp None handling")
        
        print("\n3. Fixing Discord transformer channel_type...")
        if fix_discord_channel_type():
            fixes_applied.append("Discord channel_type handling")
        
        if fixes_applied:
            print(f"\n✅ Successfully applied fixes for: {', '.join(fixes_applied)}")
            print("\n🧪 Run tests to verify:")
            print("   python -m pytest tests/test_unified_handlers.py::TestDiscordChatHandler -v")
        else:
            print("\n⚠️  No fixes needed - issues may already be resolved")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()