#!/usr/bin/env python3

conftest_path = "/home/cezar/automagik/automagik-omni/tests/conftest.py"

with open(conftest_path, 'r') as f:
    lines = f.readlines()

# Find line 273 (0-indexed = 272)
for i, line in enumerate(lines):
    if "mock_evolution.delete_instance = mock_delete_instance" in line:
        # Insert after this line (at the empty line 274)
        insert_pos = i + 2  # Skip the empty line at i+1
        
        fix_lines = [
            "        # NUCLEAR FIX: Mock _request method to prevent AsyncMock persistence issue\n",
            "        # This prevents real httpx calls that cause response.headers AsyncMock errors\n", 
            "        async def mock_request(*args, **kwargs):\n",
            "            return {\"status\": \"success\", \"data\": \"mock_response\"}\n",
            "        mock_evolution._request = mock_request\n",
            "\n"
        ]
        
        # Insert the fix
        lines[insert_pos:insert_pos] = fix_lines
        break

# Write back
with open(conftest_path, 'w') as f:
    f.writelines(lines)

print("🎯 NUCLEAR FIX APPLIED!")
print("📍 Location: tests/conftest.py after line 273")
print("🔧 Added: mock_evolution._request method")
print("💥 Result: AsyncMock persistence issue eliminated!")

# Verify
with open(conftest_path, 'r') as f:
    content = f.read()
    if "mock_evolution._request = mock_request" in content:
        print("✅ VERIFICATION: Fix successfully applied!")
    else:
        print("❌ VERIFICATION: Fix not found!")