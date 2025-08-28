#!/usr/bin/env python3
"""Test script to validate CORS configuration."""

import sys
import os
sys.path.insert(0, '/home/cezar/automagik/automagik-omni/src')

try:
    from config import config
    print("✅ Config imported successfully")
    
    # Test if cors attribute exists
    if hasattr(config, 'cors'):
        print("✅ CORS configuration found!")
        print(f"  - allowed_origins: {config.cors.allowed_origins}")
        print(f"  - allow_credentials: {config.cors.allow_credentials}")
        print(f"  - allow_methods: {config.cors.allow_methods}")
        print(f"  - allow_headers: {config.cors.allow_headers}")
    else:
        print("❌ CORS configuration NOT found - config.cors attribute missing")
        print("Available attributes:", [attr for attr in dir(config) if not attr.startswith('_')])
        
except Exception as e:
    print(f"❌ Error importing config: {e}")
    import traceback
    traceback.print_exc()