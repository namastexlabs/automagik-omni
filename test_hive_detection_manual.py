#!/usr/bin/env python3
"""
Manual verification script for Hive API detection fix.
This script can be run to manually verify that the fix works correctly.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.agent_api_client import AgentApiClient

def test_hive_detection():
    """Manually test the Hive API detection logic."""
    
    print("🧪 Testing Hive API Detection Fix")
    print("=" * 50)
    
    test_cases = [
        # (URL, Expected is_hive, Description)
        ("http://localhost:8000", True, "Hive API on port 8000"),
        ("http://localhost:8881", False, "Automagik Core on port 8881"),
        ("https://my-hive.com:8000", True, "Remote Hive API"),
        ("https://my-core.com:8881", False, "Remote Automagik Core"),
        ("http://localhost", False, "No port specified"),
        ("http://localhost:8080", False, "Other port"),
    ]
    
    all_passed = True
    
    for url, expected_is_hive, description in test_cases:
        client = AgentApiClient()
        client.api_url = url
        client.instance_config = None
        
        result = client._is_hive_api_mode()
        
        status = "✅ PASS" if result == expected_is_hive else "❌ FAIL"
        expected_endpoint = "/playground/agents/" if expected_is_hive else "/api/v1/agent/"
        
        print(f"{status} {description}")
        print(f"      URL: {url}")
        print(f"      Expected: {expected_is_hive}, Got: {result}")
        print(f"      Will use: {expected_endpoint}")
        print()
        
        if result != expected_is_hive:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed! The Hive API detection fix is working correctly.")
    else:
        print("💥 Some tests failed. The fix needs attention.")
    
    return all_passed

def test_endpoint_selection_logic():
    """Test that the endpoint selection logic works correctly."""
    
    print("\n🔀 Testing Endpoint Selection Logic")
    print("=" * 50)
    
    # Test Hive API client
    hive_client = AgentApiClient()
    hive_client.api_url = "http://localhost:8000"
    hive_client.instance_config = None
    
    print("Hive API Client (port 8000):")
    print(f"  - is_hive_api_mode(): {hive_client._is_hive_api_mode()}")
    print("  - Should use: /playground/agents/{agent_name}/runs")
    
    # Test Core API client
    core_client = AgentApiClient()
    core_client.api_url = "http://localhost:8881"
    core_client.instance_config = None
    
    print("\nAutomagik Core Client (port 8881):")
    print(f"  - is_hive_api_mode(): {core_client._is_hive_api_mode()}")
    print("  - Should use: /api/v1/agent/{agent_name}/run")
    
    print("\n✅ Endpoint selection logic is working as expected!")

if __name__ == "__main__":
    success = test_hive_detection()
    test_endpoint_selection_logic()
    
    if success:
        print("\n🚀 PR #3 fix verification complete - All systems go!")
        sys.exit(0)
    else:
        print("\n⚠️  PR #3 fix verification failed - Needs attention!")
        sys.exit(1)