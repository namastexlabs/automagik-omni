#!/usr/bin/env python3
"""Direct file modification"""

# Read the file
with open('src/api/app.py', 'r') as f:
    lines = f.readlines()

# Find the line with health tag and add unified tag
for i, line in enumerate(lines):
    if '"name": "health",' in line:
        # Find the corresponding closing bracket
        j = i
        while j < len(lines) and '}' not in lines[j]:
            j += 1
        if j < len(lines) and '}' in lines[j] and j + 1 < len(lines) and '],' in lines[j + 1]:
            # Replace the } with },
            lines[j] = lines[j].replace('}', '},')
            # Insert unified tag lines after the health closing brace
            unified_lines = [
                '        {\n',
                '            "name": "unified",\n',
                '            "description": "Unified Multi-Channel Operations",\n',
                '        }\n'
            ]
            for k, unified_line in enumerate(unified_lines):
                lines.insert(j + 1 + k, unified_line)
            print("✅ Added unified tag to OpenAPI tags")
            break

# Find where to add the unified router
for i, line in enumerate(lines):
    if 'logger.error(traceback.format_exc())' in line:
        # Check if this is in the messages router section
        context = ''.join(lines[max(0, i-10):i+1])
        if 'messages_router' in context:
            # Insert unified router code after this line
            router_lines = [
                '\n',
                '# Include unified multi-channel routes\n',
                'try:\n',
                '    from src.api.routes.unified import router as unified_router\n',
                '\n',
                '    app.include_router(unified_router, prefix="/api/v1", tags=["unified"])\n',
                '    logger.info("✅ Unified multi-channel routes included successfully")\n',
                'except Exception as e:\n',
                '    logger.error(f"❌ Failed to include unified router: {e}")\n',
                '    import traceback\n',
                '\n',
                '    logger.error(traceback.format_exc())\n'
            ]
            for k, router_line in enumerate(router_lines):
                lines.insert(i + 1 + k, router_line)
            print("✅ Added unified router inclusion")
            break

# Write the updated file
with open('src/api/app.py', 'w') as f:
    f.writelines(lines)

print("✅ Successfully updated src/api/app.py")