import os
import subprocess

os.chdir('/home/cezar/automagik/automagik-omni')
result = subprocess.run(['python3', 'test_one.py'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)