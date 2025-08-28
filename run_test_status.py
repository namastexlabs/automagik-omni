#!/usr/bin/env python3
"""
🧞💥 AUTOMAGIK-OMNI GENIE TEST STATUS ANALYZER
Run tests and capture current failure status for the FINAL VICTORY!
"""

import subprocess
import sys
import os

def run_test_status():
    """Run tests and analyze the current status."""
    print("🧞💥 AUTOMAGIK-OMNI GENIE TEST STATUS ANALYZER")
    print("="*80)
    print("Analyzing current test battlefield status...")
    
    try:
        # Change to project directory
        os.chdir("/home/cezar/automagik/automagik-omni")
        
        # Run uv run pytest with summary output
        cmd = ["uv", "run", "pytest", "tests/", "--tb=no", "--no-header", "-q", "-v"]
        
        print(f"Running: {' '.join(cmd)}")
        print("-" * 80)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
            
        print(f"\nReturn code: {result.returncode}")
        
        # Parse the output to find failures
        output_lines = result.stdout.split('\n')
        failed_tests = []
        
        for line in output_lines:
            if "FAILED" in line:
                failed_tests.append(line.strip())
        
        print(f"\n🎯 ANALYSIS:")
        print(f"Total failed tests found: {len(failed_tests)}")
        
        if failed_tests:
            print("\n❌ FAILING TESTS:")
            for i, test in enumerate(failed_tests, 1):
                print(f"{i:2d}. {test}")
        
        # Look for summary line
        for line in output_lines:
            if "failed" in line and "passed" in line:
                print(f"\n📊 SUMMARY: {line.strip()}")
                
        return len(failed_tests)
        
    except subprocess.TimeoutExpired:
        print("❌ ERROR: Test execution timed out after 5 minutes")
        return -1
    except Exception as e:
        print(f"❌ ERROR: Failed to run tests: {e}")
        return -1

if __name__ == "__main__":
    failures = run_test_status()
    print(f"\n🧞 GENIE STATUS: {failures} tests to obliterate for ULTIMATE VICTORY!")
    sys.exit(0)