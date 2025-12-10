"""
MCP Server Configuration API.

Provides endpoints for:
- Starting/stopping the MCP HTTP server
- Installing MCP clients via npx install-mcp
- Getting MCP server status
"""

import asyncio
import logging
import os
import shutil
import sys
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.api.routes.setup import get_bind_host

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])

# MCP server state (in-process tracking)
_mcp_server_running = False
_mcp_server_port = 28882

# Gateway port for internal API calls (always use 127.0.0.1 for internal communication)
_gateway_port = os.getenv("OMNI_PORT", "8882")


class McpInstallRequest(BaseModel):
    """Request schema for MCP client installation."""

    client: str = Field(
        ...,
        description="MCP client to install for (claude-code, cursor, windsurf, vscode, gemini-cli, warp, codex)",
    )
    method: Literal["http", "stdio"] = Field(..., description="Connection method")


class McpInstallResponse(BaseModel):
    """Response schema for MCP installation."""

    success: bool
    message: str | None = None
    error: str | None = None
    command: str | None = None


class McpStatusResponse(BaseModel):
    """Response schema for MCP server status."""

    running: bool
    port: int | None = None


class McpServerResponse(BaseModel):
    """Response schema for MCP server start/stop."""

    success: bool
    message: str
    port: int | None = None


@router.get("/status", response_model=McpStatusResponse)
async def get_mcp_status() -> McpStatusResponse:
    """Get MCP server status."""
    return McpStatusResponse(
        running=_mcp_server_running,
        port=_mcp_server_port if _mcp_server_running else None,
    )


@router.post("/start", response_model=McpServerResponse)
async def start_mcp_server() -> McpServerResponse:
    """Start the MCP HTTP server."""
    global _mcp_server_running

    if _mcp_server_running:
        return McpServerResponse(
            success=True,
            message="MCP server already running",
            port=_mcp_server_port,
        )

    # The MCP server is managed by the gateway via subprocess
    # We signal the gateway to start it via the internal API
    # IMPORTANT: We determine bind_host HERE (Python has direct DB access)
    # to avoid deadlock - gateway used to call back to Python for this!
    bind_host = get_bind_host()
    logger.info(f"Starting MCP server with bind_host={bind_host}")

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:{_gateway_port}/api/internal/services/mcp/start",
                json={"bind_host": bind_host},  # Pass bind_host to avoid deadlock
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    _mcp_server_running = True
                    return McpServerResponse(
                        success=True,
                        message="MCP server started",
                        port=_mcp_server_port,
                    )
                else:
                    error_text = await response.text()
                    return McpServerResponse(
                        success=False,
                        message=f"Failed to start MCP server: {error_text}",
                    )
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        return McpServerResponse(
            success=False,
            message=f"Failed to start MCP server: {str(e)}",
        )


@router.post("/stop", response_model=McpServerResponse)
async def stop_mcp_server() -> McpServerResponse:
    """Stop the MCP HTTP server."""
    global _mcp_server_running

    if not _mcp_server_running:
        return McpServerResponse(
            success=True,
            message="MCP server not running",
        )

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:{_gateway_port}/api/internal/services/mcp/stop",
                json={},  # Must send JSON body for Fastify to accept the request
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    _mcp_server_running = False
                    return McpServerResponse(
                        success=True,
                        message="MCP server stopped",
                    )
                else:
                    error_text = await response.text()
                    return McpServerResponse(
                        success=False,
                        message=f"Failed to stop MCP server: {error_text}",
                    )
    except Exception as e:
        logger.error(f"Failed to stop MCP server: {e}")
        return McpServerResponse(
            success=False,
            message=f"Failed to stop MCP server: {str(e)}",
        )


@router.post("/install", response_model=McpInstallResponse)
async def install_mcp_client(request: McpInstallRequest) -> McpInstallResponse:
    """
    Install MCP configuration for a specific client.

    Runs `npx install-mcp` command to configure the client's MCP settings.
    """
    valid_clients = ["claude", "claude-code", "cursor", "windsurf", "vscode", "gemini-cli", "warp", "codex"]

    if request.client not in valid_clients:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid client. Must be one of: {', '.join(valid_clients)}",
        )

    # Check if npx is available
    npx_path = shutil.which("npx")
    if not npx_path:
        return McpInstallResponse(
            success=False,
            error="npx not found. Please install Node.js and npm.",
        )

    # Build the install command based on method
    if request.method == "http":
        cmd = [
            npx_path,
            "-y",  # Auto-confirm npx package installation
            "install-mcp",
            f"http://localhost:{_mcp_server_port}/mcp",
            "--client",
            request.client,
            "--oauth",
            "no",
            "--yes",  # Skip install-mcp confirmation prompt
        ]
    else:
        # STDIO mode - find genie-omni-mcp command
        # First check if it's in PATH
        mcp_cmd = shutil.which("genie-omni-mcp")
        if not mcp_cmd:
            # Try common venv locations
            venv_path = os.path.dirname(sys.executable)
            potential_path = os.path.join(venv_path, "genie-omni-mcp")
            if os.path.exists(potential_path):
                mcp_cmd = potential_path
            else:
                # Fallback to uvx command
                mcp_cmd = "uvx --from automagik-omni genie-omni-mcp"

        cmd = [
            npx_path,
            "-y",  # Auto-confirm npx package installation
            "install-mcp",
            mcp_cmd,
            "--client",
            request.client,
            "--yes",  # Skip install-mcp confirmation prompt
        ]

    command_str = " ".join(cmd)
    logger.info(f"Running MCP install command: {command_str}")

    try:
        # Run the command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "HOME": os.path.expanduser("~")},
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)

        stdout_str = stdout.decode() if stdout else ""
        stderr_str = stderr.decode() if stderr else ""

        if process.returncode == 0:
            return McpInstallResponse(
                success=True,
                message=f"MCP installed for {request.client}",
                command=command_str,
            )
        else:
            error_output = stderr_str or stdout_str or "Unknown error"
            logger.error(f"MCP install failed: {error_output}")
            return McpInstallResponse(
                success=False,
                error=error_output[:500],  # Truncate long errors
                command=command_str,
            )

    except asyncio.TimeoutError:
        return McpInstallResponse(
            success=False,
            error="Installation timed out after 60 seconds",
            command=command_str,
        )
    except Exception as e:
        logger.error(f"MCP install error: {e}")
        return McpInstallResponse(
            success=False,
            error=str(e),
            command=command_str,
        )
