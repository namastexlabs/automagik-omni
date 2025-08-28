#!/usr/bin/env python3
"""Run nuclear fix validation and pytest to prove it works."""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Run comprehensive validation of the nuclear fix."""
    
    os.chdir('/home/cezar/automagik/automagik-omni')
    
    print("🚀 NUCLEAR EVOLUTION API SOLUTION - FINAL VALIDATION")
    print("=" * 60)
    
    # Step 1: Verify the fix conceptually
    print("\n🧪 Step 1: Conceptual verification...")
    try:
        result = subprocess.run([sys.executable, 'verify_fix.py'], 
                              capture_output=True, text=True, timeout=30)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode != 0:
            print("❌ Conceptual verification failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error in conceptual verification: {e}")
        return False
    
    # Step 2: Run actual pytest  
    print("\n🧪 Step 2: Running actual pytest...")
    env = os.environ.copy()
    env['PYTHONPATH'] = 'src'
    
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/test_omni_handlers.py::TestWhatsAppChatHandler::test_get_contacts_success',
        '-v', '--tb=short', '-x', '--no-header'
    ]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
        
        print("PYTEST OUTPUT:")
        print(result.stdout)
        if result.stderr:
            print("\nPYTEST STDERR:")  
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n✅ NUCLEAR FIX SUCCESS! Test passed!")
            print("\n🎯 READY TO RUN ALL TESTS:")
            print("   python3 -m pytest tests/test_omni_handlers.py tests/test_omni_handlers_fixed.py -v")
            return True
        else:
            print(f"\n❌ Test still failing with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n⏱️ Test timed out")
        return False
    except Exception as e:
        print(f"\n💥 Error running pytest: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)