"""
CRUD API for managing instance configurations.
"""

import logging
import os
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict, model_validator, HttpUrl, AnyUrl
from typing import Any

from src.api.deps import get_database, verify_api_key
from src.db.models import InstanceConfig
from src.channels.base import ChannelHandlerFactory, QRCodeResponse, ConnectionStatus
from src.channels.whatsapp.channel_handler import ValidationError
from src.ip_utils import ensure_ipv4_in_config
from src.utils.instance_utils import normalize_instance_name

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/instances/supported-channels",
    summary="Get Supported Channels",
    description="Retrieve list of all supported communication channels",
)
async def get_supported_channels(api_key: str = Depends(verify_api_key)):
    """
    Get list of supported channel types.

    Returns available channels (WhatsApp, Discord, Slack) with configuration requirements.
    """
    try:
        supported_channels = ChannelHandlerFactory.get_supported_channels()
        return {
            "supported_channels": supported_channels,
            "total_channels": len(supported_channels),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supported channels: {str(e)}",
        )


# Pydantic models for API
class InstanceConfigCreate(BaseModel):
    """Schema for creating instance configuration."""

    name: str
    channel_type: str = Field(default="whatsapp", description="Channel type: whatsapp, slack, discord")

    # WhatsApp Web API configuration (accepts both new and legacy field names)
    whatsapp_web_url: Optional[HttpUrl] = Field(None, description="WhatsApp Web API URL")
    whatsapp_web_key: Optional[str] = Field(None, description="WhatsApp Web API key")
    whatsapp_instance: Optional[str] = Field(None, description="WhatsApp instance name")
    session_id_prefix: Optional[str] = Field(None, description="Session ID prefix (WhatsApp)")
    webhook_base64: Optional[bool] = Field(None, description="Send base64 encoded data in webhooks (WhatsApp)")

    @model_validator(mode='before')
    @classmethod
    def migrate_legacy_evolution_fields(cls, data: Any) -> Any:
        """Accept legacy evolution_* field names and map to whatsapp_web_*."""
        if isinstance(data, dict):
            # Map legacy field names to new names
            if 'evolution_url' in data and 'whatsapp_web_url' not in data:
                data['whatsapp_web_url'] = data.pop('evolution_url')
            if 'evolution_key' in data and 'whatsapp_web_key' not in data:
                data['whatsapp_web_key'] = data.pop('evolution_key')
        return data

    # Discord-specific fields
    discord_bot_token: Optional[str] = Field(None, description="Discord bot token (Discord)")
    discord_client_id: Optional[str] = Field(None, description="Discord client ID (Discord)")
    discord_guild_id: Optional[str] = Field(None, description="Discord guild ID (Discord)")
    discord_default_channel_id: Optional[str] = Field(None, description="Discord default channel ID (Discord)")
    discord_voice_enabled: Optional[bool] = Field(None, description="Enable voice features (Discord)")
    discord_slash_commands_enabled: Optional[bool] = Field(None, description="Enable slash commands (Discord)")

    # WhatsApp-specific creation parameters (not stored in DB)
    phone_number: Optional[str] = Field(None, description="Phone number for WhatsApp")
    auto_qr: Optional[bool] = Field(True, description="Auto-generate QR code (WhatsApp)")
    integration: Optional[str] = Field("WHATSAPP-BAILEYS", description="WhatsApp integration type")

    # Common agent configuration (optional for wizard flow - can be set later)
    agent_api_url: Optional[HttpUrl] = None
    agent_api_key: Optional[str] = None
    default_agent: Optional[str] = None
    agent_timeout: int = 60
    is_default: bool = False

    # Automagik instance identification (for UI display)
    automagik_instance_id: Optional[str] = Field(None, description="Automagik instance ID")
    automagik_instance_name: Optional[str] = Field(None, description="Automagik instance name")

    # Unified agent fields (optional for creation, use defaults if not provided)
    agent_instance_type: Optional[str] = Field(
        default="automagik", description="Agent instance type: automagik or hive"
    )
    agent_id: Optional[str] = Field(default=None, description="Agent or team ID")
    agent_type: Optional[str] = Field(default="agent", description="Agent type: agent or team")
    agent_stream_mode: Optional[bool] = Field(default=False, description="Enable streaming mode")

    # Message splitting control
    enable_auto_split: Optional[bool] = Field(
        default=True,
        description="Enable automatic message splitting on \\n\\n (WhatsApp: full control, Discord: preference only)",
    )

    @model_validator(mode="after")
    def validate_channel_requirements(self) -> "InstanceConfigCreate":
        """Enforce required fields and URL validation per channel."""
        if self.channel_type == "whatsapp":
            if not self.whatsapp_web_url:
                raise ValueError("whatsapp_web_url is required for WhatsApp channel")
            if not self.whatsapp_web_key:
                raise ValueError("whatsapp_web_key is required for WhatsApp channel")
            if not self.whatsapp_instance:
                raise ValueError("whatsapp_instance is required for WhatsApp channel")
        return self


