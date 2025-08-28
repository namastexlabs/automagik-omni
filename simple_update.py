#!/usr/bin/env python3
import re

# Read the file
with open('src/api/app.py', 'r') as f:
    content = f.read()

# First replacement: Add unified tag to OpenAPI tags
old_tags_pattern = r'(\s+{\s+"name":\s+"health",\s+"description":\s+"System Health & Status",\s+})\s*\],'
new_tags = r'\1,\n        {\n            "name": "unified",\n            "description": "Unified Multi-Channel Operations",\n        }\n    ],'
content = re.sub(old_tags_pattern, new_tags, content)

# Second replacement: Add unified router after messages router
old_router_pattern = r'(\s+logger\.error\(traceback\.format_exc\(\)\))\n(\n# Add request logging middleware)'
new_router = r'''\1

# Include unified multi-channel routes
try:
    from src.api.routes.unified import router as unified_router

    app.include_router(unified_router, prefix="/api/v1", tags=["unified"])
    logger.info("✅ Unified multi-channel routes included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include unified router: {e}")
    import traceback

    logger.error(traceback.format_exc())
\2'''
content = re.sub(old_router_pattern, new_router, content)

# Write back
with open('src/api/app.py', 'w') as f:
    f.write(content)

print("Updated src/api/app.py successfully!")