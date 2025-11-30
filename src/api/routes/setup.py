"""
Setup API for first-run onboarding flow.

Provides unauthenticated endpoints for:
- Checking setup status (first run vs existing installation)
- Initializing database configuration
- Marking setup as completed

These endpoints are public (no API key required) to enable onboarding
before authentication is configured.
"""

import logging
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import SettingValueType
from src.services.settings_service import settings_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["Setup"])


# Pydantic schemas


class SetupStatusResponse(BaseModel):
    """Response schema for setup status check."""

    requires_setup: bool = Field(
        ..., description="Whether the application requires initial setup"
    )
    db_type: str | None = Field(
        None, description="Current database type if configured (sqlite/postgresql)"
    )


class DatabaseConfigRequest(BaseModel):
    """Request schema for database configuration during setup."""

    db_type: str = Field(..., description="Database type: sqlite or postgresql")
    postgres_url: str | None = Field(None, description="PostgreSQL connection URL if db_type=postgresql")
    redis_enabled: bool = Field(default=False, description="Enable Redis caching")
    redis_url: str | None = Field(None, description="Redis connection URL")
    redis_prefix_key: str | None = Field(None, description="Redis key prefix")
    redis_ttl: int | None = Field(None, description="Redis TTL in seconds")
    redis_save_instances: bool | None = Field(None, description="Save instances in Redis")


class SetupCompleteResponse(BaseModel):
    """Response schema for setup completion."""

    success: bool
    message: str


class GenerateApiKeyResponse(BaseModel):
    """Response schema for API key generation."""

    api_key: str = Field(..., description="Generated API key")
    message: str = Field(default="API key generated successfully")


# Endpoints


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(db: Session = Depends(get_db)):
    """
    Check if initial setup is required.

    This endpoint is unauthenticated to allow the UI to check setup status
    before the user has provided an API key.

    Returns:
        SetupStatusResponse: Setup status and current database type
    """
    try:
        # Get setup_completed flag from database
        setup_setting = settings_service.get_setting("setup_completed", db)

        if not setup_setting:
            # Flag doesn't exist - assume fresh install requires setup
            logger.info("setup_completed flag not found, assuming fresh install")
            return SetupStatusResponse(requires_setup=True, db_type=None)

        # Parse boolean value (stored as string "true"/"false")
        setup_complete = setup_setting.value.lower() in ("true", "1", "yes")

        # Get current database type
        db_type_setting = settings_service.get_setting("database_type", db)
        db_type = db_type_setting.value if db_type_setting else None

        logger.info(f"Setup status check: setup_complete={setup_complete}, db_type={db_type}")

        return SetupStatusResponse(
            requires_setup=not setup_complete,
            db_type=db_type
        )

    except Exception as e:
        logger.error(f"Failed to check setup status: {e}")
        # On error, assume setup is required to be safe
        return SetupStatusResponse(requires_setup=True, db_type=None)


@router.post("/initialize")
async def initialize_setup(
    config: DatabaseConfigRequest,
    db: Session = Depends(get_db)
):
    """
    Initialize database configuration during onboarding.

    This endpoint is unauthenticated to allow configuration before
    the user has provided an API key.

    Args:
        config: Database configuration settings

    Returns:
        Success confirmation
    """
    try:
        logger.info(f"Initializing setup with db_type={config.db_type}")

        # Validate db_type
        if config.db_type not in ("sqlite", "postgresql"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid db_type: {config.db_type}. Must be 'sqlite' or 'postgresql'"
            )

        # Validate PostgreSQL URL if db_type is postgresql
        if config.db_type == "postgresql" and not config.postgres_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="postgres_url is required when db_type is 'postgresql'"
            )

        # Helper function to create or update settings
        def _set_or_update(key: str, value: str, value_type: SettingValueType, category: str, description: str, is_secret: bool = False):
            existing = settings_service.get_setting(key, db)
            if existing:
                settings_service.update_setting(key, value, db)
                logger.info(f"Updated setting: {key}")
            else:
                settings_service.create_setting(
                    key=key,
                    value=value,
                    value_type=value_type,
                    db=db,
                    category=category,
                    description=description,
                    is_secret=is_secret,
                    created_by="setup_wizard"
                )
                logger.info(f"Created setting: {key}")

        # Save database configuration
        _set_or_update(
            key="database_type",
            value=config.db_type,
            value_type=SettingValueType.STRING,
            category="database",
            description="Database type (sqlite or postgresql)"
        )

        # Save PostgreSQL URL if provided
        if config.db_type == "postgresql" and config.postgres_url:
            _set_or_update(
                key="postgres_url",
                value=config.postgres_url,
                value_type=SettingValueType.SECRET,
                category="database",
                description="PostgreSQL connection URL",
                is_secret=True
            )

        # Save Redis configuration if enabled
        if config.redis_enabled:
            _set_or_update(
                key="cache_redis_enabled",
                value="true",
                value_type=SettingValueType.BOOLEAN,
                category="cache",
                description="Enable Redis caching"
            )

            if config.redis_url:
                _set_or_update(
                    key="cache_redis_uri",
                    value=config.redis_url,
                    value_type=SettingValueType.SECRET,
                    category="cache",
                    description="Redis connection URI",
                    is_secret=True
                )

            if config.redis_prefix_key:
                _set_or_update(
                    key="cache_redis_prefix_key",
                    value=config.redis_prefix_key,
                    value_type=SettingValueType.STRING,
                    category="cache",
                    description="Redis key prefix"
                )

            if config.redis_ttl is not None:
                _set_or_update(
                    key="cache_redis_ttl",
                    value=str(config.redis_ttl),
                    value_type=SettingValueType.INTEGER,
                    category="cache",
                    description="Redis TTL in seconds"
                )

            if config.redis_save_instances is not None:
                _set_or_update(
                    key="cache_redis_save_instances",
                    value="true" if config.redis_save_instances else "false",
                    value_type=SettingValueType.BOOLEAN,
                    category="cache",
                    description="Save instances in Redis"
                )
        else:
            # Disable Redis if not enabled
            _set_or_update(
                key="cache_redis_enabled",
                value="false",
                value_type=SettingValueType.BOOLEAN,
                category="cache",
                description="Enable Redis caching"
            )

        logger.info("Setup initialization completed successfully")

        return {
            "success": True,
            "message": f"Database configuration saved: {config.db_type}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Setup initialization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup initialization failed: {str(e)}"
        )


