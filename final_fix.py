#!/usr/bin/env python3
import os

# Read the current config file
config_path = "/home/cezar/automagik/automagik-omni/src/config.py"
with open(config_path, "r") as f:
    content = f.read()

print("🔧 Current config.py loaded...")

# First, add CorsConfig class if it doesn't exist
if "class CorsConfig" not in content:
    print("Adding CorsConfig class...")
    
    cors_class = '''
class CorsConfig(BaseModel):
    """CORS configuration for API server."""

    allowed_origins: list[str] = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_ORIGINS", "*").split(",")
    )
    allow_credentials: bool = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_CREDENTIALS", "true").lower() == "true"
    )
    allow_methods: list[str] = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    )
    allow_headers: list[str] = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_HEADERS", "*").split(",")
    )


'''
    
    # Insert CORS config before the Config class
    content = content.replace('class Config(BaseModel):', cors_class + 'class Config(BaseModel):')
    print("✅ CorsConfig class added")
else:
    print("✅ CorsConfig class already exists")

# Second, add cors attribute to Config class if it doesn't exist
if "cors: CorsConfig" not in content:
    print("Adding cors attribute to Config class...")
    # Find the timezone line and add cors after it
    content = content.replace(
        'timezone: TimezoneConfig = TimezoneConfig()',
        'timezone: TimezoneConfig = TimezoneConfig()\n    cors: CorsConfig = CorsConfig()'
    )
    print("✅ cors attribute added to Config class")
else:
    print("✅ cors attribute already exists in Config class")

# Create backup
backup_path = config_path + ".backup"
with open(backup_path, "w") as f:
    with open(config_path, "r") as original:
        f.write(original.read())
print(f"✅ Backup created: {backup_path}")

# Write the updated content back
with open(config_path, "w") as f:
    f.write(content)

print("🎉 CORS configuration fix applied successfully!")
print("")
print("🚀 The API should now restart without the AttributeError!")
print("")
print("🔧 CORS Environment Variables (with defaults):")
print("  - AUTOMAGIK_OMNI_CORS_ORIGINS=* (comma-separated)")
print("  - AUTOMAGIK_OMNI_CORS_CREDENTIALS=true")  
print("  - AUTOMAGIK_OMNI_CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS")
print("  - AUTOMAGIK_OMNI_CORS_HEADERS=* (comma-separated)")
print("")
print("🔍 Verify the fix with: python3 test_config.py")