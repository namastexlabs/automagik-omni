#!/bin/bash
cd /home/cezar/automagik/automagik-omni
cp src/api/app.py src/api/app_backup_original.py
cp src/api/app_new.py src/api/app.py
echo "✅ Successfully replaced app.py with fixed version!"
echo "✓ Backup created at src/api/app_backup_original.py"
echo "✓ Applied unified router fixes from src/api/app_new.py"