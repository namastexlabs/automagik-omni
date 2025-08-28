#!/usr/bin/env python3

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.unified_transformers import WhatsAppTransformer
from datetime import datetime

def test_parse_datetime_behavior():
    """Test what the WhatsAppTransformer._parse_datetime actually returns"""
    
    print("Testing WhatsAppTransformer._parse_datetime behavior...")
    print("=" * 60)
    
    # Test cases from the failing tests
    invalid_values = [
        None,
        "",
        "invalid-date", 
        "not-a-timestamp",
        [],
        {},
        -1,  # Negative timestamp
    ]
    
    edge_cases = [
        0,  # Zero timestamp
        1640995200.5,  # Float timestamp
        "1640995200",  # String number
    ]
    
    print("INVALID VALUES:")
    for value in invalid_values:
        try:
            result = WhatsAppTransformer._parse_datetime(value)
            print(f"  {repr(value):20} -> {repr(result)}")
        except Exception as e:
            print(f"  {repr(value):20} -> EXCEPTION: {e}")
    
    print("\nEDGE CASES:")
    for value in edge_cases:
        try:
            result = WhatsAppTransformer._parse_datetime(value)
            print(f"  {repr(value):20} -> {repr(result)}")
        except Exception as e:
            print(f"  {repr(value):20} -> EXCEPTION: {e}")

if __name__ == "__main__":
    test_parse_datetime_behavior()