#!/bin/bash
# Backup original file
cp tests/test_unified_handlers.py tests/test_unified_handlers_backup.py
echo "Created backup: tests/test_unified_handlers_backup.py"

# Replace with fixed version
cp tests/test_unified_handlers_fixed.py tests/test_unified_handlers.py
echo "Applied fixes to tests/test_unified_handlers.py"

# Verify the file was updated
echo "Verification - checking for PropertyMock import:"
grep -n "PropertyMock" tests/test_unified_handlers.py

echo "Verification - checking for _bot_instances usage:"
grep -n "_bot_instances" tests/test_unified_handlers.py

echo "Discord test fixes applied successfully!"