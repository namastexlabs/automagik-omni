#!/usr/bin/env python3
"""
Quick fix script to add CORS configuration to config.py
"""

def fix_cors_config():
    config_path = "/home/cezar/automagik/automagik-omni/src/config.py"
    
    # Read the current config file
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Check if CorsConfig already exists
    if 'class CorsConfig' in content:
        print("CorsConfig already exists in config.py")
        return
    
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
    
    # Insert CorsConfig before Config class
    content = content.replace('class Config(BaseModel):', cors_config_class + 'class Config(BaseModel):')
    
    # Add cors attribute to Config class
    content = content.replace(
        'timezone: TimezoneConfig = TimezoneConfig()',
        'timezone: TimezoneConfig = TimezoneConfig()\n    cors: CorsConfig = CorsConfig()'
    )
    
    # Write the fixed content back
    with open(config_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed CORS configuration in config.py")
    print("Added CorsConfig class and cors attribute to Config class")

if __name__ == "__main__":
    fix_cors_config()