#!/usr/bin/env python3
"""Execute the update directly"""

import os
import sys

# Change to the correct directory
os.chdir('/home/cezar/automagik/automagik-omni')

# Execute the update script
exec(open('targeted_update.py').read())