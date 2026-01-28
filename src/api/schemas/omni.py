# src/api/schemas/omni.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ChannelType(str, Enum):
    """Supported channel types."""

    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    # Future channels: SLACK = "slack", TELEGRAM = "telegram"


class OmniContactStatus(str, Enum):
    """Contact availability status across channels."""

    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    DND = "dnd"  # Do not disturb
    UNKNOWN = "unknown"


class OmniChatType(str, Enum):
    """Chat/conversation types."""

    DIRECT = "direct"  # 1:1 conversation
    GROUP = "group"  # Group chat/channel
    CHANNEL = "channel"  # Broadcast channel
    THREAD = "thread"  # Thread within a chat


# Core Omni Contact Model
class OmniContact(BaseModel):
    """Omni contact representation across all channels."""

    # Universal fields
    id: str = Field(..., description="Unique contact identifier within channel")
    name: str = Field(..., description="Display name")
    channel_type: ChannelType = Field(..., description="Source channel type")
    instance_name: str = Field(..., description="Instance this contact belongs to")

    # Optional universal fields
    avatar_url: Optional[str] = Field(None, description="Profile picture URL")
    status: OmniContactStatus = Field(OmniContactStatus.UNKNOWN, description="Online status")
    is_verified: Optional[bool] = Field(None, description="Verification status")
    is_business: Optional[bool] = Field(None, description="Business account indicator")

    # Channel-specific data (preserved as dict for flexibility)
    channel_data: Dict[str, Any] = Field(default_factory=dict, description="Channel-specific contact data")

    # Metadata
    created_at: Optional[datetime] = Field(None, description="Contact creation timestamp")
    last_seen: Optional[datetime] = Field(None, description="Last activity timestamp")


# Core Omni Chat Model
class OmniChat(BaseModel):
    """Omni chat/conversation representation across all channels."""

    # Universal fields
    id: str = Field(..., description="Unique chat identifier within channel")
    name: str = Field(..., description="Chat display name")
    chat_type: OmniChatType = Field(..., description="Type of chat")
    channel_type: ChannelType = Field(..., description="Source channel type")
    instance_name: str = Field(..., description="Instance this chat belongs to")

    # Participants and metadata
    participant_count: Optional[int] = Field(None, description="Number of participants")
    is_muted: bool = Field(False, description="Chat muted status")
    is_archived: bool = Field(False, description="Chat archived status")
    is_pinned: bool = Field(False, description="Chat pinned status")

    # Optional universal fields
    description: Optional[str] = Field(None, description="Chat description")
    avatar_url: Optional[str] = Field(None, description="Chat avatar/icon URL")
    unread_count: Optional[int] = Field(None, description="Unread message count")

    # Media processing settings
    skip_media_processing: bool = Field(False, description="Skip media processing for this chat")
    processing_note: Optional[str] = Field(None, description="Note explaining why processing is skipped")

    # Channel-specific data
    channel_data: Dict[str, Any] = Field(default_factory=dict, description="Channel-specific chat data")

    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Chat creation timestamp")
    last_message_at: Optional[datetime] = Field(None, description="Last message timestamp")


