# src/api/routes/omni.py
"""
Omni multi-channel API endpoints.
Provides consistent access to contacts, chats, and channel information across all supported channels.
"""

import logging
from typing import Optional, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.api.deps import get_database, verify_api_key, get_instance_by_name
from src.api.schemas.omni import (
    OmniContactsResponse,
    OmniChatsResponse,
    OmniChannelsResponse,
    OmniMessagesResponse,
    OmniContact,
    OmniChat,
    OmniChatType,
    OmniMessage,
    OmniMessageType,
    MessageDeliveryStatus,
    ChannelType,
    ValidateRecipientRequest,
    ValidateRecipientResponse,
    RecipientValidationResult,
    RecipientProfile,
)
from src.services.chat_id_resolver import ChatIdResolver
from src.db.models import InstanceConfig
from src.db.trace_models import OmniMessageRecord, OmniChatRecord
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
except (ImportError, AttributeError) as e:
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


def _get_chats_from_local(
    db: Session,
    instance_name: str,
    channel_type: str,
    page: int = 1,
    page_size: int = 50,
    chat_type_filter: Optional[str] = None,
) -> Tuple[List[OmniChat], int]:
    """
    Get chats from local omni_chats table.

    Uses pre-synced chat metadata for fast queries.
    Run chat_sync_service.sync_chats_for_instance() to populate/refresh data.
    """
    # Build query from omni_chats table
    query = db.query(OmniChatRecord).filter(
        OmniChatRecord.instance_name == instance_name,
        OmniChatRecord.message_count > 0,  # Only chats with messages
    )

    # Apply chat type filter
    if chat_type_filter:
        query = query.filter(OmniChatRecord.chat_type == chat_type_filter)

    # Get total count
    total_count = query.count()

    # Apply pagination and ordering by last message
    chat_records = (
        query.order_by(desc(OmniChatRecord.last_message_at)).offset((page - 1) * page_size).limit(page_size).all()
    )

    # Convert to OmniChat objects
    chats = []
    for record in chat_records:
        # Map chat_type string to enum
        if record.chat_type == "group":
            chat_type = OmniChatType.GROUP
        elif record.chat_type == "channel":
            chat_type = OmniChatType.CHANNEL
        else:
            chat_type = OmniChatType.DIRECT

        chats.append(
            OmniChat(
                id=record.chat_id,
                name=record.name or record.chat_id,
                chat_type=chat_type,
                channel_type=ChannelType(channel_type),
                instance_name=instance_name,
                participant_count=record.participant_count,
                is_muted=record.is_muted,
                is_archived=record.is_archived,
                is_pinned=record.is_pinned,
                unread_count=record.unread_count,
                skip_media_processing=record.skip_media_processing,
                processing_note=record.processing_note,
                last_message_at=record.last_message_at,
                channel_data={
                    "message_count": record.message_count,
                    "last_message_preview": record.last_message_preview,
                    "contact_phone": record.contact_phone,
                },
            )
        )

    return chats, total_count


