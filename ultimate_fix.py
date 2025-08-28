#!/usr/bin/env python3
# Ultimate CORS Configuration Fix
import os
import shutil

def apply_cors_fix():
    config_file = "/home/cezar/automagik/automagik-omni/src/config.py"
    backup_file = config_file + ".pre_cors_fix"
    
    # Create backup
    if not os.path.exists(backup_file):
        shutil.copy2(config_file, backup_file)
        print(f"✅ Backup created: {backup_file}")
    
    # Read current content
    with open(config_file, 'r') as f:
        content = f.read()
    
    print("Current config.py read successfully")
    
    # Check if already fixed
    if 'class CorsConfig' in content and 'cors: CorsConfig' in content:
        print("✅ CORS configuration already applied!")
        return True
    
    # Apply fixes
    modified = False
    
    # 1. Add CorsConfig class if missing
    if 'class CorsConfig' not in content:
        cors_config_class = '''class CorsConfig(BaseModel):
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
        # Insert before Config class
        content = content.replace('class Config(BaseModel):', cors_config_class + 'class Config(BaseModel):')
        print("✅ Added CorsConfig class")
        modified = True
    
    # 2. Add cors attribute if missing
    if 'cors: CorsConfig' not in content:
        content = content.replace(
            'timezone: TimezoneConfig = TimezoneConfig()',
            'timezone: TimezoneConfig = TimezoneConfig()\n    cors: CorsConfig = CorsConfig()'
        )
        print("✅ Added cors attribute to Config class")
        modified = True
    
    if modified:
        # Write the fixed content back
        with open(config_file, 'w') as f:
            f.write(content)
        print("✅ CORS configuration fix applied successfully!")
        return True
    else:
        print("ℹ️ No modifications needed")
        return False

if __name__ == "__main__":
    success = apply_cors_fix()
    if success:
        print("\n🎉 CORS Fix Complete!")
        print("🚀 PM2 should now restart the API successfully!")
        print("\n🔧 CORS Environment Variables (defaults shown):")
        print("  - AUTOMAGIK_OMNI_CORS_ORIGINS=*")
        print("  - AUTOMAGIK_OMNI_CORS_CREDENTIALS=true")
        print("  - AUTOMAGIK_OMNI_CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS")  
        print("  - AUTOMAGIK_OMNI_CORS_HEADERS=*")
        print("\n✨ The AttributeError: 'Config' object has no attribute 'cors' should be resolved!")