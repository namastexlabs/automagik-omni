#!/usr/bin/env python3
import os
import subprocess
import sys

os.chdir("/home/cezar/automagik/automagik-omni")

try:
    result = subprocess.run([sys.executable, "test_basic_check.py"], 
                          capture_output=True, text=True, timeout=120)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    print(f"\nReturn code: {result.returncode}")
    
except subprocess.TimeoutExpired:
    print("❌ Basic check timed out")
except Exception as e:
    print(f"❌ Error running basic check: {e}")

print("✅ Basic check completed")