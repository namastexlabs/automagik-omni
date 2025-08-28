#!/usr/bin/env python3
"""Apply Discord test fixes to test_unified_handlers.py"""

import shutil
import os

def main():
    # Backup original file
    original = "tests/test_unified_handlers.py"
    backup = "tests/test_unified_handlers_backup.py"
    fixed = "tests/test_unified_handlers_fixed.py"
    
    if os.path.exists(original):
        shutil.copy2(original, backup)
        print(f"Created backup: {backup}")
    
    if os.path.exists(fixed):
        shutil.copy2(fixed, original)
        print(f"Applied fixes to {original}")
        
        # Verify
        with open(original, 'r') as f:
            content = f.read()
            
        if "PropertyMock" in content:
            print("✓ PropertyMock import added")
        if "_bot_instances" in content:
            print("✓ _bot_instances mocking implemented")
        if "@patch('src.channels.handlers.discord_chat_handler.get_discord_bot')" not in content:
            print("✓ Removed incorrect get_discord_bot patches")
        
        print("\nDiscord test fixes applied successfully!")
        print("\nRun tests with: python -m pytest tests/test_unified_handlers.py::TestDiscordChatHandler -v")
        
    else:
        print(f"Error: {fixed} not found!")

if __name__ == "__main__":
    main()