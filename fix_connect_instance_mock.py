#!/usr/bin/env python3
"""
Script to fix the connect_instance mock in conftest.py
This fixes the AsyncMock.keys() issue by replacing the AsyncMock with a proper async function.
"""

# Read the conftest.py file
with open('tests/conftest.py', 'r') as f:
    content = f.read()

# Find and replace the exact problematic line
old_line = '        mock_evolution.connect_instance = AsyncMock(return_value={"qr": "test-qr"})'
new_code = '''        # Fix connect_instance to return a proper dict that supports .keys()
        async def mock_connect_instance(*args, **kwargs):
            return {"qr": "test-qr", "base64": "test-base64-qr"}
        mock_evolution.connect_instance = mock_connect_instance'''

# Replace the line
new_content = content.replace(old_line, new_code)

# Check if replacement was made
if new_content != content:
    # Write the fixed content back
    with open('tests/conftest.py', 'w') as f:
        f.write(new_content)
    print("✅ Fixed connect_instance mock in conftest.py")
    print("The AsyncMock.keys() issue should now be resolved!")
else:
    print("❌ Could not find the exact line to replace")
    print("Line searched for:")
    print(repr(old_line))