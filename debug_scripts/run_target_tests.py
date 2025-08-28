#!/usr/bin/env python3

import subprocess
import sys

# Target failing tests
TARGET_TESTS = [
    "tests/test_omni_endpoints.py::TestOmniChannelsEndpoint::test_successful_channels_retrieval",
    "tests/test_omni_endpoints.py::TestOmniChannelsEndpoint::test_omni_channels_empty_database",
    "tests/test_omni_endpoints.py::TestOmniEndpointsErrorHandling::test_omni_database_connection_error_handling",
    "tests/test_omni_endpoints_fixed.py::TestOmniEndpointsAuthentication::test_channels_endpoint_requires_auth",
    "tests/test_omni_endpoints_fixed.py::TestOmniContactsEndpoint::test_contacts_with_search_query",
]

def run_tests():
    """Run the target failing tests"""
    print("🎯 Running target endpoint tests...")
    
    cmd = [
        "python3", "-m", "pytest",
        *TARGET_TESTS,
        "-v", "--tb=short", "-x"
    ]
    
    try:
        result = subprocess.run(cmd, cwd="/home/cezar/automagik/automagik-omni", 
                              capture_output=True, text=True, timeout=120)
        
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Test execution timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)