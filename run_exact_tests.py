#!/usr/bin/env python3

import subprocess
import sys
import os

# Set up environment
project_root = "/home/cezar/automagik/automagik-omni"
os.chdir(project_root)
os.environ['PYTHONPATH'] = project_root
os.environ['API_KEY'] = 'test-key'

def run_specific_tests():
    """Run the exact two failing tests"""
    
    tests = [
        "tests/test_omni_endpoints_fixed.py::TestOmniEndpointsAuthentication::test_channels_endpoint_requires_auth",
        "tests/test_omni_endpoints_fixed.py::TestOmniContactsEndpoint::test_contacts_with_search_query"
    ]
    
    for i, test in enumerate(tests, 1):
        print(f"\n{'='*80}")
        print(f"🎯 Running Test {i}/2: {test.split('::')[-1]}")
        print('='*80)
        
        cmd = [
            sys.executable, "-m", "pytest", 
            test,
            "-vvv", "--tb=short", "--no-header", "-q"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            print(f"Exit Code: {result.returncode}")
            
            if result.stdout:
                print("\nSTDOUT:")
                print(result.stdout)
            if result.stderr:
                print("\nSTDERR:")  
                print(result.stderr)
                
        except subprocess.TimeoutExpired:
            print("❌ Test timed out!")
        except Exception as e:
            print(f"❌ Error running test: {e}")
        
        print("-" * 40)

if __name__ == "__main__":
    run_specific_tests()