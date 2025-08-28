#!/usr/bin/env python3
"""
Simple script to run a single test and see the output
"""
import subprocess
import sys
import os

def run_single_test(test_path: str = None):
    """Run a single test with verbose output."""
    # Change to the project directory
    os.chdir('/home/cezar/automagik/automagik-omni')
    
    if test_path:
        cmd = ['python', '-m', 'pytest', test_path, '-v', '-s', '--tb=short']
    else:
        # Run a specific failing authentication test
        cmd = ['python', '-m', 'pytest', 
               'tests/test_unified_endpoints.py::TestUnifiedEndpointsAuthentication::test_contacts_endpoint_requires_auth', 
               '-v', '-s', '--tb=short']
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Test timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"Error running test: {e}")
        return False

if __name__ == "__main__":
    test_path = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_single_test(test_path)
    sys.exit(0 if success else 1)