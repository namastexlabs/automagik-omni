"""
IPC Configuration for Unix Domain Sockets

This module provides centralized configuration for the IPC socket paths,
allowing for both production (/automagik-omni) and development (~/automagik-omni) setups.
"""

import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class IPCConfig:
    """Configuration for Unix domain socket IPC."""

    # Default production socket directory
    DEFAULT_SOCKET_DIR = "/automagik-omni/sockets"

    # Development/fallback socket directory (user's home)
    USER_SOCKET_DIR = os.path.expanduser("~/automagik-omni/sockets")

    @classmethod
    def get_socket_dir(cls) -> str:
        """
        Get the socket directory path, with fallback to user directory if needed.

        Priority:
        1. Environment variable AUTOMAGIK_SOCKET_DIR
        2. Default /automagik-omni/sockets if writable
        3. Fallback to ~/automagik-omni/sockets
        """
        # Check environment variable first
        env_dir = os.environ.get('AUTOMAGIK_SOCKET_DIR')
        if env_dir:
            socket_dir = os.path.expanduser(env_dir)
            cls._ensure_directory(socket_dir)
            return socket_dir

        # Try default production directory
        if cls._can_write_to_directory(cls.DEFAULT_SOCKET_DIR):
            return cls.DEFAULT_SOCKET_DIR

        # Fallback to user directory
        logger.debug(f"Cannot write to {cls.DEFAULT_SOCKET_DIR}, using user directory: {cls.USER_SOCKET_DIR}")
        cls._ensure_directory(cls.USER_SOCKET_DIR)
        return cls.USER_SOCKET_DIR

    @classmethod
    def get_socket_path(cls, channel_type: str, instance_name: str) -> str:
        """
        Get the full socket path for a specific channel and instance.

        Args:
            channel_type: Type of channel (discord, slack, telegram, whatsapp)
            instance_name: Name of the instance

        Returns:
            str: Full path to the socket file
        """
        socket_dir = cls.get_socket_dir()
        return os.path.join(socket_dir, f"{channel_type}-{instance_name}.sock")

    @classmethod
    def _can_write_to_directory(cls, path: str) -> bool:
        """Check if we can write to a directory (or create it)."""
        try:
            # Try to create parent directory
            parent = os.path.dirname(path)
            if parent and parent != "/" and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True, mode=0o755)

            # Try to create the directory itself
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True, mode=0o755)

            # Check if we can write
            test_file = os.path.join(path, '.test_write')
            try:
                Path(test_file).touch()
                os.unlink(test_file)
                return True
            except (OSError, PermissionError):
                return False

        except (OSError, PermissionError):
            return False

    @classmethod
    def _ensure_directory(cls, path: str):
        """Ensure a directory exists with proper permissions."""
        try:
            os.makedirs(path, exist_ok=True, mode=0o755)
            logger.debug(f"Ensured socket directory exists: {path}")
        except Exception as e:
            logger.error(f"Failed to create socket directory {path}: {e}")
            raise

    @classmethod
    def cleanup_stale_socket(cls, socket_path: str):
        """Remove stale socket file if it exists."""
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
                logger.debug(f"Removed stale socket: {socket_path}")
            except Exception as e:
                logger.warning(f"Failed to remove stale socket {socket_path}: {e}")

    @classmethod
    def list_active_sockets(cls) -> list:
        """List all active socket files."""
        socket_dir = cls.get_socket_dir()
        if not os.path.exists(socket_dir):
            return []

        sockets = []
        for entry in os.listdir(socket_dir):
            if entry.endswith('.sock'):
                full_path = os.path.join(socket_dir, entry)
                if os.path.exists(full_path):
                    # Parse channel and instance from filename
                    parts = entry[:-5].split('-', 1)  # Remove .sock and split
                    if len(parts) == 2:
                        sockets.append({
                            'channel': parts[0],
                            'instance': parts[1],
                            'path': full_path,
                            'created': os.path.getctime(full_path)
                        })

        return sockets
