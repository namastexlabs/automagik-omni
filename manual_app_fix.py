#!/usr/bin/env python3
"""
Manually fix the app.py file by making the necessary changes
"""

def main():
    app_file = "/home/cezar/automagik/automagik-omni/src/api/app.py"
    
    print("Reading app.py...")
    with open(app_file, 'r') as f:
        lines = f.readlines()
    
    # Find the line with instances import and add unified import after it
    for i, line in enumerate(lines):
        if "from src.api.routes.instances import router as instances_router" in line:
            if i + 1 < len(lines) and "from src.api.routes.unified import router as unified_router" not in lines[i + 1]:
                lines.insert(i + 1, "from src.api.routes.unified import router as unified_router\n")
                print(f"✅ Added unified import at line {i + 2}")
                break
    
    # Find the router registration and add unified router
    for i, line in enumerate(lines):
        if 'app.include_router(instances_router, prefix="/api/v1", tags=["instances"])' in line:
            if i + 1 < len(lines) and "unified_router" not in lines[i + 1]:
                lines.insert(i + 1, "# Include unified endpoints routes\n")
                lines.insert(i + 2, 'app.include_router(unified_router, prefix="/api/v1/instances", tags=["unified-instances"])\n')
                print(f"✅ Added unified router registration at lines {i + 2}-{i + 3}")
                break
    
    print("Writing fixed app.py...")
    with open(app_file, 'w') as f:
        f.writelines(lines)
    
    print("✅ App.py has been fixed!")

if __name__ == "__main__":
    main()