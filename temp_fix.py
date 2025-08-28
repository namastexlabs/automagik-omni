import re

# Read the handlers file
with open('/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py', 'r') as f:
    content = f.read()

# Replace the enum values
content = content.replace('UnifiedContactStatus.ACTIVE', 'UnifiedContactStatus.UNKNOWN')

# Write it back
with open('/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py', 'w') as f:
    f.write(content)

print("Fixed test_unified_handlers.py")

# Now fix the endpoints file
with open('/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py', 'r') as f:
    content = f.read()

# Replace the enum values
content = content.replace('UnifiedContactStatus.ACTIVE', 'UnifiedContactStatus.UNKNOWN')

# Write it back
with open('/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py', 'w') as f:
    f.write(content)

print("Fixed test_unified_endpoints.py")
print("All files fixed!")