# Core Omni Message Model
class OmniMessageType(str, Enum):
    """Message types across channels."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    CONTACT = "contact"
    LOCATION = "location"
    REACTION = "reaction"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class MessageDeliveryStatus(str, Enum):
    """Message delivery status across channels."""

    PENDING = "pending"  # Message queued, not yet sent
    SENT = "sent"  # Message sent to server
    DELIVERED = "delivered"  # Message delivered to recipient's device
    READ = "read"  # Message read by recipient
    FAILED = "failed"  # Message delivery failed
    UNKNOWN = "unknown"  # Status unknown


class MessageSource(str, Enum):
    """Source of message ingestion into omni_messages."""

    WEBHOOK = "webhook"  # Real-time message via Evolution webhook
    SYNC = "sync"  # Imported from evo_Message table
    API = "api"  # Fetched on-demand via Evolution API


class MediaStatus(str, Enum):
    """Status of media download/processing workflow."""

    PENDING = "pending"  # Media not yet downloaded
    DOWNLOADED = "downloaded"  # Media downloaded to local storage
    PROCESSED = "processed"  # Media content extracted (transcript, description)
    FAILED = "failed"  # Download or processing failed
    EXPIRED = "expired"  # URL expired and could not be re-fetched


class MessageDirection(str, Enum):
    """Message direction relative to the instance."""

    INBOUND = "inbound"  # Message received by the instance
    OUTBOUND = "outbound"  # Message sent by the instance


class MessageReaction(BaseModel):
    """Reaction attached to a message (like WhatsApp emoji reactions)."""

    emoji: str = Field(..., description="The reaction emoji")
    sender_id: Optional[str] = Field(None, description="ID of who reacted")
    sender_name: Optional[str] = Field(None, description="Name of who reacted")
    timestamp: Optional[datetime] = Field(None, description="When the reaction was added")


class MediaContent(BaseModel):
    """Processed media content (transcript for audio, description for images)."""

    content_type: str = Field(..., description="Type: audio_transcript, image_description, etc.")
    content: str = Field(..., description="The transcript or description text")
    processor_name: Optional[str] = Field(None, description="Processor used (groq_whisper, gemini, etc.)")
    confidence_score: Optional[float] = Field(None, description="Confidence score if available")
    processed_at: Optional[datetime] = Field(None, description="When content was processed")


class Mention(BaseModel):
    """A user mention in a message."""

    jid: str = Field(..., description="The JID/ID of the mentioned user (e.g., 123@lid or 123@s.whatsapp.net)")
    name: Optional[str] = Field(None, description="Resolved display name of the mentioned user")
    phone: Optional[str] = Field(None, description="Phone number if known")


class OmniMessage(BaseModel):
    """Omni message representation across all channels."""

    # Universal fields
    id: str = Field(..., description="Unique message identifier within channel")
    chat_id: str = Field(..., description="Chat/conversation this message belongs to")
    sender_id: str = Field(..., description="Sender identifier")
    sender_name: Optional[str] = Field(None, description="Sender display name")

    # Message content
    message_type: OmniMessageType = Field(..., description="Type of message")
    text: Optional[str] = Field(None, description="Raw text content with original mention IDs")
    text_display: Optional[str] = Field(None, description="Display text with mention names resolved")

    # Mentions
    mentions: List[Mention] = Field(default_factory=list, description="Users mentioned in this message")

    # Media fields
    media_url: Optional[str] = Field(None, description="Media file URL")
    media_mime_type: Optional[str] = Field(None, description="Media MIME type")
    media_size: Optional[int] = Field(None, description="Media file size in bytes")
    caption: Optional[str] = Field(None, description="Media caption")
    thumbnail_url: Optional[str] = Field(None, description="Media thumbnail URL")

    # Message metadata
    is_from_me: bool = Field(False, description="Whether message is from the instance owner")
    is_forwarded: bool = Field(False, description="Whether message is forwarded")
    is_reply: bool = Field(False, description="Whether message is a reply")
    reply_to_message_id: Optional[str] = Field(None, description="ID of message being replied to")

    # Reactions (attached to this message)
    reactions: List["MessageReaction"] = Field(default_factory=list, description="Emoji reactions on this message")

    # Delivery and read status
    delivery_status: MessageDeliveryStatus = Field(
        MessageDeliveryStatus.UNKNOWN, description="Message delivery status (pending/sent/delivered/read/failed)"
    )
    is_read: bool = Field(False, description="Whether message has been read by recipient")

    # Timestamps
    timestamp: datetime = Field(..., description="Message timestamp")
    edited_at: Optional[datetime] = Field(None, description="Edit timestamp if edited")
    read_at: Optional[datetime] = Field(None, description="Timestamp when message was read")

    # Processed media content (transcript for audio, description for images)
    media_content: Optional["MediaContent"] = Field(None, description="Processed media content if available")

    # Channel-specific data
    channel_type: ChannelType = Field(..., description="Source channel type")
    instance_name: str = Field(..., description="Instance this message belongs to")
    channel_data: Dict[str, Any] = Field(default_factory=dict, description="Channel-specific message data")


# Core Omni Channel Model
class OmniChannelInfo(BaseModel):
    """Omni channel/instance information across all channels."""

    # Universal fields
    instance_name: str = Field(..., description="Instance identifier")
    channel_type: ChannelType = Field(..., description="Channel type")
    display_name: str = Field(..., description="Human-readable instance name")

    # Connection status
    status: str = Field(..., description="Connection status: connected|disconnected|connecting|error")
    is_healthy: bool = Field(..., description="Overall health status")

    # Capabilities (what operations are supported)
    supports_contacts: bool = Field(True, description="Supports contact operations")
    supports_groups: bool = Field(True, description="Supports group/channel operations")
    supports_media: bool = Field(True, description="Supports media messages")
    supports_voice: bool = Field(False, description="Supports voice messages")

    # Optional fields
    avatar_url: Optional[str] = Field(None, description="Channel/bot avatar URL")
    description: Optional[str] = Field(None, description="Channel description")

    # Statistics
    total_contacts: Optional[int] = Field(None, description="Total contacts count")
    total_chats: Optional[int] = Field(None, description="Total chats count")

    # Channel-specific data
    channel_data: Dict[str, Any] = Field(default_factory=dict, description="Channel-specific information")

    # Timestamps
    connected_at: Optional[datetime] = Field(None, description="Connection established timestamp")
    last_activity_at: Optional[datetime] = Field(None, description="Last activity timestamp")


# Response wrapper models
class OmniContactsResponse(BaseModel):
    """Response model for omni contacts endpoint."""

    contacts: List[OmniContact] = Field(..., description="List of contacts")
    total_count: int = Field(..., description="Total number of contacts")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Items per page")
    has_more: bool = Field(False, description="More pages available")

    # Instance information
    instance_name: str = Field(..., description="Queried instance name")
    channel_type: Optional[ChannelType] = Field(None, description="Channel type filter applied")

    # Error handling for multi-channel queries
    partial_errors: List[Dict[str, str]] = Field(default_factory=list, description="Per-channel errors")


class OmniChatsResponse(BaseModel):
    """Response model for omni chats endpoint."""

    chats: List[OmniChat] = Field(..., description="List of chats")
    total_count: int = Field(..., description="Total number of chats")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Items per page")
    has_more: bool = Field(False, description="More pages available")

    # Instance information
    instance_name: str = Field(..., description="Queried instance name")
    channel_type: Optional[ChannelType] = Field(None, description="Channel type filter applied")

    # Error handling for multi-channel queries
    partial_errors: List[Dict[str, str]] = Field(default_factory=list, description="Per-channel errors")


class OmniChannelsResponse(BaseModel):
    """Response model for omni channels endpoint."""

    channels: List[OmniChannelInfo] = Field(..., description="List of channel instances")
    total_count: int = Field(..., description="Total number of channels")
    healthy_count: int = Field(..., description="Number of healthy channels")

    # Error handling
    partial_errors: List[Dict[str, str]] = Field(default_factory=list, description="Per-channel errors")


class OmniMessagesResponse(BaseModel):
    """Response model for omni messages endpoint."""

    messages: List[OmniMessage] = Field(..., description="List of messages")
    total_count: int = Field(..., description="Total number of messages")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Items per page")
    has_more: bool = Field(False, description="More pages available")

    # Instance and chat information
    instance_name: str = Field(..., description="Queried instance name")
    chat_id: str = Field(..., description="Chat identifier")
    channel_type: ChannelType = Field(..., description="Channel type")

    # Error handling
    partial_errors: List[Dict[str, str]] = Field(default_factory=list, description="Per-channel errors")


# Error response models
class OmniErrorDetail(BaseModel):
    """Detailed error information for omni endpoints."""

    instance_name: Optional[str] = Field(None, description="Instance that caused the error")
    channel_type: Optional[ChannelType] = Field(None, description="Channel type that caused the error")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class OmniErrorResponse(BaseModel):
    """Omni error response format."""

    success: bool = Field(False, description="Operation success status")
    error: str = Field(..., description="Primary error message")
    details: List[OmniErrorDetail] = Field(default_factory=list, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error occurrence timestamp")


# Recipient validation models
class ValidateRecipientRequest(BaseModel):
    """Request model for recipient validation endpoint."""

    recipients: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of recipient identifiers to validate (phone numbers for WhatsApp, user IDs for Discord)",
        examples=[["5511999999999", "5511888888888"]],
    )


class RecipientProfile(BaseModel):
    """Profile information for a valid recipient."""

    jid: Optional[str] = Field(None, description="WhatsApp JID (e.g., 5511999999999@s.whatsapp.net)")
    name: Optional[str] = Field(None, description="Contact name if available")
    lid: Optional[str] = Field(None, description="WhatsApp LID if using LID format")
    avatar_url: Optional[str] = Field(None, description="Profile picture URL if available")


class RecipientValidationResult(BaseModel):
    """Validation result for a single recipient."""

    recipient: str = Field(..., description="The recipient identifier that was validated")
    valid: bool = Field(..., description="Whether the recipient is valid and reachable")
    reason: Optional[str] = Field(
        None,
        description="Reason why validation failed (e.g., 'not_on_whatsapp', 'invalid_format', 'validation_error')",
    )
    profile: Optional[RecipientProfile] = Field(None, description="Profile information if recipient is valid")


class ValidateRecipientResponse(BaseModel):
    """Response model for recipient validation endpoint."""

    results: List[RecipientValidationResult] = Field(..., description="Validation results for each recipient")
    total_count: int = Field(..., description="Total number of recipients validated")
    valid_count: int = Field(..., description="Number of valid recipients")
    invalid_count: int = Field(..., description="Number of invalid recipients")

    # Instance information
    instance_name: str = Field(..., description="Instance used for validation")
    channel_type: ChannelType = Field(..., description="Channel type")


# =============================================================================
# Unified Message Store Models (omni_messages table)
# =============================================================================


class StoredMessageBase(BaseModel):
    """Base model for messages stored in omni_messages table."""

    id: str = Field(..., description="Composite ID: {instance}:{platform_message_id}")
    instance_name: str = Field(..., description="Instance name")
    channel_type: ChannelType = Field(..., description="Channel type (whatsapp, discord)")
    chat_id: str = Field(..., description="Chat identifier (remoteJid or channel_id)")
    platform_message_id: str = Field(..., description="Platform-specific message ID")
    platform_key: Optional[Dict[str, Any]] = Field(None, description="Full WhatsApp key object")

    direction: MessageDirection = Field(..., description="Message direction (inbound/outbound)")
    sender_id: Optional[str] = Field(None, description="Sender identifier (JID or user ID)")
    sender_name: Optional[str] = Field(None, description="Sender display name")
    is_from_me: bool = Field(False, description="Whether message is from the instance owner")

    message_type: OmniMessageType = Field(..., description="Type of message content")
    content_text: Optional[str] = Field(None, description="Text content or caption")

    has_media: bool = Field(False, description="Whether message has media attachment")
    media_url: Optional[str] = Field(None, description="Original media URL (may expire)")
    media_mime_type: Optional[str] = Field(None, description="Media MIME type")
    media_size_bytes: Optional[int] = Field(None, description="Media file size in bytes")
    media_duration_seconds: Optional[int] = Field(None, description="Duration for audio/video")
    media_status: MediaStatus = Field(MediaStatus.PENDING, description="Media processing status")

    quoted_message_id: Optional[str] = Field(None, description="ID of quoted/replied message")
    delivery_status: Optional[MessageDeliveryStatus] = Field(None, description="Message delivery status")

    source: MessageSource = Field(..., description="How message was ingested (webhook/sync/api)")
    message_timestamp: datetime = Field(..., description="Original message timestamp")


class StoredMessage(StoredMessageBase):
    """Full stored message with all fields."""

    media_local_path: Optional[str] = Field(None, description="Local file path after download")
    media_key: Optional[str] = Field(None, description="WhatsApp media encryption key")
    media_sha256: Optional[str] = Field(None, description="Media file SHA256 for dedup")

    context_info: Optional[Dict[str, Any]] = Field(None, description="Message context info")
    content_raw: Optional[Dict[str, Any]] = Field(None, description="Raw platform message object")

    sync_batch_id: Optional[str] = Field(None, description="Sync batch identifier")
    trace_id: Optional[str] = Field(None, description="Link to message trace record")

    status_updated_at: Optional[datetime] = Field(None, description="When delivery status was updated")
    created_at: Optional[datetime] = Field(None, description="When record was created")
    updated_at: Optional[datetime] = Field(None, description="When record was last updated")
    synced_at: Optional[datetime] = Field(None, description="When message was synced from Evolution")


class StoredMessageWithTranscript(StoredMessageBase):
    """Stored message with media transcript/description if available."""

    transcript: Optional[str] = Field(None, description="Audio transcript or image description")
    transcript_processor: Optional[str] = Field(None, description="Processor used for transcript")
    transcript_confidence: Optional[int] = Field(None, description="Transcript confidence score (0-100)")


class StoredMessagesResponse(BaseModel):
    """Response model for stored messages endpoint."""

    messages: List[StoredMessageBase] = Field(..., description="List of stored messages")
    total_count: int = Field(..., description="Total number of messages")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Items per page")
    has_more: bool = Field(False, description="More pages available")

    # Filtering info
    instance_name: str = Field(..., description="Instance name filter")
    chat_id: Optional[str] = Field(None, description="Chat ID filter if applied")
    source_filter: Optional[MessageSource] = Field(None, description="Source filter if applied")

    # Stats
    webhook_count: Optional[int] = Field(None, description="Messages from webhook")
    sync_count: Optional[int] = Field(None, description="Messages from sync")
    media_count: Optional[int] = Field(None, description="Messages with media")


class MessageImportStats(BaseModel):
    """Statistics from message import operation."""

    total_found: int = Field(..., description="Total messages found in source")
    total_imported: int = Field(..., description="Messages successfully imported")
    already_exists: int = Field(..., description="Messages skipped (already exist)")
    failed: int = Field(..., description="Messages that failed to import")
    with_media: int = Field(..., description="Imported messages with media")

    instance_name: str = Field(..., description="Instance that was imported")
    source: str = Field(..., description="Import source (e.g., 'evo_Message')")
    started_at: datetime = Field(..., description="Import start time")
    completed_at: Optional[datetime] = Field(None, description="Import completion time")
    duration_seconds: Optional[float] = Field(None, description="Import duration")


class MessageImportRequest(BaseModel):
    """Request model for message import endpoint."""

    instance_name: str = Field(..., description="Instance to import messages for")
    days: int = Field(30, ge=1, le=365, description="Number of days of history to import")
    batch_size: int = Field(500, ge=100, le=2000, description="Batch size for processing")
    skip_existing: bool = Field(True, description="Skip messages that already exist")


class MediaResponse(BaseModel):
    """Response model for media content endpoint."""

    base64: str = Field(..., description="Base64-encoded media content")
    mimetype: str = Field(..., description="MIME type of the media")
    fileName: Optional[str] = Field(None, description="Original file name if available")
    media_status: str = Field(..., description="Media status: downloaded, pending, failed, expired")
    source: str = Field(..., description="Where media was retrieved from: local, evolution")
