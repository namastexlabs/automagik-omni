"""
CLI entry point for genie-omni MCP server.
"""

from .server import mcp

if __name__ == "__main__":
    # Run the FastMCP server
    mcp.run()
