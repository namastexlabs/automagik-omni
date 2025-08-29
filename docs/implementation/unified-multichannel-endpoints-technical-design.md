# Unified Multi-Channel Endpoints - Technical Design Document

## Executive Summary

This document provides complete technical specifications for implementing unified multi-channel endpoints in automagik-omni, leveraging the existing excellent architectural foundations. The design enables consistent chats/contacts/channels operations across WhatsApp, Discord, and future channels while maintaining backward compatibility and achieving sub-500ms response targets.

## Architecture Analysis Summary

### Current Foundation Strengths
- **Robust ChannelHandler System**: Clean ABC with ChannelHandlerFactory registry pattern
- **Multi-Tenant InstanceConfig**: Comprehensive channel support with channel_type discriminator  
- **Advanced Performance Infrastructure**: Sophisticated rate limiting, timeout management, circuit breakers
- **Production-Ready Security**: Bearer token auth, input validation, per-instance isolation
- **Excellent Code Quality**: Minimal technical debt, clean abstractions, async-first design

### Performance Capabilities
- **Sub-500ms Response Ready**: Async architecture, efficient data structures, optimized timeouts
- **Scalable Multi-Tenant**: Per-instance isolation, connection pooling, memory management
- **Graceful Degradation**: Circuit breakers, partial failure handling, comprehensive error hierarchy

## 1. Unified Response Schema Design

### 1.1 Core Unified Models

```python
# src/api/schemas/unified.py
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class ChannelType(str, Enum):
    """Supported channel types."""
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    # Future channels: SLACK = "slack", TELEGRAM = "telegram"

class UnifiedContactStatus(str, Enum):
    """Contact availability status across channels."""
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away" 
    DND = "dnd"  # Do not disturb
    UNKNOWN = "unknown"

class UnifiedChatType(str, Enum):
    """Chat/conversation types."""
    DIRECT = "direct"      # 1:1 conversation
    GROUP = "group"        # Group chat/channel
    CHANNEL = "channel"    # Broadcast channel
    THREAD = "thread"      # Thread within a chat

# Core Unified Contact Model
class UnifiedContact(BaseModel):
    """Unified contact representation across all channels."""
    # Universal fields
    id: str = Field(..., description="Unique contact identifier within channel")
    name: str = Field(..., description="Display name")
    channel_type: ChannelType = Field(..., description="Source channel type")
    instance_name: str = Field(..., description="Instance this contact belongs to")
    
    # Optional universal fields  
    avatar_url: Optional[str] = Field(None, description="Profile picture URL")
    status: UnifiedContactStatus = Field(UnifiedContactStatus.UNKNOWN, description="Online status")
    is_verified: Optional[bool] = Field(None, description="Verification status")
    is_business: Optional[bool] = Field(None, description="Business account indicator")
    
    # Channel-specific data (preserved as dict for flexibility)
    channel_data: Dict[str, Any] = Field(default_factory=dict, description="Channel-specific contact data")
    
    # Metadata
    created_at: Optional[datetime] = Field(None, description="Contact creation timestamp")
    last_seen: Optional[datetime] = Field(None, description="Last activity timestamp")

# Core Unified Chat Model  
class UnifiedChat(BaseModel):
    """Unified chat/conversation representation across all channels."""
    # Universal fields
    id: str = Field(..., description="Unique chat identifier within channel")
    name: str = Field(..., description="Chat display name") 
    chat_type: UnifiedChatType = Field(..., description="Type of chat")
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

# Core Unified Channel Model
class UnifiedChannelInfo(BaseModel):
    """Unified channel/instance information across all channels."""
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
class UnifiedContactsResponse(BaseModel):
    """Response model for unified contacts endpoint."""
    contacts: List[UnifiedContact] = Field(..., description="List of contacts")
    total_count: int = Field(..., description="Total number of contacts")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Items per page")
    has_more: bool = Field(False, description="More pages available")
    
    # Instance information
    instance_name: str = Field(..., description="Queried instance name")
    channel_type: Optional[ChannelType] = Field(None, description="Channel type filter applied")
    
    # Error handling for multi-channel queries
    partial_errors: List[Dict[str, str]] = Field(default_factory=list, description="Per-channel errors")

class UnifiedChatsResponse(BaseModel):
    """Response model for unified chats endpoint."""
    chats: List[UnifiedChat] = Field(..., description="List of chats")
    total_count: int = Field(..., description="Total number of chats")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Items per page")
    has_more: bool = Field(False, description="More pages available")
    
    # Instance information  
    instance_name: str = Field(..., description="Queried instance name")
    channel_type: Optional[ChannelType] = Field(None, description="Channel type filter applied")
    
    # Error handling for multi-channel queries
    partial_errors: List[Dict[str, str]] = Field(default_factory=list, description="Per-channel errors")

class UnifiedChannelsResponse(BaseModel):
    """Response model for unified channels endpoint."""
    channels: List[UnifiedChannelInfo] = Field(..., description="List of channel instances")
    total_count: int = Field(..., description="Total number of channels")
    healthy_count: int = Field(..., description="Number of healthy channels")
    
    # Error handling
    partial_errors: List[Dict[str, str]] = Field(default_factory=list, description="Per-channel errors")

# Error response models
class UnifiedErrorDetail(BaseModel):
    """Detailed error information for unified endpoints."""
    instance_name: Optional[str] = Field(None, description="Instance that caused the error")
    channel_type: Optional[ChannelType] = Field(None, description="Channel type that caused the error")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

class UnifiedErrorResponse(BaseModel):
    """Unified error response format."""
    success: bool = Field(False, description="Operation success status")
    error: str = Field(..., description="Primary error message")
    details: List[UnifiedErrorDetail] = Field(default_factory=list, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error occurrence timestamp")
```

### 1.2 Data Transformation Mappings

```python
# src/services/unified_transformers.py
from typing import Dict, Any, Optional, List
from src.api.schemas.unified import (
    UnifiedContact, UnifiedChat, UnifiedChannelInfo, 
    ChannelType, UnifiedContactStatus, UnifiedChatType
)

class WhatsAppTransformer:
    """Transform WhatsApp data to unified format."""
    
    @staticmethod
    def contact_to_unified(whatsapp_contact: Dict[str, Any], instance_name: str) -> UnifiedContact:
        """Transform WhatsApp contact to unified format."""
        return UnifiedContact(
            id=whatsapp_contact.get("id", ""),
            name=whatsapp_contact.get("pushName") or whatsapp_contact.get("name", "Unknown"),
            channel_type=ChannelType.WHATSAPP,
            instance_name=instance_name,
            avatar_url=whatsapp_contact.get("profilePictureUrl"),
            is_verified=whatsapp_contact.get("isVerified"),
            is_business=whatsapp_contact.get("isBusiness"),
            channel_data={
                "phone_number": whatsapp_contact.get("id", "").replace("@c.us", ""),
                "is_contact": whatsapp_contact.get("isMyContact", False),
                "presence": whatsapp_contact.get("presence"),
                "whatsapp_name": whatsapp_contact.get("name"),
                "push_name": whatsapp_contact.get("pushName"),
                "raw_data": whatsapp_contact
            },
            last_seen=WhatsAppTransformer._parse_datetime(whatsapp_contact.get("lastSeen"))
        )
    
    @staticmethod  
    def chat_to_unified(whatsapp_chat: Dict[str, Any], instance_name: str) -> UnifiedChat:
        """Transform WhatsApp chat to unified format."""
        # Determine chat type
        chat_type = UnifiedChatType.DIRECT
        if whatsapp_chat.get("id", "").endswith("@g.us"):
            chat_type = UnifiedChatType.GROUP
        elif whatsapp_chat.get("id", "").endswith("@broadcast"):
            chat_type = UnifiedChatType.CHANNEL
            
        return UnifiedChat(
            id=whatsapp_chat.get("id", ""),
            name=whatsapp_chat.get("name") or whatsapp_chat.get("pushName", "Unknown"),
            chat_type=chat_type,
            channel_type=ChannelType.WHATSAPP,
            instance_name=instance_name,
            participant_count=len(whatsapp_chat.get("participants", [])) if chat_type == UnifiedChatType.GROUP else None,
            is_muted=whatsapp_chat.get("isMuted", False),
            is_archived=whatsapp_chat.get("isArchived", False),
            is_pinned=whatsapp_chat.get("isPinned", False),
            unread_count=whatsapp_chat.get("unreadCount", 0),
            channel_data={
                "group_id": whatsapp_chat.get("id") if chat_type == UnifiedChatType.GROUP else None,
                "participants": whatsapp_chat.get("participants", []),
                "group_metadata": whatsapp_chat.get("groupMetadata"),
                "raw_data": whatsapp_chat
            },
            last_message_at=WhatsAppTransformer._parse_datetime(whatsapp_chat.get("lastMessageTime"))
        )
    
    @staticmethod
    def _parse_datetime(timestamp: Any) -> Optional[datetime]:
        """Parse WhatsApp timestamp to datetime."""
        if not timestamp:
            return None
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp / 1000 if timestamp > 1e10 else timestamp)
            return datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
        except:
            return None

class DiscordTransformer:
    """Transform Discord data to unified format."""
    
    @staticmethod
    def contact_to_unified(discord_user: Dict[str, Any], instance_name: str) -> UnifiedContact:
        """Transform Discord user to unified format.""" 
        status_map = {
            "online": UnifiedContactStatus.ONLINE,
            "idle": UnifiedContactStatus.AWAY,
            "dnd": UnifiedContactStatus.DND,
            "offline": UnifiedContactStatus.OFFLINE,
        }
        
        return UnifiedContact(
            id=str(discord_user.get("id", "")),
            name=discord_user.get("global_name") or discord_user.get("username", "Unknown"),
            channel_type=ChannelType.DISCORD,
            instance_name=instance_name,
            avatar_url=DiscordTransformer._build_avatar_url(discord_user),
            status=status_map.get(discord_user.get("status"), UnifiedContactStatus.UNKNOWN),
            is_verified=discord_user.get("verified"),
            channel_data={
                "username": discord_user.get("username"),
                "discriminator": discord_user.get("discriminator"),
                "global_name": discord_user.get("global_name"), 
                "is_bot": discord_user.get("bot", False),
                "is_system": discord_user.get("system", False),
                "activities": discord_user.get("activities", []),
                "raw_data": discord_user
            }
        )
    
    @staticmethod
    def chat_to_unified(discord_channel: Dict[str, Any], instance_name: str) -> UnifiedChat:
        """Transform Discord channel to unified format."""
        # Map Discord channel types
        type_map = {
            0: UnifiedChatType.DIRECT,    # DM
            1: UnifiedChatType.DIRECT,    # DM  
            2: UnifiedChatType.GROUP,     # Group DM
            4: UnifiedChatType.CHANNEL,   # Guild category
            5: UnifiedChatType.CHANNEL,   # Guild text
            10: UnifiedChatType.THREAD,   # Guild news thread
            11: UnifiedChatType.THREAD,   # Guild public thread
            12: UnifiedChatType.THREAD,   # Guild private thread
        }
        
        channel_type = discord_channel.get("type", 0)
        chat_type = type_map.get(channel_type, UnifiedChatType.CHANNEL)
        
        return UnifiedChat(
            id=str(discord_channel.get("id", "")),
            name=discord_channel.get("name") or f"DM-{discord_channel.get('id')}",
            chat_type=chat_type,
            channel_type=ChannelType.DISCORD,
            instance_name=instance_name,
            description=discord_channel.get("topic"),
            participant_count=discord_channel.get("member_count"),
            channel_data={
                "guild_id": discord_channel.get("guild_id"),
                "category_id": discord_channel.get("parent_id"),
                "position": discord_channel.get("position"),
                "nsfw": discord_channel.get("nsfw", False),
                "rate_limit": discord_channel.get("rate_limit_per_user"),
                "permissions": discord_channel.get("permission_overwrites", []),
                "raw_data": discord_channel
            },
            created_at=DiscordTransformer._parse_snowflake_timestamp(discord_channel.get("id"))
        )
    
    @staticmethod
    def _build_avatar_url(user: Dict[str, Any]) -> Optional[str]:
        """Build Discord avatar URL."""
        if not user.get("avatar"):
            return None
        user_id = user.get("id")
        avatar_hash = user.get("avatar")
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
    
    @staticmethod
    def _parse_snowflake_timestamp(snowflake: Any) -> Optional[datetime]:
        """Parse Discord snowflake to datetime."""
        if not snowflake:
            return None
        try:
            snowflake_int = int(snowflake)
            timestamp = ((snowflake_int >> 22) + 1420070400000) / 1000
            return datetime.fromtimestamp(timestamp)
        except:
            return None
```

