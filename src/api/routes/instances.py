"""
CRUD API for managing instance configurations.
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import time

from src.api.deps import get_database, verify_api_key
from src.db.models import InstanceConfig
from src.channels.base import ChannelHandlerFactory, QRCodeResponse, ConnectionStatus
from src.ip_utils import ensure_ipv4_in_config
from src.utils.instance_utils import normalize_instance_name
from src.core.telemetry import track_instance_operation

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/instances/supported-channels")
async def get_supported_channels(api_key: str = Depends(verify_api_key)):
    """Get list of supported channel types."""
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
    channel_type: str = Field(
        default="whatsapp", description="Channel type: whatsapp, slack, discord"
    )

    # Channel-specific fields (optional based on type)
    evolution_url: Optional[str] = Field(
        None, description="Evolution API URL (WhatsApp)"
    )
    evolution_key: Optional[str] = Field(
        None, description="Evolution API key (WhatsApp)"
    )
    whatsapp_instance: Optional[str] = Field(None, description="WhatsApp instance name")
    session_id_prefix: Optional[str] = Field(
        None, description="Session ID prefix (WhatsApp)"
    )

    # WhatsApp-specific creation parameters (not stored in DB)
    phone_number: Optional[str] = Field(None, description="Phone number for WhatsApp")
    auto_qr: Optional[bool] = Field(
        True, description="Auto-generate QR code (WhatsApp)"
    )
    integration: Optional[str] = Field(
        "WHATSAPP-BAILEYS", description="WhatsApp integration type"
    )

    # Common agent configuration
    agent_api_url: str
    agent_api_key: str
    default_agent: str
    agent_timeout: int = 60
    is_default: bool = False


class InstanceConfigUpdate(BaseModel):
    """Schema for updating instance configuration."""

    channel_type: Optional[str] = None
    evolution_url: Optional[str] = None
    evolution_key: Optional[str] = None
    whatsapp_instance: Optional[str] = None
    session_id_prefix: Optional[str] = None
    agent_api_url: Optional[str] = None
    agent_api_key: Optional[str] = None
    default_agent: Optional[str] = None
    agent_timeout: Optional[int] = None
    is_default: Optional[bool] = None


class EvolutionStatusInfo(BaseModel):
    """Schema for Evolution API status information."""

    state: Optional[str] = None
    owner_jid: Optional[str] = None
    profile_name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    last_updated: Optional[datetime] = None
    error: Optional[str] = None


class InstanceConfigResponse(BaseModel):
    """Schema for instance configuration response."""

    id: int
    name: str
    channel_type: str
    evolution_url: Optional[str]
    evolution_key: Optional[str]
    whatsapp_instance: Optional[str]
    session_id_prefix: Optional[str]
    webhook_base64: Optional[bool]
    agent_api_url: str
    agent_api_key: str
    default_agent: str
    agent_timeout: int
    is_default: bool
    created_at: datetime
    updated_at: datetime
    evolution_status: Optional[EvolutionStatusInfo] = None

    class Config:
        from_attributes = True


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
    payload_data = instance_data.dict()
    # Mask sensitive fields for logging
    if "evolution_key" in payload_data and payload_data["evolution_key"]:
        payload_data["evolution_key"] = (
            f"{payload_data['evolution_key'][:4]}***{payload_data['evolution_key'][-4:]}"
            if len(payload_data["evolution_key"]) > 8
            else "***"
        )
    if "agent_api_key" in payload_data and payload_data["agent_api_key"]:
        payload_data["agent_api_key"] = (
            f"{payload_data['agent_api_key'][:4]}***{payload_data['agent_api_key'][-4:]}"
            if len(payload_data["agent_api_key"]) > 8
            else "***"
        )
    logger.debug(f"Instance creation payload: {payload_data}")

    # Validate input data for common issues
    if instance_data.name.lower() in ["string", "null", "undefined", ""]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid instance name. Please provide a valid instance name.",
        )

    if instance_data.channel_type == "whatsapp":
        if instance_data.evolution_url and instance_data.evolution_url.lower() in [
            "string",
            "null",
            "undefined",
            "",
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid evolution_url. Please provide a valid Evolution API URL (e.g., http://localhost:8080).",
            )
        if instance_data.evolution_key and instance_data.evolution_key.lower() in [
            "string",
            "null",
            "undefined",
            "",
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid evolution_key. Please provide a valid Evolution API key.",
            )

    # Normalize instance name for API compatibility
    original_name = instance_data.name
    normalized_name = normalize_instance_name(instance_data.name)

    # Update instance data with normalized name
    instance_data.name = normalized_name

    # Log normalization if name changed
    if original_name != normalized_name:
        logger.info(
            f"Instance name normalized: '{original_name}' -> '{normalized_name}'"
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
        db.query(InstanceConfig).filter_by(is_default=True).update(
            {"is_default": False}
        )

    # Create database instance first (without creation parameters)
    db_instance_data = instance_data.dict(
        exclude={"phone_number", "auto_qr", "integration"}
    )

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
                db.commit()
                db.refresh(db_instance)

            # Log whether we used existing or created new
            if creation_result.get("existing_instance"):
                logger.info(
                    f"Using existing Evolution instance for '{instance_data.name}'"
                )
            else:
                logger.info(
                    f"Created new Evolution instance for '{instance_data.name}'"
                )

    except Exception as e:
        # Rollback database if external service creation fails
        db.delete(db_instance)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create {instance_data.channel_type} instance: {str(e)}",
        )

    return db_instance


@router.get("/instances", response_model=List[InstanceConfigResponse])
async def list_instances(
    skip: int = 0,
    limit: int = 100,
    include_status: bool = True,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """List all instance configurations with optional Evolution API status."""
    instances = db.query(InstanceConfig).offset(skip).limit(limit).all()

    # Convert to response format and optionally include Evolution status
    response_instances = []
    for instance in instances:
        # Convert to dict first
        instance_dict = {
            "id": instance.id,
            "name": instance.name,
            "channel_type": instance.channel_type,
            "evolution_url": instance.evolution_url,
            "evolution_key": instance.evolution_key,
            "whatsapp_instance": instance.whatsapp_instance,
            "session_id_prefix": instance.session_id_prefix,
            "webhook_base64": True,
            "agent_api_url": instance.agent_api_url,
            "agent_api_key": instance.agent_api_key,
            "default_agent": instance.default_agent,
            "agent_timeout": instance.agent_timeout,
            "is_default": instance.is_default,
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
            "evolution_status": None,
        }

        # Fetch Evolution status if requested and it's a WhatsApp instance
        if (
            include_status
            and instance.channel_type == "whatsapp"
            and instance.evolution_url
            and instance.evolution_key
        ):
            try:
                from src.channels.whatsapp.evolution_client import EvolutionClient

                evolution_client = EvolutionClient(
                    instance.evolution_url, instance.evolution_key
                )

                # Get connection state
                state_response = await evolution_client.get_connection_state(
                    instance.name
                )
                logger.debug(f"Evolution status for {instance.name}: {state_response}")

                # Parse the response
                if isinstance(state_response, dict) and "instance" in state_response:
                    instance_info = state_response["instance"]
                    instance_dict["evolution_status"] = EvolutionStatusInfo(
                        state=instance_info.get("state"),
                        owner_jid=instance_info.get("ownerJid"),
                        profile_name=instance_info.get("profileName"),
                        profile_picture_url=instance_info.get("profilePictureUrl"),
                        last_updated=datetime.now(),
                    )
                else:
                    instance_dict["evolution_status"] = EvolutionStatusInfo(
                        error="Invalid response format", last_updated=datetime.now()
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to get Evolution status for {instance.name}: {e}"
                )
                instance_dict["evolution_status"] = EvolutionStatusInfo(
                    error=str(e), last_updated=datetime.now()
                )

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

    # Convert to dict first
    instance_dict = {
        "id": instance.id,
        "name": instance.name,
        "channel_type": instance.channel_type,
        "evolution_url": instance.evolution_url,
        "evolution_key": instance.evolution_key,
        "whatsapp_instance": instance.whatsapp_instance,
        "session_id_prefix": instance.session_id_prefix,
        "webhook_base64": True,
        "agent_api_url": instance.agent_api_url,
        "agent_api_key": instance.agent_api_key,
        "default_agent": instance.default_agent,
        "agent_timeout": instance.agent_timeout,
        "is_default": instance.is_default,
        "created_at": instance.created_at,
        "updated_at": instance.updated_at,
        "evolution_status": None,
    }

    # Fetch Evolution status if requested and it's a WhatsApp instance
    if (
        include_status
        and instance.channel_type == "whatsapp"
        and instance.evolution_url
        and instance.evolution_key
    ):
        try:
            from src.channels.whatsapp.evolution_client import EvolutionClient

            evolution_client = EvolutionClient(
                instance.evolution_url, instance.evolution_key
            )

            # Get connection state
            state_response = await evolution_client.get_connection_state(instance.name)
            logger.debug(f"Evolution status for {instance.name}: {state_response}")

            # Parse the response
            if isinstance(state_response, dict) and "instance" in state_response:
                instance_info = state_response["instance"]
                instance_dict["evolution_status"] = EvolutionStatusInfo(
                    state=instance_info.get("state"),
                    owner_jid=instance_info.get("ownerJid"),
                    profile_name=instance_info.get("profileName"),
                    profile_picture_url=instance_info.get("profilePictureUrl"),
                    last_updated=datetime.now(),
                )
            else:
                instance_dict["evolution_status"] = EvolutionStatusInfo(
                    error="Invalid response format", last_updated=datetime.now()
                )

        except Exception as e:
            logger.warning(f"Failed to get Evolution status for {instance.name}: {e}")
            instance_dict["evolution_status"] = EvolutionStatusInfo(
                error=str(e), last_updated=datetime.now()
            )

    return InstanceConfigResponse(**instance_dict)


@router.put("/instances/{instance_name}", response_model=InstanceConfigResponse)
def update_instance(
    instance_name: str,
    instance_data: InstanceConfigUpdate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Update an instance configuration."""

    # Get existing instance
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # If setting as default, unset other defaults
    if instance_data.is_default:
        db.query(InstanceConfig).filter_by(is_default=True).update(
            {"is_default": False}
        )

    # Update fields
    update_data = instance_data.dict(exclude_unset=True)

    # Replace localhost with actual IPv4 addresses in URLs
    update_data = ensure_ipv4_in_config(update_data)

    for field, value in update_data.items():
        setattr(instance, field, value)

    db.commit()
    db.refresh(instance)
    return instance


