#!/usr/bin/env python3

# Read the original file line by line and make targeted changes
with open('src/api/app.py', 'r') as f:
    lines = f.readlines()

# Find and modify the import line
for i, line in enumerate(lines):
    if line.strip() == "from src.api.routes.instances import router as instances_router":
        # Insert the unified router import after this line
        lines.insert(i + 1, "from src.api.routes.unified import router as unified_router\n")
        break

# Find and modify the router registration
for i, line in enumerate(lines):
    if line.strip() == "app.include_router(instances_router, prefix=\"/api/v1\", tags=[\"instances\"])":
        # Insert the unified router registration after this line
        lines.insert(i + 1, "# Include unified endpoints routes\n")
        lines.insert(i + 2, "app.include_router(unified_router, prefix=\"/api/v1\", tags=[\"instances\"])\n")
        break

# Write the modified content back
with open('src/api/app.py', 'w') as f:
    f.writelines(lines)

print("✅ Fixed src/api/app.py with unified router import and registration!")