#!/usr/bin/env python3
"""Script to update all imports from unified to omni throughout the codebase"""

import os
import glob

def update_file(filepath):
    """Update imports in a single file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Replace imports
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
            'from src.channels.whatsapp.unified_evolution_client import',
            'from src.channels.whatsapp.omni_evolution_client import'
        )
        
        content = content.replace(
            'from src.api.routes.unified import',
            'from src.api.routes.omni import'
        )
        
        # Replace class names
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
        content = content.replace('UnifiedEvolutionClient', 'OmniEvolutionClient')
        
        # Replace function names
        content = content.replace('unified_router', 'omni_router')
        content = content.replace('get_unified_handler', 'get_omni_handler')
        content = content.replace('get_unified_contacts', 'get_omni_contacts')
        content = content.replace('get_unified_chats', 'get_omni_chats')
        content = content.replace('get_unified_channels', 'get_omni_channels')
        content = content.replace('get_unified_contact_by_id', 'get_omni_contact_by_id')
        content = content.replace('get_unified_chat_by_id', 'get_omni_chat_by_id')
        content = content.replace('contact_to_unified', 'contact_to_omni')
        content = content.replace('chat_to_unified', 'chat_to_omni')
        content = content.replace('channel_to_unified', 'channel_to_omni')
        
        # Replace comments and strings
        content = content.replace('unified communication routes', 'omni communication routes')
        content = content.replace('unified endpoints', 'omni endpoints')
        content = content.replace('unified format', 'omni format')
        content = content.replace('unified operations', 'omni operations')
        content = content.replace('unified handler', 'omni handler')
        content = content.replace('Unified', 'Omni')
        content = content.replace('unified-instances', 'omni-instances')
        
        # Replace documentation
        content = content.replace('Unified multi-channel API endpoints', 'Omni multi-channel API endpoints')
        content = content.replace('unified contacts endpoint', 'omni contacts endpoint')
        content = content.replace('unified chats endpoint', 'omni chats endpoint')
        content = content.replace('unified channels endpoint', 'omni channels endpoint')
        
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"Updated: {filepath}")
            return True
        return False
        
    except Exception as e:
        print(f"Error updating {filepath}: {e}")
        return False

def main():
    """Update all relevant files"""
    base_dir = "/home/cezar/automagik/automagik-omni"
    
    # Files to update
    files_to_update = [
        "src/api/app.py",
        "src/channels/handlers/whatsapp_chat_handler.py",
        "src/channels/handlers/discord_chat_handler.py",
    ]
    
    # Also search for any Python files that might import unified modules
    patterns = [
        "src/**/*.py",
        "tests/**/*.py",
    ]
    
    all_files = []
    for pattern in patterns:
        all_files.extend(glob.glob(f"{base_dir}/{pattern}", recursive=True))
    
    updated_count = 0
    for filepath in all_files:
        if update_file(filepath):
            updated_count += 1
    
    print(f"Updated {updated_count} files in total.")

if __name__ == "__main__":
    main()