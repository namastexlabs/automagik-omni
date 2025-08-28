#!/usr/bin/env python3
"""Quick test to verify the nuclear fix for Evolution API mocking."""

import subprocess
import sys
import os

# Set PYTHONPATH to include src
env = os.environ.copy()
if 'PYTHONPATH' not in env:
    env['PYTHONPATH'] = 'src'
else:
    env['PYTHONPATH'] = f"src:{env['PYTHONPATH']}"

def run_single_test():
    """Run a single test to verify the nuclear fix works."""
    cmd = [
        'python3', '-m', 'pytest', 
        'tests/test_omni_handlers.py::TestWhatsAppChatHandler::test_get_contacts_success',
        '-v', '--tb=short', '-x'
    ]
    
    print("🧪 Testing nuclear fix for Evolution API mocking...")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, cwd='/home/cezar/automagik/automagik-omni', 
                              env=env, capture_output=True, text=True, timeout=60)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n✅ NUCLEAR FIX SUCCESS: Test passed!")
            return True
        else:
            print(f"\n❌ NUCLEAR FIX FAILED: Test failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n⏱️ Test timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"\n💥 Error running test: {e}")
        return False

if __name__ == "__main__":
    success = run_single_test()
    sys.exit(0 if success else 1)