## 2. Extended Channel Handler Interface

### 2.1 Unified Channel Handler Extension

```python
# src/channels/unified_base.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from src.channels.base import ChannelHandler
from src.api.schemas.unified import UnifiedContact, UnifiedChat, UnifiedChannelInfo
from src.db.models import InstanceConfig

class UnifiedChannelHandler(ChannelHandler):
    """Extended channel handler with unified operations support."""
    
    @abstractmethod
    async def get_contacts(
        self, 
        instance: InstanceConfig,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> Tuple[List[UnifiedContact], int]:
        """
        Get contacts from this channel in unified format.
        
        Returns:
            Tuple of (contacts_list, total_count)
        """
        pass
    
    @abstractmethod 
    async def get_chats(
        self,
        instance: InstanceConfig, 
        page: int = 1,
        page_size: int = 50,
        chat_type_filter: Optional[str] = None,
        archived: Optional[bool] = None
    ) -> Tuple[List[UnifiedChat], int]:
        """
        Get chats/conversations from this channel in unified format.
        
        Returns:
            Tuple of (chats_list, total_count)
        """
        pass
    
    @abstractmethod
    async def get_channel_info(self, instance: InstanceConfig) -> UnifiedChannelInfo:
        """Get unified channel information."""
        pass
    
    # Optional: Contact-specific operations
    async def get_contact_by_id(self, instance: InstanceConfig, contact_id: str) -> Optional[UnifiedContact]:
        """Get specific contact by ID. Default implementation returns None."""
        return None
    
    # Optional: Chat-specific operations  
    async def get_chat_by_id(self, instance: InstanceConfig, chat_id: str) -> Optional[UnifiedChat]:
        """Get specific chat by ID. Default implementation returns None."""
        return None
    
    # Health check for unified operations
    async def check_unified_health(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Check health status for unified operations."""
        return {
            "contacts_available": True,
            "chats_available": True, 
            "healthy": True,
            "last_check": datetime.now().isoformat()
        }
```

### 2.2 WhatsApp Handler Extension

```python
# src/channels/whatsapp/unified_handler.py  
from typing import List, Optional, Tuple
from src.channels.unified_base import UnifiedChannelHandler
from src.channels.whatsapp.channel_handler import WhatsAppChannelHandler
from src.services.unified_transformers import WhatsAppTransformer
from src.api.schemas.unified import UnifiedContact, UnifiedChat, UnifiedChannelInfo, ChannelType
from src.db.models import InstanceConfig
import logging

logger = logging.getLogger(__name__)

class WhatsAppUnifiedHandler(WhatsAppChannelHandler, UnifiedChannelHandler):
    """WhatsApp handler with unified operations support."""
    
    async def get_contacts(
        self,
        instance: InstanceConfig,
        page: int = 1, 
        page_size: int = 50,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> Tuple[List[UnifiedContact], int]:
        """Get WhatsApp contacts in unified format."""
        try:
            evolution_client = self._get_evolution_client(instance)
            
            # Get contacts from Evolution API
            contacts_response = await evolution_client.fetch_contacts(
                instance_name=instance.whatsapp_instance,
                limit=page_size,
                offset=(page - 1) * page_size
            )
            
            contacts_data = contacts_response.get("data", [])
            total_count = contacts_response.get("total", len(contacts_data))
            
            # Filter by search query if provided
            if search_query:
                contacts_data = [
                    c for c in contacts_data 
                    if search_query.lower() in c.get("name", "").lower() or 
                       search_query.lower() in c.get("pushName", "").lower()
                ]
                total_count = len(contacts_data)
            
            # Transform to unified format
            unified_contacts = [
                WhatsAppTransformer.contact_to_unified(contact, instance.name)
                for contact in contacts_data
            ]
            
            return unified_contacts, total_count
            
        except Exception as e:
            logger.error(f"Error getting WhatsApp contacts for {instance.name}: {e}")
            return [], 0
    
    async def get_chats(
        self,
        instance: InstanceConfig,
        page: int = 1,
        page_size: int = 50, 
        chat_type_filter: Optional[str] = None,
        archived: Optional[bool] = None
    ) -> Tuple[List[UnifiedChat], int]:
        """Get WhatsApp chats in unified format."""
        try:
            evolution_client = self._get_evolution_client(instance)
            
            # Get chats from Evolution API
            chats_response = await evolution_client.fetch_chats(
                instance_name=instance.whatsapp_instance,
                limit=page_size,
                offset=(page - 1) * page_size,
                archived=archived
            )
            
            chats_data = chats_response.get("data", [])
            total_count = chats_response.get("total", len(chats_data))
            
            # Filter by chat type if specified
            if chat_type_filter:
                if chat_type_filter == "group":
                    chats_data = [c for c in chats_data if c.get("id", "").endswith("@g.us")]
                elif chat_type_filter == "direct":
                    chats_data = [c for c in chats_data if c.get("id", "").endswith("@c.us")]
                total_count = len(chats_data)
            
            # Transform to unified format
            unified_chats = [
                WhatsAppTransformer.chat_to_unified(chat, instance.name)
                for chat in chats_data
            ]
            
            return unified_chats, total_count
            
        except Exception as e:
            logger.error(f"Error getting WhatsApp chats for {instance.name}: {e}")
            return [], 0
    
    async def get_channel_info(self, instance: InstanceConfig) -> UnifiedChannelInfo:
        """Get WhatsApp channel information."""
        try:
            # Get connection status
            status_response = await self.get_status(instance)
            
            # Get instance statistics (contacts/chats count)
            evolution_client = self._get_evolution_client(instance)
            stats = await evolution_client.get_instance_stats(instance.whatsapp_instance)
            
            return UnifiedChannelInfo(
                instance_name=instance.name,
                channel_type=ChannelType.WHATSAPP,
                display_name=f"WhatsApp - {instance.name}",
                status=status_response.status,
                is_healthy=status_response.status == "connected",
                supports_contacts=True,
                supports_groups=True,
                supports_media=True,
                supports_voice=True,
                total_contacts=stats.get("contacts_count"),
                total_chats=stats.get("chats_count"),
                channel_data={
                    "phone_number": stats.get("phone_number"),
                    "profile_name": stats.get("profile_name"),
                    "profile_picture": stats.get("profile_picture"),
                    "evolution_instance": instance.whatsapp_instance,
                    "webhook_base64": instance.webhook_base64
                },
                connected_at=stats.get("connected_at"),
                last_activity_at=stats.get("last_activity")
            )
            
        except Exception as e:
            logger.error(f"Error getting WhatsApp channel info for {instance.name}: {e}")
            return UnifiedChannelInfo(
                instance_name=instance.name,
                channel_type=ChannelType.WHATSAPP,
                display_name=f"WhatsApp - {instance.name}",
                status="error", 
                is_healthy=False,
                supports_contacts=True,
                supports_groups=True,
                supports_media=True,
                supports_voice=True,
                channel_data={"error": str(e)}
            )

    async def get_contact_by_id(self, instance: InstanceConfig, contact_id: str) -> Optional[UnifiedContact]:
        """Get specific WhatsApp contact by ID."""
        try:
            evolution_client = self._get_evolution_client(instance)
            contact_data = await evolution_client.get_contact(instance.whatsapp_instance, contact_id)
            
            if contact_data:
                return WhatsAppTransformer.contact_to_unified(contact_data, instance.name)
            return None
            
        except Exception as e:
            logger.error(f"Error getting WhatsApp contact {contact_id} for {instance.name}: {e}")
            return None

    async def get_chat_by_id(self, instance: InstanceConfig, chat_id: str) -> Optional[UnifiedChat]:
        """Get specific WhatsApp chat by ID."""
        try:
            evolution_client = self._get_evolution_client(instance)
            chat_data = await evolution_client.get_chat(instance.whatsapp_instance, chat_id)
            
            if chat_data:
                return WhatsAppTransformer.chat_to_unified(chat_data, instance.name)
            return None
            
        except Exception as e:
            logger.error(f"Error getting WhatsApp chat {chat_id} for {instance.name}: {e}")
            return None
```

