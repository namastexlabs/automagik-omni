#!/usr/bin/env python3

import os

def fix_discord_handler():
    """Fix the undefined variable bug in Discord handler."""
    file_path = '/home/cezar/automagik/automagik-omni/src/channels/handlers/discord_chat_handler.py'
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the undefined variable
    content = content.replace('return unified_contact', 'return omni_contact')
    
    # Write it back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Fixed Discord handler undefined variable bug")

if __name__ == "__main__":
    fix_discord_handler()