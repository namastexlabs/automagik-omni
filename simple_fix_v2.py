#!/usr/bin/env python3
import re

conftest_path = "/home/cezar/automagik/automagik-omni/tests/conftest.py"

with open(conftest_path, 'r') as f:
    content = f.read()

# Find and replace the specific pattern
old_pattern = """        mock_evolution.delete_instance = mock_delete_instance
        mock_client.return_value = mock_evolution"""

new_pattern = """        mock_evolution.delete_instance = mock_delete_instance
        
        # NUCLEAR FIX: Mock _request method to prevent AsyncMock persistence issue
        # This prevents real httpx calls that cause response.headers AsyncMock errors
        async def mock_request(*args, **kwargs):
            return {"status": "success", "data": "mock_response"}
        mock_evolution._request = mock_request

        mock_client.return_value = mock_evolution"""

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    with open(conftest_path, 'w') as f:
        f.write(content)
    print("✅ NUCLEAR FIX APPLIED!")
else:
    print("❌ Pattern not found")