### 2.3 Discord Handler Extension

```python
# src/channels/discord/unified_handler.py
from typing import List, Optional, Tuple
from src.channels.unified_base import UnifiedChannelHandler
from src.channels.discord.channel_handler import DiscordChannelHandler 
from src.services.unified_transformers import DiscordTransformer
from src.api.schemas.unified import UnifiedContact, UnifiedChat, UnifiedChannelInfo, ChannelType
from src.db.models import InstanceConfig
import logging

logger = logging.getLogger(__name__)

class DiscordUnifiedHandler(DiscordChannelHandler, UnifiedChannelHandler):
    """Discord handler with unified operations support."""
    
    async def get_contacts(
        self,
        instance: InstanceConfig,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> Tuple[List[UnifiedContact], int]:
        """Get Discord contacts (guild members + DM users) in unified format."""
        try:
            bot_instance = self._bot_instances.get(instance.name)
            if not bot_instance or not bot_instance.client:
                logger.warning(f"Discord bot not available for {instance.name}")
                return [], 0
            
            client = bot_instance.client
            all_users = []
            
            # Get guild members if connected to a specific guild
            if instance.discord_guild_id:
                guild = client.get_guild(int(instance.discord_guild_id))
                if guild:
                    members = guild.members
                    all_users.extend([{
                        "id": member.id,
                        "username": member.name,
                        "global_name": member.global_name,
                        "discriminator": member.discriminator,
                        "avatar": member.avatar.key if member.avatar else None,
                        "status": str(member.status) if hasattr(member, 'status') else 'unknown',
                        "bot": member.bot,
                        "activities": [str(activity) for activity in member.activities] if hasattr(member, 'activities') else []
                    } for member in members])
            
            # Get DM users  
            for channel in client.private_channels:
                if hasattr(channel, 'recipient') and channel.recipient:
                    user = channel.recipient
                    all_users.append({
                        "id": user.id,
                        "username": user.name,
                        "global_name": user.global_name if hasattr(user, 'global_name') else None,
                        "discriminator": user.discriminator,
                        "avatar": user.avatar.key if user.avatar else None,
                        "status": "unknown",
                        "bot": user.bot,
                        "activities": []
                    })
            
            # Remove duplicates by user ID
            seen_ids = set()
            unique_users = []
            for user in all_users:
                if user["id"] not in seen_ids:
                    unique_users.append(user)
                    seen_ids.add(user["id"])
            
            # Apply search filter
            if search_query:
                query = search_query.lower()
                unique_users = [
                    u for u in unique_users
                    if query in u.get("username", "").lower() or 
                       query in u.get("global_name", "").lower()
                ]
            
            # Apply status filter  
            if status_filter and status_filter != "all":
                unique_users = [u for u in unique_users if u.get("status") == status_filter]
            
            total_count = len(unique_users)
            
            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_users = unique_users[start_idx:end_idx]
            
            # Transform to unified format
            unified_contacts = [
                DiscordTransformer.contact_to_unified(user, instance.name)
                for user in paginated_users
            ]
            
            return unified_contacts, total_count
            
        except Exception as e:
            logger.error(f"Error getting Discord contacts for {instance.name}: {e}")
            return [], 0
    
    async def get_chats(
        self,
        instance: InstanceConfig,
        page: int = 1,
        page_size: int = 50,
        chat_type_filter: Optional[str] = None,
        archived: Optional[bool] = None
    ) -> Tuple[List[UnifiedChat], int]:
        """Get Discord chats (channels + DMs) in unified format."""
        try:
            bot_instance = self._bot_instances.get(instance.name)
            if not bot_instance or not bot_instance.client:
                logger.warning(f"Discord bot not available for {instance.name}")
                return [], 0
                
            client = bot_instance.client
            all_channels = []
            
            # Get guild channels if connected to specific guild
            if instance.discord_guild_id:
                guild = client.get_guild(int(instance.discord_guild_id))
                if guild:
                    for channel in guild.channels:
                        channel_data = {
                            "id": channel.id,
                            "name": channel.name,
                            "type": channel.type.value if hasattr(channel.type, 'value') else 0,
                            "guild_id": guild.id,
                            "position": getattr(channel, 'position', 0),
                            "topic": getattr(channel, 'topic', None),
                            "nsfw": getattr(channel, 'nsfw', False),
                            "rate_limit_per_user": getattr(channel, 'slowmode_delay', 0),
                            "parent_id": channel.category.id if getattr(channel, 'category', None) else None,
                            "member_count": len(channel.members) if hasattr(channel, 'members') else None
                        }
                        all_channels.append(channel_data)
            
            # Get private channels (DMs)
            for channel in client.private_channels:
                channel_data = {
                    "id": channel.id,
                    "name": getattr(channel, 'name', f"DM-{channel.id}"),
                    "type": 1,  # DM type
                    "guild_id": None
                }
                all_channels.append(channel_data)
            
            # Apply chat type filter
            if chat_type_filter:
                if chat_type_filter == "direct":
                    all_channels = [c for c in all_channels if c["type"] in [0, 1]]  # DM types
                elif chat_type_filter == "group":
                    all_channels = [c for c in all_channels if c["type"] == 2]  # Group DM
                elif chat_type_filter == "channel":
                    all_channels = [c for c in all_channels if c["type"] in [4, 5, 6]]  # Guild channels
            
            total_count = len(all_channels)
            
            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size  
            paginated_channels = all_channels[start_idx:end_idx]
            
            # Transform to unified format
            unified_chats = [
                DiscordTransformer.chat_to_unified(channel, instance.name)
                for channel in paginated_channels
            ]
            
            return unified_chats, total_count
            
        except Exception as e:
            logger.error(f"Error getting Discord chats for {instance.name}: {e}")
            return [], 0
    
    async def get_channel_info(self, instance: InstanceConfig) -> UnifiedChannelInfo:
        """Get Discord channel information."""
        try:
            bot_instance = self._bot_instances.get(instance.name)
            is_connected = (bot_instance and 
                          bot_instance.status == "connected" and 
                          bot_instance.client and
                          bot_instance.client.is_ready())
            
            channel_data = {
                "bot_user_id": bot_instance.client.user.id if (bot_instance and bot_instance.client and bot_instance.client.user) else None,
                "bot_username": bot_instance.client.user.name if (bot_instance and bot_instance.client and bot_instance.client.user) else None,
                "guild_count": len(bot_instance.client.guilds) if (bot_instance and bot_instance.client) else 0,
                "connected_guild_id": instance.discord_guild_id,
                "default_channel_id": instance.discord_default_channel_id,
                "voice_enabled": instance.discord_voice_enabled,
                "slash_commands_enabled": instance.discord_slash_commands_enabled
            }
            
            # Get statistics if connected
            total_contacts = 0
            total_chats = 0
            
            if is_connected and bot_instance.client:
                # Count unique members across all guilds
                all_members = set()
                total_chats = len(bot_instance.client.private_channels)
                
                for guild in bot_instance.client.guilds:
                    all_members.update(member.id for member in guild.members)
                    # Count text channels
                    total_chats += len([c for c in guild.channels if hasattr(c, 'send')])
                
                total_contacts = len(all_members)
            
            return UnifiedChannelInfo(
                instance_name=instance.name,
                channel_type=ChannelType.DISCORD,
                display_name=f"Discord - {instance.name}",
                status="connected" if is_connected else "disconnected",
                is_healthy=is_connected,
                supports_contacts=True,
                supports_groups=True,
                supports_media=True,
                supports_voice=instance.discord_voice_enabled or False,
                total_contacts=total_contacts,
                total_chats=total_chats,
                channel_data=channel_data,
                connected_at=bot_instance.connected_at if bot_instance else None,
                last_activity_at=datetime.now() if is_connected else None
            )
            
        except Exception as e:
            logger.error(f"Error getting Discord channel info for {instance.name}: {e}")
            return UnifiedChannelInfo(
                instance_name=instance.name,
                channel_type=ChannelType.DISCORD,
                display_name=f"Discord - {instance.name}",
                status="error",
                is_healthy=False,
                supports_contacts=True,
                supports_groups=True,
                supports_media=True,
                supports_voice=False,
                channel_data={"error": str(e)}
            )
```

## 3. Unified Channel Manager

### 3.1 Core Manager Implementation

