#!/bin/bash
cd /home/cezar/automagik/automagik-omni
export PYTHONPATH=/home/cezar/automagik/automagik-omni
export API_KEY=test-key

echo "🔍 Running failing test..."
python3 -m pytest tests/test_omni_endpoints_fixed.py::TestOmniEndpointsAuthentication::test_channels_endpoint_requires_auth -vvv --tb=short --no-header -q