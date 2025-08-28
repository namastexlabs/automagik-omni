#!/usr/bin/env python3
"""
Fix the final channel endpoint mock issues.
"""

import re
import os

def fix_final_channel_mocks():
    """Fix the remaining mock issues in channel endpoint tests.""" 
    test_file = "/home/cezar/automagik/automagik-omni/tests/test_omni_endpoints.py"
    
    if not os.path.exists(test_file):
        print(f"Error: {test_file} not found")
        return False
    
    # Read the test file
    with open(test_file, 'r') as f:
        content = f.read()
    
    print(f"Fixing final channel endpoint mock issues...")
    
    # Store original for comparison
    original_content = content
    
    # Fix 1: Replace MagicMock instances with string names for database insertion
    mock_instance_fix = r'''# Create instances in test database
        for instance in mock_multiple_instances:
            test_db\.add\(InstanceConfig\(
                name=instance\.name,
                channel_type=instance\.channel_type,
                whatsapp_instance="test",
                agent_api_url="http://test\.com",
                agent_api_key="test-key",
                default_agent="test-agent"
            \)\)'''
    
    mock_instance_replacement = '''# Create instances in test database
        test_db.add(InstanceConfig(
            name="instance1",
            channel_type=ChannelType.WHATSAPP,
            whatsapp_instance="test",
            agent_api_url="http://test.com",
            agent_api_key="test-key",
            default_agent="test-agent"
        ))
        test_db.add(InstanceConfig(
            name="instance2",
            channel_type=ChannelType.DISCORD,
            whatsapp_instance="test",
            agent_api_url="http://test.com", 
            agent_api_key="test-key",
            default_agent="test-agent"
        ))'''
    
    content = re.sub(mock_instance_fix, mock_instance_replacement, content, flags=re.MULTILINE | re.DOTALL)
    print("✓ Fixed database mock instance creation")
    
    # Fix 2: Remove the mock_multiple_instances fixture usage from the test parameters
    param_fix = (
        r'def test_channels_endpoint_requires_auth\(self, mock_get_handler, test_client, mock_multiple_instances, test_db\):',
        'def test_channels_endpoint_requires_auth(self, mock_get_handler, test_client, test_db):'
    )
    content = re.sub(param_fix[0], param_fix[1], content)
    print("✓ Removed unused mock_multiple_instances parameter")
    
    # Fix 3: Fix the empty database test - make mock return actual OmniChannelInfo objects
    empty_db_fix = r'''def test_omni_channels_empty_database\(
        self, mock_get_handler, test_client, mention_api_headers
    \):
        """Test channels endpoint with no instances in database\."""
        handler = AsyncMock\(\)
        mock_get_handler\.return_value = handler

        response = test_client\.get\("/api/v1/instances/channels", headers=mention_api_headers\)

        assert response\.status_code == 200
        data = response\.json\(\)
        assert len\(data\.get\("channels", data\.get\("instances", \[\]\)\)\) >= 0  # May have existing instances
        assert data\["total_count"\] >= 0  # May have existing instances'''
    
    empty_db_replacement = '''def test_omni_channels_empty_database(
        self, mock_get_handler, test_client, mention_api_headers
    ):
        """Test channels endpoint with no instances in database."""
        # Mock handler that returns proper OmniChannelInfo objects
        handler = AsyncMock()
        handler.get_channel_info.return_value = OmniChannelInfo(
            instance_name="test-instance", 
            channel_type=ChannelType.WHATSAPP, 
            display_name="Test Instance", 
            status="connected", 
            is_healthy=True,
            supports_contacts=True, 
            supports_groups=True, 
            supports_media=True, 
            supports_voice=False
        )
        mock_get_handler.return_value = handler

        response = test_client.get("/api/v1/instances/channels", headers=mention_api_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data.get("channels", data.get("instances", []))) >= 0  # May have existing instances
        assert data["total_count"] >= 0  # May have existing instances'''
    
    content = re.sub(empty_db_fix, empty_db_replacement, content, flags=re.MULTILINE | re.DOTALL)
    print("✓ Fixed empty database test mock to return proper OmniChannelInfo")
    
    # Write the fixed content back
    if content != original_content:
        with open(test_file, 'w') as f:
            f.write(content)
        print(f"\n✅ Successfully applied final channel endpoint mock fixes")
        return True
    else:
        print("❌ No changes were applied")
        return False

if __name__ == "__main__":
    print("🔧 Fixing final channel endpoint mock issues...")
    success = fix_final_channel_mocks()
    print("✅ Fix completed!" if success else "❌ Fix failed!")