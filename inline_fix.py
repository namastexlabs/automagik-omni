import re

# Read the file
with open('/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py', 'r') as f:
    content = f.read()

# Apply fixes
content = content.replace('UnifiedContactStatus.ACTIVE', 'UnifiedContactStatus.ONLINE')
content = content.replace('default_agent_name=', 'default_agent=')

# Write back
with open('/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py', 'w') as f:
    f.write(content)

print("Fixed test_unified_endpoints.py")

# Fix transformers
with open('/home/cezar/automagik/automagik-omni/src/services/unified_transformers.py', 'r') as f:
    content = f.read()

content = content.replace(
    'whatsapp_contact.get("pushName") or whatsapp_contact.get("name", "Unknown")',
    'whatsapp_contact.get("pushName") or whatsapp_contact.get("name") or "Unknown"'
)
content = content.replace(
    'whatsapp_contact.get("id", "").replace("@c.us", "")',
    '(whatsapp_contact.get("id") or "").replace("@c.us", "")'
)

with open('/home/cezar/automagik/automagik-omni/src/services/unified_transformers.py', 'w') as f:
    f.write(content)

print("Fixed unified_transformers.py")
print("All fixes applied!")