#!/usr/bin/env python3
import sys
import os

# Change to the project directory
os.chdir('/home/cezar/automagik/automagik-omni')

# Read the app.py file
try:
    with open('src/api/app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"Original file size: {len(content)} characters")
    
    # Change 1: Add unified tag to OpenAPI tags
    old_health_tag = '''        {
            "name": "health",
            "description": "System Health & Status",
        }
    ],'''
    
    new_tags_section = '''        {
            "name": "health",
            "description": "System Health & Status",
        },
        {
            "name": "unified",
            "description": "Unified Multi-Channel Operations",
        }
    ],'''
    
    if old_health_tag in content:
        content = content.replace(old_health_tag, new_tags_section)
        print("✅ Step 1: Added unified tag to OpenAPI tags")
    else:
        print("❌ Step 1: Could not find OpenAPI tags section")
        
    # Change 2: Add unified router inclusion
    old_messages_end = '''    logger.error(traceback.format_exc())

# Add request logging middleware'''
    
    new_section_with_unified = '''    logger.error(traceback.format_exc())

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
    
    if old_messages_end in content:
        content = content.replace(old_messages_end, new_section_with_unified)
        print("✅ Step 2: Added unified router inclusion")
    else:
        print("❌ Step 2: Could not find router inclusion section")
    
    # Write the updated content back
    with open('src/api/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated file size: {len(content)} characters")
    print("✅ Successfully updated src/api/app.py with unified endpoints registration!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)