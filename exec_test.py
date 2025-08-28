#!/usr/bin/env python3

import os
import sys

# Set the working directory
os.chdir('/home/cezar/automagik/automagik-omni')

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

# Run the test
import subprocess
result = subprocess.run([
    sys.executable, '-m', 'pytest', 
    'tests/test_omni_handlers.py::TestDiscordChatHandler::test_get_contact_by_id_success',
    '-v', '--tb=short'
], capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")