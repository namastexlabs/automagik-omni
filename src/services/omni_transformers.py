# src/services/omni_transformers.py
from typing import Dict, Any, Optional
from datetime import datetime
from src.api.schemas.omni import (
    OmniContact,
    OmniChat,
    OmniChannelInfo,
    OmniMessage,
    OmniMessageType,
    ChannelType,
    OmniContactStatus,
    OmniChatType,
)


class WhatsAppTransformer:
    """Transform WhatsApp data to omni format."""

    @staticmethod
    def contact_to_omni(whatsapp_contact: Dict[str, Any], instance_name: str) -> OmniContact:
        """Transform WhatsApp contact to omni format."""
        if not whatsapp_contact:
            return OmniContact(
                id="unknown",
                name="Unknown",
                channel_type=ChannelType.WHATSAPP,
                instance_name=instance_name,
            )
        return OmniContact(
            id=whatsapp_contact.get("id") or "",
            name=whatsapp_contact.get("pushName") or whatsapp_contact.get("name") or "Unknown",
            channel_type=ChannelType.WHATSAPP,
            instance_name=instance_name,
            avatar_url=whatsapp_contact.get("profilePictureUrl"),
            is_verified=whatsapp_contact.get("isVerified"),
            is_business=whatsapp_contact.get("isBusiness"),
            channel_data={
                "phone_number": (whatsapp_contact.get("id") or "").replace("@c.us", ""),
                "is_contact": whatsapp_contact.get("isMyContact", False),
                "presence": whatsapp_contact.get("presence"),
                "whatsapp_name": whatsapp_contact.get("name"),
                "push_name": whatsapp_contact.get("pushName"),
                "raw_data": whatsapp_contact,
            },
            last_seen=WhatsAppTransformer._parse_datetime(whatsapp_contact.get("lastSeen")),
        )

    @staticmethod
    def chat_to_omni(whatsapp_chat: Dict[str, Any], instance_name: str) -> OmniChat:
        """Transform WhatsApp chat to omni format."""
        if not whatsapp_chat:
            return OmniChat(
                id="unknown",
                name="Unknown",
                chat_type=OmniChatType.DIRECT,
                channel_type=ChannelType.WHATSAPP,
                instance_name=instance_name,
            )
        # Determine chat type
        chat_type = OmniChatType.DIRECT
        if whatsapp_chat.get("id", "").endswith("@g.us"):
            chat_type = OmniChatType.GROUP
        elif whatsapp_chat.get("id", "").endswith("@broadcast"):
            chat_type = OmniChatType.CHANNEL

        # Get last message timestamp from nested lastMessage object if available
        last_message_time = whatsapp_chat.get("lastMessageTime")
        if not last_message_time and whatsapp_chat.get("lastMessage"):
            last_message_time = whatsapp_chat.get("lastMessage", {}).get("messageTimestamp")

        return OmniChat(
            id=whatsapp_chat.get("id", ""),
            name=whatsapp_chat.get("name") or whatsapp_chat.get("pushName") or "Unknown",
            chat_type=chat_type,
            channel_type=ChannelType.WHATSAPP,
            instance_name=instance_name,
            participant_count=(len(whatsapp_chat.get("participants", [])) if chat_type == OmniChatType.GROUP else None),
            is_muted=whatsapp_chat.get("isMuted", False),
            is_archived=whatsapp_chat.get("isArchived", False),
            is_pinned=whatsapp_chat.get("isPinned", False),
            unread_count=whatsapp_chat.get("unreadCount", 0),
            channel_data={
                "group_id": (whatsapp_chat.get("id") if chat_type == OmniChatType.GROUP else None),
                "participants": whatsapp_chat.get("participants", []),
                "group_metadata": whatsapp_chat.get("groupMetadata"),
                "raw_data": whatsapp_chat,
            },
            last_message_at=WhatsAppTransformer._parse_datetime(last_message_time),
        )

    @staticmethod
    def channel_to_omni(
        instance_name: str, status_data: Dict[str, Any], instance_config: Dict[str, Any]
    ) -> OmniChannelInfo:
        """Transform WhatsApp instance to omni channel info."""
        return OmniChannelInfo(
            instance_name=instance_name,
            channel_type=ChannelType.WHATSAPP,
            display_name=instance_config.get("display_name", instance_name),
            status=status_data.get("status", "unknown"),
            is_healthy=status_data.get("status") == "connected",
            supports_contacts=True,
            supports_groups=True,
            supports_media=True,
            supports_voice=True,
            avatar_url=status_data.get("profilePictureUrl"),
            description=f"WhatsApp instance: {instance_name}",
            total_contacts=status_data.get("contactCount"),
            total_chats=status_data.get("chatCount"),
            channel_data={
                "phone_number": status_data.get("phoneNumber"),
                "profile_name": status_data.get("profileName"),
                "qr_code": status_data.get("qrCode"),
                "raw_status": status_data,
                "raw_config": instance_config,
            },
            connected_at=WhatsAppTransformer._parse_datetime(status_data.get("connectedAt")),
            last_activity_at=WhatsAppTransformer._parse_datetime(status_data.get("lastActivity")),
        )

    @staticmethod
    def message_to_omni(whatsapp_message: Dict[str, Any], instance_name: str) -> OmniMessage:
        """Transform WhatsApp message to omni format."""
        # Determine message type
        message_type = OmniMessageType.TEXT
        media_url = None
        media_mime_type = None
        media_size = None
        caption = None
        thumbnail_url = None
        text = None

        # Check for media types
        if whatsapp_message.get("message"):
            msg = whatsapp_message["message"]

            if msg.get("imageMessage"):
                message_type = OmniMessageType.IMAGE
                media = msg["imageMessage"]
                media_url = media.get("url") or media.get("directPath")
                media_mime_type = media.get("mimetype")
                media_size = media.get("fileLength")
                caption = media.get("caption")
                thumbnail_url = media.get("thumbnailUrl")
            elif msg.get("videoMessage"):
                message_type = OmniMessageType.VIDEO
                media = msg["videoMessage"]
                media_url = media.get("url") or media.get("directPath")
                media_mime_type = media.get("mimetype")
                media_size = media.get("fileLength")
                caption = media.get("caption")
                thumbnail_url = media.get("thumbnailUrl")
            elif msg.get("audioMessage") or msg.get("ptt"):
                message_type = OmniMessageType.AUDIO
                media = msg.get("audioMessage") or msg.get("ptt", {})
                media_url = media.get("url") or media.get("directPath")
                media_mime_type = media.get("mimetype")
                media_size = media.get("fileLength")
            elif msg.get("documentMessage"):
                message_type = OmniMessageType.DOCUMENT
                media = msg["documentMessage"]
                media_url = media.get("url") or media.get("directPath")
                media_mime_type = media.get("mimetype")
                media_size = media.get("fileLength")
                caption = media.get("caption") or media.get("fileName")
            elif msg.get("stickerMessage"):
                message_type = OmniMessageType.STICKER
                media = msg["stickerMessage"]
                media_url = media.get("url") or media.get("directPath")
                media_mime_type = media.get("mimetype")
            elif msg.get("contactMessage"):
                message_type = OmniMessageType.CONTACT
            elif msg.get("locationMessage"):
                message_type = OmniMessageType.LOCATION
            elif msg.get("reactionMessage"):
                message_type = OmniMessageType.REACTION
            elif msg.get("conversation"):
                text = msg.get("conversation")
            elif msg.get("extendedTextMessage"):
                text = msg.get("extendedTextMessage", {}).get("text")

        # Fallback to body if no text found
        if text is None and not caption:
            text = whatsapp_message.get("body") or whatsapp_message.get("text")

        # Extract sender info
        sender_id = whatsapp_message.get("key", {}).get("remoteJid") or whatsapp_message.get("from", "")
        is_from_me = whatsapp_message.get("key", {}).get("fromMe", False)

        return OmniMessage(
            id=whatsapp_message.get("key", {}).get("id") or whatsapp_message.get("id", ""),
            chat_id=whatsapp_message.get("key", {}).get("remoteJid") or whatsapp_message.get("chatId", ""),
            sender_id=sender_id,
            sender_name=whatsapp_message.get("pushName") or whatsapp_message.get("sender"),
            message_type=message_type,
            text=text or caption,
            media_url=media_url,
            media_mime_type=media_mime_type,
            media_size=media_size,
            caption=caption,
            thumbnail_url=thumbnail_url,
            is_from_me=is_from_me,
            is_forwarded=whatsapp_message.get("message", {})
            .get("extendedTextMessage", {})
            .get("contextInfo", {})
            .get("isForwarded", False),
            is_reply=bool(
                whatsapp_message.get("message", {})
                .get("extendedTextMessage", {})
                .get("contextInfo", {})
                .get("quotedMessage")
            ),
            reply_to_message_id=whatsapp_message.get("message", {})
            .get("extendedTextMessage", {})
            .get("contextInfo", {})
            .get("stanzaId"),
            timestamp=WhatsAppTransformer._parse_datetime(
                whatsapp_message.get("messageTimestamp") or whatsapp_message.get("timestamp")
            )
            or datetime.now(),
            channel_type=ChannelType.WHATSAPP,
            instance_name=instance_name,
            channel_data={"raw_message": whatsapp_message},
        )

    @staticmethod
    def _parse_datetime(timestamp: Any) -> Optional[datetime]:
        """Parse WhatsApp timestamp to datetime."""
        if not timestamp:
            return None
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp / 1000 if timestamp > 1e10 else timestamp)
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except Exception:
            return None


