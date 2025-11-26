"""Pydantic models for OMNI API requests and responses"""

from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum


# Enums
class ChannelType(str, Enum):
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    DISCORD = "discord"


class InstanceOperation(str, Enum):
    LIST = "list"
    GET = "get"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SET_DEFAULT = "set_default"
    STATUS = "status"
    QR = "qr"
    RESTART = "restart"
    LOGOUT = "logout"


class MessageType(str, Enum):
    TEXT = "text"
    MEDIA = "media"
    AUDIO = "audio"
    STICKER = "sticker"
    CONTACT = "contact"
    REACTION = "reaction"


class TraceOperation(str, Enum):
    LIST = "list"
    GET = "get"
    GET_PAYLOADS = "get_payloads"
    ANALYTICS = "analytics"
    BY_PHONE = "by_phone"
    CLEANUP = "cleanup"


class ProfileOperation(str, Enum):
    FETCH = "fetch"
    UPDATE_PICTURE = "update_picture"


# Instance Models
class InstanceConfig(BaseModel):
    """Instance configuration model - supports all channel types with extra fields"""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow extra fields for future API updates

    name: str
    channel_type: ChannelType = ChannelType.WHATSAPP
    evolution_url: Optional[str] = None
    evolution_key: Optional[str] = None
    whatsapp_instance: Optional[str] = None
    session_id_prefix: Optional[str] = None
    webhook_base64: Optional[bool] = True
    phone_number: Optional[str] = None
    auto_qr: Optional[bool] = True
    integration: Optional[str] = None
    agent_api_url: Optional[str] = None
    agent_api_key: Optional[str] = None
    default_agent: Optional[str] = None
    agent_timeout: Optional[int] = 60
    is_default: Optional[bool] = False
    is_active: Optional[bool] = True

    # Discord-specific fields (optional, will be included when extra="allow")
    discord_bot_token: Optional[str] = None
    discord_client_id: Optional[str] = None
    discord_public_key: Optional[str] = None
    discord_voice_enabled: Optional[bool] = None
    discord_slash_commands_enabled: Optional[bool] = None

    # Slack-specific fields (optional, for future use)
    slack_bot_token: Optional[str] = None
    slack_app_token: Optional[str] = None
    slack_signing_secret: Optional[str] = None


class InstanceResponse(InstanceConfig):
    """Instance response with additional fields"""

    model_config = ConfigDict(extra="allow")  # Inherit extra field handling

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    evolution_status: Optional[Dict[str, Any]] = None


class ConnectionStatus(BaseModel):
    """Connection status response"""

    model_config = ConfigDict(extra="allow")

    instance_name: str
    channel_type: str
    status: str
    channel_data: Optional[Dict[str, Any]] = None


class QRCodeResponse(BaseModel):
    """QR code response"""

    model_config = ConfigDict(extra="allow")

    instance_name: str
    qr_code: Optional[str] = None
    qr_url: Optional[str] = None
    connection_type: str
    status: str


# Message Models
class SendTextRequest(BaseModel):
    """Text message request"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    phone_number: str = Field(
        ..., description="Phone number with country code", alias="phone"
    )
    text: str = Field(..., description="Message text", alias="message")
    quoted_message_id: Optional[str] = None
    delay: Optional[int] = Field(None, description="Delay in milliseconds")
    split_message: Optional[bool] = Field(
        None,
        description="Optional override for message splitting behavior. If None, uses instance config (enable_auto_split). For WhatsApp: controls splitting on \\n\\n. For Discord: controls preference for \\n\\n split point (2000-char hard limit always applies).",
    )


class SendMediaRequest(BaseModel):
    """Media message request"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    phone_number: str = Field(
        ..., description="Phone number with country code", alias="phone"
    )
    media_url: Optional[str] = Field(None, description="URL of the media file")
    media_base64: Optional[str] = Field(None, description="Base64 encoded media for local files")
    media_type: Literal["image", "video", "document"] = "image"
    mime_type: Optional[str] = None
    caption: Optional[str] = None
    filename: Optional[str] = None
    quoted_message_id: Optional[str] = None
    delay: Optional[int] = None


class SendAudioRequest(BaseModel):
    """Audio message request"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    phone_number: str = Field(
        ..., description="Phone number with country code", alias="phone"
    )
    audio_url: Optional[str] = Field(None, description="URL of the audio file")
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio for local files")
    ptt: bool = Field(True, description="Send as voice note")
    quoted_message_id: Optional[str] = None
    delay: Optional[int] = None


class SendStickerRequest(BaseModel):
    """Sticker message request"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    phone_number: str = Field(
        ..., description="Phone number with country code", alias="phone"
    )
    sticker_url: str = Field(..., description="URL of the sticker file")
    quoted_message_id: Optional[str] = None
    delay: Optional[int] = None


class ContactInfo(BaseModel):
    """Contact information"""

    model_config = ConfigDict(extra="allow")

    full_name: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None
    url: Optional[str] = None


class SendContactRequest(BaseModel):
    """Contact message request"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    phone_number: str = Field(
        ..., description="Phone number with country code", alias="phone"
    )
    contacts: List[ContactInfo]
    quoted_message_id: Optional[str] = None
    delay: Optional[int] = None


class SendReactionRequest(BaseModel):
    """Reaction message request"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    phone_number: str = Field(
        ..., description="Phone number with country code", alias="phone"
    )
    message_id: str = Field(..., description="ID of message to react to")
    emoji: str = Field(..., description="Emoji reaction")


