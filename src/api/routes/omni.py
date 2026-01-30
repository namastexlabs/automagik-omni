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
    MediaResponse,
    ProfilePictureResponse,
    GroupParticipant,
    GroupParticipantRole,
    GroupInfo,
    GroupsResponse,
    GroupParticipantsResponse,
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

    Deduplication: WhatsApp has two JID formats for the same contact:
    - @lid (Linked ID) - new multi-device format
    - @s.whatsapp.net (phone number) - traditional format
    We prefer phone number format and filter out @lid when both exist for same contact name.
    """
    # Build query from omni_chats table
    query = db.query(OmniChatRecord).filter(
        OmniChatRecord.instance_name == instance_name,
        OmniChatRecord.message_count > 0,  # Only chats with messages
    )

    # Apply chat type filter
    if chat_type_filter:
        query = query.filter(OmniChatRecord.chat_type == chat_type_filter)

    # Get all matching records (we'll deduplicate in Python for simplicity)
    all_records = query.order_by(desc(OmniChatRecord.last_message_at)).all()

    # Deduplicate @lid vs @s.whatsapp.net chats
    # Strategy: Keep the version with the BEST name, preferring real names over phone numbers
    #
    # Build a map of canonical_chat_id -> best record
    best_by_canonical: dict[str, OmniChatRecord] = {}

    def has_real_name(record: OmniChatRecord) -> bool:
        """Check if record has a real contact name (not phone number or JID)."""
        if not record.name:
            return False
        # Name is just the chat_id or contains @ (JID format)
        if "@" in record.name:
            return False
        # Name is all digits (phone number)
        if record.name.replace("+", "").isdigit():
            return False
        return True

    for record in all_records:
        # Use canonical_chat_id as the dedup key, fallback to chat_id
        key = record.canonical_chat_id or record.chat_id

        if key not in best_by_canonical:
            best_by_canonical[key] = record
        else:
            existing = best_by_canonical[key]
            # Prefer the record with a real name
            existing_has_name = has_real_name(existing)
            current_has_name = has_real_name(record)

            if current_has_name and not existing_has_name:
                # Current has better name, use it
                best_by_canonical[key] = record
            elif current_has_name == existing_has_name:
                # Same name quality, prefer more messages
                if (record.message_count or 0) > (existing.message_count or 0):
                    best_by_canonical[key] = record

    # Filter out records that aren't the "best" for their canonical ID
    # Also filter out records with no proper name at all
    deduplicated_records = []
    for record in all_records:
        key = record.canonical_chat_id or record.chat_id

        # Skip if this isn't the best record for this canonical ID
        if best_by_canonical.get(key) != record:
            continue

        # Skip records with JID as name (no useful identifier)
        if record.name and "@lid" in record.name:
            continue

        deduplicated_records.append(record)

    # Apply pagination to deduplicated results
    total_count = len(deduplicated_records)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    chat_records = deduplicated_records[start_idx:end_idx]

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

        # Use canonical_chat_id as the ID (the phone number version)
        # but keep the name from whichever record has the best name
        chat_id_to_use = record.canonical_chat_id or record.chat_id
        chats.append(
            OmniChat(
                id=chat_id_to_use,
                name=record.name or chat_id_to_use,
                chat_type=chat_type,
                channel_type=ChannelType(channel_type),
                instance_name=instance_name,
                participant_count=record.participant_count,
                is_muted=record.is_muted,
                is_archived=record.is_archived,
                is_pinned=record.is_pinned,
                unread_count=record.unread_count,
                avatar_url=record.avatar_url,
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


def _extract_reaction_target_id(record: OmniMessageRecord) -> Optional[str]:
    """Extract the target message ID from a reaction message's content_raw."""
    try:
        content_raw = record.get_content_raw()
        if content_raw and "reactionMessage" in content_raw:
            reaction_msg = content_raw.get("reactionMessage", {})
            key = reaction_msg.get("key", {})
            return key.get("id")
    except Exception:
        pass
    return None