```python
# src/services/unified_channel_manager.py
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from src.db.models import InstanceConfig
from src.channels.base import ChannelHandlerFactory
from src.channels.unified_base import UnifiedChannelHandler
from src.api.schemas.unified import (
    UnifiedContactsResponse, UnifiedChatsResponse, UnifiedChannelsResponse,
    UnifiedContact, UnifiedChat, UnifiedChannelInfo, ChannelType
)
from src.core.exceptions import ChannelError, ValidationError
from src.utils.rate_limiter import RateLimiter
import logging

logger = logging.getLogger(__name__)

class UnifiedChannelManager:
    """Manages unified operations across multiple channels."""
    
    def __init__(self):
        """Initialize the unified channel manager."""
        self._rate_limiter = RateLimiter(max_requests=100, time_window=60)  # 100 requests per minute
        self._timeout_config = {
            "contacts": 5.0,  # 5 seconds for contacts
            "chats": 5.0,     # 5 seconds for chats  
            "channels": 3.0,  # 3 seconds for channel info
            "single_item": 2.0  # 2 seconds for single item lookups
        }
    
    async def get_unified_contacts(
        self,
        db: Session,
        instance_name: str,
        channel_type: Optional[ChannelType] = None,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> UnifiedContactsResponse:
        """Get unified contacts across channels."""
        
        # Rate limiting check
        if not await self._rate_limiter.check_rate_limit(f"contacts:{instance_name}"):
            raise ValidationError("Rate limit exceeded for contacts endpoint")
        
        # Get relevant instances
        instances = self._get_instances(db, instance_name, channel_type)
        if not instances:
            raise ValidationError(f"No instances found for: {instance_name}")
        
        # Execute requests in parallel with timeout
        tasks = []
        for instance in instances:
            task = self._get_instance_contacts(
                instance, page, page_size, search_query, status_filter
            )
            tasks.append(task)
        
        # Wait for all tasks with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self._timeout_config["contacts"]
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout getting contacts for {instance_name}")
            results = [TimeoutError("Operation timed out") for _ in tasks]
        
        # Process results
        all_contacts = []
        partial_errors = []
        total_count = 0
        
        for instance, result in zip(instances, results):
            if isinstance(result, Exception):
                error_msg = str(result)
                logger.error(f"Error getting contacts from {instance.name}: {error_msg}")
                partial_errors.append({
                    "instance_name": instance.name,
                    "channel_type": instance.channel_type,
                    "error": error_msg
                })
            else:
                contacts, count = result
                all_contacts.extend(contacts)
                total_count += count
        
        # Sort combined results (by name, then by channel type)
        all_contacts.sort(key=lambda c: (c.name.lower(), c.channel_type.value))
        
        # Apply pagination to combined results
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_contacts = all_contacts[start_idx:end_idx]
        
        return UnifiedContactsResponse(
            contacts=paginated_contacts,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=end_idx < len(all_contacts),
            instance_name=instance_name,
            channel_type=channel_type,
            partial_errors=partial_errors
        )
    
    async def get_unified_chats(
        self,
        db: Session,
        instance_name: str,
        channel_type: Optional[ChannelType] = None,
        page: int = 1,
        page_size: int = 50,
        chat_type_filter: Optional[str] = None,
        archived: Optional[bool] = None
    ) -> UnifiedChatsResponse:
        """Get unified chats across channels."""
        
        # Rate limiting check
        if not await self._rate_limiter.check_rate_limit(f"chats:{instance_name}"):
            raise ValidationError("Rate limit exceeded for chats endpoint")
        
        # Get relevant instances
        instances = self._get_instances(db, instance_name, channel_type)
        if not instances:
            raise ValidationError(f"No instances found for: {instance_name}")
        
        # Execute requests in parallel with timeout
        tasks = []
        for instance in instances:
            task = self._get_instance_chats(
                instance, page, page_size, chat_type_filter, archived
            )
            tasks.append(task)
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self._timeout_config["chats"]
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout getting chats for {instance_name}")
            results = [TimeoutError("Operation timed out") for _ in tasks]
        
        # Process results
        all_chats = []
        partial_errors = []
        total_count = 0
        
        for instance, result in zip(instances, results):
            if isinstance(result, Exception):
                error_msg = str(result)
                logger.error(f"Error getting chats from {instance.name}: {error_msg}")
                partial_errors.append({
                    "instance_name": instance.name,
                    "channel_type": instance.channel_type,
                    "error": error_msg
                })
            else:
                chats, count = result
                all_chats.extend(chats)
                total_count += count
        
        # Sort combined results (by last message time, most recent first)
        all_chats.sort(key=lambda c: c.last_message_at or datetime.min, reverse=True)
        
        # Apply pagination to combined results  
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_chats = all_chats[start_idx:end_idx]
        
        return UnifiedChatsResponse(
            chats=paginated_chats,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=end_idx < len(all_chats),
            instance_name=instance_name,
            channel_type=channel_type,
            partial_errors=partial_errors
        )
    
    async def get_unified_channels(
        self,
        db: Session,
        instance_name: Optional[str] = None,
        channel_type: Optional[ChannelType] = None,
        healthy_only: bool = False
    ) -> UnifiedChannelsResponse:
        """Get unified channel information."""
        
        # Rate limiting check
        cache_key = f"channels:{instance_name or 'all'}"
        if not await self._rate_limiter.check_rate_limit(cache_key):
            raise ValidationError("Rate limit exceeded for channels endpoint")
        
        # Get relevant instances
        instances = self._get_instances(db, instance_name, channel_type)
        
        # Execute requests in parallel with timeout
        tasks = [self._get_instance_channel_info(instance) for instance in instances]
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self._timeout_config["channels"]
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout getting channel info")
            results = [TimeoutError("Operation timed out") for _ in tasks]
        
        # Process results
        all_channels = []
        partial_errors = []
        healthy_count = 0
        
        for instance, result in zip(instances, results):
            if isinstance(result, Exception):
                error_msg = str(result)
                logger.error(f"Error getting channel info from {instance.name}: {error_msg}")
                partial_errors.append({
                    "instance_name": instance.name,
                    "channel_type": instance.channel_type,
                    "error": error_msg
                })
            else:
                channel_info = result
                if not healthy_only or channel_info.is_healthy:
                    all_channels.append(channel_info)
                    if channel_info.is_healthy:
                        healthy_count += 1
        
        # Sort by channel type, then by name
        all_channels.sort(key=lambda c: (c.channel_type.value, c.instance_name))
        
        return UnifiedChannelsResponse(
            channels=all_channels,
            total_count=len(all_channels),
            healthy_count=healthy_count,
            partial_errors=partial_errors
        )
    
    # Helper methods
    
    def _get_instances(
        self, 
        db: Session, 
        instance_name: Optional[str] = None,
        channel_type: Optional[ChannelType] = None
    ) -> List[InstanceConfig]:
        """Get instances based on filters."""
        query = db.query(InstanceConfig)
        
        if instance_name:
            query = query.filter(InstanceConfig.name == instance_name)
        
        if channel_type:
            query = query.filter(InstanceConfig.channel_type == channel_type.value)
        
        return query.all()
    
    async def _get_instance_contacts(
        self,
        instance: InstanceConfig,
        page: int,
        page_size: int,
        search_query: Optional[str],
        status_filter: Optional[str]
    ) -> Tuple[List[UnifiedContact], int]:
        """Get contacts from a specific instance."""
        try:
            handler = ChannelHandlerFactory.get_handler(instance.channel_type)
            if not isinstance(handler, UnifiedChannelHandler):
                logger.warning(f"Handler for {instance.channel_type} doesn't support unified operations")
                return [], 0
            
            return await handler.get_contacts(
                instance=instance,
                page=page,
                page_size=page_size,
                search_query=search_query,
                status_filter=status_filter
            )
        except Exception as e:
            logger.error(f"Error getting contacts from {instance.name}: {e}")
            raise e
    
    async def _get_instance_chats(
        self,
        instance: InstanceConfig,
        page: int,
        page_size: int,
        chat_type_filter: Optional[str],
        archived: Optional[bool]
    ) -> Tuple[List[UnifiedChat], int]:
        """Get chats from a specific instance."""
        try:
            handler = ChannelHandlerFactory.get_handler(instance.channel_type)
            if not isinstance(handler, UnifiedChannelHandler):
                logger.warning(f"Handler for {instance.channel_type} doesn't support unified operations")
                return [], 0
            
            return await handler.get_chats(
                instance=instance,
                page=page,
                page_size=page_size,
                chat_type_filter=chat_type_filter,
                archived=archived
            )
        except Exception as e:
            logger.error(f"Error getting chats from {instance.name}: {e}")
            raise e
    
    async def _get_instance_channel_info(self, instance: InstanceConfig) -> UnifiedChannelInfo:
        """Get channel info from a specific instance."""
        try:
            handler = ChannelHandlerFactory.get_handler(instance.channel_type)
            if not isinstance(handler, UnifiedChannelHandler):
                logger.warning(f"Handler for {instance.channel_type} doesn't support unified operations")
                # Return basic info for non-unified handlers
                return UnifiedChannelInfo(
                    instance_name=instance.name,
                    channel_type=ChannelType(instance.channel_type),
                    display_name=f"{instance.channel_type.title()} - {instance.name}",
                    status="unknown",
                    is_healthy=False,
                    supports_contacts=False,
                    supports_groups=False,
                    supports_media=False,
                    channel_data={"legacy_handler": True}
                )
            
            return await handler.get_channel_info(instance=instance)
        except Exception as e:
            logger.error(f"Error getting channel info from {instance.name}: {e}")
            raise e

# Global instance
unified_channel_manager = UnifiedChannelManager()
```

## 4. API Endpoint Implementation

### 4.1 Unified Endpoints Router

