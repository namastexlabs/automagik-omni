#!/usr/bin/env python3
"""
Script to fix the missing unified routes in app.py
"""

def fix_app_py():
    app_file = "/home/cezar/automagik/automagik-omni/src/api/app.py"
    
    # Read the file
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Add unified router import
    old_import = "from src.api.routes.instances import router as instances_router"
    new_import = """from src.api.routes.instances import router as instances_router
from src.api.routes.unified import router as unified_router"""
    
    content = content.replace(old_import, new_import)
    
    # Fix 2: Add unified router registration
    old_router_registration = """# Include instance management routes
app.include_router(instances_router, prefix="/api/v1", tags=["instances"])"""
    
    new_router_registration = """# Include instance management routes
app.include_router(instances_router, prefix="/api/v1", tags=["instances"])
# Include unified endpoints routes
app.include_router(unified_router, prefix="/api/v1/instances", tags=["unified-instances"])"""
    
    content = content.replace(old_router_registration, new_router_registration)
    
    # Write back the file
    with open(app_file, 'w') as f:
        f.write(content)
    
    print("✅ Fixed app.py - added unified router import and registration")

if __name__ == "__main__":
    fix_app_py()