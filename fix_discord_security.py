#!/usr/bin/env python3
"""
Critical security fix for Discord bot token exposure vulnerabilities.
This script fixes:
1. API response schema exposing discord_bot_token 
2. Missing discord_bot_token masking in logging
"""

def fix_discord_security_issues():
    file_path = "src/api/routes/instances.py"
    
    # Read the original file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Replace discord_bot_token exposure in InstanceConfigResponse schema
    content = content.replace(
        "    # Discord-specific fields\n    discord_bot_token: Optional[str] = None",
        "    # Discord-specific fields - SECURITY FIX: Don't expose actual token\n    has_discord_bot_token: Optional[bool] = None  # Security: Don't expose actual token"
    )
    
    # Fix 2: Add discord_bot_token masking in logging section
    logging_fix = """    if "agent_api_key" in payload_data and payload_data["agent_api_key"]:
        payload_data["agent_api_key"] = (
            f"{payload_data['agent_api_key'][:4]}***{payload_data['agent_api_key'][-4:]}"
            if len(payload_data["agent_api_key"]) > 8
            else "***"
        )
    if "discord_bot_token" in payload_data and payload_data["discord_bot_token"]:
        payload_data["discord_bot_token"] = "***"
    logger.debug(f"Instance creation payload: {payload_data}")"""
    
    content = content.replace(
        """    if "agent_api_key" in payload_data and payload_data["agent_api_key"]:
        payload_data["agent_api_key"] = (
            f"{payload_data['agent_api_key'][:4]}***{payload_data['agent_api_key'][-4:]}"
            if len(payload_data["agent_api_key"]) > 8
            else "***"
        )
    logger.debug(f"Instance creation payload: {payload_data}")""",
        logging_fix
    )
    
    # Write the fixed content back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ CRITICAL SECURITY FIXES APPLIED:")
    print("1. Removed discord_bot_token from InstanceConfigResponse schema")
    print("2. Added discord_bot_token masking to logging section")
    print("3. Replaced with has_discord_bot_token boolean indicator")

if __name__ == "__main__":
    fix_discord_security_issues()