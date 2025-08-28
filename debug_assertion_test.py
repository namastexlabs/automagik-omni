#!/usr/bin/env python3
"""Debug script to run specific assertion mismatch tests and capture exact output."""

import subprocess
import sys
import os

def run_test(test_name):
    """Run a specific test and capture output."""
    print(f"\n{'='*50}")
    print(f"🧪 RUNNING: {test_name}")
    print('='*50)
    
    cmd = ["python", "-m", "pytest", "-xvs", f"tests/test_omni_handlers_fixed.py::{test_name}"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"Exit Code: {result.returncode}")
        print(f"\n--- STDOUT ---")
        print(result.stdout)
        
        if result.stderr:
            print(f"\n--- STDERR ---") 
            print(result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

def main():
    """Run the specific assertion mismatch tests."""
    # Change to project root
    os.chdir('/home/cezar/automagik/automagik-omni')
    
    failing_tests = [
        "TestWhatsAppChatHandler::test_get_contact_by_id_success",
        "TestWhatsAppChatHandler::test_get_chat_by_id_success", 
    ]
    
    results = {}
    
    for test in failing_tests:
        success = run_test(test)
        results[test] = "PASSED" if success else "FAILED"
    
    print(f"\n{'='*50}")
    print("🎯 RESULTS SUMMARY")
    print('='*50)
    for test, status in results.items():
        print(f"{status}: {test}")

if __name__ == "__main__":
    main()