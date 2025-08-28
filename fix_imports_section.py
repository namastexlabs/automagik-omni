#!/usr/bin/env python3
"""Fix the imports and router registration in app.py"""
import re

def apply_fix():
    app_file = "/home/cezar/automagik/automagik-omni/src/api/app.py"
    
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Add unified router import
    original_import = "from src.api.routes.instances import router as instances_router"
    if "from src.api.routes.unified import router as unified_router" not in content:
        content = content.replace(
            original_import,
            original_import + "\nfrom src.api.routes.unified import router as unified_router"
        )
        print("✅ Added unified router import")
    
    # Fix 2: Add unified router registration  
    router_pattern = r'(# Include instance management routes\napp\.include_router\(instances_router, prefix="/api/v1", tags=\["instances"\]\))'
    if "app.include_router(unified_router" not in content:
        replacement = r'\1\n# Include unified endpoints routes\napp.include_router(unified_router, prefix="/api/v1/instances", tags=["unified-instances"])'
        content = re.sub(router_pattern, replacement, content)
        print("✅ Added unified router registration")
    
    with open(app_file, 'w') as f:
        f.write(content)
    
    print("✅ Fix applied successfully")

if __name__ == "__main__":
    apply_fix()