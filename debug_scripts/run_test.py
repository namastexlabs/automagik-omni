#!/usr/bin/env python3

import subprocess
import sys
import os

def run_test():
    """Run a specific test to understand the failure."""
    os.chdir('/home/cezar/automagik/automagik-omni')
    
    # Try to run the specific failing test
    try:
        result = subprocess.run([
            'python3', '-m', 'pytest', 
            'tests/test_omni_handlers.py::TestDiscordChatHandler::test_get_contact_by_id_success',
            '-v', '--tb=short'
        ], capture_output=True, text=True, timeout=60)
        
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")
        
    except Exception as e:
        print(f"Error running test: {e}")

if __name__ == "__main__":
    run_test()