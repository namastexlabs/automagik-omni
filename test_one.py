#!/usr/bin/env python3

import subprocess
import sys
import os

def run_single_test():
    """Run a single target test to see the error"""
    os.chdir('/home/cezar/automagik/automagik-omni')
    
    print("🧪 Running single test to see current errors...")
    
    cmd = [
        "python3", "-m", "pytest", 
        "tests/test_omni_endpoints.py::TestOmniChannelsEndpoint::test_successful_channels_retrieval",
        "-v", "--tb=short", "-s"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        print("=== STDOUT ===")
        print(result.stdout)
        print("\n=== STDERR ===")
        print(result.stderr)
        print(f"\n=== Return code: {result.returncode} ===")
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_single_test()