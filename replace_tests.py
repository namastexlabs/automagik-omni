#!/usr/bin/env python3
"""Replace test file with fixed version."""

import shutil
import os

# Replace the original test file with the fixed version
shutil.copy('tests/test_omni_transformers_fixed.py', 'tests/test_omni_transformers.py')
print("✅ Replaced tests/test_omni_transformers.py with fixed version")

# Clean up temporary file
if os.path.exists('tests/test_omni_transformers_fixed.py'):
    os.remove('tests/test_omni_transformers_fixed.py')
    print("✅ Cleaned up temporary file")

print("\n🎉 All test fixes applied successfully!")