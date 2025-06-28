#!/usr/bin/env python3
"""
Debug script to check current timezone configuration.
"""

import os
from src.config import config
from src.utils.datetime_utils import now, utcnow

print("🌐 Timezone Debug Information")
print("=" * 50)

print(f"Environment variable AUTOMAGIK_TIMEZONE: {os.getenv('AUTOMAGIK_TIMEZONE')}")
print(f"Config timezone string: {config.timezone.timezone}")
print(f"Config timezone object: {config.timezone.tz}")
print(f"Config timezone object type: {type(config.timezone.tz)}")

print("\n⏰ Time Comparison:")
current_utc = utcnow()
current_local = now()

print(f"UTC time: {current_utc}")
print(f"Local time: {current_local}")
print(f"UTC offset: {current_local.utcoffset()}")
print(f"Timezone name: {current_local.tzname()}")

print("\n📝 Log Date Format:")
print(f"Date format: {config.logging.date_format}")

# Test the logging formatter
import logging
from src.logger import setup_logging

setup_logging()
test_logger = logging.getLogger("debug_test")
test_logger.info("Test log message to check timezone")

print("=" * 50)