#!/bin/bash
set -e

echo "🔧 Applying CORS configuration fix..."

cd /home/cezar/automagik/automagik-omni

# Create backup
cp src/config.py src/config.py.backup_$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"

# Apply the fix by copying the corrected version
cp src/config_fixed.py src/config.py
echo "✅ CORS configuration fix applied"

# Verify the fix
if grep -q "class CorsConfig" src/config.py && grep -q "cors: CorsConfig" src/config.py; then
    echo "✅ Fix verified: CorsConfig class and cors attribute found"
    echo ""
    echo "🎉 CORS Fix Complete!"
    echo "🚀 PM2 should now restart the API successfully!"
    echo ""
    echo "🔧 CORS Environment Variables (defaults shown):"
    echo "  - AUTOMAGIK_OMNI_CORS_ORIGINS=*"
    echo "  - AUTOMAGIK_OMNI_CORS_CREDENTIALS=true"
    echo "  - AUTOMAGIK_OMNI_CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS"
    echo "  - AUTOMAGIK_OMNI_CORS_HEADERS=*"
    echo ""
    echo "✨ The AttributeError should be resolved!"
else
    echo "❌ Fix verification failed - please check the files manually"
    exit 1
fi