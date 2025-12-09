"""
CRUD API for managing global application settings.
"""

import logging
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from src.api.deps import get_database, verify_api_key
from src.db.models import GlobalSetting, SettingChangeHistory
from src.services.settings_service import settings_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic schemas


class SettingCreate(BaseModel):
    """Schema for creating a global setting."""

    key: str = Field(..., description="Unique setting key (e.g., 'evolution_api_key')")
    value: Any = Field(..., description="Setting value")
    value_type: str = Field(..., description="Value type: string, integer, boolean, json, secret")
    category: Optional[str] = Field(None, description="Category grouping (e.g., 'api', 'integration')")
    description: Optional[str] = Field(None, description="Human-readable description")
    is_secret: bool = Field(False, description="Whether to mask value in UI")
    is_required: bool = Field(False, description="Whether required for app operation")
    default_value: Optional[str] = Field(None, description="Default fallback value")
    validation_rules: Optional[Dict] = Field(None, description="JSON validation rules")


class SettingUpdate(BaseModel):
    """Schema for updating a setting value."""

    value: Any = Field(..., description="New setting value")
    change_reason: Optional[str] = Field(None, description="Optional reason for change")


class SettingResponse(BaseModel):
    """Schema for setting response."""

    id: int
    key: str
    value: Optional[str]  # Masked if secret
    value_type: str
    category: Optional[str]
    description: Optional[str]
    is_secret: bool
    is_required: bool
    default_value: Optional[str]
    created_at: str
    updated_at: str
    created_by: Optional[str]
    updated_by: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SettingHistoryResponse(BaseModel):
    """Schema for setting change history."""

    id: int
    setting_id: int
    old_value: Optional[str]
    new_value: Optional[str]
    changed_by: Optional[str]
    changed_at: str
    change_reason: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# API Endpoints


@router.get(
    "/settings",
    response_model=List[SettingResponse],
    summary="List Global Settings",
    description="Retrieve all global application settings",
)
async def list_settings(
    category: Optional[str] = None,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """List all global settings, optionally filtered by category."""

    settings = settings_service.list_settings(db, category=category)

    # Mask secret values in response
    return [_to_setting_response(setting) for setting in settings]


@router.get(
    "/settings/{key}",
    response_model=SettingResponse,
    summary="Get Setting",
    description="Retrieve a specific global setting by key",
)
async def get_setting(
    key: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get a specific setting by key."""

    setting = settings_service.get_setting(key, db)

    if not setting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Setting '{key}' not found")

    return _to_setting_response(setting)


@router.post(
    "/settings",
    response_model=SettingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Setting",
    description="Create a new global setting",
)
async def create_setting(
    setting_data: SettingCreate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Create a new global setting."""

    try:
        setting = settings_service.create_setting(
            key=setting_data.key,
            value=setting_data.value,
            value_type=setting_data.value_type,
            db=db,
            category=setting_data.category,
            description=setting_data.description,
            is_secret=setting_data.is_secret,
            is_required=setting_data.is_required,
            default_value=setting_data.default_value,
            validation_rules=setting_data.validation_rules,
            created_by=api_key[:8] if api_key else None,  # Masked API key
        )

        return _to_setting_response(setting)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/settings/{key}",
    response_model=SettingResponse,
    summary="Update Setting",
    description="Update an existing global setting value",
)
async def update_setting(
    key: str,
    update_data: SettingUpdate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Update a setting's value."""

    try:
        setting = settings_service.update_setting(
            key=key,
            value=update_data.value,
            db=db,
            updated_by=api_key[:8] if api_key else None,
            change_reason=update_data.change_reason,
        )

        return _to_setting_response(setting)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/settings/{key}", summary="Delete Setting", description="Delete a global setting (if not required)")
async def delete_setting(
    key: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Delete a setting."""

    try:
        success = settings_service.delete_setting(key, db)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Setting '{key}' not found")

        return {"message": f"Setting '{key}' deleted successfully"}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/settings/{key}/history",
    response_model=List[SettingHistoryResponse],
    summary="Get Setting History",
    description="Retrieve change history for a setting",
)
async def get_setting_history(
    key: str,
    limit: int = 50,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get change history for a setting."""

    history = settings_service.get_change_history(key, db, limit=limit)

    return [_to_history_response(h) for h in history]


# Helper functions


def _to_setting_response(setting: GlobalSetting) -> SettingResponse:
    """Convert ORM setting to response model with null-safe fields."""
    assert setting.id is not None
    assert setting.key is not None
    assert setting.value_type is not None
    created_at = setting.created_at.isoformat() if setting.created_at else ""
    updated_at = setting.updated_at.isoformat() if setting.updated_at else ""

    return SettingResponse(
        id=setting.id,
        key=setting.key,
        value=_mask_if_secret(setting),
        value_type=setting.value_type,
        category=setting.category,
        description=setting.description,
        is_secret=bool(setting.is_secret),
        is_required=bool(setting.is_required),
        default_value=setting.default_value,
        created_at=created_at,
        updated_at=updated_at,
        created_by=setting.created_by,
        updated_by=setting.updated_by,
    )


def _to_history_response(history: SettingChangeHistory) -> SettingHistoryResponse:
    """Convert ORM history entry to response model with null-safe fields."""
    assert history.id is not None
    assert history.setting_id is not None
    changed_at = history.changed_at.isoformat() if history.changed_at else ""

    return SettingHistoryResponse(
        id=history.id,
        setting_id=history.setting_id,
        old_value=history.old_value,
        new_value=history.new_value,
        changed_by=history.changed_by,
        changed_at=changed_at,
        change_reason=history.change_reason,
    )


def _mask_if_secret(setting: GlobalSetting) -> Optional[str]:
    """Mask secret values in API responses.

    Args:
        setting: GlobalSetting object

    Returns:
        Masked value if secret, otherwise original value
    """
    if not setting.is_secret or not setting.value:
        return setting.value

    # Mask all but first 4 and last 4 characters
    if len(setting.value) <= 8:
        return "***"

    return f"{setting.value[:4]}***{setting.value[-4:]}"
