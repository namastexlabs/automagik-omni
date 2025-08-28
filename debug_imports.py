#!/usr/bin/env python3
"""Debug import issues"""
import sys
import os

# Add src to Python path
sys.path.insert(0, 'src')

def test_import(module_name):
    try:
        if '.' in module_name:
            exec(f"from {module_name.rsplit('.', 1)[0]} import {module_name.rsplit('.', 1)[1]}")
        else:
            exec(f"import {module_name}")
        print(f"✓ {module_name}")
        return True
    except Exception as e:
        print(f"✗ {module_name}: {e}")
        return False

print("Testing key imports...")

# Test basic imports
test_import("src.channels.handlers.whatsapp_chat_handler")
test_import("src.channels.handlers.discord_chat_handler")

# Test dependencies
test_import("src.channels.omni_base")
test_import("src.channels.whatsapp.channel_handler")
test_import("src.channels.whatsapp.omni_evolution_client")
test_import("src.channels.discord.channel_handler")
test_import("src.api.schemas.omni")
test_import("src.db.models")

print("\nTesting specific classes...")
try:
    from src.channels.handlers.whatsapp_chat_handler import WhatsAppChatHandler
    print("✓ WhatsAppChatHandler class")
except Exception as e:
    print(f"✗ WhatsAppChatHandler class: {e}")

try:
    from src.channels.handlers.discord_chat_handler import DiscordChatHandler
    print("✓ DiscordChatHandler class")
except Exception as e:
    print(f"✗ DiscordChatHandler class: {e}")