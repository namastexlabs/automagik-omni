"""
Manual patch to fix app.py by adding the missing unified router
"""

import os

def patch_app():
    app_path = "/home/cezar/automagik/automagik-omni/src/api/app.py"
    
    # Read original file
    with open(app_path, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if "from src.api.routes.unified import router as unified_router" in content:
        print("✅ App.py already patched with unified router import")
    else:
        # Add the unified router import
        content = content.replace(
            "from src.api.routes.instances import router as instances_router",
            "from src.api.routes.instances import router as instances_router\nfrom src.api.routes.unified import router as unified_router"
        )
        print("✅ Added unified router import")
    
    if 'app.include_router(unified_router' in content:
        print("✅ App.py already patched with unified router registration")
    else:
        # Add the unified router registration
        content = content.replace(
            'app.include_router(instances_router, prefix="/api/v1", tags=["instances"])',
            'app.include_router(instances_router, prefix="/api/v1", tags=["instances"])\n# Include unified endpoints routes\napp.include_router(unified_router, prefix="/api/v1/instances", tags=["unified-instances"])'
        )
        print("✅ Added unified router registration")
    
    # Write back
    with open(app_path, 'w') as f:
        f.write(content)
    
    print("✅ App.py patching complete!")

if __name__ == "__main__":
    patch_app()