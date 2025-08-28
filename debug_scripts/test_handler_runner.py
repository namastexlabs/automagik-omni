#!/usr/bin/env python3
"""
Test runner to capture handler test failures
"""
import subprocess
import sys
import os

def run_test_file(test_file):
    """Run a specific test file and capture output"""
    print(f"\n{'='*80}")
    print(f"RUNNING: {test_file}")
    print('='*80)
    
    try:
        # Change to the project directory
        os.chdir('/home/cezar/automagik/automagik-omni')
        
        # Run pytest with verbose output
        result = subprocess.run([
            'python3', '-m', 'pytest', 
            f'tests/{test_file}', 
            '-v', '--tb=short', '--no-header'
        ], capture_output=True, text=True, timeout=60)
        
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Test timed out!")
        return False
    except Exception as e:
        print(f"Error running test: {e}")
        return False

def main():
    """Run both handler test files"""
    test_files = [
        'test_omni_handlers.py',
        'test_omni_handlers_fixed.py'
    ]
    
    results = {}
    for test_file in test_files:
        results[test_file] = run_test_file(test_file)
    
    print(f"\n{'='*80}")
    print("SUMMARY:")
    print('='*80)
    for test_file, success in results.items():
        status = "PASSED" if success else "FAILED"
        print(f"{test_file}: {status}")

if __name__ == "__main__":
    main()