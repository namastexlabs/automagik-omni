#!/usr/bin/env python3
import shutil
import os

# Paths
original = "/home/cezar/automagik/automagik-omni/src/config.py"
fixed = "/home/cezar/automagik/automagik-omni/src/config_fixed.py"
backup = "/home/cezar/automagik/automagik-omni/src/config.py.backup"

print("🔧 Replacing config.py with CORS-fixed version...")

# Create backup
shutil.copy2(original, backup)
print(f"✅ Backup created: {backup}")

# Replace with fixed version
shutil.copy2(fixed, original)
print(f"✅ Replaced {original} with fixed version")

# Verify the fix by checking the content
with open(original, 'r') as f:
    content = f.read()

cors_config_exists = 'class CorsConfig' in content
cors_attribute_exists = 'cors: CorsConfig = CorsConfig()' in content

if cors_config_exists and cors_attribute_exists:
    print("🎉 CORS configuration fix verified!")
    print("✅ CorsConfig class: FOUND")
    print("✅ cors attribute: FOUND")
    print("")
    print("🚀 PM2 should now restart the API successfully!")
    print("The AttributeError: 'Config' object has no attribute 'cors' should be resolved!")
else:
    print("❌ Fix verification failed!")
    print(f"CorsConfig class found: {cors_config_exists}")
    print(f"cors attribute found: {cors_attribute_exists}")

print("")
print("🔧 CORS Environment Variables (defaults shown):")
print("  - AUTOMAGIK_OMNI_CORS_ORIGINS=*")
print("  - AUTOMAGIK_OMNI_CORS_CREDENTIALS=true")
print("  - AUTOMAGIK_OMNI_CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS")
print("  - AUTOMAGIK_OMNI_CORS_HEADERS=*")