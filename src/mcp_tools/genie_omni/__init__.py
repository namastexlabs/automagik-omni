"""
Genie Omni - Agent-First WhatsApp Communication Tool

Your personal hub to the digital world.
Currently supports: WhatsApp (via Omni platform)
"""

from .server import mcp
from .config import OmniConfig

__all__ = ["mcp", "get_metadata", "get_config_class", "create_server", "OmniConfig"]


def get_metadata():
    """Return tool metadata for MCP hub discovery."""
    return {
        "name": "genie-omni",
        "version": "1.0.0",
        "description": "Agent-first WhatsApp communication via Omni Hub. Your personal hub to the digital world.",
        "author": "Namastex Labs",
        "tags": ["whatsapp", "messaging", "omni", "communication", "agent-first"],
        "config_class": OmniConfig,
    }


def get_config_class():
    """Return the configuration class for this tool."""
    return OmniConfig


def create_server(server_config: OmniConfig | None = None):
    """Return the MCP server instance.

    Args:
        server_config: Optional configuration for the Omni client

    Returns:
        The MCP server instance
    """
    from .server import initialize_client

    # Initialize client with config if provided
    if server_config:
        initialize_client(server_config)

    return mcp