def _resolve_mentions(
    db: Session,
    instance_name: str,
    text: Optional[str],
    context_info: Optional[dict],
) -> Tuple[Optional[str], list]:
    """
    Resolve mentions in message text to display names.

    Args:
        db: Database session
        instance_name: Instance name
        text: Original message text
        context_info: Message context info containing mentionedJid

    Returns:
        Tuple of (text_display, mentions_list)
        - text_display: Text with @JID replaced by @Name
        - mentions_list: List of {jid, name, phone} dicts
    """
    from src.db.trace_models import ChatIdMapping

    if not text or not context_info:
        return text, []

    mentioned_jids = context_info.get("mentionedJid", [])
    if not mentioned_jids:
        return text, []

    mentions = []
    text_display = text

    for jid in mentioned_jids:
        if not jid:
            continue

        # Extract the ID part (before @)
        jid_id = jid.split("@")[0] if "@" in jid else jid
        name = None
        phone = None

        # Try to resolve the name
        # 1. Check ChatIdMapping for LID → phone mappings
        if "@lid" in jid:
            mapping = (
                db.query(ChatIdMapping)
                .filter(
                    ChatIdMapping.instance_name == instance_name,
                    ChatIdMapping.alternate_chat_id == jid,
                )
                .first()
            )
            if mapping:
                name = mapping.contact_name
                phone = mapping.phone_number

        # 2. If still no name, check for phone format
        if not name and "@s.whatsapp.net" in jid:
            phone = jid_id
            # Try to find contact name from ChatIdMapping
            mapping = (
                db.query(ChatIdMapping)
                .filter(
                    ChatIdMapping.instance_name == instance_name,
                    ChatIdMapping.canonical_chat_id == jid,
                )
                .first()
            )
            if mapping and mapping.contact_name:
                name = mapping.contact_name

        # 3. If still no name, try to find from sender in messages
        if not name:
            from src.db.trace_models import OmniMessageRecord

            # Look for messages from this sender to get their name
            sender_msg = (
                db.query(OmniMessageRecord.sender_name)
                .filter(
                    OmniMessageRecord.instance_name == instance_name,
                    OmniMessageRecord.sender_id == jid,
                    OmniMessageRecord.sender_name.isnot(None),
                )
                .first()
            )
            if sender_msg and sender_msg[0]:
                name = sender_msg[0]

        # Build mention object
        mentions.append(
            {
                "jid": jid,
                "name": name,
                "phone": phone,
            }
        )

        # Replace in text_display: @jid_id → @Name (or @phone if no name)
        display_name = name or (f"+{phone}" if phone else jid_id)
        # Match patterns like @123456789 (the ID without domain)
        text_display = text_display.replace(f"@{jid_id}", f"@{display_name}")

    return text_display, mentions


def _resolve_sender_name(
    db: Session,
    instance_name: str,
    jid: str,
) -> Optional[str]:
    """
    Resolve a JID to a display name.

    Args:
        db: Database session
        instance_name: Instance name
        jid: The WhatsApp JID to resolve

    Returns:
        Display name if found, None otherwise
    """
    from src.db.trace_models import ChatIdMapping, OmniMessageRecord

    if not jid:
        return None

    # 1. Check ChatIdMapping for LID → phone mappings
    if "@lid" in jid:
        mapping = (
            db.query(ChatIdMapping)
            .filter(
                ChatIdMapping.instance_name == instance_name,
                ChatIdMapping.alternate_chat_id == jid,
            )
            .first()
        )
        if mapping and mapping.contact_name:
            return mapping.contact_name

    # 2. Check for phone format
    if "@s.whatsapp.net" in jid:
        mapping = (
            db.query(ChatIdMapping)
            .filter(
                ChatIdMapping.instance_name == instance_name,
                ChatIdMapping.canonical_chat_id == jid,
            )
            .first()
        )
        if mapping and mapping.contact_name:
            return mapping.contact_name

    # 3. Try to find from sender in messages
    sender_msg = (
        db.query(OmniMessageRecord.sender_name)
        .filter(
            OmniMessageRecord.instance_name == instance_name,
            OmniMessageRecord.sender_id == jid,
            OmniMessageRecord.sender_name.isnot(None),
        )
        .first()
    )
    if sender_msg and sender_msg[0]:
        return sender_msg[0]

    return None


