#!/usr/bin/env python3
import subprocess
import sys

# Run the fix script
try:
    result = subprocess.run([sys.executable, "fix_tests.py"], 
                          cwd="/home/cezar/automagik/automagik-omni",
                          capture_output=True, text=True)
    print("Fix script output:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
    print(f"Exit code: {result.returncode}")
except Exception as e:
    print(f"Error running fix script: {e}")