"""Custom exceptions for the automagik-omni project."""


class AutomagikError(Exception):
    """Base exception for automagik-omni errors."""
    pass


class ConfigurationError(AutomagikError):
    """Raised when there's a configuration issue."""
    pass


class ChannelError(AutomagikError):
    """Raised when there's a channel-related error."""
    pass


class DiscordError(ChannelError):
    """Raised when there's a Discord-specific error."""
    pass


class VoiceError(DiscordError):
    """Raised when there's a voice-related error."""
    pass


class DatabaseError(AutomagikError):
    """Raised when there's a database-related error."""
    pass


class ValidationError(AutomagikError):
    """Raised when validation fails."""
    pass