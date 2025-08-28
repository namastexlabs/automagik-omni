#!/usr/bin/env python3
import os
import sys

# Add current directory to path
sys.path.insert(0, '/home/cezar/automagik/automagik-omni')

# Import and run the fix
from nuclear_fix_asyncmock import fix_conftest_asyncmock

if __name__ == "__main__":
    success = fix_conftest_asyncmock()
    if success:
        print("\n🎯 MISSION ACCOMPLISHED!")
        print("The AsyncMock persistence issue has been surgically eliminated.")
        print("Tests should now run without 'coroutine never awaited' warnings.")
    else:
        print("\n❌ MISSION FAILED!")
        print("The pattern was not found. Please check the conftest.py file manually.")