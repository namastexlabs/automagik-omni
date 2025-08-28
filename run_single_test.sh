#!/bin/bash
cd /home/cezar/automagik/automagik-omni
python3 -m pytest tests/test_omni_endpoints.py::TestOmniChannelsEndpoint::test_successful_channels_retrieval -v --tb=short