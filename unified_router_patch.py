#!/usr/bin/env python3
"""
Script to add the unified router to the FastAPI app
"""

# Read the current app.py
with open('/home/cezar/automagik/automagik-omni/src/api/app.py', 'r') as f:
    content = f.read()

# Define the insertion point and new content
insertion_marker = "    logger.error(traceback.format_exc())\n\n# Add request logging middleware"
unified_router_section = '''    logger.error(traceback.format_exc())

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

# Perform the replacement
if insertion_marker in content:
    content = content.replace(insertion_marker, unified_router_section)
    print("✅ Added unified router to app.py")
else:
    print("❌ Could not find insertion point in app.py")
    
# Write the updated content back
with open('/home/cezar/automagik/automagik-omni/src/api/app.py', 'w') as f:
    f.write(content)

print("✅ Unified router registration completed!")