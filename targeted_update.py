#!/usr/bin/env python3

# Read the current file
with open('src/api/app.py', 'r') as f:
    content = f.read()

# Replace the OpenAPI tags section
old_health_tag = '''        {
            "name": "health",
            "description": "System Health & Status",
        }
    ],'''

new_health_and_unified_tags = '''        {
            "name": "health",
            "description": "System Health & Status",
        },
        {
            "name": "unified",
            "description": "Unified Multi-Channel Operations",
        }
    ],'''

content = content.replace(old_health_tag, new_health_and_unified_tags)

# Replace the router section after messages router
old_section = '''    logger.error(traceback.format_exc())

# Add request logging middleware'''

new_section = '''    logger.error(traceback.format_exc())

# Include unified multi-channel routes
try:
    from src.api.routes.unified import router as unified_router

    app.include_router(unified_router, prefix="/api/v1", tags=["unified"])
    logger.info("✅ Unified multi-channel routes included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include unified router: {e}")
    import traceback

    logger.error(traceback.format_exc())

# Add request logging middleware'''

content = content.replace(old_section, new_section)

# Write the updated content
with open('src/api/app.py', 'w') as f:
    f.write(content)

print("✅ Updated src/api/app.py successfully!")
print("✅ Added unified tag to OpenAPI tags")
print("✅ Added unified router inclusion after messages router")