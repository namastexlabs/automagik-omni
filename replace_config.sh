#!/bin/bash
cd /home/cezar/automagik/automagik-omni
mv src/config.py src/config.py.backup
mv config_updated.py src/config.py
echo "Config file updated with CORS support"