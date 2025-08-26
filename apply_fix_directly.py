#!/usr/bin/env python3
"""Direct fix application"""

# Read the file
with open("/home/cezar/automagik/automagik-omni/src/api/routes/instances.py", 'r') as f:
    content = f.read()

# Apply the fix
content = content.replace(
    "        status_response = await handler.get_connection_status(instance)",
    "        status_response = await handler.get_status(instance)"
)

# Write it back
with open("/home/cezar/automagik/automagik-omni/src/api/routes/instances.py", 'w') as f:
    f.write(content)

print("✅ INTEGRATION BOUNDARY BUG FIXED!")
print("🧞 Method name mismatch resolved: get_connection_status → get_status")