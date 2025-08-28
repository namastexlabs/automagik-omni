#!/usr/bin/env python3
"""
Count total tests and estimate the remaining failures
"""

import subprocess
import os

def count_tests():
    os.chdir("/home/cezar/automagik/automagik-omni")
    
    # Known endpoint failures (6)
    endpoint_failures = [
        "tests/test_omni_endpoints_fixed.py::TestOmniEndpointsAuthentication::test_channels_endpoint_requires_auth",
        "tests/test_omni_endpoints_fixed.py::TestOmniContactsEndpoint::test_successful_contacts_retrieval",
        "tests/test_omni_endpoints_fixed.py::TestOmniContactsEndpoint::test_contacts_pagination_edge_cases", 
        "tests/test_omni_endpoints_fixed.py::TestOmniContactsEndpoint::test_contacts_with_search_query",
        "tests/test_omni_endpoints_fixed.py::TestOmniChatsEndpoint::test_successful_chats_retrieval",
        "tests/test_omni_endpoints_fixed.py::TestOmniChannelsEndpoint::test_successful_channels_retrieval"
    ]
    
    # Likely handler failures based on file analysis  
    likely_handler_failures = [
        "tests/test_omni_handlers.py::TestWhatsAppChatHandler::test_get_contacts_success",
        "tests/test_omni_handlers.py::TestWhatsAppChatHandler::test_get_contacts_with_search_query",
        "tests/test_omni_handlers.py::TestWhatsAppChatHandler::test_get_chats_success",
        "tests/test_omni_handlers.py::TestDiscordChatHandler::test_get_contacts_success", 
        "tests/test_omni_handlers.py::TestDiscordChatHandler::test_get_chats_success",
        "tests/test_omni_handlers.py::TestDiscordChatHandler::test_get_contact_by_id_success",
        "tests/test_omni_handlers_fixed.py::TestWhatsAppChatHandler::test_get_contacts_success",
        "tests/test_omni_handlers_fixed.py::TestDiscordChatHandler::test_get_contacts_success",
        "tests/test_omni_handlers_fixed.py::TestDiscordChatHandler::test_discord_api_error_handling"
    ]
    
    print("🧞💥 AUTOMAGIK-OMNI TEST COUNT ANALYSIS")
    print("="*80)
    print(f"📊 KNOWN ENDPOINT FAILURES: {len(endpoint_failures)}")
    for i, test in enumerate(endpoint_failures, 1):
        print(f"  {i}. {test.split('::')[-1]}")
    
    print(f"\n📊 LIKELY HANDLER FAILURES: {len(likely_handler_failures)}")
    for i, test in enumerate(likely_handler_failures, 1):
        print(f"  {i}. {test.split('::')[-1]}")
    
    print(f"\n🎯 TOTAL TARGETED: {len(endpoint_failures) + len(likely_handler_failures)} tests")
    print(f"💥 MISSION: Convert 15 FAILED → 15 PASSED")
    print(f"🚀 FINAL GOAL: 369 + 15 = 384 PASSED, 0 FAILED")
    
    return endpoint_failures, likely_handler_failures

if __name__ == "__main__":
    endpoint_tests, handler_tests = count_tests()
    print(f"\n🧞 READY FOR AGENT ARMY DEPLOYMENT!")