#!/bin/bash
# Script to apply unified endpoint changes to app.py

cd /home/cezar/automagik/automagik-omni

echo "Applying changes to src/api/app.py..."

# Backup the original file
cp src/api/app.py src/api/app.py.backup

# Apply the changes using sed
echo "Step 1: Adding unified tag to OpenAPI tags..."
sed -i '/\"description\": \"System Health & Status\",/{
N
s/\"description\": \"System Health & Status\",\n        }\n    ],/\"description\": \"System Health & Status\",\n        },\n        {\n            \"name\": \"unified\",\n            \"description\": \"Unified Multi-Channel Operations\",\n        }\n    ],/
}' src/api/app.py

echo "Step 2: Adding unified router inclusion..."
# Find the line after messages router traceback and insert unified router code
sed -i '/logger\.error(traceback\.format_exc())/a\
\
# Include unified multi-channel routes\
try:\
    from src.api.routes.unified import router as unified_router\
\
    app.include_router(unified_router, prefix="/api/v1", tags=["unified"])\
    logger.info("✅ Unified multi-channel routes included successfully")\
except Exception as e:\
    logger.error(f"❌ Failed to include unified router: {e}")\
    import traceback\
\
    logger.error(traceback.format_exc())' src/api/app.py

echo "✅ Changes applied successfully!"

# Verify the changes
if grep -q '"name": "unified"' src/api/app.py; then
    echo "✓ Verification: Unified tag found in OpenAPI tags"
else
    echo "✗ Verification: Unified tag not found"
fi

if grep -q "from src.api.routes.unified import router as unified_router" src/api/app.py; then
    echo "✓ Verification: Unified router import found"
else
    echo "✗ Verification: Unified router import not found"
fi

echo "Done!"