def _build_channel_data(record: "OmniMessageRecord") -> dict:
    """
    Build channel_data dict for OmniMessage response.
    Includes additional data for specific message types like contacts.
    """
    data = {
        "source": record.source,
        "canonical_chat_id": record.canonical_chat_id,
    }

    # For contact messages, include the vcard data
    if record.message_type == "contact":
        content_raw = record.get_content_raw()
        if content_raw and "contactMessage" in content_raw:
            data["contactMessage"] = content_raw["contactMessage"]

    return data


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

    Reactions are aggregated and attached to their target messages rather than
    being displayed as separate messages.

    Media content (transcripts, descriptions) is fetched and attached to messages.
    """
    from src.api.schemas.omni import MessageReaction, MediaContent as MediaContentSchema, Mention
    from src.db.trace_models import MediaContent

    query = db.query(OmniMessageRecord).filter(OmniMessageRecord.instance_name == instance_name)

    # Filter by chat_id - optionally use canonical for unified queries
    if unified:
        resolver = ChatIdResolver(db)
        canonical_id = resolver.get_canonical_id(instance_name, chat_id)
        query = query.filter(OmniMessageRecord.canonical_chat_id == canonical_id)
    else:
        query = query.filter(OmniMessageRecord.chat_id == chat_id)

    # Get all messages (we need to process reactions before pagination)
    all_records = query.order_by(desc(OmniMessageRecord.message_timestamp)).all()

    # Separate reactions from regular messages and build reaction map
    reactions_by_target: dict[str, list] = {}
    regular_records = []

    for record in all_records:
        if record.message_type == "reaction":
            # Extract target message ID from reaction
            target_id = _extract_reaction_target_id(record)
            if target_id:
                if target_id not in reactions_by_target:
                    reactions_by_target[target_id] = []
                reactions_by_target[target_id].append(
                    {
                        "emoji": record.content_text or "👍",
                        "sender_id": record.sender_id,
                        "sender_name": record.sender_name,
                        "timestamp": record.message_timestamp,
                    }
                )
        else:
            regular_records.append(record)

    # Count and paginate non-reaction messages
    total_count = len(regular_records)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_records = regular_records[start_idx:end_idx]

    # Fetch media content (transcripts, descriptions) for paginated messages
    message_ids = [r.platform_message_id for r in paginated_records]
    media_content_records = (
        db.query(MediaContent)
        .filter(
            MediaContent.instance_name == instance_name,
            MediaContent.original_message_id.in_(message_ids),
            MediaContent.content_type.in_(
                ["audio_transcript", "image_description", "video_description", "document_content"]
            ),
        )
        .all()
    )

    # Build media content map by message ID
    media_content_by_msg: dict[str, MediaContent] = {}
    for mc in media_content_records:
        # Keep the most recent content if multiple exist
        if mc.original_message_id not in media_content_by_msg:
            media_content_by_msg[mc.original_message_id] = mc

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
    for record in paginated_records:
        msg_type = type_map.get(record.message_type, OmniMessageType.TEXT)
        delivery_status = status_map.get(record.delivery_status, MessageDeliveryStatus.UNKNOWN)

        # Get reactions for this message
        message_reactions = []
        if record.platform_message_id in reactions_by_target:
            for r in reactions_by_target[record.platform_message_id]:
                message_reactions.append(
                    MessageReaction(
                        emoji=r["emoji"],
                        sender_id=r["sender_id"],
                        sender_name=r["sender_name"],
                        timestamp=r["timestamp"],
                    )
                )

        # Get media content (transcript/description) if available
        media_content = None
        if record.platform_message_id in media_content_by_msg:
            mc = media_content_by_msg[record.platform_message_id]
            media_content = MediaContentSchema(
                id=mc.id,
                content_type=mc.content_type,
                content=mc.content or "",
                processor_name=mc.processor_name,
                processor_model=mc.processor_model,
                confidence_score=mc.confidence_score,
                processed_at=mc.processed_at,
            )

        # Resolve mentions in text
        context_info = record.get_context_info()
        text_display, mentions_data = _resolve_mentions(db, instance_name, record.content_text, context_info)
        mentions = [Mention(jid=m["jid"], name=m["name"], phone=m["phone"]) for m in mentions_data]

        # Extract quoted message details from context_info
        quoted_text = None
        quoted_sender_id = None
        quoted_sender_name = None
        quoted_message_type = None
        if record.quoted_message_id and context_info:
            quoted_text = context_info.get("quotedText")
            quoted_sender_id = context_info.get("participant")
            # quotedType can be int (0=text) or string - convert to string
            raw_quoted_type = context_info.get("quotedType")
            if raw_quoted_type is not None:
                quoted_message_type = str(raw_quoted_type)
            # Try to resolve quoted sender name
            if quoted_sender_id:
                quoted_sender_name = _resolve_sender_name(db, instance_name, quoted_sender_id)

        messages.append(
            OmniMessage(
                id=record.platform_message_id,
                chat_id=record.chat_id,
                sender_id=record.sender_id or (instance_name if record.is_from_me else record.chat_id),
                sender_name=record.sender_name,
                message_type=msg_type,
                text=record.content_text,
                text_display=text_display,
                mentions=mentions,
                media_url=record.media_url,
                media_mime_type=record.media_mime_type,
                media_size=record.media_size_bytes,
                media_local_path=record.media_local_path,
                media_status=record.media_status,
                caption=record.content_text if record.has_media else None,
                is_from_me=record.is_from_me,
                is_forwarded=False,
                is_reply=record.quoted_message_id is not None,
                reply_to_message_id=record.quoted_message_id,
                quoted_text=quoted_text,
                quoted_sender_id=quoted_sender_id,
                quoted_sender_name=quoted_sender_name,
                quoted_message_type=quoted_message_type,
                reactions=message_reactions,
                media_content=media_content,
                delivery_status=delivery_status,
                is_read=delivery_status == MessageDeliveryStatus.READ,
                timestamp=record.message_timestamp,
                channel_type=ChannelType(channel_type),
                instance_name=instance_name,
                channel_data=_build_channel_data(record),
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


@router.get("/{instance_name}/messages/{message_id}/media")
async def get_message_media(
    instance_name: str,
    message_id: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get media content for a message.

    This endpoint serves media from local storage if available, or downloads it first.
    Falls back to Evolution API if local download fails.

    Returns base64-encoded media content that can be displayed in the UI.
    """
    import base64
    from pathlib import Path
    from src.services.media_download import MediaDownloadService

    try:
        logger.info(f"Fetching media for message '{message_id}' in instance '{instance_name}'")

        # Find the message in omni_messages
        message = (
            db.query(OmniMessageRecord)
            .filter(
                OmniMessageRecord.instance_name == instance_name,
                OmniMessageRecord.platform_message_id == message_id,
            )
            .first()
        )

        if not message:
            # Also try by composite ID
            message = (
                db.query(OmniMessageRecord).filter(OmniMessageRecord.id == f"{instance_name}:{message_id}").first()
            )

        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found in instance {instance_name}",
            )

        if not message.has_media:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message does not have media",
            )

        # Check if media is already downloaded locally
        if message.media_status == "downloaded" and message.media_local_path:
            local_path = Path(message.media_local_path)
            if local_path.exists():
                # Serve from local storage
                logger.info(f"Serving media from local storage: {local_path}")
                with open(local_path, "rb") as f:
                    media_data = f.read()

                return MediaResponse(
                    base64=base64.b64encode(media_data).decode("utf-8"),
                    mimetype=message.media_mime_type or "application/octet-stream",
                    fileName=local_path.name,
                    media_status="downloaded",
                    source="local",
                )

        # Try to download the media
        download_service = MediaDownloadService(db)
        result = download_service.download_and_update(message.id)

        if result["success"]:
            # Refresh message from DB to get updated path
            db.refresh(message)

            if message.media_local_path:
                local_path = Path(message.media_local_path)
                if local_path.exists():
                    logger.info(f"Serving freshly downloaded media: {local_path}")
                    with open(local_path, "rb") as f:
                        media_data = f.read()

                    return MediaResponse(
                        base64=base64.b64encode(media_data).decode("utf-8"),
                        mimetype=message.media_mime_type or "application/octet-stream",
                        fileName=local_path.name,
                        media_status="downloaded",
                        source="local",
                    )

        # Local download failed - try Evolution API as fallback
        logger.info(f"Local download failed, trying Evolution API fallback for message {message_id}")

        instance = get_instance_by_name(instance_name, db)
        if instance.evolution_url and instance.evolution_key:
            import requests

            # Call Evolution API getBase64FromMediaMessage
            url = f"{instance.evolution_url}/chat/getBase64FromMediaMessage/{instance_name}"
            headers = {
                "apikey": instance.evolution_key,
                "Content-Type": "application/json",
            }
            payload = {
                "message": {"key": {"id": message_id}},
                "convertToMp4": False,
            }

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    evo_result = response.json()
                    if evo_result and evo_result.get("base64"):
                        logger.info(f"Served media from Evolution API for message {message_id}")
                        return MediaResponse(
                            base64=evo_result["base64"],
                            mimetype=evo_result.get("mimetype", message.media_mime_type or "application/octet-stream"),
                            fileName=evo_result.get("fileName"),
                            media_status=message.media_status or "pending",
                            source="evolution",
                        )
            except Exception as evo_error:
                logger.warning(f"Evolution API fallback failed: {evo_error}")

        # All methods failed
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media not available. Status: {result.get('status', 'unknown')}. Error: {result.get('error', 'Unknown')}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get media for message '{message_id}' in instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get media: {str(e)}",
        )