@router.post("/complete", response_model=SetupCompleteResponse)
async def complete_setup(db: Session = Depends(get_db)):
    """
    Mark initial setup as completed.

    This endpoint is unauthenticated to allow completion during onboarding
    after the user has configured the database but before full authentication.

    This is a one-time operation that prevents the setup wizard from showing
    again on subsequent app launches.

    Returns:
        SetupCompleteResponse: Success confirmation
    """
    try:
        # Check if setup is already complete
        setup_setting = settings_service.get_setting("setup_completed", db)

        if setup_setting:
            # Check current value
            is_already_complete = setup_setting.value.lower() in ("true", "1", "yes")

            if is_already_complete:
                logger.warning("Setup already marked as complete, ignoring duplicate request")
                return SetupCompleteResponse(
                    success=True,
                    message="Setup was already marked as complete"
                )

            # Update existing setting to True (boolean, not string)
            settings_service.update_setting("setup_completed", True, db)
            logger.info("Marked setup as completed (updated existing flag)")

        else:
            # Create the setting (shouldn't normally happen, but handle gracefully)
            settings_service.create_setting(
                key="setup_completed",
                value=True,  # Use boolean, not string
                value_type=SettingValueType.BOOLEAN,
                db=db,
                category="system",
                description="Initial setup wizard completed",
                is_secret=False,
                created_by="setup_wizard"
            )
            logger.info("Marked setup as completed (created new flag)")

        return SetupCompleteResponse(
            success=True,
            message="Setup marked as complete"
        )

    except Exception as e:
        logger.error(f"Failed to mark setup as complete: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete setup: {str(e)}"
        )


@router.get("/api-key", response_model=GenerateApiKeyResponse)
async def get_api_key(db: Session = Depends(get_db)):
    """
    Get the auto-generated API key during onboarding.

    This endpoint is unauthenticated and only works during first-run setup
    (before setup_completed is true). The API key is auto-generated during
    application startup and stored in the database.

    Returns:
        GenerateApiKeyResponse: The API key for authentication
    """
    try:
        # Check if setup is already complete - if so, don't expose the key
        setup_setting = settings_service.get_setting("setup_completed", db)
        if setup_setting and setup_setting.value.lower() in ("true", "1", "yes"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Setup already completed. API key cannot be retrieved after setup."
            )

        # Get the auto-generated API key from database
        api_key_setting = settings_service.get_setting("omni_api_key", db)

        if not api_key_setting:
            # This shouldn't happen as bootstrap creates it, but handle gracefully
            # Generate one now
            key_value = f"sk-omni-{secrets.token_urlsafe(32)}"
            settings_service.create_setting(
                key="omni_api_key",
                value=key_value,
                value_type=SettingValueType.SECRET,
                category="security",
                description="Omni API authentication key (generated during setup)",
                is_secret=True,
                is_required=True,
                db=db,
                created_by="setup_wizard"
            )
            logger.info(f"Generated new Omni API key during setup: {key_value[:12]}***")
            return GenerateApiKeyResponse(
                api_key=key_value,
                message="API key generated successfully. Save this key securely!"
            )

        return GenerateApiKeyResponse(
            api_key=api_key_setting.value,
            message="Your API key is ready. Save this key securely!"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve API key: {str(e)}"
        )
