"""
CRUD API for managing instance configurations.
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.api.deps import get_database, verify_api_key
from src.db.models import InstanceConfig
from src.channels.base import ChannelHandlerFactory, QRCodeResponse, ConnectionStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/instances/supported-channels")
async def get_supported_channels(
    api_key: str = Depends(verify_api_key)
):
    """Get list of supported channel types."""
    try:
        supported_channels = ChannelHandlerFactory.get_supported_channels()
        return {
            "supported_channels": supported_channels,
            "total_channels": len(supported_channels)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supported channels: {str(e)}"
        )


# Pydantic models for API
class InstanceConfigCreate(BaseModel):
    """Schema for creating instance configuration."""
    name: str
    channel_type: str = Field(default="whatsapp", description="Channel type: whatsapp, slack, discord")
    
    # Channel-specific fields (optional based on type)
    evolution_url: Optional[str] = Field(None, description="Evolution API URL (WhatsApp)")
    evolution_key: Optional[str] = Field(None, description="Evolution API key (WhatsApp)")
    whatsapp_instance: Optional[str] = Field(None, description="WhatsApp instance name")
    session_id_prefix: Optional[str] = Field(None, description="Session ID prefix (WhatsApp)")
    
    # WhatsApp-specific creation parameters (not stored in DB)
    phone_number: Optional[str] = Field(None, description="Phone number for WhatsApp")
    auto_qr: Optional[bool] = Field(True, description="Auto-generate QR code (WhatsApp)")
    integration: Optional[str] = Field("WHATSAPP-BAILEYS", description="WhatsApp integration type")
    
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


class InstanceConfigResponse(BaseModel):
    """Schema for instance configuration response."""
    id: int
    name: str
    channel_type: str
    evolution_url: Optional[str]
    evolution_key: Optional[str]
    whatsapp_instance: Optional[str]
    session_id_prefix: Optional[str]
    agent_api_url: str
    agent_api_key: str
    default_agent: str
    agent_timeout: int
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/instances", response_model=InstanceConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    instance_data: InstanceConfigCreate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Create a new instance configuration with channel-specific setup."""
    
    # Check if instance name already exists
    existing = db.query(InstanceConfig).filter_by(name=instance_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance '{instance_data.name}' already exists"
        )
    
    # Validate channel type
    try:
        handler = ChannelHandlerFactory.get_handler(instance_data.channel_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # If setting as default, unset other defaults
    if instance_data.is_default:
        db.query(InstanceConfig).filter_by(is_default=True).update({"is_default": False})
    
    # Create database instance first (without creation parameters)
    db_instance_data = instance_data.dict(exclude={"phone_number", "auto_qr", "integration"})
    
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
                integration=instance_data.integration
            )
            
            # Update instance with Evolution API details
            if "evolution_apikey" in creation_result:
                db_instance.evolution_key = creation_result["evolution_apikey"]
                db.commit()
                db.refresh(db_instance)
            
            # Log whether we used existing or created new
            if creation_result.get("existing_instance"):
                logger.info(f"Using existing Evolution instance for '{instance_data.name}'")
            else:
                logger.info(f"Created new Evolution instance for '{instance_data.name}'")
    
    except Exception as e:
        # Rollback database if external service creation fails
        db.delete(db_instance)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create {instance_data.channel_type} instance: {str(e)}"
        )
    
    return db_instance


@router.get("/instances", response_model=List[InstanceConfigResponse])
def list_instances(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """List all instance configurations."""
    instances = db.query(InstanceConfig).offset(skip).limit(limit).all()
    return instances


@router.get("/instances/{instance_name}", response_model=InstanceConfigResponse)
def get_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Get a specific instance configuration."""
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found"
        )
    return instance


@router.put("/instances/{instance_name}", response_model=InstanceConfigResponse)
def update_instance(
    instance_name: str,
    instance_data: InstanceConfigUpdate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Update an instance configuration."""
    
    # Get existing instance
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found"
        )
    
    # If setting as default, unset other defaults
    if instance_data.is_default:
        db.query(InstanceConfig).filter_by(is_default=True).update({"is_default": False})
    
    # Update fields
    update_data = instance_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(instance, field, value)
    
    db.commit()
    db.refresh(instance)
    return instance


@router.delete("/instances/{instance_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Delete an instance configuration."""
    
    # Get existing instance
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found"
        )
    
    # Don't allow deleting the default instance if it's the only one
    if instance.is_default:
        instance_count = db.query(InstanceConfig).count()
        if instance_count == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only remaining instance"
            )
    
    db.delete(instance)
    db.commit()
    
    # Return empty response for 204 No Content
    return


@router.get("/instances/{instance_name}/default", response_model=InstanceConfigResponse)
def get_default_instance(
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Get the default instance configuration."""
    default_instance = db.query(InstanceConfig).filter_by(is_default=True).first()
    if not default_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No default instance found"
        )
    return default_instance


@router.post("/instances/{instance_name}/set-default", response_model=InstanceConfigResponse)
def set_default_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Set an instance as the default."""
    
    # Get the instance
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found"
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
    api_key: str = Depends(verify_api_key)
):
    """Get QR code or connection info for any channel type."""
    
    logger.debug(f"QR CODE API: Request for instance {instance_name}")
    
    # Get instance from database
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        logger.error(f"QR CODE API: Instance {instance_name} not found in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found"
        )
    
    logger.debug(f"QR CODE API: Found instance {instance_name}, channel_type: {instance.channel_type}")
    
    try:
        # Get channel-specific handler
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)
        logger.debug(f"QR CODE API: Got handler {type(handler).__name__}")
        
        # Get QR code/connection info
        logger.debug(f"QR CODE API: Calling handler.get_qr_code()")
        result = await handler.get_qr_code(instance)
        logger.debug(f"QR CODE API: Handler returned {result}")
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported channel type '{instance.channel_type}': {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection info: {str(e)}"
        )


@router.get("/instances/{instance_name}/status", response_model=ConnectionStatus)
async def get_instance_status(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Get connection status for any channel type."""
    
    # Get instance from database
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found"
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
            detail=f"Unsupported channel type '{instance.channel_type}': {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.post("/instances/{instance_name}/restart")
async def restart_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Restart instance connection for any channel type."""
    
    # Get instance from database
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found"
        )
    
    try:
        # Get channel-specific handler
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)
        
        # Restart instance
        result = await handler.restart_instance(instance)
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported channel type '{instance.channel_type}': {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart instance: {str(e)}"
        )


@router.post("/instances/{instance_name}/logout")
async def logout_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Logout/disconnect instance for any channel type."""
    
    # Get instance from database
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found"
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
            detail=f"Unsupported channel type '{instance.channel_type}': {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout instance: {str(e)}"
        )


@router.delete("/instances/{instance_name}/channel")
async def delete_instance_from_channel(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Delete instance from external channel service (but keep in database)."""
    
    # Get instance from database
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found"
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
            detail=f"Unsupported channel type '{instance.channel_type}': {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete from channel service: {str(e)}"
        )