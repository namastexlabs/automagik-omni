#!/usr/bin/env python3
"""
NUCLEAR FIX: AsyncMock persistence issue in Evolution API client
Target: RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
Location: evolution_client.py:85
"""

def fix_conftest_asyncmock():
    """Fix the AsyncMock persistence issue by mocking the _request method directly."""
    conftest_path = "/home/cezar/automagik/automagik-omni/tests/conftest.py"
    
    with open(conftest_path, 'r') as f:
        content = f.read()
    
    # Find the line to replace
    old_pattern = '''        mock_evolution.delete_instance = mock_delete_instance

        mock_client.return_value = mock_evolution'''
    
    new_pattern = '''        mock_evolution.delete_instance = mock_delete_instance
        
        # NUCLEAR FIX: Mock _request method to prevent AsyncMock persistence issue
        # This prevents real httpx calls that cause response.headers AsyncMock errors
        async def mock_request(*args, **kwargs):
            return {"status": "success", "data": "mock_response"}
        mock_evolution._request = mock_request

        mock_client.return_value = mock_evolution'''
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        
        with open(conftest_path, 'w') as f:
            f.write(content)
        
        print("✅ NUCLEAR FIX APPLIED: AsyncMock persistence issue resolved!")
        print("📍 Location: tests/conftest.py")
        print("🎯 Target: _request method now properly mocked")
        print("🔥 Effect: Eliminates 'coroutine never awaited' warnings")
        return True
    else:
        print("❌ Pattern not found - conftest.py may have changed")
        return False

if __name__ == "__main__":
    fix_conftest_asyncmock()