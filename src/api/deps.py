"""
FastAPI dependency injection for database and services.
"""

import logging
import os
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import InstanceConfig
from src.config import config

# Cache for valid API keys from DB to avoid repeated queries
_cached_db_api_key: str | None = None
_cache_initialized: bool = False

# Security scheme for API key authentication
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

# Module-level logger
logger = logging.getLogger(__name__)


def _create_get_database() -> Generator[Session, None, None]:
    yield from get_db()


# Preserve dependency identity across module reloads so FastAPI overrides remain valid
get_database = globals().get("_shared_get_database")
if get_database is None:

    def _shared_get_database() -> Generator[Session, None, None]:
        yield from get_db()

    get_database = _shared_get_database
    globals()["_shared_get_database"] = get_database


def get_instance_by_name(instance_name: str, db: Session = Depends(get_database)) -> InstanceConfig:
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


def _get_valid_api_keys() -> list[str]:
    """
    Get all valid API keys from env var and database.

    Returns list of valid API keys, checking:
    1. AUTOMAGIK_OMNI_API_KEY env var (if not placeholder)
    2. omni_api_key from database settings

    Results are cached after first DB query.
    """
    global _cached_db_api_key, _cache_initialized

    keys = []

    # Check env var
    env_key = config.api.api_key
    if env_key:
        keys.append(env_key)

    # Check DB for generated key (with caching)
    if not _cache_initialized:
        try:
            from src.services.settings_service import settings_service

            db_gen = get_db()
            db = next(db_gen)
            setting = settings_service.get_setting("omni_api_key", db)
            if setting and setting.value:
                _cached_db_api_key = setting.value
            db.close()
        except Exception as e:
            logger.debug(f"Could not fetch API key from DB: {e}")
        _cache_initialized = True

    if _cached_db_api_key:
        keys.append(_cached_db_api_key)

    return keys


def _create_verify_api_key():
    def _verify(api_key: Optional[str] = Depends(api_key_header)):
        """
        Verify API key authentication from x-api-key header.

        Checks API key against:
        1. AUTOMAGIK_OMNI_API_KEY env var (if not placeholder)
        2. omni_api_key from database settings (auto-generated during setup)

        Args:
            api_key: API key from x-api-key header via APIKeyHeader security scheme

        Returns:
            str: The verified API key

        Raises:
            HTTPException: If API key is invalid or missing

        Example:
            @app.get("/protected/")
            def protected_endpoint(api_key: str = Depends(verify_api_key)):
                return {"message": "Access granted"}
        """

        # In test environment, bypass API key validation entirely for predictable test behavior
        environment = os.getenv("ENVIRONMENT", "").lower()
        if environment == "test":
            logger.debug("Test environment detected; skipping API key verification")
            return "test-environment"

        # Get all valid API keys (env var + DB)
        valid_keys = _get_valid_api_keys()

        if not valid_keys:
            # No valid keys configured - allow access (development mode)
            logger.info("No API key configured, allowing access (development mode)")
            return "development"

        # Check if API key is provided
        if not api_key:
            logger.warning("No API key provided in x-api-key header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Mask API keys for security (show only first 4 and last 4 characters)
        def mask_key(key: str) -> str:
            if len(key) <= 8:
                return "*" * len(key)
            return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"

        logger.debug(f"Received API key: [{mask_key(api_key)}]")

        if api_key not in valid_keys:
            logger.warning(f"API key mismatch. Got: [{mask_key(api_key)}]")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        logger.info("API key verified successfully")
        return api_key

    return _verify


verify_api_key = globals().get("_shared_verify_api_key")
if verify_api_key is None:
    verify_api_key = _create_verify_api_key()
    globals()["_shared_verify_api_key"] = verify_api_key

# Alias for backward compatibility (sync.py uses require_api_key)
require_api_key = verify_api_key
