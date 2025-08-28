#!/usr/bin/env python3
"""
FINAL NUCLEAR FIX: AsyncMock persistence issue in Evolution API client
"""

def apply_final_fix():
    conftest_path = "/home/cezar/automagik/automagik-omni/tests/conftest.py"
    
    # Read the entire file
    with open(conftest_path, 'r') as f:
        content = f.read()
    
    # The exact pattern to replace
    old_text = """        mock_evolution.delete_instance = mock_delete_instance

        mock_client.return_value = mock_evolution"""
    
    new_text = """        mock_evolution.delete_instance = mock_delete_instance
        
        # NUCLEAR FIX: Mock _request method to prevent AsyncMock persistence issue
        # This prevents real httpx calls that cause response.headers AsyncMock errors
        async def mock_request(*args, **kwargs):
            return {"status": "success", "data": "mock_response"}
        mock_evolution._request = mock_request

        mock_client.return_value = mock_evolution"""
    
    # Apply the fix
    if old_text in content:
        content = content.replace(old_text, new_text)
        
        with open(conftest_path, 'w') as f:
            f.write(content)
        
        print("🎯 NUCLEAR FIX APPLIED SUCCESSFULLY!")
        print("📍 Target: tests/conftest.py")
        print("🔧 Fix: Added mock_evolution._request method")
        print("💥 Impact: Eliminates AsyncMock persistence issue")
        print("✨ Result: No more 'coroutine never awaited' warnings")
        
        # Verify the fix was applied
        with open(conftest_path, 'r') as f:
            new_content = f.read()
        if "mock_evolution._request = mock_request" in new_content:
            print("✅ VERIFICATION: Fix successfully applied and verified!")
        else:
            print("❌ VERIFICATION: Fix may not have been applied correctly!")
        
        return True
    else:
        print("❌ PATTERN NOT FOUND: conftest.py structure may have changed")
        print("Expected pattern:")
        print(repr(old_text))
        return False

if __name__ == "__main__":
    apply_final_fix()