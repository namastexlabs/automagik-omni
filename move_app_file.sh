#!/bin/bash
# Move the updated app.py file to replace the original
mv /home/cezar/automagik/automagik-omni/src/api/app.py /home/cezar/automagik/automagik-omni/src/api/app_backup.py
mv /home/cezar/automagik/automagik-omni/src/api/app_updated.py /home/cezar/automagik/automagik-omni/src/api/app.py
echo "File replacement completed successfully"