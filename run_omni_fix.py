#!/usr/bin/env python3
import subprocess
import sys
import os

# Change to the project directory
os.chdir('/home/cezar/automagik/automagik-omni')

# Execute the fix script
result = subprocess.run([sys.executable, 'fix_omni_test_endpoints.py'], 
                       capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)
print(f"Return code: {result.returncode}")