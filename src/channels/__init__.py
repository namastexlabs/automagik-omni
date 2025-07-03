"""
Channels module for Agent application.
This module handles integrations with different messaging platforms.
"""

from src.channels.base import ChannelHandlerFactory
from src.channels.whatsapp.channel_handler import WhatsAppChannelHandler

# Register all channel handlers
ChannelHandlerFactory.register_handler("whatsapp", WhatsAppChannelHandler)
