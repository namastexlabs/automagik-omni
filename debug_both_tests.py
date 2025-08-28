#!/usr/bin/env python3

import subprocess
import sys
import os

# Set up environment  
project_root = "/home/cezar/automagik/automagik-omni"
os.chdir(project_root)
os.environ['PYTHONPATH'] = project_root
os.environ['API_KEY'] = 'test-key'

def run_test(test_path, test_name):
    """Run a specific test and return the result"""
    cmd = [
        sys.executable, "-m", "pytest", 
        f"{test_path}::{test_name}",
        "-vvv", "--tb=short", "--no-header", "-q"
    ]
    
    print(f"\n🔍 Running {test_name}")
    print("=" * 80)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return None

def main():
    """Debug both failing tests"""
    tests = [
        ("tests/test_omni_endpoints_fixed.py", "TestOmniEndpointsAuthentication::test_channels_endpoint_requires_auth"),
        ("tests/test_omni_endpoints_fixed.py", "TestOmniContactsEndpoint::test_contacts_with_search_query")
    ]
    
    for test_path, test_name in tests:
        result = run_test(test_path, test_name)
        if result:
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            print("-" * 40)

if __name__ == "__main__":
    main()