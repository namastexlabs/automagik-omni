#!/usr/bin/env python3
"""
Test script to verify timezone configuration is working correctly.
"""

import os
from datetime import datetime
import pytz

# Test different timezone values
test_timezones = [
    "UTC",
    "America/New_York", 
    "Europe/London",
    "Asia/Tokyo",
    "America/Sao_Paulo"
]

def test_timezone_config(tz_name):
    """Test timezone configuration."""
    print(f"\n{'='*50}")
    print(f"Testing timezone: {tz_name}")
    print(f"{'='*50}")
    
    # Set environment variable
    os.environ["AUTOMAGIK_TIMEZONE"] = tz_name
    
    # Import after setting env var to ensure it picks up the change
    import importlib
    import sys
    
    # Clear module cache to force reload
    modules_to_reload = [
        'src.config',
        'src.utils.datetime_utils'
    ]
    
    for module in modules_to_reload:
        if module in sys.modules:
            del sys.modules[module]
    
    try:
        from src.config import config
        from src.utils.datetime_utils import now, utcnow, to_local, format_local
        
        print(f"✅ Configuration loaded successfully")
        print(f"📍 Configured timezone: {config.timezone.timezone}")
        print(f"🌍 Timezone object: {config.timezone.tz}")
        
        # Test datetime functions
        utc_time = utcnow()
        local_time = now()
        converted_local = to_local(utc_time)
        
        print(f"\n⏰ Time comparisons:")
        print(f"UTC time:        {utc_time}")
        print(f"Local time:      {local_time}")
        print(f"UTC→Local:       {converted_local}")
        print(f"Formatted local: {format_local(utc_time)}")
        
        # Verify timezone offset
        if tz_name != "UTC":
            offset = local_time.utcoffset()
            print(f"UTC offset:      {offset}")
        
    except Exception as e:
        print(f"❌ Error testing timezone {tz_name}: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main test function."""
    print("🌐 Automagik Timezone Configuration Test")
    print("This script tests timezone configuration functionality")
    
    for tz_name in test_timezones:
        test_timezone_config(tz_name)
    
    print(f"\n{'='*50}")
    print("✅ Timezone testing complete!")
    print("💡 To use a specific timezone, set AUTOMAGIK_TIMEZONE in your .env file")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()