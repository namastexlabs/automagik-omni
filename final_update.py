#!/usr/bin/env python3
"""Final script to update app.py with unified endpoint registration."""

import os

# Ensure we're in the right directory
os.chdir('/home/cezar/automagik/automagik-omni')

# Read the current file
with open('src/api/app.py', 'r') as f:
    content = f.read()

original_length = len(content)
changes_made = 0

# Change 1: Add unified tag to OpenAPI tags (exact match from grep output)
old_tags_pattern = '''            "description": "System Health & Status",
        }
    ],'''

new_tags_pattern = '''            "description": "System Health & Status",
        },
        {
            "name": "unified",
            "description": "Unified Multi-Channel Operations",
        }
    ],'''

if old_tags_pattern in content:
    content = content.replace(old_tags_pattern, new_tags_pattern)
    changes_made += 1
    print("✅ Change 1: Added unified tag to OpenAPI tags section")
else:
    print("❌ Change 1: Could not find OpenAPI tags pattern")

# Change 2: Add unified router inclusion (exact match from grep output)
old_router_pattern = '''    logger.error(traceback.format_exc())

# Add request logging middleware'''

new_router_pattern = '''    logger.error(traceback.format_exc())

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

if old_router_pattern in content:
    content = content.replace(old_router_pattern, new_router_pattern)
    changes_made += 1
    print("✅ Change 2: Added unified router inclusion after messages router")
else:
    print("❌ Change 2: Could not find router pattern")

# Write the updated content
if changes_made > 0:
    with open('src/api/app.py', 'w') as f:
        f.write(content)
    
    print(f"\n✅ Successfully updated src/api/app.py!")
    print(f"   - Made {changes_made} changes")
    print(f"   - Original size: {original_length} characters")
    print(f"   - Updated size: {len(content)} characters")
    print(f"   - Size difference: +{len(content) - original_length} characters")
else:
    print("❌ No changes were made to the file")

# Verify the changes by checking if unified tag and router are present
verification_content = content
if '"name": "unified"' in verification_content:
    print("✓ Verified: Unified tag found in OpenAPI tags")
else:
    print("✗ Verification failed: Unified tag not found")

if 'from src.api.routes.unified import router as unified_router' in verification_content:
    print("✓ Verified: Unified router import found")
else:
    print("✗ Verification failed: Unified router import not found")

if 'app.include_router(unified_router, prefix="/api/v1", tags=["unified"])' in verification_content:
    print("✓ Verified: Unified router registration found")
else:
    print("✗ Verification failed: Unified router registration not found")