@router.get("/{instance_name}/profile-picture/{jid}")
async def get_profile_picture(
    instance_name: str,
    jid: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
) -> ProfilePictureResponse:
    """
    Get profile picture URL for a WhatsApp user.

    This endpoint fetches the profile picture URL from Evolution API.
    The result should be cached client-side to avoid repeated API calls.

    Args:
        instance_name: The WhatsApp instance name
        jid: The WhatsApp JID (e.g., "5511999999999@s.whatsapp.net" or participant JID)

    Returns:
        ProfilePictureResponse with the profile picture URL (may be null if not available)
    """
    import requests

    try:
        logger.debug(f"Fetching profile picture for JID '{jid}' in instance '{instance_name}'")

        instance = get_instance_by_name(instance_name, db)
        if not instance.evolution_url or not instance.evolution_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Instance not configured for Evolution API",
            )

        # Call Evolution API fetchProfilePictureUrl
        url = f"{instance.evolution_url}/chat/fetchProfilePictureUrl/{instance_name}"
        headers = {
            "apikey": instance.evolution_key,
            "Content-Type": "application/json",
        }
        payload = {"number": jid}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                evo_result = response.json()
                profile_url = evo_result.get("profilePictureUrl")
                logger.debug(f"Got profile picture for {jid}: {profile_url is not None}")
                return ProfilePictureResponse(
                    jid=jid,
                    profile_picture_url=profile_url,
                    source="evolution",
                )
            else:
                logger.warning(f"Evolution API returned {response.status_code} for profile picture: {response.text}")
                return ProfilePictureResponse(
                    jid=jid,
                    profile_picture_url=None,
                    source="evolution",
                )
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching profile picture for {jid}")
            return ProfilePictureResponse(
                jid=jid,
                profile_picture_url=None,
                source="evolution",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile picture for '{jid}' in instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile picture: {str(e)}",
        )


