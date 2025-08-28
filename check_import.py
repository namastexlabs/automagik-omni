#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/cezar/automagik/automagik-omni/src')

print("Testing config import...")

try:
    from src.config import config
    print(f"Config imported: {type(config)}")
    print(f"Has cors attribute: {hasattr(config, 'cors')}")
    if hasattr(config, 'cors'):
        print("CORS config exists!")
    else:
        print("CORS config missing - fix needed")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()