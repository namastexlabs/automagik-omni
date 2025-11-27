"""
Channels module for Agent application.
This module handles integrations with different messaging platforms.

Omnichannel Integration Roadmap:
================================
- Messaging: WhatsApp, Discord, Telegram, Slack, Signal, Teams
- Social: Instagram, LinkedIn, Twitter/X, Facebook Messenger, TikTok
- Email: Gmail, Outlook
- Calendar: Google Calendar, iCloud Calendar
- Productivity: Notion, Trello, Asana, Jira, GitHub
- Voice/Video: Discord Voice, Zoom, Google Meet
"""

import logging
from src.channels.base import ChannelHandlerFactory

logger = logging.getLogger(__name__)

# =============================================================================
# IMPLEMENTED CHANNELS
# =============================================================================

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

# =============================================================================
# COMING SOON CHANNELS (Placeholder registrations for UI discovery)
# =============================================================================

# Full channel catalog with metadata for UI display
CHANNEL_CATALOG = {
    # Implemented
    "whatsapp": {
        "name": "WhatsApp",
        "category": "messaging",
        "status": "implemented",
        "icon": "whatsapp",
        "pattern": "evolution_api",
    },
    "discord": {
        "name": "Discord",
        "category": "messaging",
        "status": "implemented",
        "icon": "discord",
        "pattern": "subprocess_bot",
    },
    # Messaging - Coming Soon
    "telegram": {
        "name": "Telegram",
        "category": "messaging",
        "status": "coming_soon",
        "icon": "telegram",
        "pattern": "subprocess_bot",
    },
    "slack": {
        "name": "Slack",
        "category": "messaging",
        "status": "coming_soon",
        "icon": "slack",
        "pattern": "subprocess_bot",
    },
    "signal": {
        "name": "Signal",
        "category": "messaging",
        "status": "coming_soon",
        "icon": "signal",
        "pattern": "subprocess_bot",
    },
    "teams": {
        "name": "Microsoft Teams",
        "category": "messaging",
        "status": "coming_soon",
        "icon": "teams",
        "pattern": "api_handler",
    },
    # Social Media - Coming Soon
    "instagram": {
        "name": "Instagram",
        "category": "social",
        "status": "coming_soon",
        "icon": "instagram",
        "pattern": "api_handler",
    },
    "linkedin": {
        "name": "LinkedIn",
        "category": "social",
        "status": "coming_soon",
        "icon": "linkedin",
        "pattern": "api_handler",
    },
    "twitter": {
        "name": "Twitter / X",
        "category": "social",
        "status": "coming_soon",
        "icon": "twitter",
        "pattern": "api_handler",
    },
    "facebook": {
        "name": "Facebook Messenger",
        "category": "social",
        "status": "coming_soon",
        "icon": "facebook",
        "pattern": "api_handler",
    },
    "tiktok": {
        "name": "TikTok",
        "category": "social",
        "status": "coming_soon",
        "icon": "tiktok",
        "pattern": "api_handler",
    },
    # Email - Coming Soon
    "gmail": {
        "name": "Gmail",
        "category": "email",
        "status": "coming_soon",
        "icon": "gmail",
        "pattern": "api_handler",
    },
    "outlook": {
        "name": "Outlook",
        "category": "email",
        "status": "coming_soon",
        "icon": "outlook",
        "pattern": "api_handler",
    },
    # Calendar - Coming Soon
    "google_calendar": {
        "name": "Google Calendar",
        "category": "calendar",
        "status": "coming_soon",
        "icon": "google_calendar",
        "pattern": "api_handler",
    },
    "icloud_calendar": {
        "name": "iCloud Calendar",
        "category": "calendar",
        "status": "coming_soon",
        "icon": "apple",
        "pattern": "api_handler",
    },
    # Productivity - Coming Soon
    "notion": {
        "name": "Notion",
        "category": "productivity",
        "status": "coming_soon",
        "icon": "notion",
        "pattern": "api_handler",
    },
    "trello": {
        "name": "Trello",
        "category": "productivity",
        "status": "coming_soon",
        "icon": "trello",
        "pattern": "api_handler",
    },
    "asana": {
        "name": "Asana",
        "category": "productivity",
        "status": "coming_soon",
        "icon": "asana",
        "pattern": "api_handler",
    },
    "jira": {
        "name": "Jira",
        "category": "productivity",
        "status": "coming_soon",
        "icon": "jira",
        "pattern": "api_handler",
    },
    "github": {
        "name": "GitHub",
        "category": "productivity",
        "status": "coming_soon",
        "icon": "github",
        "pattern": "api_handler",
    },
    # Voice/Video - Coming Soon
    "zoom": {
        "name": "Zoom",
        "category": "voice",
        "status": "coming_soon",
        "icon": "zoom",
        "pattern": "api_handler",
    },
    "google_meet": {
        "name": "Google Meet",
        "category": "voice",
        "status": "coming_soon",
        "icon": "google_meet",
        "pattern": "api_handler",
    },
}


def get_supported_channels():
    """Get list of all supported channels with their status."""
    return CHANNEL_CATALOG


def get_implemented_channels():
    """Get list of implemented (ready to use) channels."""
    return {k: v for k, v in CHANNEL_CATALOG.items() if v["status"] == "implemented"}


def get_coming_soon_channels():
    """Get list of coming soon channels."""
    return {k: v for k, v in CHANNEL_CATALOG.items() if v["status"] == "coming_soon"}


def get_channels_by_category(category: str):
    """Get channels filtered by category."""
    return {k: v for k, v in CHANNEL_CATALOG.items() if v["category"] == category}
