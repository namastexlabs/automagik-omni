"""
WhatsApp instance management API endpoints.
Provides CRUD operations for WhatsApp instances via Evolution API.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.api.deps import get_database, verify_api_key
from src.db.models import InstanceConfig
from src.channels.whatsapp.evolution_client import (
    get_evolution_client,
    EvolutionCreateRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for WhatsApp management
class WhatsAppInstanceCreate(BaseModel):
    """Schema for creating WhatsApp instance."""

    name: str = Field(description="Instance name (will be used as instanceName)")
    phone_number: Optional[str] = Field(
        None, description="Phone number with country code (e.g., 5511999999999)"
    )
    integration: str = Field(
        "WHATSAPP-BAILEYS", description="WhatsApp integration type"
    )
    auto_qr: bool = Field(True, description="Generate QR code automatically")
    settings: Optional[Dict[str, Any]] = Field(
        None, description="Additional instance settings"
    )

    # Agent configuration
    agent_api_url: str = Field(description="Agent API URL")
    agent_api_key: str = Field(description="Agent API key")
    default_agent: str = Field(description="Default agent name")
    agent_timeout: int = Field(60, description="Agent timeout in seconds")


class WhatsAppInstanceResponse(BaseModel):
    """Schema for WhatsApp instance response."""

    # Omni-Hub instance data
    id: int
    name: str
    whatsapp_instance: str
    session_id_prefix: Optional[str]
    agent_api_url: str
    agent_api_key: str
    default_agent: str
    agent_timeout: int
    is_default: bool

    # Evolution API data
    evolution_instance_id: Optional[str] = None
    evolution_status: Optional[str] = None
    evolution_owner: Optional[str] = None
    evolution_profile_name: Optional[str] = None
    qr_code: Optional[str] = None

    class Config:
        from_attributes = True


class WhatsAppConnectionState(BaseModel):
    """Schema for connection state response."""

    instance_name: str
    status: str  # "open", "close", "connecting"
    evolution_data: Optional[Dict[str, Any]] = None


class QRCodeResponse(BaseModel):
    """Schema for QR code response."""

    instance_name: str
    qr_code: Optional[str] = None
    status: str
    message: str


@router.post(
    "/instances",
    response_model=WhatsAppInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_whatsapp_instance(
    instance_data: WhatsAppInstanceCreate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Create a new WhatsApp instance."""

    # Check if instance name already exists in our database
    existing = db.query(InstanceConfig).filter_by(name=instance_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance '{instance_data.name}' already exists",
        )

    try:
        # Create instance in Evolution API
        evolution_client = get_evolution_client()

        # Prepare Evolution API request
        evolution_request = EvolutionCreateRequest(
            instanceName=instance_data.name,
            integration=instance_data.integration,
            qrcode=instance_data.auto_qr,
            number=instance_data.phone_number,
            **(instance_data.settings or {}),
        )

        evolution_response = await evolution_client.create_instance(evolution_request)
        logger.info(f"Evolution instance created: {evolution_response}")

        # Extract Evolution data
        evolution_instance = evolution_response.get("instance", {})
        evolution_instance_id = evolution_instance.get("instanceId")
        evolution_apikey = evolution_response.get("hash", {}).get("apikey")

        # Create instance in our database
        db_instance = InstanceConfig(
            name=instance_data.name,
            evolution_url="",  # Will be set from webhook
            evolution_key=evolution_apikey or "",
            whatsapp_instance=instance_data.name,  # Use same name
            session_id_prefix=f"{instance_data.name}-",
            agent_api_url=instance_data.agent_api_url,
            agent_api_key=instance_data.agent_api_key,
            default_agent=instance_data.default_agent,
            agent_timeout=instance_data.agent_timeout,
            is_default=False,
        )

        db.add(db_instance)
        db.commit()
        db.refresh(db_instance)

        # Prepare response
        response_data = WhatsAppInstanceResponse.from_orm(db_instance)
        response_data.evolution_instance_id = evolution_instance_id
        response_data.evolution_status = evolution_instance.get("status")

        return response_data

    except Exception as e:
        logger.error(f"Failed to create WhatsApp instance: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create WhatsApp instance: {str(e)}",
        )