class InstanceConfigUpdate(BaseModel):
    """Schema for updating instance configuration."""

    channel_type: Optional[str] = None

    # WhatsApp Web API configuration (accepts both new and legacy field names)
    whatsapp_web_url: Optional[HttpUrl] = None
    whatsapp_web_key: Optional[str] = None
    whatsapp_instance: Optional[str] = None
    session_id_prefix: Optional[str] = None
    webhook_base64: Optional[bool] = None

    @model_validator(mode='before')
    @classmethod
    def migrate_legacy_evolution_fields(cls, data: Any) -> Any:
        """Accept legacy evolution_* field names and map to whatsapp_web_*."""
        if isinstance(data, dict):
            if 'evolution_url' in data and 'whatsapp_web_url' not in data:
                data['whatsapp_web_url'] = data.pop('evolution_url')
            if 'evolution_key' in data and 'whatsapp_web_key' not in data:
                data['whatsapp_web_key'] = data.pop('evolution_key')
        return data

    # Discord-specific fields
    discord_bot_token: Optional[str] = None
    discord_client_id: Optional[str] = None
    discord_guild_id: Optional[str] = None
    discord_default_channel_id: Optional[str] = None
    discord_voice_enabled: Optional[bool] = None
    discord_slash_commands_enabled: Optional[bool] = None

    agent_api_url: Optional[HttpUrl] = None
    agent_api_key: Optional[str] = None
    default_agent: Optional[str] = None
    agent_timeout: Optional[int] = None
    is_default: Optional[bool] = None
    automagik_instance_id: Optional[str] = None
    automagik_instance_name: Optional[str] = None

    # Unified agent fields
    agent_instance_type: Optional[str] = None
    agent_id: Optional[str] = None
    agent_type: Optional[str] = None
    agent_stream_mode: Optional[bool] = None

    # Message splitting control
    enable_auto_split: Optional[bool] = None


class WhatsAppWebStatusInfo(BaseModel):
    """Schema for WhatsApp Web API connection status information."""

    state: Optional[str] = None
    owner_jid: Optional[str] = None
    profile_name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    last_updated: Optional[datetime] = None
    error: Optional[str] = None


# Backward compatibility alias
EvolutionStatusInfo = WhatsAppWebStatusInfo


