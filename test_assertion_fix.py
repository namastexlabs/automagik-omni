#!/usr/bin/env python3
"""Verify that the assertion mismatch fixes are working."""

import subprocess
import sys
import os

def run_specific_tests():
    """Run the 4 assertion mismatch tests that were failing."""
    os.chdir('/home/cezar/automagik/automagik-omni')
    
    failing_tests = [
        "TestWhatsAppChatHandler::test_get_contact_by_id_success",
        "TestWhatsAppChatHandler::test_get_chat_by_id_success",
        # Add the Discord tests too since they might have similar issues
        "TestDiscordChatHandler::test_get_contact_by_id_success", 
        "TestDiscordChatHandler::test_get_chat_by_id_success"
    ]
    
    print("🧪 Testing assertion mismatch fixes...")
    print("="*60)
    
    for test in failing_tests:
        print(f"\n🔍 Running: {test}")
        cmd = ["python", "-m", "pytest", "-xvs", f"tests/test_omni_handlers_fixed.py::{test}"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ PASSED: {test}")
            else:
                print(f"❌ FAILED: {test}")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT: {test}")
        except Exception as e:
            print(f"💥 ERROR: {test} - {e}")
    
    print("\n" + "="*60)
    print("🎯 Running full test suite to check for regressions...")
    
    # Run all tests to make sure we didn't break anything
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Extract summary from output
        lines = result.stdout.split('\n')
        summary_lines = [line for line in lines if 'failed' in line.lower() or 'passed' in line.lower() or 'error' in line.lower()][-5:]
        
        print("📊 TEST SUITE SUMMARY:")
        for line in summary_lines:
            if line.strip():
                print(f"   {line}")
                
    except Exception as e:
        print(f"💥 Error running full test suite: {e}")

if __name__ == "__main__":
    run_specific_tests()