@router.delete("/instances/{instance_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Delete an instance configuration from both database and external service."""

    # Get existing instance
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # Don't allow deleting the default instance if it's the only one
    if instance.is_default:
        instance_count = db.query(InstanceConfig).count()
        if instance_count == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only remaining instance",
            )

    # First try to delete from external service (Evolution API)
    evolution_delete_success = False
    evolution_error = None

    try:
        # Get channel-specific handler
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)

        # Delete from external service
        await handler.delete_instance(instance)
        evolution_delete_success = True
        logger.info(
            f"Successfully deleted instance '{instance_name}' from {instance.channel_type} service"
        )

    except Exception as e:
        evolution_error = str(e)
        logger.warning(
            f"Failed to delete instance '{instance_name}' from {instance.channel_type} service: {e}"
        )
        # Continue with database deletion even if external service fails

    # Always delete from database
    db.delete(instance)
    db.commit()

    logger.info(f"Instance '{instance_name}' deleted from database")

    # Log the final result
    if evolution_delete_success:
        logger.info(
            f"Instance '{instance_name}' completely deleted from both service and database"
        )
    else:
        logger.warning(
            f"Instance '{instance_name}' deleted from database only. External service deletion failed: {evolution_error}"
        )

    # Return empty response for 204 No Content
    return


