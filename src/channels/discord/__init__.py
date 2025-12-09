"""Discord channel implementation."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Discord components - all optional, guarded by try-except
DISCORD_COMPONENTS_AVAILABLE = False
DiscordChannelHandler: Any = None
DiscordBotManager: Any = None
DiscordVoiceManager: Any = None
VoiceSession: Any = None
STTProvider: Any = None
TTSProvider: Any = None

try:
    from .channel_handler import DiscordChannelHandler
    from .bot_manager import DiscordBotManager
    from .voice_manager import (
        DiscordVoiceManager,
        VoiceSession,
        STTProvider,
        TTSProvider,
    )

    DISCORD_COMPONENTS_AVAILABLE = True
    logger.info("Discord components loaded successfully")
except (ImportError, AttributeError) as e:
    logger.warning(f"Discord components not available: {e}. Install with: uv sync --extra discord")

__all__ = [
    "DISCORD_COMPONENTS_AVAILABLE",
    "DiscordChannelHandler",
    "DiscordBotManager",
    "DiscordVoiceManager",
    "VoiceSession",
    "STTProvider",
    "TTSProvider",
]
