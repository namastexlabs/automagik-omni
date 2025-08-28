#!/usr/bin/env python3
"""Rename and update test files from unified to omni"""

import os
import shutil

def update_test_file_content(filepath):
    """Update imports and content in a test file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Update imports
    content = content.replace(
        'from src.api.schemas.unified import',
        'from src.api.schemas.omni import'
    )
    content = content.replace(
        'from src.channels.unified_base import',
        'from src.channels.omni_base import'
    )
    content = content.replace(
        'from src.services.unified_transformers import',
        'from src.services.omni_transformers import'
    )
    content = content.replace(
        'from src.api.routes.unified import',
        'from src.api.routes.omni import'
    )
    
    # Update class names
    content = content.replace('UnifiedChannelHandler', 'OmniChannelHandler')
    content = content.replace('UnifiedContact', 'OmniContact')
    content = content.replace('UnifiedChat', 'OmniChat')
    content = content.replace('UnifiedChannelInfo', 'OmniChannelInfo')
    content = content.replace('UnifiedContactsResponse', 'OmniContactsResponse')
    content = content.replace('UnifiedChatsResponse', 'OmniChatsResponse')
    content = content.replace('UnifiedChannelsResponse', 'OmniChannelsResponse')
    content = content.replace('UnifiedErrorDetail', 'OmniErrorDetail')
    content = content.replace('UnifiedErrorResponse', 'OmniErrorResponse')
    content = content.replace('UnifiedContactStatus', 'OmniContactStatus')
    content = content.replace('UnifiedChatType', 'OmniChatType')
    
    # Update function names
    content = content.replace('get_unified_', 'get_omni_')
    content = content.replace('contact_to_unified', 'contact_to_omni')
    content = content.replace('chat_to_unified', 'chat_to_omni')
    content = content.replace('channel_to_unified', 'channel_to_omni')
    
    # Update variable names
    content = content.replace('unified_', 'omni_')
    content = content.replace('Unified', 'Omni')
    
    # Update comments and strings
    content = content.replace('unified format', 'omni format')
    content = content.replace('unified operations', 'omni operations')
    content = content.replace('unified endpoints', 'omni endpoints')
    content = content.replace('unified models', 'omni models')
    content = content.replace('unified transformers', 'omni transformers')
    content = content.replace('unified handlers', 'omni handlers')
    
    with open(filepath, 'w') as f:
        f.write(content)

def rename_and_update_tests():
    \"\"\"Rename test files and update their content\"\"\"
    base_dir = "/home/cezar/automagik/automagik-omni"
    
    # Mapping of old file names to new names
    test_file_mappings = {
        "tests/test_unified_models.py": "tests/test_omni_models.py",
        "tests/test_unified_transformers.py": "tests/test_omni_transformers.py", 
        "tests/test_unified_handlers.py": "tests/test_omni_handlers.py",
        "tests/test_unified_endpoints.py": "tests/test_omni_endpoints.py"
    }
    
    for old_path, new_path in test_file_mappings.items():
        old_full_path = os.path.join(base_dir, old_path)
        new_full_path = os.path.join(base_dir, new_path)
        
        if os.path.exists(old_full_path):
            # Copy file to new location
            shutil.copy2(old_full_path, new_full_path)
            print(f"Copied {old_path} -> {new_path}")
            
            # Update content in the new file
            update_test_file_content(new_full_path)
            print(f"Updated content in {new_path}")
    
    print("Test file renaming and updating complete!")

if __name__ == "__main__":
    rename_and_update_tests()