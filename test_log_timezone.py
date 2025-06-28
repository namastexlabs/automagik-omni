#!/usr/bin/env python3
"""
Test script to verify logging uses configured timezone.
"""

import os
import logging

def test_logging_timezone():
    """Test if logging respects timezone configuration."""
    
    # Test different timezones
    timezones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]
    
    for tz in timezones:
        print(f"\n{'='*50}")
        print(f"Testing logging with timezone: {tz}")
        print(f"{'='*50}")
        
        # Set timezone
        os.environ["AUTOMAGIK_TIMEZONE"] = tz
        
        # Clear module cache to force reload
        import sys
        modules_to_clear = [
            'src.config',
            'src.utils.datetime_utils',
            'src.logger'
        ]
        
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        try:
            # Import after clearing cache
            from src.logger import setup_logging
            from src.config import config
            
            # Setup logging with current timezone
            setup_logging()
            
            # Get a test logger
            test_logger = logging.getLogger(f"test_timezone_{tz.replace('/', '_')}")
            
            print(f"Configured timezone: {config.timezone.timezone}")
            print(f"Timezone object: {config.timezone.tz}")
            print(f"Log date format: {config.logging.date_format}")
            
            # Test different log levels
            test_logger.info(f"INFO log message in {tz}")
            test_logger.warning(f"WARNING log message in {tz}")
            test_logger.error(f"ERROR log message in {tz}")
            
            # Show current time in timezone
            current_time = config.timezone.now()
            print(f"Current time in {tz}: {current_time}")
            
        except Exception as e:
            print(f"❌ Error testing timezone {tz}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🕐 Testing Logging Timezone Configuration")
    test_logging_timezone()
    print(f"\n{'='*50}")
    print("✅ Logging timezone test complete!")
    print(f"{'='*50}")