```python
# src/api/routes/unified.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from src.api.deps import get_database, verify_api_key
from src.api.schemas.unified import (
    UnifiedContactsResponse, UnifiedChatsResponse, UnifiedChannelsResponse,
    ChannelType, UnifiedErrorResponse, UnifiedContact, UnifiedChat
)
from src.services.unified_channel_manager import unified_channel_manager
from src.core.exceptions import ValidationError, ChannelError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/unified", tags=["Unified Multi-Channel"])

@router.get(
    "/contacts/{instance_name}",
    response_model=UnifiedContactsResponse,
    summary="Get unified contacts across channels",
    description="""
    Get contacts from all channels for a specific instance in unified format.
    
    - **instance_name**: Instance identifier to query
    - **channel_type**: Optional filter by specific channel type 
    - **page**: Page number for pagination (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)
    - **search**: Optional search query for contact names
    - **status**: Optional filter by contact status (online, offline, away, dnd)
    
    Returns unified contact data with consistent schemas across WhatsApp, Discord, etc.
    Supports graceful degradation - partial results returned if some channels fail.
    """
)
async def get_unified_contacts(
    instance_name: str,
    channel_type: Optional[ChannelType] = Query(None, description="Filter by channel type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query for contact names"),
    status: Optional[str] = Query(None, description="Filter by contact status"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Get unified contacts endpoint."""
    try:
        logger.info(f"Getting unified contacts for {instance_name}, channel_type={channel_type}")
        
        response = await unified_channel_manager.get_unified_contacts(
            db=db,
            instance_name=instance_name,
            channel_type=channel_type,
            page=page,
            page_size=page_size,
            search_query=search,
            status_filter=status
        )
        
        logger.info(f"Retrieved {len(response.contacts)} contacts (total: {response.total_count})")
        return response
        
    except ValidationError as e:
        logger.warning(f"Validation error in unified contacts: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error in unified contacts endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "/chats/{instance_name}",
    response_model=UnifiedChatsResponse,
    summary="Get unified chats across channels",
    description="""
    Get chats/conversations from all channels for a specific instance in unified format.
    
    - **instance_name**: Instance identifier to query
    - **channel_type**: Optional filter by specific channel type
    - **page**: Page number for pagination (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)
    - **chat_type**: Optional filter by chat type (direct, group, channel, thread)
    - **archived**: Optional filter for archived chats (true/false)
    
    Returns unified chat data sorted by last message time (most recent first).
    Supports graceful degradation - partial results returned if some channels fail.
    """
)
async def get_unified_chats(
    instance_name: str,
    channel_type: Optional[ChannelType] = Query(None, description="Filter by channel type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    chat_type: Optional[str] = Query(None, description="Filter by chat type"),
    archived: Optional[bool] = Query(None, description="Filter archived chats"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Get unified chats endpoint."""
    try:
        logger.info(f"Getting unified chats for {instance_name}, channel_type={channel_type}")
        
        response = await unified_channel_manager.get_unified_chats(
            db=db,
            instance_name=instance_name,
            channel_type=channel_type,
            page=page,
            page_size=page_size,
            chat_type_filter=chat_type,
            archived=archived
        )
        
        logger.info(f"Retrieved {len(response.chats)} chats (total: {response.total_count})")
        return response
        
    except ValidationError as e:
        logger.warning(f"Validation error in unified chats: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error in unified chats endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "/channels",
    response_model=UnifiedChannelsResponse,
    summary="Get unified channel information",
    description="""
    Get information about all channel instances in unified format.
    
    - **instance_name**: Optional filter by specific instance
    - **channel_type**: Optional filter by specific channel type  
    - **healthy_only**: Only return healthy/connected channels (default: false)
    
    Returns comprehensive channel status, capabilities, and statistics.
    Useful for monitoring and health checks across all channels.
    """
)
async def get_unified_channels(
    instance_name: Optional[str] = Query(None, description="Filter by instance name"),
    channel_type: Optional[ChannelType] = Query(None, description="Filter by channel type"),
    healthy_only: bool = Query(False, description="Only return healthy channels"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Get unified channels endpoint."""
    try:
        logger.info(f"Getting unified channels, instance={instance_name}, type={channel_type}")
        
        response = await unified_channel_manager.get_unified_channels(
            db=db,
            instance_name=instance_name,
            channel_type=channel_type,
            healthy_only=healthy_only
        )
        
        logger.info(f"Retrieved {len(response.channels)} channels ({response.healthy_count} healthy)")
        return response
        
    except ValidationError as e:
        logger.warning(f"Validation error in unified channels: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error in unified channels endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Individual item endpoints for specific lookups

@router.get(
    "/contact/{instance_name}/{contact_id}",
    response_model=UnifiedContact,
    summary="Get specific contact by ID",
    description="""
    Get a specific contact by ID from any channel in unified format.
    
    - **instance_name**: Instance identifier
    - **contact_id**: Unique contact identifier within the channel
    - **channel_type**: Optional channel type hint for faster lookup
    
    Returns single contact in unified format or 404 if not found.
    """
)
async def get_unified_contact(
    instance_name: str,
    contact_id: str,
    channel_type: Optional[ChannelType] = Query(None, description="Channel type hint"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Get specific contact endpoint."""
    try:
        # Implementation for single contact lookup
        # This would use the channel handlers' get_contact_by_id methods
        logger.info(f"Getting contact {contact_id} from {instance_name}")
        
        # Get relevant instances
        instances = unified_channel_manager._get_instances(db, instance_name, channel_type)
        if not instances:
            raise HTTPException(status_code=404, detail="Instance not found")
        
        # Try each instance until we find the contact
        for instance in instances:
            try:
                handler = ChannelHandlerFactory.get_handler(instance.channel_type)
                if hasattr(handler, 'get_contact_by_id'):
                    contact = await handler.get_contact_by_id(instance, contact_id)
                    if contact:
                        return contact
            except Exception as e:
                logger.warning(f"Error getting contact from {instance.name}: {e}")
                continue
        
        raise HTTPException(status_code=404, detail="Contact not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get contact endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "/chat/{instance_name}/{chat_id}",
    response_model=UnifiedChat,
    summary="Get specific chat by ID",
    description="""
    Get a specific chat by ID from any channel in unified format.
    
    - **instance_name**: Instance identifier
    - **chat_id**: Unique chat identifier within the channel
    - **channel_type**: Optional channel type hint for faster lookup
    
    Returns single chat in unified format or 404 if not found.
    """
)
async def get_unified_chat(
    instance_name: str,
    chat_id: str,
    channel_type: Optional[ChannelType] = Query(None, description="Channel type hint"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Get specific chat endpoint."""
    try:
        logger.info(f"Getting chat {chat_id} from {instance_name}")
        
        # Get relevant instances
        instances = unified_channel_manager._get_instances(db, instance_name, channel_type)
        if not instances:
            raise HTTPException(status_code=404, detail="Instance not found")
        
        # Try each instance until we find the chat
        for instance in instances:
            try:
                handler = ChannelHandlerFactory.get_handler(instance.channel_type)
                if hasattr(handler, 'get_chat_by_id'):
                    chat = await handler.get_chat_by_id(instance, chat_id)
                    if chat:
                        return chat
            except Exception as e:
                logger.warning(f"Error getting chat from {instance.name}: {e}")
                continue
        
        raise HTTPException(status_code=404, detail="Chat not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint
@router.get(
    "/health",
    summary="Unified endpoints health check",
    description="Check health status of unified endpoints system"
)
async def unified_health_check(
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key)
):
    """Health check for unified endpoints."""
    try:
        # Quick health check - get channel count
        channels_response = await unified_channel_manager.get_unified_channels(
            db=db, healthy_only=False
        )
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "total_channels": channels_response.total_count,
            "healthy_channels": channels_response.healthy_count,
            "system": "unified-endpoints"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "system": "unified-endpoints"
        }
```

### 4.2 Registration with Main App

```python
# src/api/app.py - Add to existing imports and router registration

from src.api.routes import unified

# Add to existing router includes
app.include_router(unified.router)

# Update OpenAPI metadata
app.openapi_tags = [
    # ... existing tags ...
    {
        "name": "Unified Multi-Channel",
        "description": "Unified endpoints for cross-channel operations. Access contacts, chats, and channels across WhatsApp, Discord, and other platforms with consistent schemas and graceful degradation."
    }
]
```

## 5. Error Handling Strategy

### 5.1 Graceful Degradation Implementation

