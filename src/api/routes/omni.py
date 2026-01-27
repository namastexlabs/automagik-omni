# src/api/routes/omni.py
"""
Omni multi-channel API endpoints.
Provides consistent access to contacts, chats, and channel information across all supported channels.
"""

import logging
from typing import Optional, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from src.api.deps import get_database, verify_api_key, get_instance_by_name
from src.api.schemas.omni import (
    OmniContactsResponse,
    OmniChatsResponse,
    OmniChannelsResponse,
    OmniMessagesResponse,
    OmniContact,
    OmniChat,
    OmniChatType,
    ChannelType,
    ValidateRecipientRequest,
    ValidateRecipientResponse,
    RecipientValidationResult,
    RecipientProfile,
)
from src.db.models import InstanceConfig
from src.db.trace_models import OmniMessageRecord
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


def _get_chat_names_from_evo(db: Session, instance_name: str, chat_ids: List[str]) -> dict:
    """Get chat names from evo_Chat table (has group names)."""
    from sqlalchemy import text

    if not chat_ids:
        return {}

    try:
        result = db.execute(
            text("""
                SELECT c."remoteJid", c.name
                FROM "evo_Chat" c
                JOIN "evo_Instance" i ON c."instanceId" = i.id
                WHERE i.name = :instance_name
                AND c."remoteJid" = ANY(:chat_ids)
            """),
            {"instance_name": instance_name, "chat_ids": chat_ids},
        ).fetchall()
        return {r[0]: r[1] for r in result if r[1] and r[1] != "None"}
    except Exception as e:
        logger.warning(f"Failed to get chat names from evo_Chat: {e}")
        return {}


def _get_chats_from_local(
    db: Session,
    instance_name: str,
    channel_type: str,
    page: int = 1,
    page_size: int = 50,
    chat_type_filter: Optional[str] = None,
) -> Tuple[List[OmniChat], int]:
    """
    Get chats from local omni_messages table using canonical_chat_id for unified conversations.

    Aggregates messages by canonical_chat_id to provide unified chat list.
    Uses evo_Chat for group names, sender_name for direct chat names.
    """
    # Subquery to get latest message and stats per canonical chat
    # Use canonical_chat_id if set, otherwise fall back to chat_id
    chat_stats = (
        db.query(
            func.coalesce(OmniMessageRecord.canonical_chat_id, OmniMessageRecord.chat_id).label("chat_id"),
            func.max(OmniMessageRecord.message_timestamp).label("last_message_at"),
            func.count(OmniMessageRecord.id).label("message_count"),
        )
        .filter(OmniMessageRecord.instance_name == instance_name)
        .group_by(func.coalesce(OmniMessageRecord.canonical_chat_id, OmniMessageRecord.chat_id))
    )

    # Apply chat type filter
    if chat_type_filter:
        if chat_type_filter == "group":
            chat_stats = chat_stats.having(
                func.coalesce(OmniMessageRecord.canonical_chat_id, OmniMessageRecord.chat_id).like("%@g.us")
            )
        elif chat_type_filter == "direct":
            chat_stats = chat_stats.having(
                ~func.coalesce(OmniMessageRecord.canonical_chat_id, OmniMessageRecord.chat_id).like("%@g.us")
            )

    # Get total count
    total_count = chat_stats.count()

    # Apply pagination and ordering
    chat_results = chat_stats.order_by(desc("last_message_at")).offset((page - 1) * page_size).limit(page_size).all()

    # Get chat IDs for name lookup
    chat_ids = [row.chat_id for row in chat_results if row.chat_id]

    # Get group names from evo_Chat
    evo_names = _get_chat_names_from_evo(db, instance_name, chat_ids)

    # Get contact names for direct chats from inbound messages
    direct_chat_ids = [cid for cid in chat_ids if not cid.endswith("@g.us")]
    contact_names = {}
    if direct_chat_ids:
        for chat_id in direct_chat_ids:
            recent_msg = (
                db.query(OmniMessageRecord.sender_name)
                .filter(
                    OmniMessageRecord.instance_name == instance_name,
                    func.coalesce(OmniMessageRecord.canonical_chat_id, OmniMessageRecord.chat_id) == chat_id,
                    OmniMessageRecord.is_from_me == False,  # noqa: E712
                    OmniMessageRecord.sender_name.isnot(None),
                    OmniMessageRecord.sender_name != "",
                )
                .order_by(OmniMessageRecord.message_timestamp.desc())
                .first()
            )
            if recent_msg and recent_msg[0]:
                contact_names[chat_id] = recent_msg[0]

    # Build OmniChat objects
    chats = []
    for row in chat_results:
        chat_id = row.chat_id
        is_group = chat_id.endswith("@g.us") if chat_id else False
        is_broadcast = chat_id.endswith("@broadcast") if chat_id else False

        # Determine chat type
        if is_group:
            chat_type = OmniChatType.GROUP
        elif is_broadcast:
            chat_type = OmniChatType.CHANNEL
        else:
            chat_type = OmniChatType.DIRECT

        # Get chat name from appropriate source
        if is_group or is_broadcast:
            # Use evo_Chat name for groups/broadcasts
            chat_name = evo_names.get(chat_id, chat_id)
        else:
            # Use contact name from messages for direct chats
            chat_name = contact_names.get(chat_id, chat_id)

        chats.append(
            OmniChat(
                id=chat_id,
                name=chat_name,
                chat_type=chat_type,
                channel_type=ChannelType(channel_type),
                instance_name=instance_name,
                participant_count=None,  # Would need separate query for groups
                is_muted=False,
                is_archived=False,
                is_pinned=False,
                unread_count=None,  # Not tracked in omni_messages
                last_message_at=row.last_message_at,
                channel_data={"message_count": row.message_count},
            )
        )

    return chats, total_count


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
