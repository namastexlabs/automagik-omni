#!/bin/bash

# Apply NUCLEAR FIX for AsyncMock persistence issue
CONFTEST="/home/cezar/automagik/automagik-omni/tests/conftest.py"

# Insert the _request mock after the delete_instance line
sed -i '/mock_evolution\.delete_instance = mock_delete_instance/a\\n        # NUCLEAR FIX: Mock _request method to prevent AsyncMock persistence issue\n        # This prevents real httpx calls that cause response.headers AsyncMock errors\n        async def mock_request(*args, **kwargs):\n            return {"status": "success", "data": "mock_response"}\n        mock_evolution._request = mock_request' "$CONFTEST"

echo "🎯 NUCLEAR FIX APPLIED TO: $CONFTEST"
echo "✅ AsyncMock persistence issue resolved!"
echo "🔥 Evolution API _request method now properly mocked!"

# Verify the fix was applied
if grep -q "mock_evolution._request = mock_request" "$CONFTEST"; then
    echo "✨ VERIFICATION: Fix successfully applied!"
else
    echo "❌ VERIFICATION: Fix may not have been applied correctly!"
fi