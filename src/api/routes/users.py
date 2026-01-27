"""
User Management API Routes.

Provides endpoints for listing, viewing, merging, and linking users
across multiple channels (WhatsApp, Discord, etc.).
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.api.deps import get_database, verify_api_key
from src.services.user_service import user_service
from src.db.models import User, UserExternalId

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic response models
class ExternalIdResponse(BaseModel):
    """External ID response model."""

    id: int
    provider: str
    external_id: str
    instance_name: Optional[str] = None
    created_at: Optional[str] = None


class UserResponse(BaseModel):
    """User response model."""

    id: str
    phone_number: str
    whatsapp_jid: str
    instance_name: str
    display_name: Optional[str] = None
    last_session_name_interaction: Optional[str] = None
    last_agent_user_id: Optional[str] = None
    last_seen_at: Optional[str] = None
    message_count: Optional[int] = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    external_ids: Optional[List[ExternalIdResponse]] = None


class UserListResponse(BaseModel):
    """Response for user list endpoint."""

    users: List[UserResponse]
    total: int
    limit: int
    offset: int


class LinkExternalIdRequest(BaseModel):
    """Request to link an external ID to a user."""

    provider: str = Field(..., description="Provider name: 'whatsapp', 'discord', etc.")
    external_id: str = Field(..., description="External ID from the provider")
    instance_name: Optional[str] = Field(None, description="Instance name (optional)")


class MergeUsersRequest(BaseModel):
    """Request to merge one user into another."""

    source_user_id: str = Field(..., description="User ID to merge FROM (will be deleted)")


class MergeUsersResponse(BaseModel):
    """Response from merge operation."""

    target_user_id: str
    source_user_id: str
    external_ids_transferred: int
    message_count_added: int


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List Users",
    description="List all users with optional filtering by instance or provider",
)
async def list_users(
    instance_name: Optional[str] = None,
    provider: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    List all users with optional filtering.

    - **instance_name**: Filter by instance
    - **provider**: Filter by external ID provider (e.g., 'discord', 'whatsapp')
    - **limit**: Max results (default 100)
    - **offset**: Pagination offset
    """
    try:
        users = user_service.get_all_users(
            db=db,
            instance_name=instance_name,
            provider=provider,
            limit=limit,
            offset=offset,
        )

        # Get total count (without pagination)
        query = db.query(User)
        if instance_name:
            query = query.filter(User.instance_name == instance_name)
        if provider:
            query = query.join(UserExternalId).filter(UserExternalId.provider == provider)
        total = query.count()

        return UserListResponse(
            users=[
                UserResponse(
                    id=u.id,
                    phone_number=u.phone_number,
                    whatsapp_jid=u.whatsapp_jid,
                    instance_name=u.instance_name,
                    display_name=u.display_name,
                    last_session_name_interaction=u.last_session_name_interaction,
                    last_agent_user_id=u.last_agent_user_id,
                    last_seen_at=u.last_seen_at.isoformat() if u.last_seen_at else None,
                    message_count=u.message_count,
                    created_at=u.created_at.isoformat() if u.created_at else None,
                    updated_at=u.updated_at.isoformat() if u.updated_at else None,
                )
                for u in users
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Failed to list users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}",
        )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get User",
    description="Get user details including all external IDs",
)
async def get_user(
    user_id: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get detailed user information including all linked external IDs.
    """
    try:
        user_data = user_service.get_user_with_external_ids(user_id, db)

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        return UserResponse(
            id=user_data["id"],
            phone_number=user_data["phone_number"],
            whatsapp_jid=user_data["whatsapp_jid"],
            instance_name=user_data["instance_name"],
            display_name=user_data["display_name"],
            last_session_name_interaction=user_data["last_session_name_interaction"],
            last_agent_user_id=user_data["last_agent_user_id"],
            last_seen_at=user_data["last_seen_at"],
            message_count=user_data["message_count"],
            created_at=user_data["created_at"],
            updated_at=user_data["updated_at"],
            external_ids=[
                ExternalIdResponse(
                    id=ext["id"],
                    provider=ext["provider"],
                    external_id=ext["external_id"],
                    instance_name=ext["instance_name"],
                    created_at=ext["created_at"],
                )
                for ext in user_data["external_ids"]
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}",
        )


@router.post(
    "/users/{user_id}/link",
    response_model=UserResponse,
    summary="Link External ID",
    description="Link an external ID (Discord, WhatsApp, etc.) to a user",
)
async def link_external_id(
    user_id: str,
    request: LinkExternalIdRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Link an external provider ID to a user.

    This is used to unify identities across platforms.
    For example, link a Discord user ID to an existing WhatsApp user.
    """
    try:
        # Check user exists
        user = user_service.get_user_by_id(user_id, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        # Link external ID
        user_service.link_external_id(
            user_id=user_id,
            provider=request.provider,
            external_id=request.external_id,
            instance_name=request.instance_name,
            db=db,
        )

        # Return updated user
        user_data = user_service.get_user_with_external_ids(user_id, db)

        return UserResponse(
            id=user_data["id"],
            phone_number=user_data["phone_number"],
            whatsapp_jid=user_data["whatsapp_jid"],
            instance_name=user_data["instance_name"],
            display_name=user_data["display_name"],
            last_session_name_interaction=user_data["last_session_name_interaction"],
            last_agent_user_id=user_data["last_agent_user_id"],
            last_seen_at=user_data["last_seen_at"],
            message_count=user_data["message_count"],
            created_at=user_data["created_at"],
            updated_at=user_data["updated_at"],
            external_ids=[
                ExternalIdResponse(
                    id=ext["id"],
                    provider=ext["provider"],
                    external_id=ext["external_id"],
                    instance_name=ext["instance_name"],
                    created_at=ext["created_at"],
                )
                for ext in user_data["external_ids"]
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to link external ID to user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link external ID: {str(e)}",
        )


@router.post(
    "/users/{user_id}/merge",
    response_model=MergeUsersResponse,
    summary="Merge Users",
    description="Merge another user into this user (unify identities)",
)
async def merge_users(
    user_id: str,
    request: MergeUsersRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Merge source user into target user.

    All external IDs from source are transferred to target.
    Source user is deleted after merge.

    Use this to unify users when you discover they're the same person
    (e.g., same person using WhatsApp and Discord).
    """
    try:
        stats = user_service.merge_users(
            target_user_id=user_id,
            source_user_id=request.source_user_id,
            db=db,
        )

        return MergeUsersResponse(**stats)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to merge users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge users: {str(e)}",
        )


@router.delete(
    "/users/{user_id}",
    summary="Delete User",
    description="Delete a user and all their external IDs",
)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Delete a user and all their linked external IDs.
    """
    try:
        deleted = user_service.delete_user(user_id, db)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        return {"message": f"User {user_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}",
        )
