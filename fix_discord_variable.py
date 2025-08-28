#!/usr/bin/env python3
"""Fix Discord handler variable name bug"""

import os

def fix_discord_handler():
    """Fix the variable name bug in discord_chat_handler.py"""
    file_path = "/home/cezar/automagik/automagik-omni/src/channels/handlers/discord_chat_handler.py"
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the variable name issue
    fixed_content = content.replace('return unified_contact', 'return omni_contact')
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(fixed_content)
    
    print("✅ Fixed Discord handler variable name bug: unified_contact → omni_contact")
    print(f"📁 File: {file_path}")

if __name__ == "__main__":
    fix_discord_handler()