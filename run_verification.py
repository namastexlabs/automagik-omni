#!/usr/bin/env python3
import subprocess
import os

os.chdir('/home/cezar/automagik/automagik-omni')

# Run the specific failing tests first
tests_to_check = [
    "tests/test_omni_handlers_fixed.py::TestWhatsAppChatHandler::test_get_contact_by_id_success",
    "tests/test_omni_handlers_fixed.py::TestWhatsAppChatHandler::test_get_chat_by_id_success",
]

print("🧪 VERIFICATION: Testing assertion mismatch fixes")
print("="*60)

for test in tests_to_check:
    print(f"\n🔍 Running: {test}")
    
    result = subprocess.run(
        ["python", "-m", "pytest", "-xvs", test],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✅ PASSED: {test}")
    else:
        print(f"❌ FAILED: {test}")
        print("--- FAILURE OUTPUT ---")
        print(result.stdout)
        if result.stderr:
            print("--- STDERR ---")
            print(result.stderr)

print("\n" + "="*60)
print("🎯 ASSERTION MISMATCH FIX VERIFICATION COMPLETE")