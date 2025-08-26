#!/usr/bin/env python3
"""Apply the critical integration boundary fix"""

import sys
import os

# Apply the fix
file_path = "/home/cezar/automagik/automagik-omni/src/api/routes/instances.py"

# Read file content
with open(file_path, 'r') as f:
    content = f.read()

# Apply the fix
old_code = "        status_response = await handler.get_connection_status(instance)"
new_code = "        status_response = await handler.get_status(instance)"

if old_code in content:
    content = content.replace(old_code, new_code)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ FIXED: Method name mismatch bug resolved!")
    print("🧞 Both failing integration tests should now pass!")
else:
    print("❌ Fix pattern not found!")
    sys.exit(1)