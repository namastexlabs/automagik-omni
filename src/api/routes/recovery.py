"""
API key recovery endpoint for Automagik Omni.

Localhost-only access - no authentication required.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.db.database import get_db
from src.services.settings_service import settings_service

router = APIRouter(prefix="/recovery", tags=["recovery"])


class ApiKeyRecoveryResponse(BaseModel):
    """Response for API key recovery."""
    api_key: str
    message: str


@router.get("/api-key", response_model=ApiKeyRecoveryResponse)
async def recover_api_key(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Recover API key - localhost only, no authentication.

    Security rationale: If you have localhost access, you could
    access the database directly anyway. Adding password
    protection would create false security while making legitimate
    recovery harder.
    """
    # Check if request is from localhost
    client_host = request.client.host if request.client else None

    # Allow localhost addresses (IPv4 and IPv6)
    localhost_addresses = ("127.0.0.1", "::1", "localhost")

    if client_host not in localhost_addresses:
        raise HTTPException(
            status_code=403,
            detail="API key recovery is only available from localhost. "
                   "Access this endpoint from the same machine running Omni."
        )

    # Get the API key from database
    setting = settings_service.get_setting("omni_api_key", db)

    if not setting or not setting.value:
        raise HTTPException(
            status_code=404,
            detail="No API key found. Run 'omni start' to auto-generate one."
        )

    return ApiKeyRecoveryResponse(
        api_key=setting.value,
        message="Store this key securely. This endpoint is only accessible from localhost."
    )
