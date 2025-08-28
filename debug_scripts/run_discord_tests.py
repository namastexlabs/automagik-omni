#!/usr/bin/env python3
"""
Simple script to run Discord transformer tests and show the errors
"""
import sys
import os
sys.path.insert(0, 'src')

import pytest

if __name__ == "__main__":
    # Run specific Discord transformer tests
    result = pytest.main([
        "tests/test_unified_transformers.py::TestDiscordTransformer", 
        "-v", "-x", "--tb=short"
    ])
    sys.exit(result)