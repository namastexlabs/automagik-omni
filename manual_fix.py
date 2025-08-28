#!/usr/bin/env python3

def fix_app_file():
    file_path = "/home/cezar/automagik/automagik-omni/src/api/app.py"
    
    # Read the file
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find the import line and add the unified router import after it
    for i, line in enumerate(lines):
        if "from src.api.routes.instances import router as instances_router" in line:
            lines.insert(i + 1, "from src.api.routes.unified import router as unified_router\n")
            print(f"✅ Added unified router import at line {i + 2}")
            break
    
    # Find the router registration and add unified router after it
    for i, line in enumerate(lines):
        if 'app.include_router(instances_router, prefix="/api/v1", tags=["instances"])' in line:
            lines.insert(i + 1, '# Include unified endpoints routes\n')
            lines.insert(i + 2, 'app.include_router(unified_router, prefix="/api/v1/instances", tags=["unified-instances"])\n')
            print(f"✅ Added unified router registration at lines {i + 2}-{i + 3}")
            break
    
    # Write back the file
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    print("✅ Successfully fixed app.py")

if __name__ == "__main__":
    fix_app_file()