@router.get("/instances/{instance_name}/default", response_model=InstanceConfigResponse)
def get_default_instance(
    db: Session = Depends(get_database), api_key: str = Depends(verify_api_key)
):
    """Get the default instance configuration."""
    default_instance = db.query(InstanceConfig).filter_by(is_default=True).first()
    if not default_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No default instance found"
        )
    return default_instance


@router.post(
    "/instances/{instance_name}/set-default", response_model=InstanceConfigResponse
)
def set_default_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Set an instance as the default."""

    # Get the instance
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    # Unset other defaults
    db.query(InstanceConfig).filter_by(is_default=True).update({"is_default": False})

    # Set this as default
    instance.is_default = True
    db.commit()
    db.refresh(instance)

    return instance


# Channel-specific operations
@router.get("/instances/{instance_name}/qr", response_model=QRCodeResponse)
async def get_instance_qr_code(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get QR code or connection info for any channel type."""

    logger.debug(f"QR CODE API: Request for instance {instance_name}")

    # Get instance from database
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        logger.error(f"QR CODE API: Instance {instance_name} not found in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    logger.debug(
        f"QR CODE API: Found instance {instance_name}, channel_type: {instance.channel_type}"
    )

    try:
        # Get channel-specific handler
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)
        logger.debug(f"QR CODE API: Got handler {type(handler).__name__}")

        # Get QR code/connection info
        logger.debug("QR CODE API: Calling handler.get_qr_code()")
        result = await handler.get_qr_code(instance)
        logger.debug(f"QR CODE API: Handler returned {result}")
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported channel type '{instance.channel_type}': {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection info: {str(e)}",
        )


