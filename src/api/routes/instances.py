"""
CRUD API for managing instance configurations.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.api.deps import get_database, verify_api_key
from src.db.models import InstanceConfig

router = APIRouter()


# Pydantic models for API
class InstanceConfigCreate(BaseModel):
    """Schema for creating instance configuration."""
    name: str
    evolution_url: str = ""
    evolution_key: str = ""
    whatsapp_instance: str
    session_id_prefix: Optional[str] = None
    agent_api_url: str
    agent_api_key: str
    default_agent: str
    agent_timeout: int = 60
    is_default: bool = False


class InstanceConfigUpdate(BaseModel):
    """Schema for updating instance configuration."""
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
    evolution_url: str
    evolution_key: str
    whatsapp_instance: str
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
def create_instance(
    instance_data: InstanceConfigCreate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Create a new instance configuration."""
    
    # Check if instance name already exists
    existing = db.query(InstanceConfig).filter_by(name=instance_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance '{instance_data.name}' already exists"
        )
    
    # If setting as default, unset other defaults
    if instance_data.is_default:
        db.query(InstanceConfig).filter_by(is_default=True).update({"is_default": False})
    
    # Create new instance
    db_instance = InstanceConfig(**instance_data.dict())
    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)
    
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