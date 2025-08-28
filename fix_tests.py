#!/usr/bin/env python3
"""
Fix test files to match actual implementation.
"""

import re

def fix_handler_test():
    """Fix the handler test file."""
    file_path = "/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace profilePicture with profilePictureUrl
    content = content.replace('"profilePicture":', '"profilePictureUrl":')
    
    # Fix the mock configuration to match InstanceConfig model
    old_config = '''config = MagicMock(spec=InstanceConfig)
        config.name = "test-whatsapp"
        config.channel_type = "whatsapp"
        config.config = {
            "evolution_api_url": "https://api.evolution.test",
            "evolution_api_key": "test-api-key-123"
        }'''
    
    new_config = '''config = MagicMock(spec=InstanceConfig)
        config.name = "test-whatsapp"
        config.channel_type = "whatsapp"
        config.evolution_url = "https://api.evolution.test"
        config.evolution_key = "test-api-key-123"
        config.config = {}'''
    
    if old_config.replace('        ', '    ') in content:
        content = content.replace(old_config.replace('        ', '    '), new_config.replace('        ', '    '))
    elif old_config in content:
        content = content.replace(old_config, new_config)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed {file_path}")

def fix_endpoints_test():
    """Fix the endpoint test files if they have similar issues."""
    try:
        file_path = "/home/cezar/automagik/automagik-omni/tests/test_unified_endpoints.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace profilePicture with profilePictureUrl
        if '"profilePicture":' in content:
            content = content.replace('"profilePicture":', '"profilePictureUrl":')
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"Fixed {file_path}")
        else:
            print(f"No issues found in {file_path}")
    except FileNotFoundError:
        print("Endpoint test file not found, skipping")

def fix_authentication_tests():
    """Fix authentication-related tests by ensuring proper mocks."""
    import os
    test_files = [
        "/home/cezar/automagik/automagik-omni/tests/test_api_endpoints_e2e.py",
        "/home/cezar/automagik/automagik-omni/tests/test_mentions_integration.py"
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Fix profilePicture references if any
            if '"profilePicture":' in content:
                content = content.replace('"profilePicture":', '"profilePictureUrl":')
                
                with open(file_path, 'w') as f:
                    f.write(content)
                
                print(f"Fixed {file_path}")

if __name__ == "__main__":
    fix_handler_test()
    fix_endpoints_test()
    fix_authentication_tests()
    print("Test fixes complete!")