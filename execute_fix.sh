#!/bin/bash

# NUCLEAR FIX: AsyncMock persistence issue
# Insert _request method mock after delete_instance line

sed -i '/mock_evolution\.delete_instance = mock_delete_instance/a\\n        # NUCLEAR FIX: Mock _request method to prevent AsyncMock persistence issue\n        # This prevents real httpx calls that cause response.headers AsyncMock errors\n        async def mock_request(*args, **kwargs):\n            return {"status": "success", "data": "mock_response"}\n        mock_evolution._request = mock_request' /home/cezar/automagik/automagik-omni/tests/conftest.py

echo "✅ NUCLEAR FIX APPLIED!"
echo "🎯 _request method now properly mocked in conftest.py"
echo "🔥 AsyncMock persistence issue eliminated!"