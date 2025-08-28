#!/usr/bin/env python3
"""Update Discord handler to use omni imports"""

def update_discord_handler():
    filepath = "/home/cezar/automagik/automagik-omni/src/channels/handlers/discord_chat_handler.py"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Update imports
    content = content.replace(
        'from src.channels.unified_base import UnifiedChannelHandler',
        'from src.channels.omni_base import OmniChannelHandler'
    )
    
    content = content.replace(
        'from src.api.schemas.unified import UnifiedContact, UnifiedChat, UnifiedChannelInfo',
        'from src.api.schemas.omni import OmniContact, OmniChat, OmniChannelInfo'
    )
    
    content = content.replace(
        'from src.services.unified_transformers import DiscordTransformer',
        'from src.services.omni_transformers import DiscordTransformer'
    )
    
    # Update class definition
    content = content.replace(
        'class DiscordChatHandler(DiscordChannelHandler, UnifiedChannelHandler):',
        'class DiscordChatHandler(DiscordChannelHandler, OmniChannelHandler):'
    )
    
    # Update type annotations and references
    content = content.replace('UnifiedContact', 'OmniContact')
    content = content.replace('UnifiedChat', 'OmniChat')
    content = content.replace('UnifiedChannelInfo', 'OmniChannelInfo')
    
    # Update method calls
    content = content.replace('contact_to_unified', 'contact_to_omni')
    content = content.replace('chat_to_unified', 'chat_to_omni')
    content = content.replace('channel_to_unified', 'channel_to_omni')
    
    # Update variable names
    content = content.replace('unified_contact = ', 'omni_contact = ')
    content = content.replace('unified_chat = ', 'omni_chat = ')
    content = content.replace('unified_channel_info = ', 'omni_channel_info = ')
    content = content.replace('unified_contact)', 'omni_contact)')
    content = content.replace('unified_chat)', 'omni_chat)')
    content = content.replace('return unified_channel_info', 'return omni_channel_info')
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print("Updated Discord handler successfully!")

if __name__ == "__main__":
    update_discord_handler()