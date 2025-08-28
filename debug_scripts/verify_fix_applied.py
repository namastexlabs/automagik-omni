#!/usr/bin/env python3
"""
Verify that the AsyncMock.keys() fix has been applied to conftest.py
"""

# Read the current conftest.py content
with open('tests/conftest.py', 'r') as f:
    content = f.read()

# Check if the problematic line is still there
problematic_line = 'mock_evolution.connect_instance = AsyncMock(return_value={"qr": "test-qr"})'
fixed_pattern = 'async def mock_connect_instance'

print("🔍 VERIFYING FIX STATUS:")
print("=" * 50)

if problematic_line in content:
    print("❌ PROBLEM: Original problematic line still exists")
    print(f"   Found: {problematic_line}")
    print("\n🛠️  NEED TO APPLY FIX")
    
    # Apply the fix
    print("Applying fix...")
    new_code = '''        # Fix connect_instance to return a proper dict that supports .keys()
        async def mock_connect_instance(*args, **kwargs):
            return {"qr": "test-qr", "base64": "test-base64-qr"}
        mock_evolution.connect_instance = mock_connect_instance'''
    
    new_content = content.replace(problematic_line, new_code)
    
    with open('tests/conftest.py', 'w') as f:
        f.write(new_content)
    
    print("✅ FIX APPLIED!")
    
elif fixed_pattern in content:
    print("✅ SUCCESS: Fix has been applied!")
    print(f"   Found: {fixed_pattern}")
    
    # Show the fixed lines
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'async def mock_connect_instance' in line:
            print(f"\n📋 FIXED CODE (lines {i+1}-{i+4}):")
            for j in range(max(0, i-1), min(len(lines), i+4)):
                marker = ">>> " if j == i else "    "
                print(f"{marker}Line {j+1}: {lines[j]}")
            break
else:
    print("❓ UNKNOWN: Neither original nor fixed pattern found")
    print("The file content may have changed unexpectedly")

print("\n🎯 WHAT THIS FIX DOES:")
print("- Replaces AsyncMock(return_value=dict) with proper async function")
print("- Ensures .keys() calls work on the returned dictionary")
print("- Resolves: 'AsyncMock.keys() returned a non-iterable (type coroutine)'")
print("- Location: src/channels/whatsapp/channel_handler.py:294")

# Double-check by looking for the specific error pattern
print("\n🔍 SEARCHING FOR OTHER POTENTIAL ISSUES:")
potential_issues = [
    'AsyncMock(return_value={',
    '.keys()',
]

for pattern in potential_issues:
    if pattern in content:
        count = content.count(pattern)
        print(f"   Found {count} occurrence(s) of: {pattern}")
    else:
        print(f"   No occurrences of: {pattern}")

print("\n✅ VERIFICATION COMPLETE!")