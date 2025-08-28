#!/usr/bin/env python3

# Quick script to fix the missing unified router in app.py

import sys

# Read the original file
with open('src/api/app.py', 'r') as f:
    content = f.read()

# Make the first replacement - add unified router import
content = content.replace(
    "from src.api.routes.instances import router as instances_router\nfrom src.db.database import create_tables",
    "from src.api.routes.instances import router as instances_router\nfrom src.api.routes.unified import router as unified_router\nfrom src.db.database import create_tables"
)

# Make the second replacement - add unified router registration
content = content.replace(
    "# Include instance management routes\napp.include_router(instances_router, prefix=\"/api/v1\", tags=[\"instances\"])",
    "# Include instance management routes\napp.include_router(instances_router, prefix=\"/api/v1\", tags=[\"instances\"])\n# Include unified endpoints routes\napp.include_router(unified_router, prefix=\"/api/v1\", tags=[\"instances\"])"
)

# Write the modified content back to the file
with open('src/api/app.py', 'w') as f:
    f.write(content)

print("✅ Successfully added unified router import and registration to src/api/app.py")
print("Changes made:")
print("1. Added 'from src.api.routes.unified import router as unified_router'")
print("2. Added 'app.include_router(unified_router, prefix=\"/api/v1\", tags=[\"instances\"])'")