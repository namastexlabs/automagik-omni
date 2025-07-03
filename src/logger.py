"""
Centralized logging configuration for the application.
Provides colorful, emoji-decorated log formatting with customizable options.
"""

import logging
import sys
import os
import uuid
from datetime import datetime
from typing import Optional

from src.config import config
from src.utils.datetime_utils import now


class ColoredFormatter(logging.Formatter):
    """Custom formatter for colored and emoji-decorated log output."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    # Emoji decorations for log levels
    EMOJIS = {
        "DEBUG": "🔍",
        "INFO": "✓",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🔥",
    }

    def __init__(
        self,
        fmt: str = None,
        datefmt: str = None,
        use_colors: bool = True,
        use_emojis: bool = True,
        shorten_paths: bool = True,
    ):
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
        parts = name.split(".")
        if len(parts) <= 2:
            return name

        # Find the most specific meaningful components
        # For whatsapp modules, keep 'whatsapp.something'
        if "whatsapp" in parts:
            whatsapp_idx = parts.index("whatsapp")
            return ".".join(parts[whatsapp_idx:])

        # For services, just keep the service name
        if "services" in parts:
            service_idx = parts.index("services")
            if service_idx + 1 < len(parts):
                return parts[service_idx + 1]  # Just the service name

        # For CLI modules, just return 'cli'
        if "cli" in parts:
            return "cli"

        # For channels other than whatsapp, return 'channel.name'
        if "channels" in parts:
            channel_idx = parts.index("channels")
            if channel_idx + 1 < len(parts):
                return parts[channel_idx + 1]  # Just the channel name

        # If no specific rule matches, return last component
        return parts[-1]

    def format(self, record):
        # Make a copy of the record to avoid modifying the original
        record_copy = logging.makeLogRecord(record.__dict__)

        # Convert timestamp to configured timezone
        try:
            # Convert record time (which is a UTC timestamp) to configured timezone
            import pytz
            from src.utils.datetime_utils import to_local

            # Create timezone-aware UTC datetime from timestamp
            utc_time = datetime.fromtimestamp(record.created, tz=pytz.UTC)
            local_time = to_local(utc_time)
            # Update the record with timezone-aware time
            record_copy.created = local_time.timestamp()
        except Exception:
            # Fallback to original time if timezone conversion fails
            # This ensures logging still works even if timezone config is broken
            pass

        # Add colors to the levelname if enabled
        if self.use_colors:
            levelname = record_copy.levelname
            if levelname in self.COLORS:
                colored_levelname = (
                    f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
                )
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
                self.EMOJIS[levelname]
                # Only add emoji if not already present
                if not any(emoji in formatted_msg for emoji in self.EMOJIS.values()):
                    formatted_msg = f"{self.EMOJIS[levelname]} {formatted_msg}"

        return formatted_msg


def setup_logging(
    level: Optional[str] = None,
    use_colors: bool = None,
    use_emojis: bool = True,
    shorten_paths: bool = None,
) -> None:
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

    # Create the console formatter (with colors and emojis)
    console_formatter = ColoredFormatter(
        fmt=log_format,
        datefmt=date_format,
        use_colors=use_colors,
        use_emojis=use_emojis,
        shorten_paths=shorten_paths,
    )

    # Create the file formatter (without colors and emojis for clean file output)
    file_log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_formatter = logging.Formatter(fmt=file_log_format, datefmt="%Y-%m-%d %H:%M:%S")

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, str(level).upper()))

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler with the custom formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if log folder is configured
    if config.logging.enable_file_logging and config.logging.log_folder:
        try:
            # Create log folder if it doesn't exist
            os.makedirs(config.logging.log_folder, exist_ok=True)

            # Generate unique server restart ID
            server_id = str(uuid.uuid4())[:8]
            timestamp = now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"omnihub_{timestamp}_{server_id}.log"
            log_filepath = os.path.join(config.logging.log_folder, log_filename)

            # Create file handler
            file_handler = logging.FileHandler(log_filepath, mode="w", encoding="utf-8")
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

            # Log that file logging is enabled
            root_logger.info(f"📁 File logging enabled: {log_filepath}")

        except Exception as e:
            # If file logging fails, log error but continue with console logging
            root_logger.error(f"❌ Failed to setup file logging: {e}")

    # Control HTTP client logging to prevent duplicates
    # Set HTTP client libraries to WARNING level to reduce noise
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Configure uvicorn loggers to use our custom formatter
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_error_logger = logging.getLogger("uvicorn.error")

    # Remove uvicorn's default handlers and use our formatter
    for uvicorn_log in [uvicorn_logger, uvicorn_access_logger, uvicorn_error_logger]:
        uvicorn_log.handlers.clear()
        uvicorn_log.propagate = True  # Let our root logger handle it

    # Set uvicorn to INFO level to reduce noise but keep important messages
    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_access_logger.setLevel(logging.WARNING)  # Reduce HTTP access logs
    uvicorn_error_logger.setLevel(logging.WARNING)

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
