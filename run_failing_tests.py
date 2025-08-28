#!/usr/bin/env python3
"""
Run specific failing tests and capture output.
"""
import subprocess
import sys
import os

# Set the working directory to the project root
os.chdir("/home/cezar/automagik/automagik-omni")

# List of failing tests
failing_tests = [
    "tests/test_omni_endpoints_fixed.py::TestOmniEndpointsAuthentication::test_channels_endpoint_requires_auth",
    "tests/test_omni_endpoints_fixed.py::TestOmniContactsEndpoint::test_successful_contacts_retrieval",
    "tests/test_omni_endpoints_fixed.py::TestOmniContactsEndpoint::test_contacts_pagination_edge_cases",
    "tests/test_omni_endpoints_fixed.py::TestOmniContactsEndpoint::test_contacts_with_search_query",
    "tests/test_omni_endpoints_fixed.py::TestOmniChatsEndpoint::test_successful_chats_retrieval",
    "tests/test_omni_endpoints_fixed.py::TestOmniChannelsEndpoint::test_successful_channels_retrieval"
]

try:
    # Run pytest with verbose output
    cmd = ["python3", "-m", "pytest"] + failing_tests + ["-v", "--tb=short"]
    
    print(f"Running command: {' '.join(cmd)}")
    print("=" * 80)
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")
    
except subprocess.TimeoutExpired:
    print("ERROR: Test execution timed out after 5 minutes")
except Exception as e:
    print(f"ERROR: Failed to run tests: {e}")

sys.exit(0)