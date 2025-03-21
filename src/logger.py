"""
Centralized logging configuration for the application.
Provides colorful, emoji-decorated log formatting with customizable options.
"""

import logging
import sys
from typing import Optional, Dict, Any

from src.config import config

class ColoredFormatter(logging.Formatter):
    """Custom formatter for colored and emoji-decorated log output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[94m',     # Blue
        'INFO': '\033[92m',      # Green
        'WARNING': '\033[93m',   # Yellow
        'ERROR': '\033[91m',     # Red
        'CRITICAL': '\033[95m',  # Magenta
        'RESET': '\033[0m',      # Reset
    }
    
    # Emoji decorations for log levels
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '✓',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔥',
    }
    
    def __init__(self, fmt: str = None, datefmt: str = None, use_colors: bool = True, 
                 use_emojis: bool = True, shorten_paths: bool = True):
        """Initialize the formatter with customization options.
        
        Args:
            fmt: Log format string
            datefmt: Date format string
            use_colors: Whether to use ANSI colors
            use_emojis: Whether to use emoji decorations
            shorten_paths: Whether to shorten module paths for non-error logs
        """
        self.use_colors = use_colors
        self.use_emojis = use_emojis
        self.shorten_paths = shorten_paths
        super().__init__(fmt=fmt, datefmt=datefmt)
    
    def _shorten_name(self, name: str) -> str:
        """Shorten module paths to be more readable.
        
        For paths like:
        - 'src.channels.whatsapp.client' -> 'whatsapp.client'
        - 'src.services.agent_service' -> 'agent_service'
        """
        if not name or not self.shorten_paths:
            return name
            
        # Get components of the module path
        parts = name.split('.')
        if len(parts) <= 2:
            return name
            
        # Find the most specific meaningful components
        # For whatsapp modules, keep 'whatsapp.something'
        if 'whatsapp' in parts:
            whatsapp_idx = parts.index('whatsapp')
            return '.'.join(parts[whatsapp_idx:])
        
        # For services, just keep the service name
        if 'services' in parts:
            service_idx = parts.index('services')
            if service_idx + 1 < len(parts):
                return parts[service_idx + 1]  # Just the service name
        
        # For CLI modules, just return 'cli'
        if 'cli' in parts:
            return 'cli'
            
        # For channels other than whatsapp, return 'channel.name'
        if 'channels' in parts:
            channel_idx = parts.index('channels')
            if channel_idx + 1 < len(parts):
                return parts[channel_idx + 1]  # Just the channel name
        
        # If no specific rule matches, return last component
        return parts[-1]
    
    def format(self, record):
        # Make a copy of the record to avoid modifying the original
        record_copy = logging.makeLogRecord(record.__dict__)
        
        # Add colors to the levelname if enabled
        if self.use_colors:
            levelname = record_copy.levelname
            if levelname in self.COLORS:
                colored_levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
                record_copy.levelname = colored_levelname
        
        # Shorten module name for non-error logs
        if self.shorten_paths and record.levelno < logging.ERROR:
            record_copy.name = self._shorten_name(record.name)
        
        # Format the record first to get the message attribute
        formatted_msg = super().format(record_copy)
        
        # Add emoji decoration to the message if enabled
        if self.use_emojis:
            levelname = record.levelname  # Use original record level
            if levelname in self.EMOJIS:
                emoji = self.EMOJIS[levelname]
                # Only add emoji if not already present
                if not any(emoji in formatted_msg for emoji in self.EMOJIS.values()):
                    formatted_msg = f"{self.EMOJIS[levelname]} {formatted_msg}"
        
        return formatted_msg

def setup_logging(level: Optional[str] = None, use_colors: bool = None, 
                 use_emojis: bool = True, shorten_paths: bool = None) -> None:
    """Set up logging configuration for the entire application.
    
    Args:
        level: Log level (if None, use from config)
        use_colors: Whether to use ANSI colors (if None, use from config)
        use_emojis: Whether to use emoji decorations
        shorten_paths: Whether to shorten module paths for non-error logs (if None, use from config)
    """
    # Use config values if not specified
    if level is None:
        level = config.logging.level
    
    if use_colors is None:
        use_colors = config.logging.use_colors
        
    if shorten_paths is None:
        shorten_paths = config.logging.shorten_paths
    
    # Get format strings from config
    log_format = config.logging.format
    date_format = config.logging.date_format
    
    # Create the formatter
    formatter = ColoredFormatter(
        fmt=log_format,
        datefmt=date_format,
        use_colors=use_colors,
        use_emojis=use_emojis,
        shorten_paths=shorten_paths
    )
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, str(level).upper()))
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler with the custom formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Log that logging has been set up
    logger = logging.getLogger(__name__)
    logger.debug("Logging initialized with level: %s", level)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.
    
    This is a convenience wrapper around logging.getLogger that ensures
    the custom configuration is applied if not already set up.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    # Check if root logger has handlers
    if not logging.getLogger().handlers:
        setup_logging()
    
    return logging.getLogger(name) 