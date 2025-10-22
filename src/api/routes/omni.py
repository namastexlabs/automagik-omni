# src/api/routes/omni.py
"""
Omni multi-channel API endpoints.
Provides consistent access to contacts, chats, and channel information across all supported channels.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from src.api.deps import get_database, verify_api_key, get_instance_by_name
from src.api.schemas.omni import (
    OmniContactsResponse,
    OmniChatsResponse,
    OmniChannelsResponse,
    OmniMessagesResponse,
    OmniContact,
    OmniChat,
    ChannelType,
)
from src.db.models import InstanceConfig
from src.channels.base import ChannelHandlerFactory
from src.channels.handlers.whatsapp_chat_handler import WhatsAppChatHandler
from src.channels.omni_base import OmniChannelHandler

router = APIRouter(tags=["Omni Channel Abstraction"])
logger = logging.getLogger(__name__)

# Register omni handlers
ChannelHandlerFactory.register_handler("whatsapp", WhatsAppChatHandler)

# Register Discord handler if available
try:
    from src.channels.handlers.discord_chat_handler import DiscordChatHandler

    ChannelHandlerFactory.register_handler("discord", DiscordChatHandler)
    logger.info("Discord chat handler registered")
except ImportError as e:
    logger.info(f"Discord dependencies not installed. Discord support disabled. ({str(e)})")


def get_omni_handler(channel_type: str) -> OmniChannelHandler:
    """Get omni handler for channel type."""
    try:
        handler = ChannelHandlerFactory.get_handler(channel_type)
        if not isinstance(handler, OmniChannelHandler):
            raise ValueError(f"Handler for {channel_type} does not support omni operations")
        return handler
    except Exception as e:
        logger.error(f"Failed to get omni handler for {channel_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Omni operations not supported for channel type: {channel_type}",
        )


@router.get("/{instance_name}/contacts", response_model=OmniContactsResponse)
async def get_omni_contacts(
    instance_name: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    search_query: Optional[str] = Query(None, description="Search query for contact names"),
    status_filter: Optional[str] = Query(None, description="Filter by contact status"),
    channel_type: Optional[ChannelType] = Query(None, description="Filter by specific channel type"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get contacts from instance in omni format.

    Supports pagination, search, and filtering across all channel types.
    Returns contacts in a consistent format regardless of the underlying channel.
    """
    try:
        logger.info(f"Fetching omni contacts for instance '{instance_name}' - page: {page}, size: {page_size}")

        # Get instance configuration
        instance = get_instance_by_name(instance_name, db)

        # If channel_type filter is provided, ensure it matches instance channel
        if channel_type and instance.channel_type != channel_type.value:
            return OmniContactsResponse(
                contacts=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_more=False,
                instance_name=instance_name,
                channel_type=channel_type,
                partial_errors=[
                    {
                        "instance_name": instance_name,
                        "channel_type": instance.channel_type,
                        "error_code": "channel_type_mismatch",
                        "message": f"Instance {instance_name} is {instance.channel_type}, not {channel_type.value}",
                    }
                ],
            )

        # Get omni handler for instance channel type
        handler = get_omni_handler(instance.channel_type)

        # Fetch contacts
        contacts, total_count = await handler.get_contacts(
            instance=instance,
            page=page,
            page_size=page_size,
            search_query=search_query,
            status_filter=status_filter,
        )

        # Calculate pagination info
        has_more = (page * page_size) < total_count

        logger.info(
            f"Successfully fetched {len(contacts)} contacts (total: {total_count}) for instance '{instance_name}'"
        )

        return OmniContactsResponse(
            contacts=contacts,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=has_more,
            instance_name=instance_name,
            channel_type=ChannelType(instance.channel_type),
            partial_errors=[],
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like instance not found)
        raise
    except Exception as e:
        logger.error(f"Failed to fetch omni contacts for instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch contacts: {str(e)}",
        )