```python
# src/services/error_handlers.py
from typing import Dict, Any, List, Optional
from src.api.schemas.unified import UnifiedErrorDetail, UnifiedErrorResponse
from src.core.exceptions import ChannelError, ValidationError
import logging

logger = logging.getLogger(__name__)

class PartialResultHandler:
    """Handles graceful degradation for multi-channel operations."""
    
    @staticmethod
    def handle_partial_failures(
        results: List[Any],
        errors: List[Exception],
        instances: List[Any]
    ) -> Dict[str, Any]:
        """Process partial results and errors."""
        
        partial_errors = []
        successful_results = []
        
        for i, (result, error, instance) in enumerate(zip(results, errors, instances)):
            if isinstance(result, Exception) or error:
                error_detail = UnifiedErrorDetail(
                    instance_name=instance.name,
                    channel_type=instance.channel_type,
                    error_code=PartialResultHandler._get_error_code(error or result),
                    error_message=str(error or result),
                    details=PartialResultHandler._get_error_details(error or result)
                )
                partial_errors.append(error_detail.dict())
            else:
                successful_results.append(result)
        
        return {
            "successful_results": successful_results,
            "partial_errors": partial_errors,
            "success_rate": len(successful_results) / len(results) if results else 0
        }
    
    @staticmethod
    def _get_error_code(error: Exception) -> str:
        """Get standardized error code."""
        if isinstance(error, ValidationError):
            return "VALIDATION_ERROR"
        elif isinstance(error, ChannelError):
            return "CHANNEL_ERROR"
        elif isinstance(error, TimeoutError):
            return "TIMEOUT_ERROR"
        elif isinstance(error, ConnectionError):
            return "CONNECTION_ERROR"
        else:
            return "UNKNOWN_ERROR"
    
    @staticmethod
    def _get_error_details(error: Exception) -> Optional[Dict[str, Any]]:
        """Get additional error details."""
        details = {}
        
        if hasattr(error, 'response'):
            details['http_status'] = getattr(error.response, 'status_code', None)
        
        if isinstance(error, TimeoutError):
            details['timeout'] = True
            details['retryable'] = True
        elif isinstance(error, ConnectionError):
            details['connection_issue'] = True
            details['retryable'] = True
        elif isinstance(error, ValidationError):
            details['retryable'] = False
        
        return details if details else None

class UnifiedErrorHandler:
    """Central error handling for unified endpoints."""
    
    @staticmethod
    def create_error_response(
        error: Exception,
        instance_name: Optional[str] = None,
        channel_type: Optional[str] = None
    ) -> UnifiedErrorResponse:
        """Create standardized error response."""
        
        error_detail = UnifiedErrorDetail(
            instance_name=instance_name,
            channel_type=channel_type,
            error_code=PartialResultHandler._get_error_code(error),
            error_message=str(error),
            details=PartialResultHandler._get_error_details(error)
        )
        
        return UnifiedErrorResponse(
            error=str(error),
            details=[error_detail]
        )
    
    @staticmethod
    def log_error(
        error: Exception,
        endpoint: str,
        instance_name: Optional[str] = None,
        channel_type: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Log error with context."""
        context = {
            "endpoint": endpoint,
            "instance_name": instance_name,
            "channel_type": channel_type,
            "error_type": type(error).__name__
        }
        
        if additional_context:
            context.update(additional_context)
        
        logger.error(f"Unified endpoint error: {error}", extra=context)
```

## 6. Performance Optimization

### 6.1 Caching Strategy

```python
# src/services/unified_cache.py
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with TTL."""
    data: Any
    created_at: datetime
    ttl_seconds: int
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)

class UnifiedCache:
    """In-memory cache for unified endpoints with TTL support."""
    
    def __init__(self):
        """Initialize cache."""
        self._cache: Dict[str, CacheEntry] = {}
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = datetime.now()
        
        # Default TTL values (in seconds)
        self._default_ttls = {
            "contacts": 300,     # 5 minutes
            "chats": 180,        # 3 minutes  
            "channels": 60,      # 1 minute
            "contact_item": 600, # 10 minutes
            "chat_item": 600     # 10 minutes
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        await self._cleanup_if_needed()
        
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            logger.debug(f"Cache hit for key: {key}")
            return entry.data
        
        if entry:
            # Remove expired entry
            del self._cache[key]
            logger.debug(f"Cache entry expired and removed: {key}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set item in cache with TTL."""
        if ttl is None:
            # Determine TTL based on key pattern
            ttl = self._get_default_ttl(key)
        
        entry = CacheEntry(
            data=value,
            created_at=datetime.now(),
            ttl_seconds=ttl
        )
        
        self._cache[key] = entry
        logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")
    
    async def delete(self, key: str) -> None:
        """Delete item from cache."""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache entry deleted: {key}")
    
    async def clear_instance(self, instance_name: str) -> None:
        """Clear all cache entries for an instance."""
        keys_to_delete = [
            key for key in self._cache.keys() 
            if f":{instance_name}:" in key or key.endswith(f":{instance_name}")
        ]
        
        for key in keys_to_delete:
            del self._cache[key]
        
        logger.info(f"Cleared cache for instance: {instance_name} ({len(keys_to_delete)} entries)")
    
    def _get_default_ttl(self, key: str) -> int:
        """Get default TTL based on key pattern."""
        for pattern, ttl in self._default_ttls.items():
            if pattern in key:
                return ttl
        return 300  # Default 5 minutes
    
    async def _cleanup_if_needed(self) -> None:
        """Periodic cleanup of expired entries."""
        now = datetime.now()
        if now - self._last_cleanup < timedelta(seconds=self._cleanup_interval):
            return
        
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        self._last_cleanup = now
        if expired_keys:
            logger.info(f"Cache cleanup removed {len(expired_keys)} expired entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired)
        
        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "last_cleanup": self._last_cleanup.isoformat()
        }

# Cache key generators
class CacheKeys:
    """Cache key generators for consistent naming."""
    
    @staticmethod
    def contacts(instance_name: str, page: int, page_size: int, 
                search: Optional[str] = None, status: Optional[str] = None) -> str:
        """Generate cache key for contacts."""
        key_parts = [
            "contacts",
            instance_name,
            f"p{page}",
            f"s{page_size}"
        ]
        
        if search:
            key_parts.append(f"q{search}")
        if status:
            key_parts.append(f"st{status}")
        
        return ":".join(key_parts)
    
    @staticmethod
    def chats(instance_name: str, page: int, page_size: int,
             chat_type: Optional[str] = None, archived: Optional[bool] = None) -> str:
        """Generate cache key for chats."""
        key_parts = [
            "chats", 
            instance_name,
            f"p{page}",
            f"s{page_size}"
        ]
        
        if chat_type:
            key_parts.append(f"t{chat_type}")
        if archived is not None:
            key_parts.append(f"a{archived}")
        
        return ":".join(key_parts)
    
    @staticmethod
    def channels(instance_name: Optional[str] = None, 
                channel_type: Optional[str] = None,
                healthy_only: bool = False) -> str:
        """Generate cache key for channels."""
        key_parts = ["channels"]
        
        if instance_name:
            key_parts.append(instance_name)
        if channel_type:
            key_parts.append(channel_type)
        if healthy_only:
            key_parts.append("healthy")
        
        return ":".join(key_parts)
    
    @staticmethod
    def contact_item(instance_name: str, contact_id: str) -> str:
        """Generate cache key for single contact."""
        return f"contact_item:{instance_name}:{contact_id}"
    
    @staticmethod
    def chat_item(instance_name: str, chat_id: str) -> str:
        """Generate cache key for single chat."""
        return f"chat_item:{instance_name}:{chat_id}"

# Global cache instance
unified_cache = UnifiedCache()
```

### 6.2 Cache Integration with Manager

```python
# src/services/unified_channel_manager.py - Add caching to existing methods

from src.services.unified_cache import unified_cache, CacheKeys

class UnifiedChannelManager:
    """Updated manager with caching support."""
    
    async def get_unified_contacts(
        self,
        db: Session,
        instance_name: str,
        channel_type: Optional[ChannelType] = None,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> UnifiedContactsResponse:
        """Get unified contacts with caching."""
        
        # Generate cache key
        cache_key = CacheKeys.contacts(
            instance_name, page, page_size, search_query, status_filter
        )
        
        # Try cache first
        cached_result = await unified_cache.get(cache_key)
        if cached_result:
            logger.debug(f"Returning cached contacts for {instance_name}")
            return UnifiedContactsResponse(**cached_result)
        
        # Cache miss - get fresh data
        result = await self._get_unified_contacts_fresh(
            db, instance_name, channel_type, page, page_size, search_query, status_filter
        )
        
        # Cache the result
        await unified_cache.set(cache_key, result.dict())
        
        return result
    
    async def _get_unified_contacts_fresh(self, ...):
        """Original get_unified_contacts logic without caching."""
        # Implementation from previous version
        pass
    
    # Similar caching for chats and channels...
```

## 7. Testing Strategy

### 7.1 Unit Tests for Unified Endpoints