def _sync_groups_from_evolution(
    db: Session,
    instance: InstanceConfig,
    instance_name: str,
    batch_size: int = 50,
    batch_delay: float = 5.0,
) -> dict:
    """Sync group participants from Evolution API to local database.

    Uses existing groups from omni_chats and fetches participants for each
    using the group/participants endpoint. Processes in batches to avoid
    WhatsApp rate limiting.

    Args:
        db: Database session
        instance: Instance configuration
        instance_name: Name of the instance
        batch_size: Number of groups to process per batch (default: 50)
        batch_delay: Seconds to wait between batches (default: 5.0)

    Returns:
        Dict with sync statistics
    """
    import time
    import requests
    from src.db.trace_models import OmniGroupParticipant
    from src.utils.datetime_utils import datetime_utcnow
    from src.services.settings_service import get_evolution_api_key_global
    from src.config import config

    # Use Evolution API URL from config
    evolution_url = config.get_env("EVOLUTION_API_URL", "http://127.0.0.1:18082")
    evolution_key = get_evolution_api_key_global()

    if not evolution_url or not evolution_key:
        raise Exception("Evolution API not configured")

    headers = {"apikey": evolution_key}
    now = datetime_utcnow()

    # Get groups from local database (already synced via chat sync)
    group_records = (
        db.query(OmniChatRecord)
        .filter(
            OmniChatRecord.instance_name == instance_name,
            OmniChatRecord.chat_type == "group",
        )
        .all()
    )

    total_groups = len(group_records)
    logger.info(f"Syncing participants for {total_groups} groups (batch_size={batch_size}, delay={batch_delay}s)")

    # Clear existing participants for this instance (full refresh)
    db.query(OmniGroupParticipant).filter(OmniGroupParticipant.instance_name == instance_name).delete()
    db.commit()

    # Stats
    synced_count = 0
    success_count = 0
    failed_count = 0
    timeout_count = 0

    # Process in batches
    for batch_num, batch_start in enumerate(range(0, total_groups, batch_size)):
        batch_end = min(batch_start + batch_size, total_groups)
        batch = group_records[batch_start:batch_end]

        logger.info(f"Processing batch {batch_num + 1}: groups {batch_start + 1}-{batch_end} of {total_groups}")

        for record in batch:
            group_id = record.chat_id
            try:
                # Call Evolution API group/participants
                url = f"{evolution_url}/group/participants/{instance_name}"
                params = {"groupJid": group_id}
                response = requests.get(url, headers=headers, params=params, timeout=15)

                if response.status_code != 200:
                    logger.warning(f"Failed to get participants for {group_id}: {response.status_code}")
                    failed_count += 1
                    continue

                data = response.json()
                participants = data.get("participants", data) if isinstance(data, dict) else data

                # Update participant count
                record.participant_count = len(participants) if isinstance(participants, list) else 0
                record.updated_at = now

                # Add participants
                for p in participants if isinstance(participants, list) else []:
                    participant_id = p.get("id", "")
                    if not participant_id:
                        continue

                    phone = participant_id.replace("@s.whatsapp.net", "").replace("@lid", "")
                    admin_status = p.get("admin")
                    role = (
                        "superadmin"
                        if admin_status == "superadmin"
                        else "admin"
                        if admin_status == "admin"
                        else "member"
                    )

                    participant = OmniGroupParticipant(
                        id=OmniGroupParticipant.generate_id(instance_name, group_id, participant_id),
                        instance_name=instance_name,
                        group_id=group_id,
                        participant_id=participant_id,
                        phone_number=phone if phone else None,
                        name=p.get("name"),
                        role=role,
                        synced_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(participant)
                    synced_count += 1

                success_count += 1

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout getting participants for {group_id}")
                timeout_count += 1
                continue
            except Exception as e:
                logger.warning(f"Error getting participants for {group_id}: {e}")
                failed_count += 1
                continue

        # Commit after each batch
        db.commit()

        # Delay between batches (except after last batch)
        if batch_end < total_groups:
            logger.info(f"Batch complete. Waiting {batch_delay}s before next batch...")
            time.sleep(batch_delay)

    return {
        "total_groups": total_groups,
        "success": success_count,
        "failed": failed_count,
        "timeouts": timeout_count,
        "participants_synced": synced_count,
    }


@router.get("/{instance_name}/groups", response_model=GroupsResponse)
async def get_groups(
    instance_name: str,
    include_participants: bool = Query(True, description="Include participant list for each group"),
    sync: bool = Query(False, description="Force sync from Evolution API (slower, updates local cache)"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get all WhatsApp groups for an instance with their participants.

    By default reads from local database (fast). Use sync=true to fetch
    fresh data from Evolution API and update the local cache.

    Args:
        instance_name: The WhatsApp instance name
        include_participants: Whether to include participant list (default: True)
        sync: Force sync from Evolution API (default: False)

    Returns:
        List of groups with participant information
    """
    from src.db.trace_models import OmniGroupParticipant

    try:
        logger.info(f"Fetching groups for instance '{instance_name}' (sync={sync})")

        instance = get_instance_by_name(instance_name, db)

        # Sync from Evolution if requested
        if sync:
            synced = _sync_groups_from_evolution(db, instance, instance_name)
            logger.info(f"Synced {synced} participants from Evolution API")

        # Read from local database
        group_records = (
            db.query(OmniChatRecord)
            .filter(
                OmniChatRecord.instance_name == instance_name,
                OmniChatRecord.chat_type == "group",
            )
            .all()
        )

        # Build LID to phone mapping for resolving participant IDs
        from src.db.trace_models import ChatIdMapping

        lid_mappings = (
            db.query(ChatIdMapping)
            .filter(
                ChatIdMapping.instance_name == instance_name,
                ChatIdMapping.alternate_chat_id.like("%@lid"),
            )
            .all()
        )
        # Map both with and without @lid suffix for easier lookup
        lid_to_phone = {}
        for m in lid_mappings:
            lid_num = m.alternate_chat_id.replace("@lid", "")
            lid_to_phone[lid_num] = m.phone_number
            lid_to_phone[m.alternate_chat_id] = m.phone_number

        groups = []
        for record in group_records:
            participants = []
            if include_participants:
                participant_records = (
                    db.query(OmniGroupParticipant)
                    .filter(
                        OmniGroupParticipant.instance_name == instance_name,
                        OmniGroupParticipant.group_id == record.chat_id,
                    )
                    .all()
                )

                for p in participant_records:
                    role = (
                        GroupParticipantRole.SUPERADMIN
                        if p.role == "superadmin"
                        else (GroupParticipantRole.ADMIN if p.role == "admin" else GroupParticipantRole.MEMBER)
                    )
                    # Resolve LID to phone number if available
                    phone = p.phone_number
                    if p.participant_id and "@lid" in p.participant_id:
                        # For LID participants, try to resolve to real phone
                        lid_num = p.participant_id.replace("@lid", "")
                        resolved = lid_to_phone.get(lid_num) or lid_to_phone.get(p.participant_id)
                        if resolved:
                            phone = resolved

                    participants.append(
                        GroupParticipant(
                            id=p.participant_id,
                            phone_number=phone,
                            name=p.name,
                            role=role,
                        )
                    )

            groups.append(
                GroupInfo(
                    id=record.chat_id,
                    subject=record.name or "Unknown",
                    owner=None,  # Not stored locally
                    description=record.description,
                    participant_count=record.participant_count or len(participants),
                    participants=participants,
                    creation_timestamp=None,
                )
            )

        logger.info(f"Returning {len(groups)} groups for instance '{instance_name}'")

        return GroupsResponse(
            groups=groups,
            total_count=len(groups),
            instance_name=instance_name,
            channel_type=ChannelType.WHATSAPP,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get groups for instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get groups: {str(e)}",
        )


@router.get("/{instance_name}/groups/{group_id}/participants", response_model=GroupParticipantsResponse)
async def get_group_participants(
    instance_name: str,
    group_id: str,
    sync: bool = Query(False, description="Force sync from Evolution API (slower, updates local cache)"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get participants for a specific WhatsApp group.

    By default reads from local database (fast). Use sync=true to fetch
    fresh data from Evolution API and update the local cache.

    Args:
        instance_name: The WhatsApp instance name
        group_id: The group JID (e.g., "120363421396472428@g.us")
        sync: Force sync from Evolution API (default: False)

    Returns:
        List of participants with their roles and contact info
    """
    from src.db.trace_models import OmniGroupParticipant

    try:
        logger.info(f"Fetching participants for group '{group_id}' in instance '{instance_name}' (sync={sync})")

        # Ensure group_id has proper suffix
        if not group_id.endswith("@g.us"):
            group_id = f"{group_id}@g.us"

        instance = get_instance_by_name(instance_name, db)

        # Sync from Evolution if requested
        if sync:
            _sync_groups_from_evolution(db, instance, instance_name)

        # Get group name from omni_chats
        chat_record_id = OmniChatRecord.generate_id(instance_name, group_id)
        chat_record = db.query(OmniChatRecord).filter(OmniChatRecord.id == chat_record_id).first()
        group_name = chat_record.name if chat_record else None

        # Build LID to phone mapping for resolving participant IDs
        from src.db.trace_models import ChatIdMapping

        lid_mappings = (
            db.query(ChatIdMapping)
            .filter(
                ChatIdMapping.instance_name == instance_name,
                ChatIdMapping.alternate_chat_id.like("%@lid"),
            )
            .all()
        )
        # Map both with and without @lid suffix for easier lookup
        lid_to_phone = {}
        for m in lid_mappings:
            lid_num = m.alternate_chat_id.replace("@lid", "")
            lid_to_phone[lid_num] = m.phone_number
            lid_to_phone[m.alternate_chat_id] = m.phone_number

        # Read participants from local database
        participant_records = (
            db.query(OmniGroupParticipant)
            .filter(
                OmniGroupParticipant.instance_name == instance_name,
                OmniGroupParticipant.group_id == group_id,
            )
            .all()
        )

        participants = []
        for p in participant_records:
            role = (
                GroupParticipantRole.SUPERADMIN
                if p.role == "superadmin"
                else (GroupParticipantRole.ADMIN if p.role == "admin" else GroupParticipantRole.MEMBER)
            )
            # Resolve LID to phone number if available
            phone = p.phone_number
            if p.participant_id and "@lid" in p.participant_id:
                # For LID participants, try to resolve to real phone
                lid_num = p.participant_id.replace("@lid", "")
                resolved = lid_to_phone.get(lid_num) or lid_to_phone.get(p.participant_id)
                if resolved:
                    phone = resolved

            participants.append(
                GroupParticipant(
                    id=p.participant_id,
                    phone_number=phone,
                    name=p.name,
                    role=role,
                )
            )

        logger.info(f"Returning {len(participants)} participants for group '{group_id}'")

        return GroupParticipantsResponse(
            group_id=group_id,
            group_name=group_name,
            participants=participants,
            total_count=len(participants),
            instance_name=instance_name,
            channel_type=ChannelType.WHATSAPP,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get participants for group '{group_id}' in instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get group participants: {str(e)}",
        )


@router.post("/{instance_name}/groups/sync")
async def sync_groups(
    instance_name: str,
    batch_size: int = Query(50, ge=10, le=100, description="Groups to process per batch"),
    batch_delay: float = Query(5.0, ge=1.0, le=30.0, description="Seconds to wait between batches"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Sync all groups and participants from Evolution API.

    Processes groups in batches to avoid WhatsApp rate limiting.
    For 249 groups with batch_size=50 and delay=5s, expect ~30 seconds total.

    Args:
        instance_name: The WhatsApp instance name
        batch_size: Groups per batch (default: 50, range: 10-100)
        batch_delay: Seconds between batches (default: 5, range: 1-30)

    Returns:
        Sync statistics including success/failure counts
    """
    try:
        logger.info(f"Starting group sync for instance '{instance_name}' (batch={batch_size}, delay={batch_delay}s)")

        instance = get_instance_by_name(instance_name, db)
        stats = _sync_groups_from_evolution(db, instance, instance_name, batch_size=batch_size, batch_delay=batch_delay)

        logger.info(f"Group sync complete for '{instance_name}': {stats}")

        return {
            "instance_name": instance_name,
            "status": "success",
            **stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync groups for instance '{instance_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync groups: {str(e)}",
        )
