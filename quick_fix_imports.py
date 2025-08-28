#!/usr/bin/env python3
"""Quick fix for key import files"""

def update_file(filepath, replacements):
    """Update a file with the given replacements"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"Updated {filepath}")
        
    except Exception as e:
        print(f"Error updating {filepath}: {e}")

# Update key files
files_and_replacements = {
    "/home/cezar/automagik/automagik-omni/src/api/app.py": {
        "from src.api.routes.unified import router as unified_router": "from src.api.routes.omni import router as omni_router",
        "unified_router": "omni_router",
        "# Include unified communication routes": "# Include omni communication routes",
        "3. Send messages using the unified endpoints": "3. Send messages using the omni endpoints"
    },
    "/home/cezar/automagik/automagik-omni/src/channels/handlers/whatsapp_chat_handler.py": {
        "from src.channels.unified_base import UnifiedChannelHandler": "from src.channels.omni_base import OmniChannelHandler",
        "from src.api.schemas.unified import UnifiedContact, UnifiedChat, UnifiedChannelInfo": "from src.api.schemas.omni import OmniContact, OmniChat, OmniChannelInfo",
        "class WhatsAppChatHandler(WhatsAppChannelHandler, UnifiedChannelHandler):": "class WhatsAppChatHandler(WhatsAppChannelHandler, OmniChannelHandler):",
        "UnifiedContact": "OmniContact",
        "UnifiedChat": "OmniChat", 
        "UnifiedChannelInfo": "OmniChannelInfo"
    },
    "/home/cezar/automagik/automagik-omni/src/channels/handlers/discord_chat_handler.py": {
        "from src.channels.unified_base import UnifiedChannelHandler": "from src.channels.omni_base import OmniChannelHandler",
        "from src.api.schemas.unified import UnifiedContact, UnifiedChat, UnifiedChannelInfo": "from src.api.schemas.omni import OmniContact, OmniChat, OmniChannelInfo",
        "class DiscordChatHandler(DiscordChannelHandler, UnifiedChannelHandler):": "class DiscordChatHandler(DiscordChannelHandler, OmniChannelHandler):",
        "UnifiedContact": "OmniContact",
        "UnifiedChat": "OmniChat",
        "UnifiedChannelInfo": "OmniChannelInfo"
    }
}

for filepath, replacements in files_and_replacements.items():
    update_file(filepath, replacements)

print("Quick fix complete!")