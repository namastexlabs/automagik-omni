#!/usr/bin/env python3
"""
Standalone FastMCP server on dedicated port.

This server runs independently from the main FastAPI app,
eliminating the double proxy layer:
  Before: Gateway → FastAPI → FastMCP (2 hops)
  After:  Gateway → FastMCP (1 hop, -15ms per request)
"""

import os
import sys
import logging
import uvicorn
from src.mcp_tools.genie_omni.server import mcp
from src.logger import setup_logging

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# MCP server configuration
MCP_PORT = int(os.environ.get("MCP_PORT", "18880"))
MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")


def main():
    """Start the standalone MCP server."""
    logger.info(f"Starting standalone MCP server on {MCP_HOST}:{MCP_PORT}")
    logger.info("MCP server will handle all /mcp requests directly")
    logger.info("This eliminates the FastAPI proxy layer (-15ms per request)")

    # Create MCP HTTP app (served at root "/" since we're standalone)
    mcp_app = mcp.http_app(
        path="/",  # Root path for standalone server
        transport="http",  # StreamableHTTP protocol
    )

    # Run uvicorn server
    uvicorn.run(
        mcp_app,
        host=MCP_HOST,
        port=MCP_PORT,
        log_level="info",
        access_log=False,  # Reduce noise, MCP has its own logging
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"MCP server failed to start: {e}", exc_info=True)
        sys.exit(1)
