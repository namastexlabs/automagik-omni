#!/usr/bin/env python3
"""
Updated sections for app.py file
"""

# This is the corrected OpenAPI tags section (around line 246-271)
openapi_tags_section = '''    openapi_tags=[
        {
            "name": "instances",
            "description": "Instance Management",
        },
        {
            "name": "messages", 
            "description": "Message Operations",
        },
        {
            "name": "traces",
            "description": "Message Tracing & Analytics", 
        },
        {
            "name": "webhooks",
            "description": "Webhook Receivers",
        },
        {
            "name": "profiles",
            "description": "User Profile Management",
        },
        {
            "name": "health",
            "description": "System Health & Status",
        },
        {
            "name": "unified",
            "description": "Unified Multi-Channel Operations",
        }
    ],'''

# This is the router inclusion section to add after messages router (around line 292)
unified_router_section = '''
# Include unified multi-channel routes
try:
    from src.api.routes.unified import router as unified_router

    app.include_router(unified_router, prefix="/api/v1", tags=["unified"])
    logger.info("✅ Unified multi-channel routes included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include unified router: {e}")
    import traceback

    logger.error(traceback.format_exc())
'''

# Now let's apply these changes to the actual file
with open('src/api/app.py', 'r') as f:
    content = f.read()

# First change: Update OpenAPI tags
old_tags = '''    openapi_tags=[
        {
            "name": "instances",
            "description": "Instance Management",
        },
        {
            "name": "messages", 
            "description": "Message Operations",
        },
        {
            "name": "traces",
            "description": "Message Tracing & Analytics", 
        },
        {
            "name": "webhooks",
            "description": "Webhook Receivers",
        },
        {
            "name": "profiles",
            "description": "User Profile Management",
        },
        {
            "name": "health",
            "description": "System Health & Status",
        }
    ],'''

content = content.replace(old_tags, openapi_tags_section)

# Second change: Add unified router after messages router
old_section = '''    logger.error(traceback.format_exc())

# Add request logging middleware'''

new_section = '''    logger.error(traceback.format_exc())
''' + unified_router_section + '''
# Add request logging middleware'''

content = content.replace(old_section, new_section)

# Write the updated content
with open('src/api/app.py', 'w') as f:
    f.write(content)

print("✅ Updated src/api/app.py successfully!")
print("✅ Added unified tag to OpenAPI tags")  
print("✅ Added unified router inclusion after messages router")