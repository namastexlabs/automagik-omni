import os

# Change to the right directory
os.chdir("/home/cezar/automagik/automagik-omni")

# Read current conftest.py
with open('tests/conftest.py', 'r') as f:
    content = f.read()

# Replace the problematic line
old_line = '        mock_evolution.connect_instance = AsyncMock(return_value={"qr": "test-qr"})'
new_code = '''        # Fix connect_instance to return a proper dict that supports .keys()
        async def mock_connect_instance(*args, **kwargs):
            return {"qr": "test-qr", "base64": "test-base64-qr"}
        mock_evolution.connect_instance = mock_connect_instance'''

if old_line in content:
    new_content = content.replace(old_line, new_code)
    with open('tests/conftest.py', 'w') as f:
        f.write(new_content)
    print("✅ SUCCESS: Fixed AsyncMock.keys() issue in conftest.py")
    print("The connect_instance mock now returns a proper dict")
else:
    print("❌ ERROR: Could not find the target line to replace")
    print("Looking for:", old_line)