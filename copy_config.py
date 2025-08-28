#!/usr/bin/env python3
import shutil
import os

# Create backup
src = "/home/cezar/automagik/automagik-omni/src/config.py"
backup = "/home/cezar/automagik/automagik-omni/src/config.py.backup"
new_config = "/home/cezar/automagik/automagik-omni/config_updated.py"

# Create backup
shutil.copy2(src, backup)
print(f"✅ Backup created: {backup}")

# Copy new config
shutil.copy2(new_config, src)
print(f"✅ Updated config copied to: {src}")

# Remove the temporary file
os.remove(new_config)
print(f"✅ Temporary file removed")

print("Config file updated successfully!")