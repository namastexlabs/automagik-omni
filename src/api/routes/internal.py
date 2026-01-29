"""
Internal API endpoints for service-to-service communication.

Localhost-only access - no authentication required.
These endpoints allow internal services (like Evolution) to fetch
configuration from Omni without needing the API key.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.db.database import get_db
from src.services.settings_service import settings_service

router = APIRouter(prefix="/_internal", tags=["internal"])


class EvolutionKeyResponse(BaseModel):
    """Response for Evolution API key retrieval."""

    key: str
    message: str


def _verify_localhost(request: Request) -> None:
    """
    Verify the request is from localhost.

    Raises:
        HTTPException: If request is not from localhost
    """
    client_host = request.client.host if request.client else None

    # Allow localhost addresses (IPv4 and IPv6)
    localhost_addresses = ("127.0.0.1", "::1", "localhost")

    if client_host not in localhost_addresses:
        raise HTTPException(status_code=403, detail="Internal endpoints are only accessible from localhost.")


@router.get("/evolution-key", response_model=EvolutionKeyResponse)
async def get_evolution_key(request: Request, db: Session = Depends(get_db)):
    """
    Get the unified API key for Evolution server configuration.

    This endpoint allows Evolution to fetch the API key from Omni's database
    on startup, enabling unified key architecture without manual configuration.

    **Localhost only** - No authentication required.

    Usage:
    - Evolution startup script calls this endpoint
    - Returns the omni_api_key to use as AUTHENTICATION_API_KEY
    - Eliminates need for separate Evolution API key configuration

    Security rationale: If you have localhost access, you could read the
    database file directly. This endpoint just makes it easier for Evolution
    to fetch the key programmatically on startup.
    """
    _verify_localhost(request)

    # Get the unified API key (omni_api_key)
    setting = settings_service.get_setting("omni_api_key", db)

    if not setting or not setting.value:
        raise HTTPException(
            status_code=404, detail="No API key found. Omni needs to be started first to generate the key."
        )

    return EvolutionKeyResponse(
        key=setting.value, message="Use this key as AUTHENTICATION_API_KEY for the WhatsApp Web server."
    )


class SubprocessConfigResponse(BaseModel):
    """Configuration for subprocess startup (Evolution, etc.)."""

    database_connection_uri: str | None = None
    database_provider: str = "postgresql"
    authentication_api_key: str | None = None


@router.get("/subprocess-config", response_model=SubprocessConfigResponse)
async def get_subprocess_config(request: Request, db: Session = Depends(get_db)):
    """
    Get configuration for subprocess startup (Evolution, Discord, etc.).

    Returns environment variables needed by subprocesses:
    - DATABASE_CONNECTION_URI: PostgreSQL connection string
    - DATABASE_PROVIDER: "postgresql"
    - AUTHENTICATION_API_KEY: Unified API key

    **Localhost only** - No authentication required.

    Called by gateway/process.ts before spawning Evolution.
    """
    _verify_localhost(request)

    # Get database URL from env var (set by gateway when starting Python)
    # The gateway passes AUTOMAGIK_OMNI_DATABASE_URL with the dynamic postgres port
    database_url = os.getenv("AUTOMAGIK_OMNI_DATABASE_URL")

    # Evolution shares the same database as Omni - table prefixes handle separation
    # Python tables use 'omni_' prefix, Evolution tables use 'evo_' prefix
    # PostgreSQL only - no SQLite support
    database_uri = database_url if database_url else None
    db_type = "postgresql"

    # Get API key
    api_key = settings_service.get_setting_value("omni_api_key", db)

    return SubprocessConfigResponse(
        database_connection_uri=database_uri,
        database_provider=db_type,
        authentication_api_key=api_key,
    )


@router.get("/health")
async def internal_health(request: Request):
    """
    Internal health check endpoint.

    Localhost only - useful for service orchestration.
    """
    _verify_localhost(request)

    return {"status": "healthy", "service": "omni-internal"}


class ChannelStartupInfo(BaseModel):
    """Information about which channels should be auto-started."""

    evolution_needed: bool = False
    evolution_reason: str | None = None
    discord_needed: bool = False
    discord_reason: str | None = None
    whatsapp_instances: list[str] = []
    discord_instances: list[str] = []


@router.get("/channel-startup-info", response_model=ChannelStartupInfo)
async def get_channel_startup_info(request: Request, db: Session = Depends(get_db)):
    """
    Get information about which channels need to be auto-started.

    Checks database for:
    - WhatsApp instances with connectionStatus='open' in evo_Instance
    - Discord instances that are enabled in omni_instance_configs

    **Localhost only** - No authentication required.

    Called by gateway at startup to decide which channels to start.
    """
    from sqlalchemy import text

    _verify_localhost(request)

    result = ChannelStartupInfo()

    # Check for WhatsApp instances that exist (were previously configured)
    # We check for ANY evo_Instance, not just connected ones, because:
    # - At startup, Evolution isn't running yet, so status won't be 'open'
    # - If user had Evolution running before restart, we want to restart it
    try:
        whatsapp_query = text("""
            SELECT name, "connectionStatus" FROM "evo_Instance"
        """)
        whatsapp_rows = db.execute(whatsapp_query).fetchall()
        result.whatsapp_instances = [row[0] for row in whatsapp_rows]

        if result.whatsapp_instances:
            result.evolution_needed = True
            connected_count = sum(1 for row in whatsapp_rows if row[1] == "open")
            if connected_count > 0:
                result.evolution_reason = f"Found {len(result.whatsapp_instances)} WhatsApp instance(s), {connected_count} connected: {', '.join(result.whatsapp_instances)}"
            else:
                result.evolution_reason = f"Found {len(result.whatsapp_instances)} WhatsApp instance(s) (will reconnect): {', '.join(result.whatsapp_instances)}"
    except Exception:
        # evo_Instance table might not exist yet
        pass

    # Check for Discord instances that are active and have a bot token
    # This matches the logic in discord_service_manager.py
    try:
        discord_query = text("""
            SELECT name FROM omni_instance_configs
            WHERE channel_type = 'discord'
              AND is_active = true
              AND discord_bot_token IS NOT NULL
        """)
        discord_rows = db.execute(discord_query).fetchall()
        result.discord_instances = [row[0] for row in discord_rows]

        if result.discord_instances:
            result.discord_needed = True
            result.discord_reason = f"Found {len(result.discord_instances)} active Discord instance(s): {', '.join(result.discord_instances)}"
    except Exception:
        # Table might not exist or column might not be there
        pass

    return result