class InstanceConfigResponse(BaseModel):
    """Schema for instance configuration response."""

    id: int
    name: str
    channel_type: str

    # WhatsApp Web API configuration (use new names in responses)
    whatsapp_web_url: Optional[str] = None
    whatsapp_web_key: Optional[str] = None
    whatsapp_instance: Optional[str] = None
    session_id_prefix: Optional[str] = None
    webhook_base64: Optional[bool] = None

    # Discord-specific fields - SECURITY FIX: Don't expose actual token
    has_discord_bot_token: Optional[bool] = None  # Security: Don't expose actual token
    discord_client_id: Optional[str] = None
    discord_guild_id: Optional[str] = None
    discord_default_channel_id: Optional[str] = None
    discord_voice_enabled: Optional[bool] = None
    discord_slash_commands_enabled: Optional[bool] = None

    agent_api_url: Optional[str] = None
    agent_api_key: Optional[str] = None
    default_agent: Optional[str] = None
    agent_timeout: int = 60
    is_default: bool = False
    is_active: bool = False
    connection_status: Optional[str] = None  # Live status: "connected"|"disconnected"|"connecting"|"error"|"unknown"
    automagik_instance_id: Optional[str] = None
    automagik_instance_name: Optional[str] = None

    # Profile information from WhatsApp Web API
    profile_name: Optional[str] = None
    profile_pic_url: Optional[str] = None
    owner_jid: Optional[str] = None

    created_at: datetime
    updated_at: datetime
    whatsapp_web_status: Optional[WhatsAppWebStatusInfo] = None

    # Unified agent fields
    agent_instance_type: Optional[str] = None
    agent_id: Optional[str] = None
    agent_type: Optional[str] = None
    agent_stream_mode: Optional[bool] = None

    # Message splitting control
    enable_auto_split: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "/instances",
    response_model=InstanceConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_instance(
    instance_data: InstanceConfigCreate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Create a new instance configuration with channel-specific setup."""

    # Log incoming request payload (with sensitive data masked)
    logger.info(f"Creating instance: {instance_data.name}")
    payload_data = instance_data.model_dump()
    # Mask sensitive fields for logging - SECURITY FIX: Added Discord token masking
    if "whatsapp_web_key" in payload_data and payload_data["whatsapp_web_key"]:
        payload_data["whatsapp_web_key"] = (
            f"{payload_data['whatsapp_web_key'][:4]}***{payload_data['whatsapp_web_key'][-4:]}"
            if len(payload_data["whatsapp_web_key"]) > 8
            else "***"
        )
    if "agent_api_key" in payload_data and payload_data["agent_api_key"]:
        payload_data["agent_api_key"] = (
            f"{payload_data['agent_api_key'][:4]}***{payload_data['agent_api_key'][-4:]}"
            if len(payload_data["agent_api_key"]) > 8
            else "***"
        )
    if "discord_bot_token" in payload_data and payload_data["discord_bot_token"]:
        payload_data["discord_bot_token"] = "***"
    logger.debug(f"Instance creation payload: {payload_data}")

    # Validate input data for common issues
    if instance_data.name.lower() in ["string", "null", "undefined", ""]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid instance name. Please provide a valid instance name.",
        )

    if instance_data.channel_type == "whatsapp":
        url_value = str(instance_data.whatsapp_web_url) if instance_data.whatsapp_web_url else ""
        if url_value.lower() in ["string", "null", "undefined", ""]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid whatsapp_web_url. Please provide a valid WhatsApp Web API URL (e.g., http://localhost:8080).",
            )

        key_value = instance_data.whatsapp_web_key or ""
        if key_value.lower() in ["string", "null", "undefined", ""]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid whatsapp_web_key. Please provide a valid WhatsApp Web API key.",
            )

    # Normalize instance name for API compatibility
    original_name = instance_data.name
    normalized_name = normalize_instance_name(instance_data.name)

    # Update instance data with normalized name
    instance_data.name = normalized_name

    # Log normalization if name changed
    if original_name != normalized_name:
        logger.info(f"Instance name normalized: '{original_name}' -> '{normalized_name}'")

        # Check if normalization removed too much content (validation)
        # If the normalized name is significantly shorter or only contains basic chars after heavy modification
        if len(normalized_name) < len(original_name) * 0.5 or "!" in original_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Instance name '{original_name}' contains invalid characters. Use only letters, numbers, hyphens, and underscores.",
            )

    # Check if normalized instance name already exists
    existing = db.query(InstanceConfig).filter_by(name=normalized_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance '{normalized_name}' already exists (normalized from '{original_name}')",
        )

    # Validate channel type
    try:
        handler = ChannelHandlerFactory.get_handler(instance_data.channel_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # If setting as default, unset other defaults
    if instance_data.is_default:
        db.query(InstanceConfig).filter_by(is_default=True).update({"is_default": False})

    # Create database instance first (without creation parameters)
    db_instance_data = instance_data.model_dump(exclude={"phone_number", "auto_qr", "integration"}, exclude_unset=False)
    # Coerce AnyUrl/HttpUrl to plain strings for DB compatibility
    for key, value in list(db_instance_data.items()):
        if isinstance(value, AnyUrl):
            db_instance_data[key] = str(value)

    # Map WhatsApp Web API field names to database column names
    # (Schema uses whatsapp_web_*, DB uses evolution_* for backward compatibility)
    if "whatsapp_web_url" in db_instance_data:
        db_instance_data["evolution_url"] = db_instance_data.pop("whatsapp_web_url")
    if "whatsapp_web_key" in db_instance_data:
        db_instance_data["evolution_key"] = db_instance_data.pop("whatsapp_web_key")

    # Replace localhost with actual IPv4 addresses in URLs
    db_instance_data = ensure_ipv4_in_config(db_instance_data)

    # Set channel-specific defaults for WhatsApp
    if instance_data.channel_type == "whatsapp":
        if not db_instance_data.get("whatsapp_instance"):
            db_instance_data["whatsapp_instance"] = instance_data.name
        if not db_instance_data.get("session_id_prefix"):
            db_instance_data["session_id_prefix"] = f"{instance_data.name}-"

    db_instance = InstanceConfig(**db_instance_data)
    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)

    # Create instance in external service if needed
    try:
        if instance_data.channel_type == "whatsapp":
            creation_result = await handler.create_instance(
                db_instance,
                phone_number=instance_data.phone_number,
                auto_qr=instance_data.auto_qr,
                integration=instance_data.integration,
            )

            # Update instance with Evolution API details
            if "evolution_apikey" in creation_result:
                db_instance.evolution_key = creation_result["evolution_apikey"]

            # Mark instance as active after successful creation
            db_instance.is_active = True
            db.commit()
            db.refresh(db_instance)

            # Log whether we used existing or created new
            if creation_result.get("existing_instance"):
                logger.info(f"Using existing Evolution instance for '{instance_data.name}'")
            else:
                logger.info(f"Created new Evolution instance for '{instance_data.name}'")

    except ValidationError as e:
        # Rollback database if validation fails
        db.delete(db_instance)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid configuration: {str(e)}",
        )
    except Exception as e:
        # DESKTOP FIX: Don't delete instance if Evolution API is unreachable
        # Keep the config in database so users can retry connection later
        # Mark instance as inactive (disconnected state)
        logger.warning(
            f"Failed to connect to {instance_data.channel_type} service for '{instance_data.name}': {str(e)}"
        )
        logger.warning(
            f"Instance '{instance_data.name}' saved to database in disconnected state. User can retry connection later."
        )

        # Keep instance in DB but mark as inactive
        db_instance.is_active = False
        db.commit()
        db.refresh(db_instance)

        # Return instance with warning instead of failing completely
        # This allows desktop users to save configs even when Evolution API is unreachable
        return db_instance

    return db_instance


@router.get("/instances", response_model=List[InstanceConfigResponse])
async def list_instances(
    skip: int = 0,
    limit: int = 100,
    include_status: bool = True,
    include_live_status: bool = False,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """List all instance configurations with optional Evolution API status.

    Args:
        include_live_status: If True, fetch live connection status for each instance
                            via channel handlers (with caching and timeout).
    """
    instances = db.query(InstanceConfig).offset(skip).limit(limit).all()

    # Fetch live statuses if requested
    live_statuses = {}
    if include_live_status:
        try:
            from src.services.instance_status_service import get_live_statuses
            live_statuses = await get_live_statuses(instances)
        except Exception as e:
            logger.warning(f"Failed to fetch live statuses: {e}")

    environment = os.getenv("ENVIRONMENT", "").lower()
    skip_status_checks = environment == "test" or os.getenv("SKIP_EVOLUTION_STATUS", "").lower() in {"true", "1", "yes"}
    if not skip_status_checks:
        try:
            from src.config import config

            skip_status_checks = (
                getattr(config, "environment", None) and config.environment.environment.lower() == "test"
            )
        except Exception:
            skip_status_checks = False

    # Convert to response format and optionally include Evolution status
    response_instances = []
    for instance in instances:
        # Convert to dict first - SECURITY FIX: Use has_discord_bot_token
        instance_dict = {
            "id": instance.id,
            "name": instance.name,
            "channel_type": instance.channel_type,
            "whatsapp_web_url": instance.whatsapp_web_url,  # Use property alias
            "whatsapp_web_key": instance.whatsapp_web_key,  # Use property alias
            "whatsapp_instance": instance.whatsapp_instance,
            "session_id_prefix": instance.session_id_prefix,
            "webhook_base64": instance.webhook_base64,
            "agent_api_url": instance.agent_api_url,
            "agent_api_key": instance.agent_api_key,
            "default_agent": instance.default_agent,
            "agent_timeout": instance.agent_timeout,
            "is_default": instance.is_default,
            "is_active": instance.is_active,
            "connection_status": live_statuses.get(instance.name),
            "automagik_instance_id": instance.automagik_instance_id,
            "automagik_instance_name": instance.automagik_instance_name,
            "profile_name": getattr(instance, "profile_name", None),
            "profile_pic_url": getattr(instance, "profile_pic_url", None),
            "owner_jid": getattr(instance, "owner_jid", None),
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
            # Include unified fields
            "agent_instance_type": getattr(instance, "agent_instance_type", None),
            "agent_id": getattr(instance, "agent_id", None),
            "agent_type": getattr(instance, "agent_type", None),
            "agent_stream_mode": getattr(instance, "agent_stream_mode", None),
            "enable_auto_split": instance.enable_auto_split,
            # SECURITY FIX: Use boolean indicator instead of exposing token
            "has_discord_bot_token": bool(getattr(instance, "discord_bot_token", None)),
            "discord_client_id": getattr(instance, "discord_client_id", None),
            "discord_guild_id": getattr(instance, "discord_guild_id", None),
            "discord_default_channel_id": getattr(instance, "discord_default_channel_id", None),
            "discord_voice_enabled": getattr(instance, "discord_voice_enabled", None),
            "discord_slash_commands_enabled": getattr(instance, "discord_slash_commands_enabled", None),
            "evolution_status": None,
        }

        # Fetch Evolution status if requested and it's a WhatsApp instance
        if skip_status_checks:
            logger.debug(
                "Skipping Evolution status lookup for %s in test environment",
                instance.name,
            )
        elif include_status and instance.channel_type == "whatsapp":
            try:
                from src.channels.whatsapp.evolution_client import EvolutionClient
                from src.config import config
                from src.services.settings_service import settings_service

                # Get bootstrap key from database (with .env fallback)
                # Use gateway proxy URL - Evolution runs on dynamic ports managed by gateway
                gateway_port = os.getenv("OMNI_PORT", "8882")
                evolution_url = instance.evolution_url or settings_service.get_setting_value("evolution_api_url", db, default=f"http://localhost:{gateway_port}/evolution")
                bootstrap_key = settings_service.get_setting_value("evolution_api_key", db, default=None)
                if not bootstrap_key:
                    bootstrap_key = config.get_env("EVOLUTION_API_KEY", "")

                if not bootstrap_key:
                    logger.warning(f"No Evolution API key found in database or environment for {instance.name}, skipping status check")
                    instance_dict["whatsapp_web_status"] = None
                else:
                    # Pass instance name for logging/debugging only (auth uses bootstrap key)
                    whatsapp_instance_name = instance.whatsapp_instance or instance.name
                    evolution_client = EvolutionClient(evolution_url, bootstrap_key, whatsapp_instance_name)

                    # Get connection state
                    state_response = await evolution_client.get_connection_state(instance.name)
                    logger.debug(f"Evolution status for {instance.name}: {state_response}")

                    # Parse the response
                    if isinstance(state_response, dict) and "instance" in state_response:
                        instance_info = state_response["instance"]
                        instance_dict["whatsapp_web_status"] = EvolutionStatusInfo(
                            state=instance_info.get("state"),
                            owner_jid=instance_info.get("ownerJid"),
                            profile_name=instance_info.get("profileName"),
                            profile_picture_url=instance_info.get("profilePictureUrl"),
                            last_updated=datetime.now(),
                        )
                    else:
                        instance_dict["whatsapp_web_status"] = EvolutionStatusInfo(
                            error="Invalid response format", last_updated=datetime.now()
                        )

            except Exception as e:
                logger.warning(f"Failed to get Evolution status for {instance.name}: {e}")
                instance_dict["whatsapp_web_status"] = EvolutionStatusInfo(error=str(e), last_updated=datetime.now())

        response_instances.append(InstanceConfigResponse(**instance_dict))

    return response_instances


@router.get("/instances/{instance_name}", response_model=InstanceConfigResponse)
async def get_instance(
    instance_name: str,
    include_status: bool = True,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get a specific instance configuration with optional Evolution API status."""
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # Convert to dict first - SECURITY FIX: Use has_discord_bot_token
    instance_dict = {
        "id": instance.id,
        "name": instance.name,
        "channel_type": instance.channel_type,
        "whatsapp_web_url": instance.whatsapp_web_url,  # Use property alias
        "whatsapp_web_key": instance.whatsapp_web_key,  # Use property alias
        "whatsapp_instance": instance.whatsapp_instance,
        "session_id_prefix": instance.session_id_prefix,
        "webhook_base64": instance.webhook_base64,
        "agent_api_url": instance.agent_api_url,
        "agent_api_key": instance.agent_api_key,
        "default_agent": instance.default_agent,
        "agent_timeout": instance.agent_timeout,
        "is_default": instance.is_default,
        "is_active": instance.is_active,
        "automagik_instance_id": instance.automagik_instance_id,
        "automagik_instance_name": instance.automagik_instance_name,
        "profile_name": getattr(instance, "profile_name", None),
        "profile_pic_url": getattr(instance, "profile_pic_url", None),
        "owner_jid": getattr(instance, "owner_jid", None),
        "created_at": instance.created_at,
        "updated_at": instance.updated_at,
        # Include unified fields
        "agent_instance_type": getattr(instance, "agent_instance_type", None),
        "agent_id": getattr(instance, "agent_id", None),
        "agent_type": getattr(instance, "agent_type", None),
        "agent_stream_mode": getattr(instance, "agent_stream_mode", None),
        "enable_auto_split": instance.enable_auto_split,
        # SECURITY FIX: Use boolean indicator instead of exposing token
        "has_discord_bot_token": bool(getattr(instance, "discord_bot_token", None)),
        "discord_client_id": getattr(instance, "discord_client_id", None),
        "discord_guild_id": getattr(instance, "discord_guild_id", None),
        "discord_default_channel_id": getattr(instance, "discord_default_channel_id", None),
        "discord_voice_enabled": getattr(instance, "discord_voice_enabled", None),
        "discord_slash_commands_enabled": getattr(instance, "discord_slash_commands_enabled", None),
        "evolution_status": None,
    }

    # Fetch Evolution status if requested and it's a WhatsApp instance
    environment = os.getenv("ENVIRONMENT", "").lower()
    skip_status_checks = environment == "test" or os.getenv("SKIP_EVOLUTION_STATUS", "").lower() in {"true", "1", "yes"}
    if not skip_status_checks:
        try:
            from src.config import config

            skip_status_checks = (
                getattr(config, "environment", None) and config.environment.environment.lower() == "test"
            )
        except Exception:
            skip_status_checks = False

    if skip_status_checks:
        logger.debug(
            "Skipping Evolution status lookup for %s in test environment",
            instance.name,
        )
    elif include_status and instance.channel_type == "whatsapp" and instance.evolution_url:
        try:
            from src.channels.whatsapp.evolution_client import EvolutionClient
            from src.config import config
            from src.services.settings_service import settings_service

            # Get bootstrap key from database (with .env fallback)
            bootstrap_key = settings_service.get_setting_value("evolution_api_key", db, default=None)
            if not bootstrap_key:
                bootstrap_key = config.get_env("EVOLUTION_API_KEY", "")

            if not bootstrap_key:
                logger.warning(f"No Evolution API key found in database or environment, skipping status check for {instance.name}")
            else:
                # Pass instance name for logging/debugging only (auth uses bootstrap key)
                whatsapp_instance_name = instance.whatsapp_instance or instance.name
                evolution_client = EvolutionClient(instance.evolution_url, bootstrap_key, whatsapp_instance_name)

                # Get connection state using fetch_instances (more accurate than get_connection_state)
                evolution_instances = await evolution_client.fetch_instances(instance.name)
                logger.debug(f"Evolution status for {instance.name}: {evolution_instances}")

                # Parse the response
                if evolution_instances and len(evolution_instances) > 0:
                    evolution_instance = evolution_instances[0]
                    instance_dict["whatsapp_web_status"] = EvolutionStatusInfo(
                        state=evolution_instance.status,
                        owner_jid=evolution_instance.ownerJid,
                        profile_name=evolution_instance.profileName,
                        profile_picture_url=evolution_instance.profilePicUrl,
                        last_updated=datetime.now(),
                    )
                else:
                    instance_dict["whatsapp_web_status"] = EvolutionStatusInfo(
                        error="Instance not found in WhatsApp Web API", last_updated=datetime.now()
                    )

        except Exception as e:
            logger.warning(f"Failed to get Evolution status for {instance.name}: {e}")
            instance_dict["whatsapp_web_status"] = EvolutionStatusInfo(error=str(e), last_updated=datetime.now())

    return InstanceConfigResponse(**instance_dict)


@router.put("/instances/{instance_name}", response_model=InstanceConfigResponse)
async def update_instance(
    instance_name: str,
    update_data: InstanceConfigUpdate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Update an instance configuration."""
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # Get only provided fields (exclude None values from update)
    update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
    # Coerce AnyUrl/HttpUrl to plain strings for DB compatibility
    for key, value in list(update_dict.items()):
        if isinstance(value, AnyUrl):
            update_dict[key] = str(value)

    # Map WhatsApp Web API field names to database column names
    # (Schema uses whatsapp_web_*, DB uses evolution_* for backward compatibility)
    if "whatsapp_web_url" in update_dict:
        update_dict["evolution_url"] = update_dict.pop("whatsapp_web_url")
    if "whatsapp_web_key" in update_dict:
        update_dict["evolution_key"] = update_dict.pop("whatsapp_web_key")

    # Replace localhost with actual IPv4 addresses in URLs
    if update_dict:
        update_dict = ensure_ipv4_in_config(update_dict)

    # If setting as default, unset other defaults
    if update_dict.get("is_default"):
        db.query(InstanceConfig).filter(InstanceConfig.id != instance.id).filter_by(is_default=True).update(
            {"is_default": False}
        )

    # Update instance
    for field, value in update_dict.items():
        setattr(instance, field, value)

    db.commit()
    db.refresh(instance)

    return instance


@router.delete("/instances/{instance_name}")
async def delete_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Delete an instance configuration and associated external resources."""
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # Delete from external service if applicable
    try:
        if instance.channel_type == "whatsapp" and instance.evolution_url:
            handler = ChannelHandlerFactory.get_handler(instance.channel_type)
            await handler.delete_instance(instance)
            logger.info(f"Deleted Evolution instance for '{instance_name}'")
    except Exception as e:
        logger.warning(f"Failed to delete external instance for '{instance_name}': {e}")
        # Continue with database deletion even if external deletion fails

    # Delete from database
    db.delete(instance)
    db.commit()

    return {"message": f"Instance '{instance_name}' deleted successfully"}


@router.get("/instances/{instance_name}/qr")
async def get_qr_code(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
) -> QRCodeResponse:
    """Get QR code for instance connection."""
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # Get appropriate channel handler
    try:
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)
        qr_response = await handler.get_qr_code(instance)
        return qr_response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get QR code: {str(e)}",
        )


