#!/usr/bin/env python3
"""Simple script to fix CORS configuration by reading and modifying the existing config.py"""

config_file = "/home/cezar/automagik/automagik-omni/src/config.py"

# Read current content
with open(config_file, 'r') as f:
    content = f.read()

print("Current config file read successfully...")

# Check if CorsConfig already exists
if 'class CorsConfig' in content:
    print("CorsConfig class already exists!")
else:
    print("Adding CorsConfig class...")
    
    # Add CorsConfig class before Config class
    cors_config_class = '''
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
    
    content = content.replace('class Config(BaseModel):', cors_config_class + 'class Config(BaseModel):')

# Check if cors attribute exists in Config class
if 'cors: CorsConfig = CorsConfig()' in content:
    print("CORS attribute already exists in Config class!")
else:
    print("Adding cors attribute to Config class...")
    content = content.replace(
        'timezone: TimezoneConfig = TimezoneConfig()',
        'timezone: TimezoneConfig = TimezoneConfig()\n    cors: CorsConfig = CorsConfig()'
    )

# Write back the modified content
with open(config_file, 'w') as f:
    f.write(content)

print("✅ CORS configuration fix applied!")
print("🚀 The API should restart successfully now!")