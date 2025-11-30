"""
Internal API endpoints for service-to-service communication.

Localhost-only access - no authentication required.
These endpoints allow internal services (like Evolution) to fetch
configuration from Omni without needing the API key.
"""

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
        raise HTTPException(
            status_code=403,
            detail="Internal endpoints are only accessible from localhost."
        )


@router.get("/evolution-key", response_model=EvolutionKeyResponse)
async def get_evolution_key(
    request: Request,
    db: Session = Depends(get_db)
):
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
            status_code=404,
            detail="No API key found. Omni needs to be started first to generate the key."
        )

    return EvolutionKeyResponse(
        key=setting.value,
        message="Use this key as AUTHENTICATION_API_KEY for Evolution server."
    )


@router.get("/health")
async def internal_health(request: Request):
    """
    Internal health check endpoint.

    Localhost only - useful for service orchestration.
    """
    _verify_localhost(request)

    return {
        "status": "healthy",
        "service": "omni-internal"
    }
