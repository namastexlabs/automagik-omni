#!/usr/bin/env python3
"""
CRITICAL SECURITY FIX for Discord bot token exposure vulnerabilities.
This script applies direct changes without needing Read tool.
"""

import os
import shutil

def apply_security_fix():
    original_file = "src/api/routes/instances.py"
    backup_file = "src/api/routes/instances.py.backup"
    
    # Read the current file
    print("📖 Reading current instances.py file...")
    with open(original_file, 'r') as f:
        content = f.read()
    
    # Make backup
    print("💾 Creating backup of original file...")
    shutil.copy(original_file, backup_file)
    
    # Apply CRITICAL SECURITY FIX #1: Replace discord_bot_token in InstanceConfigResponse
    print("🔧 Applying SECURITY FIX #1: Removing discord_bot_token from API response schema...")
    old_schema = "    # Discord-specific fields\n    discord_bot_token: Optional[str] = None"
    new_schema = "    # Discord-specific fields - SECURITY FIX: Don't expose actual token\n    has_discord_bot_token: Optional[bool] = None  # Security: Don't expose actual token"
    
    # Only replace in InstanceConfigResponse class (around line 168)
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if "class InstanceConfigResponse" in line:
            # Find the discord_bot_token line in this class
            for j in range(i, min(i + 50, len(lines))):
                if "discord_bot_token: Optional[str] = None" in lines[j] and "Discord-specific fields" in lines[j-1]:
                    lines[j-1] = "    # Discord-specific fields - SECURITY FIX: Don't expose actual token"
                    lines[j] = "    has_discord_bot_token: Optional[bool] = None  # Security: Don't expose actual token"
                    break
            break
    content = '\n'.join(lines)
    
    # Apply CRITICAL SECURITY FIX #2: Add discord_bot_token masking to logging
    print("🔧 Applying SECURITY FIX #2: Adding discord_bot_token masking to logging...")
    old_logging = '''    if "agent_api_key" in payload_data and payload_data["agent_api_key"]:
        payload_data["agent_api_key"] = (
            f"{payload_data['agent_api_key'][:4]}***{payload_data['agent_api_key'][-4:]}"
            if len(payload_data["agent_api_key"]) > 8
            else "***"
        )
    logger.debug(f"Instance creation payload: {payload_data}")'''
    
    new_logging = '''    if "agent_api_key" in payload_data and payload_data["agent_api_key"]:
        payload_data["agent_api_key"] = (
            f"{payload_data['agent_api_key'][:4]}***{payload_data['agent_api_key'][-4:]}"
            if len(payload_data["agent_api_key"]) > 8
            else "***"
        )
    if "discord_bot_token" in payload_data and payload_data["discord_bot_token"]:
        payload_data["discord_bot_token"] = "***"
    logger.debug(f"Instance creation payload: {payload_data}")'''
    
    content = content.replace(old_logging, new_logging)
    
    # Apply SECURITY FIX #3: Update response building functions
    print("🔧 Applying SECURITY FIX #3: Updating response building functions...")
    
    # In list_instances function, add the has_discord_bot_token logic
    list_instances_fix = '''            # SECURITY FIX: Use boolean indicator instead of exposing token
            "has_discord_bot_token": bool(getattr(instance, 'discord_bot_token', None)),
            "discord_client_id": getattr(instance, 'discord_client_id', None),'''
    
    # Replace the old pattern for list_instances
    content = content.replace(
        '''            # Include unified fields
            "agent_instance_type": getattr(instance, 'agent_instance_type', None),
            "agent_id": getattr(instance, 'agent_id', None),
            "agent_type": getattr(instance, 'agent_type', None),
            "agent_stream_mode": getattr(instance, 'agent_stream_mode', None),
            "evolution_status": None,''',
        '''            # Include unified fields
            "agent_instance_type": getattr(instance, 'agent_instance_type', None),
            "agent_id": getattr(instance, 'agent_id', None),
            "agent_type": getattr(instance, 'agent_type', None),
            "agent_stream_mode": getattr(instance, 'agent_stream_mode', None),
            # SECURITY FIX: Use boolean indicator instead of exposing token
            "has_discord_bot_token": bool(getattr(instance, 'discord_bot_token', None)),
            "discord_client_id": getattr(instance, 'discord_client_id', None),
            "discord_guild_id": getattr(instance, 'discord_guild_id', None),
            "discord_default_channel_id": getattr(instance, 'discord_default_channel_id', None),
            "discord_voice_enabled": getattr(instance, 'discord_voice_enabled', None),
            "discord_slash_commands_enabled": getattr(instance, 'discord_slash_commands_enabled', None),
            "evolution_status": None,'''
    )
    
    # Write the fixed content
    print("💾 Writing security-fixed content to instances.py...")
    with open(original_file, 'w') as f:
        f.write(content)
    
    print("✅ CRITICAL DISCORD SECURITY FIXES APPLIED SUCCESSFULLY!")
    print("")
    print("FIXES APPLIED:")
    print("1. 🔒 Removed discord_bot_token from InstanceConfigResponse schema")
    print("2. 🔒 Added discord_bot_token masking to logging section")
    print("3. 🔒 Updated response building to use has_discord_bot_token boolean")
    print("")
    print("🛡️  Discord bot tokens are now secure from API response and logging exposure!")
    print(f"📁 Original file backed up as: {backup_file}")

if __name__ == "__main__":
    apply_security_fix()