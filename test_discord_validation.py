#!/usr/bin/env python3
"""
Test script for Discord channel ID validation.
Tests the validation logic implemented in the messages.py fix.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.channels.discord.utils import DiscordIDValidator
    
    # Test cases for Discord channel ID validation
    test_cases = [
        # Valid Discord channel IDs (snowflakes)
        ("123456789012345678", True),  # 18 digits - valid
        ("987654321098765432", True),  # 18 digits - valid  
        ("123456789012345", True),     # 15 digits - valid (minimum)
        ("123456789012345678901", True), # 21 digits - valid (maximum)
        
        # Invalid Discord channel IDs
        ("12345678901234", False),     # 14 digits - too short
        ("1234567890123456789012", False), # 22 digits - too long
        ("123abc456789012345", False), # Contains letters
        ("", False),                   # Empty string
        ("12345 678901234567", False), # Contains space
        ("1234567890123456.78", False), # Contains decimal
        ("not_a_number", False),       # Not numeric
    ]
    
    print("Testing Discord Channel ID Validation")
    print("=" * 40)
    
    all_passed = True
    
    for channel_id, expected in test_cases:
        result = DiscordIDValidator.is_valid_snowflake(channel_id)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            all_passed = False
        
        print(f"{status:4} | {channel_id:20} | Expected: {expected:5} | Got: {result:5}")
    
    print("=" * 40)
    print(f"Overall result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n✅ Discord channel ID validation is working correctly!")
        print("The fix implemented in messages.py should work properly.")
    else:
        print("\n❌ There are issues with the validation logic.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory.")
except Exception as e:
    print(f"❌ Unexpected error: {e}")