#!/bin/bash

echo "Applying CORS configuration fix..."

# Backup the current config.py
cp src/config.py src/config.py.backup

# Replace with the fixed version
cp config_fixed.py src/config.py

echo "✅ CORS configuration fix applied successfully!"
echo "Original config.py backed up to src/config.py.backup"
echo ""
echo "The API should now restart successfully with CORS support."
echo "CORS configuration can be controlled via environment variables:"
echo "  - AUTOMAGIK_OMNI_CORS_ORIGINS (default: *)"
echo "  - AUTOMAGIK_OMNI_CORS_CREDENTIALS (default: true)"
echo "  - AUTOMAGIK_OMNI_CORS_METHODS (default: GET,POST,PUT,DELETE,OPTIONS)"
echo "  - AUTOMAGIK_OMNI_CORS_HEADERS (default: *)"