def _get_messages_from_local(
    db: Session,
    instance_name: str,
    chat_id: str,
    channel_type: str,
    page: int = 1,
    page_size: int = 50,
    unified: bool = True,
) -> Tuple[List[OmniMessage], int]:
    """
    Get messages from local omni_messages table.

    Args:
        unified: If True, uses canonical_chat_id for merged conversations
    """
    query = db.query(OmniMessageRecord).filter(OmniMessageRecord.instance_name == instance_name)

    # Filter by chat_id - optionally use canonical for unified queries
    if unified:
        resolver = ChatIdResolver(db)
        canonical_id = resolver.get_canonical_id(instance_name, chat_id)
        query = query.filter(OmniMessageRecord.canonical_chat_id == canonical_id)
    else:
        query = query.filter(OmniMessageRecord.chat_id == chat_id)

    # Get total count
    total_count = query.count()

    # Apply pagination and ordering (newest first)
    message_records = (
        query.order_by(desc(OmniMessageRecord.message_timestamp)).offset((page - 1) * page_size).limit(page_size).all()
    )

    # Map message type string to enum
    type_map = {
        "text": OmniMessageType.TEXT,
        "image": OmniMessageType.IMAGE,
        "video": OmniMessageType.VIDEO,
        "audio": OmniMessageType.AUDIO,
        "document": OmniMessageType.DOCUMENT,
        "sticker": OmniMessageType.STICKER,
        "contact": OmniMessageType.CONTACT,
        "location": OmniMessageType.LOCATION,
        "reaction": OmniMessageType.REACTION,
        "system": OmniMessageType.SYSTEM,
    }

    # Map delivery status
    status_map = {
        "pending": MessageDeliveryStatus.PENDING,
        "sent": MessageDeliveryStatus.SENT,
        "delivered": MessageDeliveryStatus.DELIVERED,
        "read": MessageDeliveryStatus.READ,
        "failed": MessageDeliveryStatus.FAILED,
    }

    # Convert to OmniMessage objects
    messages = []
    for record in message_records:
        msg_type = type_map.get(record.message_type, OmniMessageType.TEXT)
        delivery_status = status_map.get(record.delivery_status, MessageDeliveryStatus.UNKNOWN)

        messages.append(
            OmniMessage(
                id=record.platform_message_id,
                chat_id=record.chat_id,
                sender_id=record.sender_id or (instance_name if record.is_from_me else record.chat_id),
                sender_name=record.sender_name,
                message_type=msg_type,
                text=record.content_text,
                media_url=record.media_url,
                media_mime_type=record.media_mime_type,
                media_size=record.media_size_bytes,
                caption=record.content_text if record.has_media else None,
                is_from_me=record.is_from_me,
                is_forwarded=False,
                is_reply=record.quoted_message_id is not None,
                reply_to_message_id=record.quoted_message_id,
                delivery_status=delivery_status,
                is_read=delivery_status == MessageDeliveryStatus.READ,
                timestamp=record.message_timestamp,
                channel_type=ChannelType(channel_type),
                instance_name=instance_name,
                channel_data={
                    "source": record.source,
                    "canonical_chat_id": record.canonical_chat_id,
                },
            )
        )

    return messages, total_count


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
    has_unread: Optional[bool] = Query(None, description="Filter by unread status (true=has unread, false=no unread)"),
    channel_type: Optional[ChannelType] = Query(None, description="Filter by specific channel type"),
    source: str = Query(
        "local", description="Data source: 'local' (omni_messages, unified) or 'evolution' (Evolution API)"
    ),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get chats from instance in omni format.

    Supports pagination and filtering across all channel types.
    Returns chats in a consistent format regardless of the underlying channel.

    Data Sources:
    - source=local (default): Reads from local omni_messages table with unified conversations
      (merges @lid and @s.whatsapp.net formats using canonical_chat_id)
    - source=evolution: Calls Evolution API directly (legacy behavior)

    Filters:
    - chat_type_filter: Filter by chat type (direct, group, channel, thread)
    - archived: Filter by archived status (evolution source only)
    - has_unread: Filter by unread status (evolution source only)
    """
    try:
        logger.info(
            f"Fetching omni chats for instance '{instance_name}' - page: {page}, size: {page_size}, source: {source}"
        )

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

        # Choose data source
        if source == "local":
            # Read from local omni_messages table (unified conversations)
            chats, total_count = _get_chats_from_local(
                db=db,
                instance_name=instance_name,
                channel_type=instance.channel_type,
                page=page,
                page_size=page_size,
                chat_type_filter=chat_type_filter,
            )
            # Note: archived and has_unread filters not supported for local source
            if archived is not None or has_unread is not None:
                logger.warning("archived and has_unread filters are not supported with source=local")
        else:
            # Use Evolution API (legacy behavior)
            handler = get_omni_handler(instance.channel_type)
            chats, total_count = await handler.get_chats(
                instance=instance,
                page=page,
                page_size=page_size,
                chat_type_filter=chat_type_filter,
                archived=archived,
            )

            # Apply has_unread filter (post-fetch filtering) - only for evolution source
            if has_unread is not None:
                if has_unread:
                    # Only chats with unread messages
                    chats = [c for c in chats if (c.unread_count or 0) > 0]
                else:
                    # Only chats with no unread messages
                    chats = [c for c in chats if (c.unread_count or 0) == 0]
                total_count = len(chats)

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
    page_size: int = Query(50, ge=1, le=1000, description="Items per page (max 1000)"),
    before_message_id: Optional[str] = Query(
        None, description="Message ID to fetch messages before (cursor pagination, evolution only)"
    ),
    source: str = Query("local", description="Data source: 'local' (omni_messages) or 'evolution' (Evolution API)"),
    unified: bool = Query(True, description="Use canonical_chat_id for unified conversations (local source only)"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get messages from a chat in omni format.

    Data Sources:
    - source=local (default): Reads from local omni_messages table
      - Supports unified=true to merge @lid and @s.whatsapp.net conversations
      - Fast, no Evolution API dependency
    - source=evolution: Calls Evolution API directly (legacy)
      - Supports cursor pagination with before_message_id
    """
    try:
        logger.info(
            f"Fetching omni messages for chat '{chat_id}' in instance '{instance_name}' - page: {page}, size: {page_size}, source: {source}"
        )

        # Get instance configuration
        instance = get_instance_by_name(instance_name, db)

        if source == "local":
            # Read from local omni_messages table
            messages, total_count = _get_messages_from_local(
                db=db,
                instance_name=instance_name,
                chat_id=chat_id,
                channel_type=instance.channel_type,
                page=page,
                page_size=page_size,
                unified=unified,
            )
        else:
            # Use Evolution API (legacy behavior)
            handler = get_omni_handler(instance.channel_type)
            messages, total_count = await handler.get_messages(
                instance=instance,
                chat_id=chat_id,
                page=page,
                page_size=page_size,
                before_message_id=before_message_id,
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


@router.post("/{instance_name}/sync")
async def sync_instance_data(
    instance_name: str,
    sync_chats: bool = Query(True, description="Sync chat metadata from evo_Chat"),
    sync_messages: bool = Query(False, description="Sync messages from evo_Message (can be slow)"),
    days: int = Query(7, ge=1, le=365, description="Days of message history to sync"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Sync local data from Evolution API tables.

    Populates omni_chats and omni_messages tables for local-first queries.
    Run this after initial setup or to refresh data.
    """
    from src.services.chat_sync_service import ChatSyncService
    from src.services.message_import import MessageImportService

    try:
        logger.info(f"Starting sync for instance '{instance_name}'")

        # Validate instance exists (raises 404 if not found)
        get_instance_by_name(instance_name, db)

        result = {
            "instance_name": instance_name,
            "chats": None,
            "messages": None,
        }

        # Sync chats
        if sync_chats:
            chat_service = ChatSyncService(db)
            result["chats"] = chat_service.sync_chats_for_instance(instance_name)

        # Sync messages (optional, can be slow)
        if sync_messages:
            msg_service = MessageImportService(db)
            stats = msg_service.import_from_evolution(instance_name, days=days)
            result["messages"] = stats.to_dict()

        logger.info(f"Sync complete for instance '{instance_name}': {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync failed for instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


@router.post("/{instance_name}/validate-recipient", response_model=ValidateRecipientResponse)
async def validate_recipients(
    instance_name: str,
    request: ValidateRecipientRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Validate recipients to check if they are valid and reachable on the channel.

    For WhatsApp: Checks if phone numbers are registered on WhatsApp.
    For Discord: Checks if user IDs exist in the guild.

    This endpoint is useful for:
    - Pre-validating numbers before adding them to cadences/campaigns
    - Checking if a contact is still active on the platform
    - Avoiding message delivery failures

    Args:
        instance_name: Instance to validate against
        request: List of recipient identifiers (phone numbers for WhatsApp)

    Returns:
        Validation results including validity status and profile info if available
    """
    try:
        logger.info(f"Validating {len(request.recipients)} recipients for instance '{instance_name}'")

        # Get instance configuration
        instance = get_instance_by_name(instance_name, db)

        # Get omni handler for instance channel type
        handler = get_omni_handler(instance.channel_type)

        # Validate recipients
        validation_results = await handler.validate_recipients(
            instance=instance,
            recipients=request.recipients,
        )

        # Transform results to response format
        results = []
        for result in validation_results:
            profile = None
            if result.get("profile"):
                profile = RecipientProfile(
                    jid=result["profile"].get("jid"),
                    name=result["profile"].get("name"),
                    lid=result["profile"].get("lid"),
                    avatar_url=result["profile"].get("avatar_url"),
                )

            results.append(
                RecipientValidationResult(
                    recipient=result["recipient"],
                    valid=result["valid"],
                    reason=result.get("reason"),
                    profile=profile,
                )
            )

        valid_count = sum(1 for r in results if r.valid)
        invalid_count = len(results) - valid_count

        logger.info(
            f"Validated {len(results)} recipients for instance '{instance_name}': "
            f"{valid_count} valid, {invalid_count} invalid"
        )

        return ValidateRecipientResponse(
            results=results,
            total_count=len(results),
            valid_count=valid_count,
            invalid_count=invalid_count,
            instance_name=instance_name,
            channel_type=ChannelType(instance.channel_type),
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like instance not found)
        raise
    except Exception as e:
        logger.error(f"Failed to validate recipients for instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate recipients: {str(e)}",
        )


@router.patch(
    "/instances/{instance_name}/chats/{chat_id}/processing",
    summary="Toggle Chat Media Processing",
    description="Enable or disable media processing (transcription, image analysis) for a specific chat",
)
async def toggle_chat_processing(
    instance_name: str,
    chat_id: str,
    skip_media_processing: bool = Query(..., description="Set to true to disable processing, false to enable"),
    processing_note: Optional[str] = Query(
        None, description="Optional note explaining why (e.g., 'Promotions', 'News channel')"
    ),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Toggle media processing for a chat.

    When skip_media_processing is true:
    - Audio messages won't be transcribed
    - Images won't be analyzed
    - Documents won't be processed
    - Chat will be excluded from batch processing jobs

    Useful for promotional groups, news channels, or other high-volume
    chats where media processing isn't needed.
    """
    from src.utils.datetime_utils import datetime_utcnow

    # Find the chat record
    record_id = OmniChatRecord.generate_id(instance_name, chat_id)
    chat_record = db.query(OmniChatRecord).filter(OmniChatRecord.id == record_id).first()

    if not chat_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat {chat_id} not found for instance {instance_name}",
        )

    # Update the flags
    chat_record.skip_media_processing = skip_media_processing
    chat_record.processing_note = processing_note
    chat_record.updated_at = datetime_utcnow()

    db.commit()
    db.refresh(chat_record)

    logger.info(
        f"Updated chat processing for {instance_name}/{chat_id}: skip={skip_media_processing}, note='{processing_note}'"
    )

    return {
        "chat_id": chat_id,
        "instance_name": instance_name,
        "skip_media_processing": chat_record.skip_media_processing,
        "processing_note": chat_record.processing_note,
        "name": chat_record.name,
        "chat_type": chat_record.chat_type,
    }


@router.patch(
    "/instances/{instance_name}/chats/processing/bulk",
    summary="Bulk Toggle Chat Processing",
    description="Enable or disable media processing for multiple chats at once",
)
async def bulk_toggle_chat_processing(
    instance_name: str,
    chat_ids: List[str] = Query(..., description="List of chat IDs to update"),
    skip_media_processing: bool = Query(..., description="Set to true to disable processing, false to enable"),
    processing_note: Optional[str] = Query(None, description="Optional note explaining why"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Bulk toggle media processing for multiple chats.

    Useful for quickly muting all promotional groups or news channels.
    """
    from src.utils.datetime_utils import datetime_utcnow

    updated = []
    not_found = []

    for chat_id in chat_ids:
        record_id = OmniChatRecord.generate_id(instance_name, chat_id)
        chat_record = db.query(OmniChatRecord).filter(OmniChatRecord.id == record_id).first()

        if chat_record:
            chat_record.skip_media_processing = skip_media_processing
            chat_record.processing_note = processing_note
            chat_record.updated_at = datetime_utcnow()
            updated.append(chat_id)
        else:
            not_found.append(chat_id)

    db.commit()

    logger.info(f"Bulk updated chat processing for {instance_name}: {len(updated)} updated, {len(not_found)} not found")

    return {
        "instance_name": instance_name,
        "skip_media_processing": skip_media_processing,
        "processing_note": processing_note,
        "updated_count": len(updated),
        "updated_chat_ids": updated,
        "not_found_count": len(not_found),
        "not_found_chat_ids": not_found,
    }