@router.get("/instances/{instance_name}/status")
async def get_connection_status(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
) -> ConnectionStatus:
    """Get connection status for instance."""
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # Get appropriate channel handler
    try:
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)
        status_response = await handler.get_status(instance)
        return status_response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection status: {str(e)}",
        )


@router.post("/instances/{instance_name}/connect")
async def connect_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Connect/reconnect an instance."""
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # Get appropriate channel handler
    try:
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)
        await handler.connect_instance(instance)

        # Update instance as active
        instance.is_active = True
        db.commit()

        return {"message": f"Instance '{instance_name}' connected successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect instance: {str(e)}",
        )


@router.post("/instances/{instance_name}/disconnect")
async def disconnect_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Disconnect an instance."""
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # Get appropriate channel handler
    try:
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)
        await handler.disconnect_instance(instance)

        # Update instance as inactive
        instance.is_active = False
        db.commit()

        return {"message": f"Instance '{instance_name}' disconnected successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect instance: {str(e)}",
        )


@router.post("/instances/{instance_name}/restart")
async def restart_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Restart an instance connection."""
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # Get appropriate channel handler
    try:
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)
        await handler.restart_instance(instance)

        # Update instance as active after successful restart
        instance.is_active = True
        db.commit()

        return {
            "success": True,
            "message": f"Instance '{instance_name}' restarted successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart instance: {str(e)}",
        )


@router.post("/instances/{instance_name}/logout")
async def logout_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Logout an instance (disconnect and clear session data)."""
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # Get appropriate channel handler
    try:
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)
        result = await handler.logout_instance(instance)

        # Update instance as inactive after logout
        instance.is_active = False
        db.commit()

        return {
            "message": f"Instance '{instance_name}' logged out successfully",
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout instance: {str(e)}",
        )


@router.post("/instances/discover")
async def discover_instances(
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Resync with Evolution API - discover and auto-configure instances.

    Uses global Evolution credentials from environment if DB is empty,
    then auto-generates API keys for each discovered instance.
    Useful when database has been recreated or wiped.
    """
    try:
        from src.services.discovery_service import discovery_service

        logger.info("Manual instance discovery/resync triggered")

        # Call enhanced discovery service (now supports empty DB via global env vars)
        discovered_instances = await discovery_service.discover_evolution_instances(db)

        return {
            "message": f"Resync complete - {len(discovered_instances)} instances configured",
            "instances": [
                {
                    "name": inst.name,
                    "whatsapp_instance": inst.whatsapp_instance,
                    "profile_name": inst.profile_name,
                    "evolution_key": inst.evolution_key,
                    "evolution_url": inst.evolution_url,
                }
                for inst in discovered_instances
            ],
            "total": len(discovered_instances),
        }

    except Exception as e:
        logger.error(f"Discovery/resync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resync with Evolution: {str(e)}",
        )
