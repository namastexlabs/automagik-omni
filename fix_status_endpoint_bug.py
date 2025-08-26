#!/usr/bin/env python3
"""
Fix the method name mismatch bug in instances.py status endpoint.

The endpoint calls handler.get_connection_status() but channel handlers 
only implement get_status() as defined in the abstract base class.
"""

import os

def fix_status_endpoint_bug():
    """Fix the method name mismatch in instances.py"""
    
    file_path = "/home/cezar/automagik/automagik-omni/src/api/routes/instances.py"
    
    print("🧞⚡ Fixing integration boundary bug in status endpoint...")
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the method name mismatch
    old_line = "        status_response = await handler.get_connection_status(instance)"
    new_line = "        status_response = await handler.get_status(instance)"
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        
        # Write the fixed content back
        with open(file_path, 'w') as f:
            f.write(content)
            
        print(f"✅ FIXED: Changed get_connection_status() to get_status() in {file_path}")
        print("🎯 Both failing tests should now pass!")
        return True
    else:
        print(f"❌ ERROR: Could not find the buggy line in {file_path}")
        return False

if __name__ == "__main__":
    success = fix_status_endpoint_bug()
    if success:
        print("\n🧞 INTEGRATION BOUNDARY BUG ELIMINATED!")
        print("The method name mismatch that caused 500 errors has been fixed.")
        print("Tests should now properly mock the status endpoint calls.")
    else:
        print("\n❌ Fix failed - manual intervention required")