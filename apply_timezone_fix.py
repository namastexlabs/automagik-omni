#!/usr/bin/env python3
"""Simple script to apply timezone fixes"""
import os
import shutil

def apply_discord_fix():
    # Copy the fixed version
    source = "discord_service_fixed.py" 
    target = "src/services/discord_service.py"
    
    if os.path.exists(source):
        shutil.copy2(source, target)
        print("✅ Applied timezone fix to Discord service")
        return True
    else:
        print("❌ Fixed file not found")
        return False

if __name__ == '__main__':
    success = apply_discord_fix()
    if success:
        print("Discord service timezone fix applied successfully!")
        print("Line 161: 'started_at': datetime.now(timezone.utc) → 'started_at': utcnow()")
        print("Added import: from src.utils.datetime_utils import utcnow")
    else:
        print("Failed to apply fix")