```python
# tests/test_unified_endpoints.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from src.api.app import app
from src.api.schemas.unified import UnifiedContact, ChannelType

class TestUnifiedEndpoints:
    """Test suite for unified endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def sample_instances(self):
        """Sample instance configurations."""
        return [
            Mock(
                name="test_whatsapp",
                channel_type="whatsapp",
                whatsapp_instance="test_wa"
            ),
            Mock(
                name="test_discord", 
                channel_type="discord",
                discord_bot_token="test_token"
            )
        ]
    
    def test_get_unified_contacts_success(self, client, mock_db_session, sample_instances):
        """Test successful contacts retrieval."""
        with patch('src.api.routes.unified.get_database') as mock_get_db:
            with patch('src.api.routes.unified.verify_api_key') as mock_verify:
                with patch('src.services.unified_channel_manager.unified_channel_manager.get_unified_contacts') as mock_manager:
                    
                    # Setup mocks
                    mock_get_db.return_value = mock_db_session
                    mock_verify.return_value = "test_key"
                    
                    mock_response = Mock()
                    mock_response.contacts = [
                        UnifiedContact(
                            id="test_contact_1",
                            name="Test Contact",
                            channel_type=ChannelType.WHATSAPP,
                            instance_name="test_whatsapp"
                        )
                    ]
                    mock_response.total_count = 1
                    mock_response.dict.return_value = {
                        "contacts": [mock_response.contacts[0].dict()],
                        "total_count": 1,
                        "page": 1,
                        "page_size": 50,
                        "has_more": False,
                        "instance_name": "test_whatsapp",
                        "channel_type": None,
                        "partial_errors": []
                    }
                    
                    mock_manager.return_value = mock_response
                    
                    # Make request
                    response = client.get(
                        "/unified/contacts/test_whatsapp",
                        headers={"Authorization": "Bearer test_key"}
                    )
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert len(data["contacts"]) == 1
                    assert data["contacts"][0]["name"] == "Test Contact"
                    assert data["total_count"] == 1
    
    def test_get_unified_contacts_with_filters(self, client):
        """Test contacts endpoint with query filters."""
        with patch('src.api.routes.unified.get_database'):
            with patch('src.api.routes.unified.verify_api_key'):
                with patch('src.services.unified_channel_manager.unified_channel_manager.get_unified_contacts') as mock_manager:
                    
                    mock_manager.return_value = Mock(dict=lambda: {"contacts": [], "total_count": 0})
                    
                    response = client.get(
                        "/unified/contacts/test_instance",
                        params={
                            "channel_type": "whatsapp",
                            "page": 2,
                            "page_size": 25,
                            "search": "john",
                            "status": "online"
                        },
                        headers={"Authorization": "Bearer test_key"}
                    )
                    
                    # Verify manager was called with correct parameters
                    mock_manager.assert_called_once()
                    args, kwargs = mock_manager.call_args
                    assert kwargs["instance_name"] == "test_instance"
                    assert kwargs["channel_type"] == ChannelType.WHATSAPP
                    assert kwargs["page"] == 2
                    assert kwargs["page_size"] == 25
                    assert kwargs["search_query"] == "john"
                    assert kwargs["status_filter"] == "online"
    
    def test_get_unified_contacts_validation_error(self, client):
        """Test contacts endpoint validation error handling."""
        with patch('src.api.routes.unified.get_database'):
            with patch('src.api.routes.unified.verify_api_key'):
                with patch('src.services.unified_channel_manager.unified_channel_manager.get_unified_contacts') as mock_manager:
                    
                    from src.core.exceptions import ValidationError
                    mock_manager.side_effect = ValidationError("Rate limit exceeded")
                    
                    response = client.get(
                        "/unified/contacts/test_instance",
                        headers={"Authorization": "Bearer test_key"}
                    )
                    
                    assert response.status_code == 422
                    assert "Rate limit exceeded" in response.json()["detail"]
    
    def test_get_unified_chats_success(self, client):
        """Test successful chats retrieval."""
        with patch('src.api.routes.unified.get_database'):
            with patch('src.api.routes.unified.verify_api_key'):
                with patch('src.services.unified_channel_manager.unified_channel_manager.get_unified_chats') as mock_manager:
                    
                    mock_response = Mock()
                    mock_response.dict.return_value = {
                        "chats": [],
                        "total_count": 0,
                        "page": 1,
                        "page_size": 50,
                        "has_more": False,
                        "instance_name": "test_instance",
                        "channel_type": None,
                        "partial_errors": []
                    }
                    mock_manager.return_value = mock_response
                    
                    response = client.get(
                        "/unified/chats/test_instance",
                        headers={"Authorization": "Bearer test_key"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert "chats" in data
                    assert "total_count" in data
    
    def test_get_unified_channels_success(self, client):
        """Test successful channels retrieval."""
        with patch('src.api.routes.unified.get_database'):
            with patch('src.api.routes.unified.verify_api_key'):
                with patch('src.services.unified_channel_manager.unified_channel_manager.get_unified_channels') as mock_manager:
                    
                    mock_response = Mock()
                    mock_response.dict.return_value = {
                        "channels": [],
                        "total_count": 0,
                        "healthy_count": 0,
                        "partial_errors": []
                    }
                    mock_manager.return_value = mock_response
                    
                    response = client.get(
                        "/unified/channels",
                        headers={"Authorization": "Bearer test_key"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert "channels" in data
                    assert "total_count" in data
                    assert "healthy_count" in data
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        with patch('src.api.routes.unified.get_database'):
            with patch('src.api.routes.unified.verify_api_key'):
                with patch('src.services.unified_channel_manager.unified_channel_manager.get_unified_channels') as mock_manager:
                    
                    mock_response = Mock()
                    mock_response.total_count = 5
                    mock_response.healthy_count = 4
                    mock_manager.return_value = mock_response
                    
                    response = client.get(
                        "/unified/health",
                        headers={"Authorization": "Bearer test_key"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "healthy"
                    assert data["total_channels"] == 5
                    assert data["healthy_channels"] == 4
```

### 7.2 Integration Tests

```python
# tests/test_unified_integration.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.services.unified_channel_manager import UnifiedChannelManager
from src.services.unified_transformers import WhatsAppTransformer, DiscordTransformer
from src.api.schemas.unified import ChannelType

class TestUnifiedIntegration:
    """Integration tests for unified endpoints."""
    
    @pytest.fixture
    async def manager(self):
        """Unified channel manager fixture."""
        return UnifiedChannelManager()
    
    @pytest.fixture
    def sample_whatsapp_contact(self):
        """Sample WhatsApp contact data."""
        return {
            "id": "5511999999999@c.us",
            "name": "John Doe",
            "pushName": "John",
            "profilePictureUrl": "https://example.com/avatar.jpg",
            "isVerified": True,
            "isBusiness": False,
            "isMyContact": True,
            "presence": "available"
        }
    
    @pytest.fixture  
    def sample_discord_user(self):
        """Sample Discord user data."""
        return {
            "id": "123456789012345678",
            "username": "johndoe",
            "global_name": "John Doe", 
            "discriminator": "1234",
            "avatar": "abc123def456",
            "status": "online",
            "bot": False,
            "activities": ["Playing Spotify"]
        }
    
    def test_whatsapp_transformer_contact(self, sample_whatsapp_contact):
        """Test WhatsApp contact transformation."""
        unified_contact = WhatsAppTransformer.contact_to_unified(
            sample_whatsapp_contact, "test_instance"
        )
        
        assert unified_contact.id == "5511999999999@c.us"
        assert unified_contact.name == "John"  # Uses pushName
        assert unified_contact.channel_type == ChannelType.WHATSAPP
        assert unified_contact.instance_name == "test_instance"
        assert unified_contact.is_verified == True
        assert unified_contact.is_business == False
        assert unified_contact.channel_data["phone_number"] == "5511999999999"
    
    def test_discord_transformer_contact(self, sample_discord_user):
        """Test Discord user transformation."""
        unified_contact = DiscordTransformer.contact_to_unified(
            sample_discord_user, "test_instance"
        )
        
        assert unified_contact.id == "123456789012345678"
        assert unified_contact.name == "John Doe"  # Uses global_name
        assert unified_contact.channel_type == ChannelType.DISCORD
        assert unified_contact.instance_name == "test_instance"
        assert unified_contact.channel_data["username"] == "johndoe"
        assert unified_contact.channel_data["is_bot"] == False
    
    @pytest.mark.asyncio
    async def test_manager_parallel_execution(self, manager):
        """Test manager executes channel queries in parallel."""
        
        # Mock instances
        whatsapp_instance = Mock()
        whatsapp_instance.name = "wa_test"
        whatsapp_instance.channel_type = "whatsapp"
        
        discord_instance = Mock()
        discord_instance.name = "discord_test"
        discord_instance.channel_type = "discord"
        
        instances = [whatsapp_instance, discord_instance]
        
        # Mock the channel operations to simulate different response times
        async def slow_whatsapp_operation(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return [Mock()], 1
        
        async def fast_discord_operation(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            return [Mock()], 1
        
        with patch.object(manager, '_get_instances', return_value=instances):
            with patch.object(manager, '_get_instance_contacts') as mock_get_contacts:
                mock_get_contacts.side_effect = [
                    slow_whatsapp_operation(),
                    fast_discord_operation()
                ]
                
                # Measure execution time
                import time
                start_time = time.time()
                
                db = Mock()
                result = await manager.get_unified_contacts(
                    db=db,
                    instance_name="test",
                    page=1,
                    page_size=50
                )
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Should complete in ~100ms (not 150ms if sequential)
                assert execution_time < 0.15  # Allow some overhead
                assert len(mock_get_contacts.call_args_list) == 2
    
    @pytest.mark.asyncio
    async def test_manager_timeout_handling(self, manager):
        """Test manager handles timeouts gracefully."""
        
        # Mock instance that will timeout
        timeout_instance = Mock()
        timeout_instance.name = "timeout_test"
        timeout_instance.channel_type = "whatsapp"
        
        async def timeout_operation(*args, **kwargs):
            await asyncio.sleep(10)  # Long delay to trigger timeout
            return [], 0
        
        with patch.object(manager, '_get_instances', return_value=[timeout_instance]):
            with patch.object(manager, '_get_instance_contacts', side_effect=timeout_operation):
                
                db = Mock()
                result = await manager.get_unified_contacts(
                    db=db,
                    instance_name="test",
                    page=1,
                    page_size=50
                )
                
                # Should have partial errors due to timeout
                assert len(result.partial_errors) == 1
                assert "timeout" in result.partial_errors[0]["error"].lower()
                assert len(result.contacts) == 0
    
    @pytest.mark.asyncio
    async def test_manager_partial_failure_handling(self, manager):
        """Test manager handles partial failures correctly."""
        
        # Mock instances - one success, one failure
        success_instance = Mock()
        success_instance.name = "success_test"
        success_instance.channel_type = "whatsapp"
        
        failure_instance = Mock()
        failure_instance.name = "failure_test"
        failure_instance.channel_type = "discord"
        
        instances = [success_instance, failure_instance]
        
        async def success_operation(*args, **kwargs):
            return [Mock(name="Test Contact")], 1
        
        async def failure_operation(*args, **kwargs):
            raise Exception("Connection failed")
        
        with patch.object(manager, '_get_instances', return_value=instances):
            with patch.object(manager, '_get_instance_contacts') as mock_get_contacts:
                mock_get_contacts.side_effect = [
                    success_operation(),
                    failure_operation()
                ]
                
                db = Mock()
                result = await manager.get_unified_contacts(
                    db=db,
                    instance_name="test",
                    page=1,
                    page_size=50
                )
                
                # Should have one success and one error
                assert len(result.contacts) == 1
                assert len(result.partial_errors) == 1
                assert result.partial_errors[0]["instance_name"] == "failure_test"
                assert "Connection failed" in result.partial_errors[0]["error"]
```