class DiscordTransformer:
    """Transform Discord data to omni format."""

    @staticmethod
    def contact_to_omni(discord_user: Dict[str, Any], instance_name: str) -> OmniContact:
        """Transform Discord user to omni format."""
        status_map = {
            "online": OmniContactStatus.ONLINE,
            "idle": OmniContactStatus.AWAY,
            "dnd": OmniContactStatus.DND,
            "offline": OmniContactStatus.OFFLINE,
        }

        return OmniContact(
            id=str(discord_user.get("id", "")),
            name=discord_user.get("global_name") or discord_user.get("username", "Unknown"),
            channel_type=ChannelType.DISCORD,
            instance_name=instance_name,
            avatar_url=DiscordTransformer._build_avatar_url(discord_user),
            status=status_map.get(discord_user.get("status"), OmniContactStatus.UNKNOWN),
            is_verified=discord_user.get("verified"),
            channel_data={
                "username": discord_user.get("username"),
                "discriminator": discord_user.get("discriminator"),
                "global_name": discord_user.get("global_name"),
                "is_bot": discord_user.get("bot", False),
                "is_system": discord_user.get("system", False),
                "activities": discord_user.get("activities", []),
                "raw_data": discord_user,
            },
        )

    @staticmethod
    def chat_to_omni(discord_channel: Dict[str, Any], instance_name: str) -> OmniChat:
        """Transform Discord channel to omni format."""
        # Map Discord channel types
        type_map = {
            0: OmniChatType.DIRECT,  # DM
            1: OmniChatType.DIRECT,  # DM
            2: OmniChatType.GROUP,  # Group DM
            4: OmniChatType.CHANNEL,  # Guild category
            5: OmniChatType.CHANNEL,  # Guild text
            10: OmniChatType.THREAD,  # Guild news thread
            11: OmniChatType.THREAD,  # Guild public thread
            12: OmniChatType.THREAD,  # Guild private thread
        }

        channel_type = int(discord_channel.get("type", 0))
        chat_type = type_map.get(channel_type, OmniChatType.CHANNEL)

        return OmniChat(
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
                "raw_data": discord_channel,
            },
            created_at=DiscordTransformer._parse_snowflake_timestamp(discord_channel.get("id")),
        )

    @staticmethod
    def channel_to_omni(
        instance_name: str, status_data: Dict[str, Any], instance_config: Dict[str, Any]
    ) -> OmniChannelInfo:
        """Transform Discord instance to omni channel info."""
        return OmniChannelInfo(
            instance_name=instance_name,
            channel_type=ChannelType.DISCORD,
            display_name=instance_config.get("display_name", instance_name),
            status=status_data.get("status", "unknown"),
            is_healthy=status_data.get("status") == "connected",
            supports_contacts=True,
            supports_groups=True,
            supports_media=True,
            supports_voice=True,
            avatar_url=status_data.get("avatar_url"),
            description=f"Discord instance: {instance_name}",
            total_contacts=status_data.get("member_count"),
            total_chats=status_data.get("channel_count"),
            channel_data={
                "bot_id": status_data.get("bot_id"),
                "guild_count": status_data.get("guild_count"),
                "shard_id": status_data.get("shard_id"),
                "raw_status": status_data,
                "raw_config": instance_config,
            },
            connected_at=DiscordTransformer._parse_datetime(status_data.get("connected_at")),
            last_activity_at=DiscordTransformer._parse_datetime(status_data.get("last_activity")),
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
        except Exception:
            return None

    @staticmethod
    def message_to_omni(discord_message: Dict[str, Any], instance_name: str) -> OmniMessage:
        """Transform Discord message to omni format."""
        # Determine message type
        message_type = OmniMessageType.TEXT
        media_url = None
        media_mime_type = None
        media_size = None
        caption = None
        thumbnail_url = None

        # Check for attachments (images, videos, documents)
        attachments = discord_message.get("attachments", [])
        if attachments:
            attachment = attachments[0]  # Use first attachment
            content_type = attachment.get("content_type", "")
            if content_type.startswith("image/"):
                message_type = OmniMessageType.IMAGE
            elif content_type.startswith("video/"):
                message_type = OmniMessageType.VIDEO
            elif content_type.startswith("audio/"):
                message_type = OmniMessageType.AUDIO
            else:
                message_type = OmniMessageType.DOCUMENT

            media_url = attachment.get("url") or attachment.get("proxy_url")
            media_mime_type = content_type
            media_size = attachment.get("size")
            caption = attachment.get("filename")

        # Check for stickers
        elif discord_message.get("sticker_items"):
            message_type = OmniMessageType.STICKER
            sticker = discord_message["sticker_items"][0]
            media_url = f"https://cdn.discordapp.com/stickers/{sticker.get('id')}.png"

        # Extract text content
        text = discord_message.get("content")

        # Check if it's a reply
        referenced_message = discord_message.get("referenced_message")
        is_reply = bool(referenced_message)
        reply_to_message_id = referenced_message.get("id") if referenced_message else None

        return OmniMessage(
            id=str(discord_message.get("id", "")),
            chat_id=str(discord_message.get("channel_id", "")),
            sender_id=str(discord_message.get("author", {}).get("id", "")),
            sender_name=discord_message.get("author", {}).get("username"),
            message_type=message_type,
            text=text,
            media_url=media_url,
            media_mime_type=media_mime_type,
            media_size=media_size,
            caption=caption,
            thumbnail_url=thumbnail_url,
            is_from_me=discord_message.get("author", {}).get("bot", False),  # Bot messages are "from us"
            is_forwarded=False,  # Discord doesn't have native forwarding
            is_reply=is_reply,
            reply_to_message_id=str(reply_to_message_id) if reply_to_message_id else None,
            timestamp=DiscordTransformer._parse_datetime(discord_message.get("timestamp")) or datetime.now(),
            edited_at=DiscordTransformer._parse_datetime(discord_message.get("edited_timestamp")),
            channel_type=ChannelType.DISCORD,
            instance_name=instance_name,
            channel_data={
                "embeds": discord_message.get("embeds", []),
                "mentions": discord_message.get("mentions", []),
                "mention_roles": discord_message.get("mention_roles", []),
                "reactions": discord_message.get("reactions", []),
                "raw_message": discord_message,
            },
        )

    @staticmethod
    def _parse_datetime(timestamp: Any) -> Optional[datetime]:
        """Parse Discord timestamp to datetime."""
        if not timestamp:
            return None
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp)
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except Exception:
            return None
