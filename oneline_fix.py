import re
path="/home/cezar/automagik/automagik-omni/tests/conftest.py"
content=open(path).read()
fixed=content.replace("        mock_evolution.delete_instance = mock_delete_instance\n\n        mock_client.return_value = mock_evolution", "        mock_evolution.delete_instance = mock_delete_instance\n\n        # NUCLEAR FIX: Mock _request method to prevent AsyncMock persistence issue\n        async def mock_request(*args, **kwargs):\n            return {\"status\": \"success\", \"data\": \"mock_response\"}\n        mock_evolution._request = mock_request\n\n        mock_client.return_value = mock_evolution")
open(path,'w').write(fixed)
print("✅ NUCLEAR FIX APPLIED!" if "_request = mock_request" in fixed else "❌ Fix failed")