## 8. Implementation Plan

### 8.1 Phase 1: Core Infrastructure (Week 1-2)

**Priority**: High
**Dependencies**: None

**Tasks:**
1. **Create Unified Schema Models** (`src/api/schemas/unified.py`)
   - Implement all UnifiedContact, UnifiedChat, UnifiedChannelInfo models
   - Add response wrapper models with pagination support
   - Create error response models for graceful degradation

2. **Implement Data Transformers** (`src/services/unified_transformers.py`)
   - WhatsAppTransformer with contact/chat transformation methods
   - DiscordTransformer with user/channel transformation methods
   - Add datetime parsing utilities and error handling

3. **Extend Channel Handler Base** (`src/channels/unified_base.py`)
   - Create UnifiedChannelHandler ABC extending ChannelHandler
   - Define unified operation interfaces (get_contacts, get_chats, get_channel_info)
   - Add optional single-item lookup methods

**Acceptance Criteria:**
- All schema models validate correctly with Pydantic
- Transformers handle real WhatsApp/Discord API responses
- Base handler interface is properly defined and documented

### 8.2 Phase 2: Channel Handler Implementation (Week 2-3)

**Priority**: High  
**Dependencies**: Phase 1

**Tasks:**
1. **WhatsApp Unified Handler** (`src/channels/whatsapp/unified_handler.py`)
   - Extend WhatsAppChannelHandler with UnifiedChannelHandler
   - Implement contacts/chats retrieval with pagination
   - Add search and filtering capabilities
   - Handle Evolution API errors gracefully

2. **Discord Unified Handler** (`src/channels/discord/unified_handler.py`)
   - Extend DiscordChannelHandler with UnifiedChannelHandler  
   - Implement guild members and DM users as contacts
   - Implement channels and DMs as chats
   - Add Discord-specific error handling

3. **Update Channel Factory Registration**
   - Register new unified handlers in factory
   - Update existing imports and initialization
   - Ensure backward compatibility

**Acceptance Criteria:**
- Both handlers return unified format data correctly
- Pagination works across both channel types
- Error handling provides useful feedback
- Performance is within sub-500ms targets for typical requests

### 8.3 Phase 3: Unified Manager & API (Week 3-4)

**Priority**: High
**Dependencies**: Phase 2

**Tasks:**
1. **Unified Channel Manager** (`src/services/unified_channel_manager.py`)
   - Implement parallel execution across multiple channels
   - Add timeout handling and graceful degradation
   - Implement rate limiting per instance/endpoint
   - Add comprehensive error aggregation

2. **API Endpoints** (`src/api/routes/unified.py`)
   - Implement all unified endpoints with proper documentation
   - Add query parameter validation and filtering
   - Implement proper HTTP status codes and error responses
   - Add health check endpoint

3. **Integration with Main App**
   - Register unified router in main FastAPI app
   - Update OpenAPI documentation and tags
   - Ensure authentication works correctly

**Acceptance Criteria:**
- All endpoints return consistent unified responses
- Parallel execution improves performance significantly
- Graceful degradation works when individual channels fail
- API documentation is comprehensive and accurate

### 8.4 Phase 4: Performance & Caching (Week 4-5)

**Priority**: Medium
**Dependencies**: Phase 3

**Tasks:**
1. **Caching Implementation** (`src/services/unified_cache.py`)
   - Implement in-memory cache with TTL support
   - Add cache key generators for consistent naming
   - Implement cache invalidation strategies
   - Add cache statistics and monitoring

2. **Manager Cache Integration**
   - Add caching to UnifiedChannelManager methods
   - Implement cache-aside pattern
   - Add cache warming for frequently accessed data
   - Add cache health monitoring

3. **Performance Optimization**
   - Profile endpoint performance under load
   - Optimize database queries and connection usage
   - Fine-tune timeout values for optimal balance
   - Add performance logging and metrics

**Acceptance Criteria:**
- Sub-500ms response times achieved for cached data
- Cache hit rates >80% for typical usage patterns  
- Memory usage remains stable under load
- Performance degrades gracefully under high load

### 8.5 Phase 5: Testing & Documentation (Week 5-6)

**Priority**: Medium
**Dependencies**: Phase 4

**Tasks:**
1. **Unit Tests**
   - Test all schema models and transformers
   - Test unified handlers with mocked dependencies
   - Test manager with various failure scenarios
   - Test API endpoints with comprehensive cases

2. **Integration Tests**
   - Test end-to-end flows with real channel handlers
   - Test performance under concurrent load
   - Test graceful degradation scenarios
   - Test caching behavior and invalidation

3. **Documentation Updates**
   - Update API documentation with unified endpoints
   - Create developer guide for extending unified system
   - Add troubleshooting guide for common issues
   - Update deployment documentation

**Acceptance Criteria:**
- Test coverage >90% for all unified endpoint code
- Integration tests pass consistently
- Documentation is comprehensive and up-to-date
- Performance benchmarks meet requirements

### 8.6 Phase 6: Production Readiness (Week 6)

**Priority**: Low
**Dependencies**: Phase 5

**Tasks:**
1. **Monitoring & Observability**
   - Add structured logging for all unified operations
   - Add metrics for endpoint performance and success rates
   - Add health check monitoring and alerting
   - Add error tracking and reporting

2. **Production Configuration**
   - Add production-ready timeout and rate limit configurations
   - Add environment-specific cache settings
   - Add graceful shutdown handling
   - Add resource limit configuration

3. **Deployment Preparation**
   - Update deployment scripts for unified endpoints
   - Add migration scripts if needed
   - Add rollback procedures
   - Test deployment in staging environment

**Acceptance Criteria:**
- Comprehensive monitoring and alerting in place
- Production configuration tested and validated
- Deployment procedures documented and tested
- System ready for production traffic

## 9. Migration Strategy

### 9.1 Backward Compatibility

The unified endpoints are designed to be **fully backward compatible**:

- **Existing endpoints remain unchanged**: All current WhatsApp and Discord endpoints continue to work exactly as before
- **Additive changes only**: New unified endpoints are added alongside existing ones
- **No breaking changes**: Existing client integrations are not affected
- **Gradual migration path**: Clients can migrate to unified endpoints at their own pace

### 9.2 Rollout Plan

1. **Phase 1: Internal Testing**
   - Deploy unified endpoints in staging environment
   - Extensive testing with internal tools and scripts
   - Performance validation and optimization

2. **Phase 2: Beta Release**
   - Enable unified endpoints for selected beta customers
   - Monitor performance, error rates, and feedback
   - Iterative improvements based on real usage

3. **Phase 3: General Availability**
   - Full rollout to all customers
   - Update documentation and provide migration guides
   - Continue monitoring and optimization

4. **Phase 4: Optimization**
   - Performance tuning based on production usage patterns
   - Feature enhancements based on user feedback
   - Long-term architectural improvements

## 10. Monitoring and Observability

### 10.1 Key Metrics

**Performance Metrics:**
- Response time percentiles (P50, P95, P99) for each endpoint
- Request rate per endpoint and instance
- Error rates by error type and channel
- Cache hit rates and effectiveness

**Business Metrics:**
- Active instances per channel type
- Request distribution across channels
- Feature adoption rates (unified vs legacy endpoints)
- Customer satisfaction scores

**System Metrics:**
- Memory usage for caching layer
- Database connection pool utilization
- External API call success rates and latencies
- Resource utilization under various load patterns

### 10.2 Alerting Strategy

**Critical Alerts:**
- Response time > 1000ms for 5+ minutes
- Error rate > 10% for any endpoint
- Any instance completely unavailable
- Cache system failure or excessive memory usage

**Warning Alerts:**
- Response time > 500ms for 10+ minutes
- Error rate > 5% for any endpoint
- Cache hit rate < 60%
- High resource utilization (>80% for 15+ minutes)

## 11. Future Extensions

### 11.1 Additional Channel Support

The unified system is designed to easily support additional channels:

**Planned Channels:**
- **Slack**: Team messaging and bot interactions
- **Telegram**: Messaging and bot API integration
- **Microsoft Teams**: Enterprise communication platform
- **SMS/WhatsApp Business API**: Direct carrier integration

**Extension Process:**
1. Create new transformer class following existing patterns
2. Implement UnifiedChannelHandler for the new channel
3. Register handler in ChannelHandlerFactory
4. Add channel-specific configuration fields to InstanceConfig
5. Test and deploy with existing unified endpoints

### 11.2 Advanced Features

**Response Streaming:** Real-time updates for contacts and chats using Server-Sent Events or WebSockets

**Cross-Channel Operations:** Unified messaging that can send to multiple channels simultaneously

**Advanced Analytics:** Cross-channel conversation analysis and user behavior insights

**AI-Powered Features:** Unified sentiment analysis, auto-translation, and smart routing across channels

## Conclusion

This technical design provides a comprehensive implementation plan for unified multi-channel endpoints that leverages automagik-omni's excellent existing architecture. The design ensures:

✅ **Sub-500ms Performance**: Achieved through async operations, caching, and optimized timeouts
✅ **Graceful Degradation**: Partial results when individual channels fail
✅ **Backward Compatibility**: Existing endpoints remain unchanged
✅ **Extensible Architecture**: Easy addition of new channels
✅ **Production Ready**: Comprehensive error handling, monitoring, and testing

The implementation can begin immediately using the existing ChannelHandler foundation, with the dev-coder agent able to implement each phase systematically while maintaining system stability and performance.