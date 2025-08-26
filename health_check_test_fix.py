#!/usr/bin/env python3
"""
Script to fix the health check test by replacing the old simple expectation 
with the new complex health response format.
"""

import re

def fix_health_check_test():
    file_path = "/home/cezar/automagik/automagik-omni/tests/test_api_endpoints_e2e.py"
    
    # Read the current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match the old health check test
    old_pattern = r'(def test_health_check_no_auth_required\(self, client\):\s*"""Test health check endpoint works without authentication\."""\s*response = client\.get\("/health"\)\s*assert response\.status_code == 200\s*)assert response\.json\(\) == \{"status": "healthy"\}'
    
    new_code = r'''\1data = response.json()
        # Check the basic structure of the new health response
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "services" in data
        assert "api" in data["services"]
        assert data["services"]["api"]["status"] == "up"'''
    
    # Apply the fix
    new_content = re.sub(old_pattern, new_code, content, flags=re.MULTILINE | re.DOTALL)
    
    if new_content != content:
        # Write the fixed content
        with open(file_path, 'w') as f:
            f.write(new_content)
        print("✅ Fixed health check test expectation to match new response format")
        return True
    else:
        print("❌ Health check test pattern not found or already fixed")
        return False

if __name__ == "__main__":
    fix_health_check_test()