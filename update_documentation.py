#!/usr/bin/env python3
"""Update documentation files from unified to omni"""

import os
import shutil

def update_doc_file(filepath):
    \"\"\"Update a documentation file\"\"\"
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Update technical terms
    content = content.replace('unified-multichannel-endpoints', 'omni-multichannel-endpoints')
    content = content.replace('Unified Multi-Channel Endpoints', 'Omni Multi-Channel Endpoints')
    content = content.replace('unified endpoints', 'omni endpoints')
    content = content.replace('Unified endpoints', 'Omni endpoints')
    content = content.replace('unified API', 'omni API')
    content = content.replace('Unified API', 'Omni API')
    content = content.replace('unified interface', 'omni interface')
    content = content.replace('Unified interface', 'Omni interface')
    
    # Update class and schema names
    content = content.replace('UnifiedContact', 'OmniContact')
    content = content.replace('UnifiedChat', 'OmniChat')
    content = content.replace('UnifiedChannelInfo', 'OmniChannelInfo')
    content = content.replace('UnifiedContactsResponse', 'OmniContactsResponse')
    content = content.replace('UnifiedChatsResponse', 'OmniChatsResponse')
    content = content.replace('UnifiedChannelsResponse', 'OmniChannelsResponse')
    
    # Update file paths
    content = content.replace('/api/schemas/unified.py', '/api/schemas/omni.py')
    content = content.replace('/api/routes/unified.py', '/api/routes/omni.py')
    content = content.replace('/channels/unified_base.py', '/channels/omni_base.py')
    content = content.replace('/services/unified_transformers.py', '/services/omni_transformers.py')
    
    # Update function names
    content = content.replace('get_unified_contacts', 'get_omni_contacts')
    content = content.replace('get_unified_chats', 'get_omni_chats')
    content = content.replace('get_unified_channels', 'get_omni_channels')
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

def update_all_docs():
    \"\"\"Update all documentation files\"\"\"
    base_dir = "/home/cezar/automagik/automagik-omni"
    
    # Files to update
    doc_files = [
        "README.md",
        "docs/implementation/unified-multichannel-endpoints-technical-design.md", 
        "genie/wishes/unified-multichannel-endpoints.md",
        "genie/wishes/cross-channel-user-sync-optimization.md",
        "genie/wishes/README.md"
    ]
    
    updated_count = 0
    for doc_file in doc_files:
        filepath = os.path.join(base_dir, doc_file)
        if os.path.exists(filepath):
            if update_doc_file(filepath):
                print(f"Updated: {doc_file}")
                updated_count += 1
    
    # Also rename the specific documentation files
    old_doc_path = os.path.join(base_dir, "docs/implementation/unified-multichannel-endpoints-technical-design.md")
    new_doc_path = os.path.join(base_dir, "docs/implementation/omni-multichannel-endpoints-technical-design.md")
    
    if os.path.exists(old_doc_path):
        shutil.move(old_doc_path, new_doc_path)
        print(f"Renamed: unified-multichannel-endpoints-technical-design.md -> omni-multichannel-endpoints-technical-design.md")
    
    old_wish_path = os.path.join(base_dir, "genie/wishes/unified-multichannel-endpoints.md")
    new_wish_path = os.path.join(base_dir, "genie/wishes/omni-multichannel-endpoints.md")
    
    if os.path.exists(old_wish_path):
        shutil.move(old_wish_path, new_wish_path)
        print(f"Renamed: unified-multichannel-endpoints.md -> omni-multichannel-endpoints.md")
    
    print(f"Documentation update complete! Updated {updated_count} files.")

if __name__ == "__main__":
    update_all_docs()