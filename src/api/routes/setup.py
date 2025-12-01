"""
Setup API for first-run onboarding flow.

Provides unauthenticated endpoints for:
- Checking setup status (first run vs existing installation)
- Initializing database configuration
- Configuring communication channels (WhatsApp, Discord)
- Marking setup as completed

These endpoints are public (no API key required) to enable onboarding
before authentication is configured.
"""

import logging
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import SettingValueType, InstanceConfig
from src.services.settings_service import settings_service
from src.utils.instance_utils import normalize_instance_name

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


# =============================================================================
# Channel Configuration Endpoints
# =============================================================================


class ChannelStatus(BaseModel):
    """Status of a single channel."""
    enabled: bool = Field(..., description="Whether the channel is enabled")
    configured: bool = Field(..., description="Whether the channel is fully configured")
    status: str = Field(..., description="Channel status: ready, needs_config, unavailable, error")
    message: Optional[str] = Field(None, description="Additional status message")


class ChannelStatusResponse(BaseModel):
    """Response schema for channel status check."""
    whatsapp: ChannelStatus
    discord: ChannelStatus


class ChannelConfigRequest(BaseModel):
    """Request schema for channel configuration during setup."""
    whatsapp_enabled: bool = Field(default=True, description="Enable WhatsApp channel")
    discord_enabled: bool = Field(default=False, description="Enable Discord channel")
    discord_instance_name: Optional[str] = Field(None, description="Discord instance name")
    discord_bot_token: Optional[str] = Field(None, description="Discord bot token")
    discord_client_id: Optional[str] = Field(None, description="Discord application client ID")


class ChannelConfigResponse(BaseModel):
    """Response schema for channel configuration."""
    success: bool
    message: str
    whatsapp_status: str
    discord_status: str


class DiscordValidationRequest(BaseModel):
    """Request schema for Discord token validation."""
    bot_token: str = Field(..., description="Discord bot token to validate")
    client_id: str = Field(..., description="Discord application client ID")


@router.get("/channels/status", response_model=ChannelStatusResponse)
async def get_channels_status(db: Session = Depends(get_db)):
    """
    Get the status of available communication channels.

    This endpoint is unauthenticated to allow the wizard to check
    channel availability during onboarding.

    Returns:
        ChannelStatusResponse: Status of WhatsApp and Discord channels
    """
    try:
        # Check WhatsApp status (via Evolution API)
        whatsapp_status = await _check_whatsapp_status(db)

        # Check Discord status
        discord_status = await _check_discord_status(db)

        return ChannelStatusResponse(
            whatsapp=whatsapp_status,
            discord=discord_status
        )

    except Exception as e:
        logger.error(f"Failed to check channel status: {e}")
        # Return degraded status on error
        return ChannelStatusResponse(
            whatsapp=ChannelStatus(
                enabled=False,
                configured=False,
                status="error",
                message=f"Failed to check status: {str(e)}"
            ),
            discord=ChannelStatus(
                enabled=False,
                configured=False,
                status="error",
                message=f"Failed to check status: {str(e)}"
            )
        )


async def _check_whatsapp_status(db: Session) -> ChannelStatus:
    """Check WhatsApp (Evolution API) availability."""
    try:
        # Get Evolution API URL
        evolution_url = settings_service.get_setting_value(
            "evolution_api_url", db, default="http://localhost:18082"
        )

        # Get unified API key
        api_key = settings_service.get_setting_value("omni_api_key", db, default=None)

        if not api_key:
            return ChannelStatus(
                enabled=True,  # WhatsApp is enabled by default
                configured=False,
                status="needs_config",
                message="API key not generated yet"
            )

        # Try to connect to Evolution API
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(
                    f"{evolution_url}/instance/fetchInstances",
                    headers={"apikey": api_key}
                )
                if response.status_code == 200:
                    return ChannelStatus(
                        enabled=True,
                        configured=True,
                        status="ready",
                        message="WhatsApp Web API connected"
                    )
                elif response.status_code == 401:
                    return ChannelStatus(
                        enabled=True,
                        configured=False,
                        status="needs_config",
                        message="API key mismatch - configure WhatsApp Web with unified key"
                    )
                else:
                    return ChannelStatus(
                        enabled=True,
                        configured=False,
                        status="error",
                        message=f"WhatsApp Web API returned {response.status_code}"
                    )
            except httpx.ConnectError:
                return ChannelStatus(
                    enabled=True,
                    configured=False,
                    status="unavailable",
                    message="WhatsApp Web API not reachable - is it running?"
                )

    except Exception as e:
        logger.warning(f"WhatsApp status check failed: {e}")
        return ChannelStatus(
            enabled=True,
            configured=False,
            status="error",
            message=str(e)
        )


async def _check_discord_status(db: Session) -> ChannelStatus:
    """Check Discord channel configuration."""
    try:
        # Check if channel is enabled
        enabled_setting = settings_service.get_setting("channel_discord_enabled", db)
        is_enabled = enabled_setting and enabled_setting.value.lower() in ("true", "1", "yes")

        # Check if any Discord instance exists
        discord_instances = db.query(InstanceConfig).filter(
            InstanceConfig.channel_type == "discord"
        ).count()

        if discord_instances > 0:
            return ChannelStatus(
                enabled=True,
                configured=True,
                status="ready",
                message=f"{discord_instances} Discord instance(s) configured"
            )

        return ChannelStatus(
            enabled=is_enabled,
            configured=False,
            status="needs_config",
            message="No Discord instances configured"
        )

    except Exception as e:
        logger.warning(f"Discord status check failed: {e}")
        return ChannelStatus(
            enabled=False,
            configured=False,
            status="error",
            message=str(e)
        )


