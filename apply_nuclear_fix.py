#!/usr/bin/env python3
"""
Apply NUCLEAR FIX for AsyncMock persistence issue
"""

def apply_fix():
    conftest_path = "/home/cezar/automagik/automagik-omni/tests/conftest.py"
    
    # Read the file
    with open(conftest_path, 'r') as f:
        lines = f.readlines()
    
    # Find the insertion point (after line 273: mock_evolution.delete_instance = mock_delete_instance)
    insert_after_line = None
    for i, line in enumerate(lines):
        if "mock_evolution.delete_instance = mock_delete_instance" in line:
            insert_after_line = i
            break
    
    if insert_after_line is None:
        print("❌ Could not find insertion point")
        return False
    
    # Find the next line that's not empty (where mock_client.return_value = mock_evolution is)
    next_content_line = insert_after_line + 1
    while next_content_line < len(lines) and lines[next_content_line].strip() == "":
        next_content_line += 1
    
    # Insert the mock _request method
    fix_lines = [
        "        \n",
        "        # NUCLEAR FIX: Mock _request method to prevent AsyncMock persistence issue\n",
        "        # This prevents real httpx calls that cause response.headers AsyncMock errors\n",
        "        async def mock_request(*args, **kwargs):\n",
        "            return {\"status\": \"success\", \"data\": \"mock_response\"}\n",
        "        mock_evolution._request = mock_request\n",
    ]
    
    # Insert the fix lines
    lines[next_content_line:next_content_line] = fix_lines
    
    # Write back to file
    with open(conftest_path, 'w') as f:
        f.writelines(lines)
    
    print("✅ NUCLEAR FIX APPLIED SUCCESSFULLY!")
    print("📍 Location: tests/conftest.py")
    print("🎯 Added: mock_evolution._request method")
    print("🔥 Effect: Prevents AsyncMock persistence issue in Evolution API")
    return True

if __name__ == "__main__":
    apply_fix()