@router.get("/{instance_name}/chats", response_model=OmniChatsResponse)
async def get_omni_chats(
    instance_name: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    chat_type_filter: Optional[str] = Query(None, description="Filter by chat type (direct, group, channel, thread)"),
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
    channel_type: Optional[ChannelType] = Query(None, description="Filter by specific channel type"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get chats from instance in omni format.

    Supports pagination and filtering across all channel types.
    Returns chats in a consistent format regardless of the underlying channel.
    """
    try:
        logger.info(f"Fetching omni chats for instance '{instance_name}' - page: {page}, size: {page_size}")

        # Get instance configuration
        instance = get_instance_by_name(instance_name, db)

        # If channel_type filter is provided, ensure it matches instance channel
        if channel_type and instance.channel_type != channel_type.value:
            return OmniChatsResponse(
                chats=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_more=False,
                instance_name=instance_name,
                channel_type=channel_type,
                partial_errors=[
                    {
                        "instance_name": instance_name,
                        "channel_type": instance.channel_type,
                        "error_code": "channel_type_mismatch",
                        "message": f"Instance {instance_name} is {instance.channel_type}, not {channel_type.value}",
                    }
                ],
            )

        # Get omni handler for instance channel type
        handler = get_omni_handler(instance.channel_type)

        # Fetch chats
        chats, total_count = await handler.get_chats(
            instance=instance,
            page=page,
            page_size=page_size,
            chat_type_filter=chat_type_filter,
            archived=archived,
        )

        # Calculate pagination info
        has_more = (page * page_size) < total_count

        logger.info(f"Successfully fetched {len(chats)} chats (total: {total_count}) for instance '{instance_name}'")

        return OmniChatsResponse(
            chats=chats,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=has_more,
            instance_name=instance_name,
            channel_type=ChannelType(instance.channel_type),
            partial_errors=[],
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like instance not found)
        raise
    except Exception as e:
        logger.error(f"Failed to fetch omni chats for instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chats: {str(e)}",
        )


@router.get("/", response_model=OmniChannelsResponse)
async def get_omni_channels(
    channel_type: Optional[ChannelType] = Query(None, description="Filter by specific channel type"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get all channel instances in omni format.

    Returns information about all configured instances across all channel types,
    including their connection status and capabilities.
    """
    try:
        logger.info(f"Fetching omni channels - channel_type filter: {channel_type}")

        # Get all instances from database
        query = db.query(InstanceConfig)
        if channel_type:
            query = query.filter(InstanceConfig.channel_type == channel_type.value)
        instances = query.all()

        channels = []
        partial_errors = []
        healthy_count = 0

        for instance in instances:
            try:
                # Get omni handler for instance channel type
                handler = get_omni_handler(instance.channel_type)

                # Get channel info
                channel_info = await handler.get_channel_info(instance)
                channels.append(channel_info)

                if channel_info.is_healthy:
                    healthy_count += 1

            except Exception as e:
                logger.warning(f"Failed to get channel info for instance '{instance.name}': {e}")
                partial_errors.append(
                    {
                        "instance_name": instance.name,
                        "channel_type": instance.channel_type,
                        "error_code": "channel_info_error",
                        "message": f"Failed to get channel info: {str(e)}",
                    }
                )

        logger.info(f"Successfully fetched {len(channels)} channels ({healthy_count} healthy)")

        return OmniChannelsResponse(
            channels=channels,
            total_count=len(channels),
            healthy_count=healthy_count,
            partial_errors=partial_errors,
        )

    except Exception as e:
        logger.error(f"Failed to fetch omni channels: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch channels: {str(e)}",
        )


@router.get("/{instance_name}/contacts/{contact_id}", response_model=OmniContact)
async def get_omni_contact_by_id(
    instance_name: str,
    contact_id: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get a specific contact by ID in omni format.
    """
    try:
        logger.info(f"Fetching omni contact '{contact_id}' for instance '{instance_name}'")

        # Get instance configuration
        instance = get_instance_by_name(instance_name, db)

        # Get omni handler for instance channel type
        handler = get_omni_handler(instance.channel_type)

        # Fetch contact
        contact = await handler.get_contact_by_id(instance, contact_id)

        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contact '{contact_id}' not found in instance '{instance_name}'",
            )

        logger.info(f"Successfully fetched contact '{contact_id}' for instance '{instance_name}'")
        return contact

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to fetch omni contact '{contact_id}' for instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch contact: {str(e)}",
        )


@router.get("/{instance_name}/chats/{chat_id}", response_model=OmniChat)
async def get_omni_chat_by_id(
    instance_name: str,
    chat_id: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get a specific chat by ID in omni format.
    """
    try:
        logger.info(f"Fetching omni chat '{chat_id}' for instance '{instance_name}'")

        # Get instance configuration
        instance = get_instance_by_name(instance_name, db)

        # Get omni handler for instance channel type
        handler = get_omni_handler(instance.channel_type)

        # Fetch chat
        chat = await handler.get_chat_by_id(instance, chat_id)

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat '{chat_id}' not found in instance '{instance_name}'",
            )

        logger.info(f"Successfully fetched chat '{chat_id}' for instance '{instance_name}'")
        return chat

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to fetch omni chat '{chat_id}' for instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat: {str(e)}",
        )


@router.get("/{instance_name}/chats/{chat_id}/messages", response_model=OmniMessagesResponse)
async def get_omni_chat_messages(
    instance_name: str,
    chat_id: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    before_message_id: Optional[str] = Query(
        None, description="Message ID to fetch messages before (cursor pagination)"
    ),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get messages from a chat in omni format.

    Supports pagination and filtering across all channel types.
    Returns messages in a consistent format regardless of the underlying channel.
    """
    try:
        logger.info(
            f"Fetching omni messages for chat '{chat_id}' in instance '{instance_name}' - page: {page}, size: {page_size}"
        )

        # Get instance configuration
        instance = get_instance_by_name(instance_name, db)

        # Get omni handler for instance channel type
        handler = get_omni_handler(instance.channel_type)

        # Fetch messages
        messages, total_count = await handler.get_messages(
            instance=instance, chat_id=chat_id, page=page, page_size=page_size, before_message_id=before_message_id
        )

        # Calculate pagination info
        has_more = (page * page_size) < total_count

        logger.info(
            f"Successfully fetched {len(messages)} messages (total: {total_count}) for chat '{chat_id}' in instance '{instance_name}'"
        )

        return OmniMessagesResponse(
            messages=messages,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=has_more,
            instance_name=instance_name,
            chat_id=chat_id,
            channel_type=ChannelType(instance.channel_type),
            partial_errors=[],
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like instance not found)
        raise
    except Exception as e:
        logger.error(f"Failed to fetch omni messages for chat '{chat_id}' in instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch messages: {str(e)}",
        )
