"""
Channels module for Agent application.
This module handles integrations with different messaging platforms.
"""

import logging
from src.channels.base import ChannelHandlerFactory

logger = logging.getLogger(__name__)

# Register WhatsApp handler (always available as it's in core deps)
try:
    from src.channels.whatsapp.channel_handler import WhatsAppChannelHandler

    ChannelHandlerFactory.register_handler("whatsapp", WhatsAppChannelHandler)
    logger.info("WhatsApp channel handler registered")
except ImportError as e:
    logger.warning(f"Failed to load WhatsApp handler: {e}")

# Register Discord handler (if discord.py is installed)
try:
    import discord
    from src.channels.discord.channel_handler import DiscordChannelHandler

    ChannelHandlerFactory.register_handler("discord", DiscordChannelHandler)
    logger.info("Discord channel handler registered")
except ImportError:
    logger.info("Discord dependencies not installed. Install with: pip install discord.py")
