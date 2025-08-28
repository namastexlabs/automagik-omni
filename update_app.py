#!/usr/bin/env python3
"""Script to update app.py with unified endpoints registration."""

def main():
    app_file = "src/api/app.py"
    
    # Read the file
    with open(app_file, 'r') as f:
        lines = f.readlines()
    
    # Find and update the OpenAPI tags section
    for i, line in enumerate(lines):
        if '"name": "health",' in line and i < len(lines) - 2:
            # Found the health tag, look for the closing bracket
            if '"description": "System Health & Status",' in lines[i+1] and '}' in lines[i+2]:
                # Insert the unified tag before the closing bracket
                lines[i+2] = lines[i+2].replace('}', '},\n        {\n            "name": "unified",\n            "description": "Unified Multi-Channel Operations",\n        }')
                print("✅ Added unified tag to OpenAPI tags")
                break
    
    # Find and update the router inclusion section
    for i, line in enumerate(lines):
        if 'logger.error(traceback.format_exc())' in line:
            # Check if this is after the messages router section
            if i > 0 and any('messages_router' in lines[j] for j in range(max(0, i-10), i)):
                # Insert the unified router inclusion after this line
                unified_router_code = '''
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
                lines.insert(i+1, unified_router_code)
                print("✅ Added unified router inclusion")
                break
    
    # Write the updated file
    with open(app_file, 'w') as f:
        f.writelines(lines)
    
    print("✅ Successfully updated src/api/app.py")

if __name__ == "__main__":
    main()