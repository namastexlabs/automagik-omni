#!/usr/bin/env python3
"""
Fix test_omni_endpoints.py to align with actual omni API implementation.
Addresses the main issues from unified → omni transformation:
1. Route path changes from /unified to /instances
2. Schema name changes (UnifiedContact → OmniContact, etc.)
3. Import statement updates
4. Handler method calls and response expectations
"""

import re
import os

def fix_omni_endpoints_tests():
    """Apply comprehensive fixes to test_omni_endpoints.py"""
    test_file = "/home/cezar/automagik/automagik-omni/tests/test_omni_endpoints.py"
    
    if not os.path.exists(test_file):
        print(f"Error: {test_file} not found")
        return False
    
    # Read the test file
    with open(test_file, 'r') as f:
        content = f.read()
    
    print(f"Original file size: {len(content)} characters")
    
    # Store original for comparison
    original_content = content
    
    # Fix 1: Import statements - ensure we're importing from omni modules
    import_fixes = [
        # Schema imports
        (r'from src\.api\.schemas\.unified import', 'from src.api.schemas.omni import'),
        # Handler imports  
        (r'from src\.channels\.unified_base import', 'from src.channels.omni_base import'),
        # Ensure we have the right classes imported
        (r'UnifiedContact,\s*UnifiedChat,\s*UnifiedChannelInfo', 'OmniContact, OmniChat, OmniChannelInfo'),
        (r'UnifiedContactsResponse,\s*UnifiedChatsResponse,\s*UnifiedChannelsResponse', 'OmniContactsResponse, OmniChatsResponse, OmniChannelsResponse'),
        (r'UnifiedChannelHandler', 'OmniChannelHandler'),
        (r'UnifiedContactStatus', 'OmniContactStatus'),
        (r'UnifiedChatType', 'OmniChatType'),
    ]
    
    # Fix 2: URL path changes - ensure all URLs use /instances paths (should already be correct)
    url_fixes = [
        (r'"/api/v1/unified/', '"/api/v1/instances/'),
        (r"'/api/v1/unified/", "'/api/v1/instances/"),
    ]
    
    # Fix 3: Mock patching - update to patch omni modules
    mock_fixes = [
        (r'@patch\([\'"]src\.api\.routes\.unified\.get_unified_handler[\'"]', '@patch(\'src.api.routes.omni.get_omni_handler\''),
        (r'@patch\([\'"]src\.api\.routes\.unified\.get_instance_by_name[\'"]', '@patch(\'src.api.routes.omni.get_instance_by_name\''),
        (r'get_unified_handler', 'get_omni_handler'),
    ]
    
    # Fix 4: Schema class name changes
    schema_fixes = [
        (r'\bUnifiedContact\b', 'OmniContact'),
        (r'\bUnifiedChat\b', 'OmniChat'), 
        (r'\bUnifiedChannelInfo\b', 'OmniChannelInfo'),
        (r'\bUnifiedContactsResponse\b', 'OmniContactsResponse'),
        (r'\bUnifiedChatsResponse\b', 'OmniChatsResponse'),
        (r'\bUnifiedChannelsResponse\b', 'OmniChannelsResponse'),
        (r'\bUnifiedChannelHandler\b', 'OmniChannelHandler'),
        (r'\bUnifiedContactStatus\b', 'OmniContactStatus'),
        (r'\bUnifiedChatType\b', 'OmniChatType'),
    ]
    
    # Fix 5: Handler method signature fixes
    handler_fixes = [
        # get_contacts method calls - add missing parameters
        (r'\.get_contacts\(\s*([^,)]+),\s*page=([^,)]+),\s*page_size=([^,)]+),\s*search_query=([^)]+)\)',
         r'.get_contacts(instance=\1, page=\2, page_size=\3, search_query=\4, status_filter=None)'),
        
        # get_chats method calls - add missing parameters  
        (r'\.get_chats\(\s*([^,)]+),\s*page=([^,)]+),\s*page_size=([^,)]+)\)',
         r'.get_chats(instance=\1, page=\2, page_size=\3, chat_type_filter=None, archived=None)'),
         
        # get_chats with filters
        (r'\.get_chats\(\s*([^,)]+),\s*page=([^,)]+),\s*page_size=([^,)]+),\s*chat_type_filter=([^,)]+),\s*archived=([^)]+)\)',
         r'.get_chats(instance=\1, page=\2, page_size=\3, chat_type_filter=\4, archived=\5)'),
    ]
    
    # Apply all fixes
    all_fixes = import_fixes + url_fixes + mock_fixes + schema_fixes + handler_fixes
    
    fixes_applied = 0
    for pattern, replacement in all_fixes:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            fixes_applied += 1
            print(f"Applied fix: {pattern[:50]}... → {replacement[:50]}...")
            content = new_content
    
    # Fix 6: Response schema field additions - ensure OmniChannelInfo has all required fields
    channel_info_fixes = [
        # Add missing required fields to OmniChannelInfo constructor calls
        (r'OmniChannelInfo\(\s*instance_name=([^,)]+),\s*channel_type=([^,)]+),\s*display_name=([^,)]+),\s*status=([^,)]+),\s*is_healthy=([^)]+)\)',
         r'OmniChannelInfo(instance_name=\1, channel_type=\2, display_name=\3, status=\4, is_healthy=\5, supports_contacts=True, supports_groups=True, supports_media=True, supports_voice=False)'),
    ]
    
    for pattern, replacement in channel_info_fixes:
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        if new_content != content:
            fixes_applied += 1
            print(f"Applied channel info fix")
            content = new_content
    
    # Fix 7: Enum values - ensure we're using the right enum values
    enum_fixes = [
        (r'OmniContactStatus\.ACTIVE', 'OmniContactStatus.ONLINE'),
        (r'OmniChatType\.BROADCAST', 'OmniChatType.CHANNEL'),  # @broadcast maps to CHANNEL
    ]
    
    for pattern, replacement in enum_fixes:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            fixes_applied += 1
            print(f"Applied enum fix: {pattern} → {replacement}")
            content = new_content
    
    # Write the fixed content back
    if content != original_content:
        with open(test_file, 'w') as f:
            f.write(content)
        print(f"\n✅ Successfully applied {fixes_applied} fixes to {test_file}")
        print(f"New file size: {len(content)} characters")
        print(f"Content changed: {len(content) != len(original_content)}")
        return True
    else:
        print("❌ No changes were needed or no patterns matched")
        return False

if __name__ == "__main__":
    print("🔧 Fixing omni endpoints tests...")
    success = fix_omni_endpoints_tests()
    print("✅ Fix completed!" if success else "❌ Fix failed!")