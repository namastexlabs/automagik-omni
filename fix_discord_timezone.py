#!/usr/bin/env python3
"""
Simple script to fix the specific timezone issue in discord_service.py
"""
import re

def fix_discord_service():
    file_path = "src/services/discord_service.py"
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Fix the datetime.now(timezone.utc) call
        content = content.replace(
            "'started_at': datetime.now(timezone.utc),",
            "'started_at': utcnow(),"
        )
        
        # Add the import if not present
        if 'from src.utils.datetime_utils import utcnow' not in content:
            # Find the position after the health_check import
            health_check_import = 'from src.utils.health_check import wait_for_api_health'
            if health_check_import in content:
                pos = content.find(health_check_import) + len(health_check_import)
                content = content[:pos] + '\nfrom src.utils.datetime_utils import utcnow' + content[pos:]
        
        # Write back
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✅ Successfully fixed Discord service timezone issue")
            return True
        else:
            print("No changes needed")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    fix_discord_service()