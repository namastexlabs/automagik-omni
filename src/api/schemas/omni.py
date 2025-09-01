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
    DIRECT = "direct"      # 1:1 conversation
    GROUP = "group"        # Group chat/channel
    CHANNEL = "channel"    # Broadcast channel
    THREAD = "thread"      # Thread within a chat

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

    # Channel-specific data
    channel_data: Dict[str, Any] = Field(default_factory=dict, description="Channel-specific chat data")

    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Chat creation timestamp")
    last_message_at: Optional[datetime] = Field(None, description="Last message timestamp")

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
