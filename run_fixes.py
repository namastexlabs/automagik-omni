#!/usr/bin/env python3
import subprocess
import sys
import os

# Change to the project directory
os.chdir("/home/cezar/automagik/automagik-omni")

# Execute the fix script
try:
    result = subprocess.run([sys.executable, "fix_unified_endpoint_tests.py"], 
                          capture_output=True, text=True, check=True)
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
except subprocess.CalledProcessError as e:
    print(f"Error running fix script: {e}")
    print("STDOUT:", e.stdout)
    print("STDERR:", e.stderr)