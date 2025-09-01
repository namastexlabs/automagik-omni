"""Discord channel implementation."""

import logging

logger = logging.getLogger(__name__)

try:
    from .channel_handler import DiscordChannelHandler
    from .bot_manager import DiscordBotManager
    from .voice_manager import DiscordVoiceManager, VoiceSession, STTProvider, TTSProvider
    
    __all__ = [
        "DiscordChannelHandler",
        "DiscordBotManager",
        "DiscordVoiceManager",
        "VoiceSession",
        "STTProvider",
        "TTSProvider",
    ]
except ImportError as e:
    logger.warning(f"Discord components not available: {e}")
    __all__ = []
