#!/usr/bin/env python3
import subprocess

# First fix the import
result = subprocess.run([
    'sed', '-i', 
    's/from src\\.api\\.routes\\.instances import router as instances_router/from src.api.routes.instances import router as instances_router\\nfrom src.api.routes.unified import router as unified_router/',
    '/home/cezar/automagik/automagik-omni/src/api/app.py'
], capture_output=True, text=True)

print(f"Import fix result: {result.returncode}")
if result.stderr:
    print(f"Error: {result.stderr}")

# Then fix the router registration  
result = subprocess.run([
    'sed', '-i', 
    's/# Include instance management routes\\napp\\.include_router(instances_router, prefix="\\/api\\/v1", tags=\\["instances"\\])/# Include instance management routes\\napp.include_router(instances_router, prefix="\\/api\\/v1", tags=["instances"])\\n# Include unified endpoints routes\\napp.include_router(unified_router, prefix="\\/api\\/v1\\/instances", tags=["unified-instances"])/',
    '/home/cezar/automagik/automagik-omni/src/api/app.py'
], capture_output=True, text=True)

print(f"Router fix result: {result.returncode}")
if result.stderr:
    print(f"Error: {result.stderr}")