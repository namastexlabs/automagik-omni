path="/home/cezar/automagik/automagik-omni/tests/conftest.py"
content=open(path).read()
# Correct pattern - no empty line between them
old = "        mock_evolution.delete_instance = mock_delete_instance\n        mock_client.return_value = mock_evolution"
new = """        mock_evolution.delete_instance = mock_delete_instance
        
        # NUCLEAR FIX: Mock _request method to prevent AsyncMock persistence issue
        # This prevents real httpx calls that cause response.headers AsyncMock errors
        async def mock_request(*args, **kwargs):
            return {"status": "success", "data": "mock_response"}
        mock_evolution._request = mock_request

        mock_client.return_value = mock_evolution"""
fixed = content.replace(old, new)
open(path,'w').write(fixed)
print("✅ NUCLEAR FIX APPLIED!" if "_request = mock_request" in fixed else "❌ Fix failed")