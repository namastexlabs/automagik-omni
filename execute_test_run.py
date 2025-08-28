#!/usr/bin/env python3
import os
import subprocess

os.chdir("/home/cezar/automagik/automagik-omni")
os.chmod("run_failing_tests.py", 0o755)

result = subprocess.run(["python3", "run_failing_tests.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)