"""
MCP server integration with FastAPI and authentication.
"""
import logging
from src.mcp_tools.genie_omni.server import mcp

logger = logging.getLogger(__name__)


def create_mcp_app():
    """
    Create the MCP ASGI app with HTTP transport and authentication.

    Authentication is handled by FastMCP's BearerTokenAuth using the
    MCP_AUTH_TOKEN environment variable.

    Returns:
        Starlette app with lifespan support
    """
    # Create MCP app with HTTP transport
    # Authentication is configured in server.py using BearerTokenAuth
    mcp_app = mcp.http_app(
        path="/",  # Root path since we're mounting at /mcp
        transport="http",  # StreamableHTTP protocol
    )

    logger.info("MCP server initialized with HTTP transport at /mcp")
    return mcp_app