@router.get("/instances", response_model=List[WhatsAppInstanceResponse])
async def list_whatsapp_instances(
    db: Session = Depends(get_database), api_key: str = Depends(verify_api_key)
):
    """List all WhatsApp instances with Evolution API status."""

    # Get instances from our database
    db_instances = db.query(InstanceConfig).all()

    # Get Evolution API instances
    try:
        evolution_client = get_evolution_client()
        evolution_instances = await evolution_client.fetch_instances()
        evolution_map = {inst.instanceName: inst for inst in evolution_instances}
    except Exception as e:
        logger.warning(f"Failed to fetch Evolution instances: {e}")
        evolution_map = {}

    # Combine data
    response_instances = []
    for db_instance in db_instances:
        response_data = WhatsAppInstanceResponse.from_orm(db_instance)

        # Add Evolution data if available
        if db_instance.name in evolution_map:
            evo_inst = evolution_map[db_instance.name]
            response_data.evolution_instance_id = evo_inst.instanceId
            response_data.evolution_status = evo_inst.status
            response_data.evolution_owner = evo_inst.owner
            response_data.evolution_profile_name = evo_inst.profileName

        response_instances.append(response_data)

    return response_instances


@router.get("/instances/{instance_name}/qr", response_model=QRCodeResponse)
async def get_qr_code(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get QR code for WhatsApp instance connection."""

    # Verify instance exists in our database
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    try:
        evolution_client = get_evolution_client()

        # Get connection info (includes QR code)
        connect_response = await evolution_client.connect_instance(instance_name)

        qr_code = None
        message = "QR code not available"

        # Extract QR code from response
        if "qrcode" in connect_response:
            qr_code = connect_response["qrcode"].get("base64")
            message = "QR code ready for scanning"
        elif "message" in connect_response:
            message = connect_response["message"]

        return QRCodeResponse(
            instance_name=instance_name,
            qr_code=qr_code,
            status="success",
            message=message,
        )

    except Exception as e:
        logger.error(f"Failed to get QR code for {instance_name}: {e}")
        return QRCodeResponse(
            instance_name=instance_name,
            qr_code=None,
            status="error",
            message=f"Failed to get QR code: {str(e)}",
        )


@router.get("/instances/{instance_name}/status", response_model=WhatsAppConnectionState)
async def get_connection_status(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get connection status of WhatsApp instance."""

    # Verify instance exists
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    try:
        evolution_client = get_evolution_client()
        state_response = await evolution_client.get_connection_state(instance_name)

        return WhatsAppConnectionState(
            instance_name=instance_name,
            status=state_response.get("instance", {}).get("state", "unknown"),
            evolution_data=state_response,
        )

    except Exception as e:
        logger.error(f"Failed to get connection state for {instance_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection state: {str(e)}",
        )


@router.post("/instances/{instance_name}/restart")
async def restart_whatsapp_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Restart WhatsApp instance."""

    # Verify instance exists
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    try:
        evolution_client = get_evolution_client()
        result = await evolution_client.restart_instance(instance_name)

        return {
            "status": "success",
            "message": f"Instance '{instance_name}' restart initiated",
            "evolution_response": result,
        }

    except Exception as e:
        logger.error(f"Failed to restart instance {instance_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart instance: {str(e)}",
        )


@router.post("/instances/{instance_name}/logout")
async def logout_whatsapp_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Logout WhatsApp instance (disconnect without deleting)."""

    # Verify instance exists
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found",
        )

    try:
        evolution_client = get_evolution_client()
        result = await evolution_client.logout_instance(instance_name)

        return {
            "status": "success",
            "message": f"Instance '{instance_name}' logged out",
            "evolution_response": result,
        }

    except Exception as e:
        logger.error(f"Failed to logout instance {instance_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout instance: {str(e)}",
        )


@router.delete("/instances/{instance_name}")
async def delete_whatsapp_instance(
    instance_name: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Delete WhatsApp instance from both Evolution API and our database."""

    # Get instance from our database
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

    try:
        # Delete from Evolution API first
        evolution_client = get_evolution_client()
        evolution_result = await evolution_client.delete_instance(instance_name)
        logger.info(f"Evolution instance deleted: {evolution_result}")

    except Exception as e:
        logger.warning(f"Failed to delete from Evolution API: {e}")
        # Continue with database deletion even if Evolution API fails

    try:
        # Delete from our database
        db.delete(instance)
        db.commit()

        return {
            "status": "success",
            "message": f"Instance '{instance_name}' deleted successfully",
        }

    except Exception as e:
        logger.error(f"Failed to delete instance from database: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete instance from database: {str(e)}",
        )
