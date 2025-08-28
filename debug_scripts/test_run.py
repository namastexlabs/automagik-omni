import subprocess
import sys
import os

os.chdir('/home/cezar/automagik/automagik-omni')

# Run a simple test
result = subprocess.run([
    'python3', '-c', """
import sys
sys.path.insert(0, 'src')
try:
    from api.routes.omni import get_omni_contacts
    import inspect
    sig = inspect.signature(get_omni_contacts)
    print('Parameters:', list(sig.parameters.keys()))
except Exception as e:
    print('Error:', e)
"""
], capture_output=True, text=True)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)