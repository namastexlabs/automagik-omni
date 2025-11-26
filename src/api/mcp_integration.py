"""
MCP server integration with FastAPI and authentication.
"""
import logging
import os
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from src.mcp_tools.genie_omni.server import mcp
from src.config import config

logger = logging.getLogger(__name__)


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce x-api-key authentication for MCP requests."""

    async def dispatch(self, request: Request, call_next):
        # Extract API key from header
        api_key = request.headers.get("x-api-key")

        # Skip auth in test environment
        if os.getenv("ENVIRONMENT", "").lower() == "test":
            return await call_next(request)

        # Check if key is configured
        configured_key = config.api.api_key
        if not configured_key:
            # Development mode - allow without key
            logger.warning("MCP: No API key configured, allowing access (development mode)")
            return await call_next(request)

        # Validate key
        if not api_key:
            logger.warning("MCP: Missing x-api-key header")
            return JSONResponse(
                status_code=401,
                content={"error": "Missing API key", "detail": "x-api-key header is required"},
            )

        if api_key != configured_key:
            logger.warning(f"MCP: Invalid API key: {api_key[:4]}...{api_key[-4:]}")
            return JSONResponse(status_code=401, content={"error": "Invalid API key"})

        logger.info(f"MCP: Authenticated request with key: {api_key[:4]}...{api_key[-4:]}")
        return await call_next(request)


def create_mcp_app():
    """
    Create the MCP ASGI app with HTTP transport and authentication.

    Returns:
        Starlette app with lifespan support
    """
    # Create MCP app with HTTP transport
    mcp_app = mcp.http_app(
        path="/mcp",  # This is the internal path within the mounted app
        transport="http",  # StreamableHTTP protocol
        middleware=[Middleware(MCPAuthMiddleware)],  # Apply authentication
    )

    logger.info("MCP server initialized with HTTP transport at /mcp")
    return mcp_app
