#!/usr/bin/env python3

# Execute the changes inline
content = open('src/api/app.py', 'r').read()

# Update OpenAPI tags section
old_tags = '''        {
            "name": "health",
            "description": "System Health & Status",
        }
    ],'''

new_tags = '''        {
            "name": "health",
            "description": "System Health & Status",
        },
        {
            "name": "unified",
            "description": "Unified Multi-Channel Operations",
        }
    ],'''

content = content.replace(old_tags, new_tags)

# Update router section
old_messages_end = '''    logger.error(traceback.format_exc())

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

content = content.replace(old_messages_end, new_section)

# Write back
with open('src/api/app.py', 'w') as f:
    f.write(content)

print("Updated successfully")