#!/usr/bin/env python3
import os
import sys

# Change to project directory
os.chdir('/home/cezar/automagik/automagik-omni')

# Add src to path
sys.path.insert(0, 'src')

# Try importing the handlers to see if there are import issues
try:
    from src.channels.handlers.whatsapp_chat_handler import WhatsAppChatHandler
    print("✓ WhatsAppChatHandler imported successfully")
except Exception as e:
    print(f"✗ WhatsAppChatHandler import failed: {e}")

try:
    from src.channels.handlers.discord_chat_handler import DiscordChatHandler
    print("✓ DiscordChatHandler imported successfully")
except Exception as e:
    print(f"✗ DiscordChatHandler import failed: {e}")

# Try importing test modules
try:
    from tests.test_omni_handlers import TestWhatsAppChatHandler
    print("✓ test_omni_handlers imported successfully")
except Exception as e:
    print(f"✗ test_omni_handlers import failed: {e}")

try:
    from tests.test_omni_handlers_fixed import TestWhatsAppChatHandlerFixed
    print("✓ test_omni_handlers_fixed imported successfully")
except Exception as e:
    print(f"✗ test_omni_handlers_fixed import failed: {e}")