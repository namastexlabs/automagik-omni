#!/usr/bin/env python3

import os
import subprocess
import sys

def apply_fixes():
    """Apply all the fixes for the handler tests."""
    
    # Fix 1: Discord handler undefined variable bug
    file_path = '/home/cezar/automagik/automagik-omni/src/channels/handlers/discord_chat_handler.py'
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the undefined variable - should be 2 occurrences
    original_content = content
    content = content.replace('return unified_contact', 'return omni_contact')
    
    if content != original_content:
        # Write it back
        with open(file_path, 'w') as f:
            f.write(content)
        print("✅ Fixed Discord handler undefined variable bug")
    else:
        print("ℹ️ Discord handler - no changes needed")

if __name__ == "__main__":
    apply_fixes()