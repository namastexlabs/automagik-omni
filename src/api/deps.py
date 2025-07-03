"""
FastAPI dependency injection for database and services.
"""

import logging
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import InstanceConfig
from src.config import config

# Security scheme for API key authentication
security = HTTPBearer()

# Module-level logger
logger = logging.getLogger(__name__)


def get_database() -> Generator[Session, None, None]:
    """Database dependency."""
    yield from get_db()


def get_instance_by_name(
    instance_name: str, db: Session = Depends(get_database)
) -> InstanceConfig:
    """
    Get instance configuration by name.

    Args:
        instance_name: Name of the instance
        db: Database session

    Returns:
        InstanceConfig for the instance

    Raises:
        HTTPException: If instance not found
    """
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )
    return instance


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify API key authentication.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        str: The verified API key

    Raises:
        HTTPException: If API key is invalid or missing

    Example:
        @app.get("/protected/")
        def protected_endpoint(api_key: str = Depends(verify_api_key)):
            return {"message": "Access granted"}
    """

    if not config.api.api_key:
        # If no API key is configured, allow access (development mode)
        logger.info("No API key configured, allowing access (development mode)")
        return "development"

    # Mask API keys for security (show only first 4 and last 4 characters)
    def mask_key(key: str) -> str:
        if len(key) <= 8:
            return "*" * len(key)
        return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"

    logger.debug(f"Expected API key: [{mask_key(config.api.api_key)}]")
    logger.debug(f"Received credentials: [{mask_key(credentials.credentials)}]")

    if credentials.credentials != config.api.api_key:
        logger.warning(
            f"API key mismatch. Expected: [{mask_key(config.api.api_key)}], Got: [{mask_key(credentials.credentials)}]"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("API key verified successfully")
    return credentials.credentials
