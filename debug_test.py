#!/usr/bin/env python3

import os
import sys

# Add the project root to the Python path
project_root = "/home/cezar/automagik/automagik-omni"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.chdir(project_root)

# Set environment variables
os.environ['PYTHONPATH'] = project_root
os.environ['API_KEY'] = 'test-key'

import subprocess

def run_single_test():
    """Run the failing test with verbose output to see the actual error"""
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_omni_endpoints_fixed.py::TestOmniEndpointsAuthentication::test_channels_endpoint_requires_auth",
        "-vvv", "--tb=short", "--no-header"
    ]
    
    print(f"🔍 Running: {' '.join(cmd)}")
    print("=" * 80)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print(f"\n✅ Exit Code: {result.returncode}")
        return result.returncode
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out!")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_single_test()
    sys.exit(exit_code)