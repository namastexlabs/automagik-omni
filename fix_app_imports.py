#!/usr/bin/env python3
"""Script to update imports in app.py from unified to omni"""

import re

def update_app_imports():
    app_file = "/home/cezar/automagik/automagik-omni/src/api/app.py"
    
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Replace imports
    content = content.replace(
        'from src.api.routes.unified import router as unified_router',
        'from src.api.routes.omni import router as omni_router'
    )
    
    # Replace router usage
    content = content.replace('unified_router', 'omni_router')
    
    # Replace comments
    content = content.replace(
        '# Include unified communication routes',
        '# Include omni communication routes'
    )
    
    content = content.replace(
        '3. Send messages using the unified endpoints',
        '3. Send messages using the omni endpoints'
    )
    
    with open(app_file, 'w') as f:
        f.write(content)
    
    print("Updated app.py imports successfully!")

if __name__ == "__main__":
    update_app_imports()