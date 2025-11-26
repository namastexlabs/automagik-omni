"""
Genie Omni - Agent-First WhatsApp Communication Tool
Your personal hub to the digital world.

Philosophy: Tools designed from Genie's perspective, not API perspective.
You ARE connected to WhatsApp. You CAN send and read messages.
"""

import logging
from typing import Optional
from fastmcp import FastMCP, Context
from .client import OmniClient
from .config import OmniConfig

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("genie-omni")

# Global client and config (initialized on first use)
_client: Optional[OmniClient] = None
_config: Optional[OmniConfig] = None


def initialize_client(config: OmniConfig) -> None:
    """Initialize the global client with a specific config.

    Args:
        config: Configuration for the Omni client
    """
    global _client, _config
    _config = config
    _client = OmniClient(config)


def get_config(ctx: Optional[Context] = None) -> OmniConfig:
    """Get configuration from context or global config (cached in context state)."""
    if ctx:
        # Try to get cached config from context state (per-request cache)
        cached = ctx.get_state("genie_omni_config")
        if cached:
            return cached

        # Try to get user-specific config from context (multi-tenant mode)
        if hasattr(ctx, "tool_config") and ctx.tool_config:
            try:
                from automagik_tools.hub.config_injection import create_user_config_instance
                user_config = create_user_config_instance(OmniConfig, ctx.tool_config)
                # Cache in context state for this request
                ctx.set_state("genie_omni_config", user_config)
                return user_config
            except Exception:
                pass

    global _config
    if _config is None:
        _config = OmniConfig.from_env()
    return _config


def get_client(ctx: Optional[Context] = None) -> OmniClient:
    """Get client with user-specific or global config (cached in context state)."""
    if ctx:
        # Try to get cached client from context state (per-request cache)
        cached = ctx.get_state("genie_omni_client")
        if cached:
            return cached

    cfg = get_config(ctx)

    # For multi-tenant with user config, create fresh client and cache it
    if ctx and hasattr(ctx, "tool_config") and ctx.tool_config:
        client = OmniClient(cfg)
        ctx.set_state("genie_omni_client", client)
        return client

    # For single-tenant, use singleton
    global _client
    if _client is None:
        _client = OmniClient(cfg)
    return _client


# Register all tool modules
from .tools import identity, contacts, reading, messaging, discovery, admin, multimodal

identity.register_tools(mcp, get_client)
contacts.register_tools(mcp, get_client)
reading.register_tools(mcp, get_client)
messaging.register_tools(mcp, get_client, get_config)
discovery.register_tools(mcp, get_client, get_config)
admin.register_tools(mcp, get_client)
multimodal.register_tools(mcp, get_client, get_config)