@router.post("/channels/configure", response_model=ChannelConfigResponse)
async def configure_channels(
    config: ChannelConfigRequest,
    db: Session = Depends(get_db)
):
    """
    Configure communication channels during onboarding.

    This endpoint is unauthenticated to allow configuration during setup.

    - WhatsApp: Auto-configured using unified API key
    - Discord: Requires bot token and client ID from Discord Developer Portal

    Args:
        config: Channel configuration settings

    Returns:
        ChannelConfigResponse: Configuration result
    """
    try:
        whatsapp_status = "skipped"
        discord_status = "skipped"

        # Helper function to create or update settings
        def _set_or_update(key: str, value: str, value_type: SettingValueType, category: str, description: str, is_secret: bool = False):
            existing = settings_service.get_setting(key, db)
            if existing:
                settings_service.update_setting(key, value, db)
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

        # Configure WhatsApp
        if config.whatsapp_enabled:
            _set_or_update(
                key="channel_whatsapp_enabled",
                value="true",
                value_type=SettingValueType.BOOLEAN,
                category="channels",
                description="WhatsApp channel enabled"
            )
            whatsapp_status = "enabled"
            logger.info("WhatsApp channel enabled")
        else:
            _set_or_update(
                key="channel_whatsapp_enabled",
                value="false",
                value_type=SettingValueType.BOOLEAN,
                category="channels",
                description="WhatsApp channel enabled"
            )
            whatsapp_status = "disabled"

        # Configure Discord
        if config.discord_enabled:
            # Validate Discord credentials
            if not config.discord_bot_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="discord_bot_token is required when discord_enabled is true"
                )
            if not config.discord_client_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="discord_client_id is required when discord_enabled is true"
                )
            if not config.discord_instance_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="discord_instance_name is required when discord_enabled is true"
                )

            # Normalize instance name
            instance_name = normalize_instance_name(config.discord_instance_name)

            # Validate Discord token format (basic check)
            if not config.discord_bot_token.startswith(("MT", "Nj", "OD", "Mz", "NT", "OT")):
                logger.warning("Discord bot token doesn't match expected format, but proceeding")

            # Enable Discord channel
            _set_or_update(
                key="channel_discord_enabled",
                value="true",
                value_type=SettingValueType.BOOLEAN,
                category="channels",
                description="Discord channel enabled"
            )

            # Check if instance already exists
            existing_instance = db.query(InstanceConfig).filter(
                InstanceConfig.name == instance_name
            ).first()

            if existing_instance:
                # Update existing instance
                existing_instance.discord_bot_token = config.discord_bot_token
                existing_instance.discord_client_id = config.discord_client_id
                db.commit()
                discord_status = f"updated:{instance_name}"
                logger.info(f"Updated Discord instance: {instance_name}")
            else:
                # Create new Discord instance
                new_instance = InstanceConfig(
                    name=instance_name,
                    channel_type="discord",
                    discord_bot_token=config.discord_bot_token,
                    discord_client_id=config.discord_client_id,
                    default_agent="default-agent",
                    agent_api_url="http://localhost:8000",
                    agent_api_key="default-key",
                    is_active=False,  # Will be activated when bot connects
                    is_default=False,
                )
                db.add(new_instance)
                db.commit()
                discord_status = f"created:{instance_name}"
                logger.info(f"Created Discord instance: {instance_name}")

        else:
            _set_or_update(
                key="channel_discord_enabled",
                value="false",
                value_type=SettingValueType.BOOLEAN,
                category="channels",
                description="Discord channel enabled"
            )
            discord_status = "disabled"

        return ChannelConfigResponse(
            success=True,
            message="Channel configuration saved",
            whatsapp_status=whatsapp_status,
            discord_status=discord_status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Channel configuration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Channel configuration failed: {str(e)}"
        )


@router.post("/channels/validate-discord")
async def validate_discord_token(request: DiscordValidationRequest):
    """
    Validate Discord bot credentials.

    Tests the provided bot token by making an API call to Discord.

    Args:
        request: DiscordValidationRequest with bot_token and client_id

    Returns:
        Validation result with bot information if successful
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get bot user info from Discord API
            response = await client.get(
                "https://discord.com/api/v10/users/@me",
                headers={"Authorization": f"Bot {request.bot_token}"}
            )

            if response.status_code == 200:
                bot_info = response.json()
                return {
                    "valid": True,
                    "bot_name": bot_info.get("username"),
                    "bot_id": bot_info.get("id"),
                    "message": f"Bot '{bot_info.get('username')}' validated successfully"
                }
            elif response.status_code == 401:
                return {
                    "valid": False,
                    "message": "Invalid bot token"
                }
            else:
                return {
                    "valid": False,
                    "message": f"Discord API returned {response.status_code}"
                }

    except httpx.ConnectError:
        return {
            "valid": False,
            "message": "Could not connect to Discord API"
        }
    except Exception as e:
        logger.error(f"Discord validation failed: {e}")
        return {
            "valid": False,
            "message": f"Validation error: {str(e)}"
        }
