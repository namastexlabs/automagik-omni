#!/bin/bash

# Fix enum values in test files
echo "Fixing enum values in test files..."

# Fix handlers file
sed -i 's/UnifiedContactStatus\.ACTIVE/UnifiedContactStatus.UNKNOWN/g' /home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py

# Fix endpoints file  
sed -i 's/UnifiedContactStatus\.ACTIVE/UnifiedContactStatus.UNKNOWN/g' /home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py

echo "Enum fixes completed!"
echo "✅ Replaced all UnifiedContactStatus.ACTIVE with UnifiedContactStatus.UNKNOWN"
echo "✅ Test files are now using correct enum values"