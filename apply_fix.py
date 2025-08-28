import sys
import os

# Change to the correct directory
os.chdir('/home/cezar/automagik/automagik-omni')

# Read current content
with open('src/api/app.py', 'r') as f:
    content = f.read()

# Check if already fixed
if 'from src.api.routes.unified import router as unified_router' in content:
    print("✅ Unified router import already exists")
    exit(0)

# Fix 1: Add unified router import after instances router import
import_pattern = 'from src.api.routes.instances import router as instances_router\nfrom src.db.database import create_tables'
import_replacement = 'from src.api.routes.instances import router as instances_router\nfrom src.api.routes.unified import router as unified_router\nfrom src.db.database import create_tables'

content = content.replace(import_pattern, import_replacement)

# Fix 2: Add unified router registration after instances router registration
router_pattern = '# Include instance management routes\napp.include_router(instances_router, prefix="/api/v1", tags=["instances"])'
router_replacement = '# Include instance management routes\napp.include_router(instances_router, prefix="/api/v1", tags=["instances"])\n# Include unified endpoints routes\napp.include_router(unified_router, prefix="/api/v1", tags=["instances"])'

content = content.replace(router_pattern, router_replacement)

# Write back to file
with open('src/api/app.py', 'w') as f:
    f.write(content)

print("✅ Fixed app.py with unified router!")
print("✓ Added import: from src.api.routes.unified import router as unified_router") 
print("✓ Added registration: app.include_router(unified_router, prefix='/api/v1', tags=['instances'])")