@router.get("/instances/{instance_name}/status", response_model=ConnectionStatus)
async def get_instance_status(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get connection status for any channel type."""

    # Get instance from database
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    try:
        # Get channel-specific handler
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)

        # Get status
        result = await handler.get_status(instance)
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported channel type '{instance.channel_type}': {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}",
        )


@router.post("/instances/{instance_name}/restart")
async def restart_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Restart instance connection for any channel type."""

    # Get instance from database
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    try:
        # Get channel-specific handler
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)

        # Restart instance
        result = await handler.restart_instance(instance)

        # Also sync status with Evolution to update our database
        if instance.channel_type == "whatsapp":
            try:
                from src.services.discovery_service import discovery_service

                await discovery_service.sync_instance_status(instance_name, db)
            except Exception as e:
                logger.warning(f"Failed to sync instance status after restart: {e}")

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported channel type '{instance.channel_type}': {str(e)}",
        )
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
    """Logout/disconnect instance for any channel type."""

    # Get instance from database
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    try:
        # Get channel-specific handler
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)

        # Logout instance
        result = await handler.logout_instance(instance)
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported channel type '{instance.channel_type}': {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout instance: {str(e)}",
        )


@router.post("/instances/discover")
async def discover_evolution_instances(
    db: Session = Depends(get_database), api_key: str = Depends(verify_api_key)
):
    """
    Manually trigger Evolution instance discovery.

    Discovers instances from Evolution API and creates missing database entries.
    Only creates new instances - does not modify existing ones.
    """
    try:
        from src.services.discovery_service import discovery_service

        logger.info("Manual Evolution instance discovery triggered")
        discovered_instances = await discovery_service.discover_evolution_instances(db)

        if discovered_instances:
            return {
                "status": "success",
                "message": f"Discovered {len(discovered_instances)} Evolution instances",
                "instances": [
                    {
                        "name": instance.name,
                        "active": instance.is_active,
                        "agent_id": instance.agent_id,
                    }
                    for instance in discovered_instances
                ],
            }
        else:
            return {
                "status": "success",
                "message": "No new Evolution instances discovered",
                "instances": [],
            }

    except Exception as e:
        logger.error(f"Manual discovery failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Discovery failed: {str(e)}",
        )


@router.delete("/instances/{instance_name}/channel")
async def delete_instance_from_channel(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Delete instance from external channel service (but keep in database)."""

    # Get instance from database
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    try:
        # Get channel-specific handler
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)

        # Delete from external service
        result = await handler.delete_instance(instance)
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported channel type '{instance.channel_type}': {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete from channel service: {str(e)}",
        )
