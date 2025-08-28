#!/usr/bin/env python3

import subprocess
import sys

def run_failing_test():
    """Run the first failing test with maximum verbosity"""
    
    cmd = [
        "python3", "-m", "pytest", 
        "tests/test_omni_endpoints_fixed.py::TestOmniEndpointsAuthentication::test_channels_endpoint_requires_auth",
        "-vvv", "-s", "--tb=long", "--no-header", "--no-summary"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print("=" * 80)
    
    try:
        result = subprocess.run(cmd, cwd="/home/cezar/automagik/automagik-omni", 
                              capture_output=True, text=True, timeout=60)
        
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Test execution timed out!")
        return False
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

if __name__ == "__main__":
    success = run_failing_test()
    sys.exit(0 if success else 1)