class MessageResponse(BaseModel):
    """Generic message response"""

    model_config = ConfigDict(extra="allow")

    success: bool
    message_id: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


# Trace Models
class TraceFilter(BaseModel):
    """Trace filter parameters"""

    model_config = ConfigDict(extra="allow")

    phone: Optional[str] = None
    instance_name: Optional[str] = None
    trace_status: Optional[str] = None
    message_type: Optional[str] = None
    session_name: Optional[str] = None
    agent_session_id: Optional[str] = None
    has_media: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 50
    offset: int = 0


class TraceResponse(BaseModel):
    """Trace response model"""

    model_config = ConfigDict(extra="allow")

    trace_id: str
    instance_name: str
    whatsapp_message_id: Optional[str] = None
    sender_phone: str
    sender_name: Optional[str] = None
    message_type: Optional[str] = None
    status: str
    session_name: Optional[str] = None
    agent_session_id: Optional[str] = None
    has_media: bool = False
    has_quoted_message: bool = False
    error_message: Optional[str] = None
    error_stage: Optional[str] = None
    received_at: datetime
    completed_at: Optional[datetime] = None
    agent_processing_time_ms: Optional[float] = None
    total_processing_time_ms: Optional[float] = None
    agent_response_success: Optional[bool] = None
    evolution_success: Optional[bool] = None
    payload_count: int = 0


class TracePayloadResponse(BaseModel):
    """Trace payload response - matches Omni backend schema"""

    model_config = ConfigDict(extra="allow")

    # Core fields (match backend exactly)
    id: int  # Fixed: Backend returns int primary key, not str
    trace_id: str
    stage: str  # Fixed: Backend uses "stage" not "direction"
    payload_type: str
    timestamp: Optional[str]  # Fixed: Backend uses "timestamp" not "created_at"

    # Metadata fields
    status_code: Optional[int] = None
    error_details: Optional[str] = None
    payload_size_original: Optional[int] = None
    payload_size_compressed: Optional[int] = None
    compression_ratio: Optional[float] = None

    # Content flags
    contains_media: bool = False
    contains_base64: bool = False

    # Actual payload data (optional)
    payload: Optional[Dict[str, Any]] = None


class TraceAnalytics(BaseModel):
    """Trace analytics summary"""

    model_config = ConfigDict(extra="allow")

    total_messages: int
    successful_messages: int
    failed_messages: int
    success_rate: float
    avg_processing_time_ms: Optional[float] = None
    avg_agent_time_ms: Optional[float] = None
    message_types: Dict[str, int]
    error_stages: Dict[str, int]
    instances: Dict[str, int]


# Profile Models
class FetchProfileRequest(BaseModel):
    """Profile fetch request"""

    model_config = ConfigDict(extra="allow")

    user_id: Optional[str] = None
    phone_number: Optional[str] = None


class UpdateProfilePictureRequest(BaseModel):
    """Profile picture update request"""

    model_config = ConfigDict(extra="allow")

    picture_url: str = Field(..., description="URL of the new profile picture")


# Unified Message Request
MessageRequestType = Union[
    SendTextRequest,
    SendMediaRequest,
    SendAudioRequest,
    SendStickerRequest,
    SendContactRequest,
    SendReactionRequest,
]


# Chat Models
class ChatResponse(BaseModel):
    """Chat response model"""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    chat_type: str  # direct, group, channel, thread
    channel_type: str  # whatsapp, discord
    instance_name: str
    participant_count: Optional[int] = None
    is_muted: bool = False
    is_archived: bool = False
    is_pinned: bool = False
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    unread_count: Optional[int] = None  # Fixed: Backend returns None when not available
    channel_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None


class ChatListResponse(BaseModel):
    """Chat list response with pagination"""

    model_config = ConfigDict(extra="allow")

    chats: List[ChatResponse]
    total_count: int
    page: int
    page_size: int
    has_more: bool
    instance_name: str
    channel_type: Optional[str] = None
    partial_errors: List[Dict[str, Any]] = []


# Contact Models
class ContactResponse(BaseModel):
    """Contact response model"""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    channel_type: str  # whatsapp, discord
    instance_name: str
    avatar_url: Optional[str] = None
    status: Optional[str] = None
    is_verified: Optional[bool] = None
    is_business: Optional[bool] = None
    channel_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None


class ContactListResponse(BaseModel):
    """Contact list response with pagination"""

    model_config = ConfigDict(extra="allow")

    contacts: List[ContactResponse]
    total_count: int
    page: int
    page_size: int
    has_more: bool
    instance_name: str
    channel_type: Optional[str] = None
    partial_errors: List[Dict[str, Any]] = []


# Channel Models
class ChannelResponse(BaseModel):
    """Channel/Instance response in Omni format"""

    model_config = ConfigDict(extra="allow")

    instance_name: str
    channel_type: str  # whatsapp, discord
    display_name: str
    status: str
    is_healthy: bool
    supports_contacts: bool
    supports_groups: bool
    supports_media: bool
    supports_voice: bool
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    total_contacts: Optional[int] = None
    total_chats: Optional[int] = None
    channel_data: Optional[Dict[str, Any]] = None
    connected_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None


class ChannelListResponse(BaseModel):
    """Channel list response"""

    model_config = ConfigDict(extra="allow")

    channels: List[ChannelResponse]
    total_count: int
    healthy_count: int
    partial_errors: List[Dict[str, Any]] = []
