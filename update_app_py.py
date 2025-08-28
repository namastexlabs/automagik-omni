#!/usr/bin/env python3
"""Update app.py to use omni routes"""

def update_app():
    filepath = "/home/cezar/automagik/automagik-omni/src/api/app.py"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Update imports
    content = content.replace(
        'from src.api.routes.unified import router as unified_router',
        'from src.api.routes.omni import router as omni_router'
    )
    
    # Update router usage
    content = content.replace('unified_router', 'omni_router')
    
    # Update comments
    content = content.replace(
        '# Include unified communication routes',
        '# Include omni communication routes'
    )
    
    content = content.replace(
        '3. Send messages using the unified endpoints',
        '3. Send messages using the omni endpoints'
    )
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print("Updated app.py successfully!")

if __name__ == "__main__":
    update_app()