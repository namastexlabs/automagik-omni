# src/channels/handlers/discord_chat_handler.py
"""
Discord unified channel handler implementation.
"""

import logging
from typing import List, Optional, Tuple
from src.channels.omni_base import OmniChannelHandler
from src.channels.discord.channel_handler import DiscordChannelHandler
from src.api.schemas.omni import OmniContact, OmniChat, OmniChannelInfo, OmniMessage
from src.services.omni_transformers import DiscordTransformer
from src.db.models import InstanceConfig

logger = logging.getLogger(__name__)


class DiscordChatHandler(DiscordChannelHandler, OmniChannelHandler):
    """Discord channel handler with unified operations support."""

    async def get_contacts(
        self,
        instance: InstanceConfig,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> Tuple[List[OmniContact], int]:
        """
        Get contacts from Discord in unified format.
        """
        try:
            logger.debug(f"Fetching Discord contacts for instance {instance.name} - page: {page}, size: {page_size}")

            # Check if bot instance exists
            if instance.name not in self._bot_instances:
                logger.error(f"Discord bot instance '{instance.name}' not found")
                return [], 0

            bot_instance = self._bot_instances[instance.name]

            # Check if bot is connected
            if bot_instance.status != "connected" or not bot_instance.client:
                logger.error(f"Discord bot instance '{instance.name}' is not connected")
                return [], 0

            client = bot_instance.client
            contacts = []

            # Collect users from all guilds the bot is in
            all_users = set()
            for guild in client.guilds:
                for member in guild.members:
                    # Skip bots if desired (can be configurable)
                    if member.bot:
                        continue
                    all_users.add(member)

            # Convert to list and apply filtering
            user_list = list(all_users)

            # Apply search filter if provided
            if search_query:
                filtered_users = []
                search_lower = search_query.lower()
                for user in user_list:
                    user_name = (user.global_name or user.display_name or user.name).lower()
                    if search_lower in user_name:
                        filtered_users.append(user)
                user_list = filtered_users

            # Apply status filter if provided
            if status_filter:
                filtered_users = []
                for user in user_list:
                    if hasattr(user, "status") and str(user.status) == status_filter:
                        filtered_users.append(user)
                user_list = filtered_users

            total_count = len(user_list)

            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_users = user_list[start_idx:end_idx]

            # Transform to unified format
            for user in paginated_users:
                try:
                    user_data = {
                        "id": user.id,
                        "username": user.name,
                        "global_name": getattr(user, "global_name", None),
                        "discriminator": getattr(user, "discriminator", None),
                        "avatar": getattr(user, "avatar", None),
                        "bot": getattr(user, "bot", False),
                        "system": getattr(user, "system", False),
                        "status": str(getattr(user, "status", "unknown")),
                        "activities": [activity.name for activity in getattr(user, "activities", [])],
                        "verified": getattr(user, "verified", None),
                    }

                    omni_contact = DiscordTransformer.contact_to_omni(user_data, instance.name)
                    contacts.append(omni_contact)
                except Exception as e:
                    logger.warning(f"Failed to transform Discord user data: {e}")
                    continue

            logger.info(
                f"Successfully fetched {len(contacts)} Discord contacts (total: {total_count}) for instance {instance.name}"
            )
            return contacts, total_count

        except Exception as e:
            logger.error(f"Failed to fetch Discord contacts for instance {instance.name}: {e}")
            return [], 0

    async def get_chats(
        self,
        instance: InstanceConfig,
        page: int = 1,
        page_size: int = 50,
        chat_type_filter: Optional[str] = None,
        archived: Optional[bool] = None,
    ) -> Tuple[List[OmniChat], int]:
        """
        Get chats/conversations from Discord in unified format.
        """
        try:
            logger.debug(f"Fetching Discord chats for instance {instance.name} - page: {page}, size: {page_size}")

            # Check if bot instance exists
            if instance.name not in self._bot_instances:
                logger.error(f"Discord bot instance '{instance.name}' not found")
                return [], 0

            bot_instance = self._bot_instances[instance.name]

            # Check if bot is connected
            if bot_instance.status != "connected" or not bot_instance.client:
                logger.error(f"Discord bot instance '{instance.name}' is not connected")
                return [], 0

            client = bot_instance.client
            chats = []

            # Collect channels from all guilds the bot has access to
            all_channels = []

            # Add guild channels
            for guild in client.guilds:
                for channel in guild.channels:
                    # Include text channels, voice channels, categories, threads
                    if hasattr(channel, "type"):
                        all_channels.append(channel)

            # Add DM channels if available
            if hasattr(client, "private_channels"):
                for dm_channel in client.private_channels:
                    all_channels.append(dm_channel)

            # Apply chat type filter if provided
            if chat_type_filter:
                filtered_channels = []
                for channel in all_channels:
                    channel_type = getattr(channel, "type", None)
                    if channel_type is not None:
                        # Map Discord channel types to our unified types
                        discord_type_value = channel_type.value if hasattr(channel_type, "value") else int(channel_type)

                        if chat_type_filter == "direct" and discord_type_value in [
                            0,
                            1,
                        ]:  # DM channels
                            filtered_channels.append(channel)
                        elif chat_type_filter == "group" and discord_type_value == 2:  # Group DM
                            filtered_channels.append(channel)
                        elif chat_type_filter == "channel" and discord_type_value in [
                            4,
                            5,
                        ]:  # Guild channels
                            filtered_channels.append(channel)
                        elif chat_type_filter == "thread" and discord_type_value in [
                            10,
                            11,
                            12,
                        ]:  # Thread channels
                            filtered_channels.append(channel)
                all_channels = filtered_channels

            # Note: Discord doesn't have an "archived" concept like WhatsApp groups,
            # but we could potentially check if channels are "closed" or "deleted"
            # For now, we'll ignore the archived filter for Discord

            total_count = len(all_channels)

            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_channels = all_channels[start_idx:end_idx]

            # Transform to unified format
            for channel in paginated_channels:
                try:
                    channel_data = {
                        "id": getattr(channel, "id", ""),
                        "name": getattr(channel, "name", "") or f"Channel-{getattr(channel, 'id', '')}",
                        "type": (
                            getattr(channel, "type", 0).value
                            if hasattr(getattr(channel, "type", 0), "value")
                            else int(getattr(channel, "type", 0))
                        ),
                        "guild_id": getattr(channel, "guild_id", None)
                        or (
                            getattr(channel, "guild", {}).id if hasattr(getattr(channel, "guild", None), "id") else None
                        ),
                        "parent_id": getattr(channel, "parent_id", None),
                        "topic": getattr(channel, "topic", None),
                        "position": getattr(channel, "position", None),
                        "nsfw": getattr(channel, "nsfw", False),
                        "rate_limit_per_user": getattr(channel, "slowmode_delay", None),
                        "member_count": (len(getattr(channel, "members", [])) if hasattr(channel, "members") else None),
                        "permission_overwrites": [],  # We could add this if needed
                    }

                    omni_chat = DiscordTransformer.chat_to_omni(channel_data, instance.name)
                    chats.append(omni_chat)
                except Exception as e:
                    logger.warning(f"Failed to transform Discord channel data: {e}")
                    continue

            logger.info(
                f"Successfully fetched {len(chats)} Discord chats (total: {total_count}) for instance {instance.name}"
            )
            return chats, total_count

        except Exception as e:
            logger.error(f"Failed to fetch Discord chats for instance {instance.name}: {e}")
            return [], 0

    async def get_channel_info(self, instance: InstanceConfig) -> OmniChannelInfo:
        """
        Get Discord channel information in unified format.
        """
        try:
            logger.debug(f"Fetching Discord channel info for instance {instance.name}")

            # Get connection status (using parent class method)
            status_response = await self.get_status(instance)

            # Transform status response to dictionary format for transformer
            status_data = {
                "status": status_response.status,
                "instance_name": status_response.instance_name,
                "channel_type": status_response.channel_type,
                "channel_data": status_response.channel_data or {},
            }

            # Extract additional info from channel_data if available
            if status_response.channel_data:
                status_data.update(status_response.channel_data)

            # Get additional stats if bot is connected
            if (
                instance.name in self._bot_instances
                and self._bot_instances[instance.name].status == "connected"
                and self._bot_instances[instance.name].client
            ):
                client = self._bot_instances[instance.name].client

                # Count total members across all guilds
                total_members = sum(len(guild.members) for guild in client.guilds)
                # Count total channels across all guilds
                total_channels = sum(len(guild.channels) for guild in client.guilds)

                status_data.update(
                    {
                        "member_count": total_members,
                        "channel_count": total_channels,
                        "guild_count": len(client.guilds),
                        "bot_id": client.user.id if client.user else None,
                        "connected_at": None,  # Discord doesn't provide this easily
                        "last_activity": None,  # We could track this if needed
                    }
                )

            # Use instance config data
            instance_config = {
                "display_name": f"Discord - {instance.name}",
                "instance_name": instance.name,
            }

            omni_channel_info = DiscordTransformer.channel_to_omni(instance.name, status_data, instance_config)

            logger.info(f"Successfully fetched Discord channel info for instance {instance.name}")
            return omni_channel_info

        except Exception as e:
            logger.error(f"Failed to fetch Discord channel info for instance {instance.name}: {e}")
            raise

    async def get_contact_by_id(self, instance: InstanceConfig, contact_id: str) -> Optional[OmniContact]:
        """
        Get a specific Discord contact by ID in unified format.
        """
        try:
            logger.debug(f"Fetching Discord contact {contact_id} for instance {instance.name}")

            # Check if bot instance exists and is connected
            if (
                instance.name not in self._bot_instances
                or self._bot_instances[instance.name].status != "connected"
                or not self._bot_instances[instance.name].client
            ):
                return None

            client = self._bot_instances[instance.name].client

            # Try to get user by ID
            try:
                user = await client.fetch_user(int(contact_id))
                if user:
                    user_data = {
                        "id": user.id,
                        "username": user.name,
                        "global_name": getattr(user, "global_name", None),
                        "discriminator": getattr(user, "discriminator", None),
                        "avatar": getattr(user, "avatar", None),
                        "bot": getattr(user, "bot", False),
                        "system": getattr(user, "system", False),
                        "verified": getattr(user, "verified", None),
                    }

                    omni_contact = DiscordTransformer.contact_to_omni(user_data, instance.name)
                    logger.info(f"Found Discord contact {contact_id} for instance {instance.name}")
                    return omni_contact
            except Exception:
                # If fetch_user fails, try to find in guild members
                for guild in client.guilds:
                    member = guild.get_member(int(contact_id))
                    if member:
                        user_data = {
                            "id": member.id,
                            "username": member.name,
                            "global_name": getattr(member, "global_name", None),
                            "discriminator": getattr(member, "discriminator", None),
                            "avatar": getattr(member, "avatar", None),
                            "bot": getattr(member, "bot", False),
                            "system": getattr(member, "system", False),
                            "status": str(getattr(member, "status", "unknown")),
                            "activities": [activity.name for activity in getattr(member, "activities", [])],
                            "verified": getattr(member, "verified", None),
                        }

                        omni_contact = DiscordTransformer.contact_to_omni(user_data, instance.name)
                        logger.info(f"Found Discord contact {contact_id} for instance {instance.name}")
                        return omni_contact

            logger.warning(f"Discord contact {contact_id} not found for instance {instance.name}")
            return None

        except Exception as e:
            logger.error(f"Failed to fetch Discord contact {contact_id} for instance {instance.name}: {e}")
            return None

    async def get_chat_by_id(self, instance: InstanceConfig, chat_id: str) -> Optional[OmniChat]:
        """
        Get a specific Discord chat by ID in unified format.
        """
        try:
            logger.debug(f"Fetching Discord chat {chat_id} for instance {instance.name}")

            # Check if bot instance exists and is connected
            if (
                instance.name not in self._bot_instances
                or self._bot_instances[instance.name].status != "connected"
                or not self._bot_instances[instance.name].client
            ):
                return None

            client = self._bot_instances[instance.name].client

            # Try to get channel by ID
            try:
                channel = client.get_channel(int(chat_id))
                if not channel:
                    # Try to fetch it if not in cache
                    channel = await client.fetch_channel(int(chat_id))

                if channel:
                    channel_data = {
                        "id": getattr(channel, "id", ""),
                        "name": getattr(channel, "name", "") or f"Channel-{getattr(channel, 'id', '')}",
                        "type": (
                            getattr(channel, "type", 0).value
                            if hasattr(getattr(channel, "type", 0), "value")
                            else int(getattr(channel, "type", 0))
                        ),
                        "guild_id": getattr(channel, "guild_id", None)
                        or (
                            getattr(channel, "guild", {}).id if hasattr(getattr(channel, "guild", None), "id") else None
                        ),
                        "parent_id": getattr(channel, "parent_id", None),
                        "topic": getattr(channel, "topic", None),
                        "position": getattr(channel, "position", None),
                        "nsfw": getattr(channel, "nsfw", False),
                        "rate_limit_per_user": getattr(channel, "slowmode_delay", None),
                        "member_count": (len(getattr(channel, "members", [])) if hasattr(channel, "members") else None),
                        "permission_overwrites": [],
                    }

                    omni_chat = DiscordTransformer.chat_to_omni(channel_data, instance.name)
                    logger.info(f"Found Discord chat {chat_id} for instance {instance.name}")
                    return omni_chat
            except Exception as e:
                logger.warning(f"Failed to fetch Discord channel {chat_id}: {e}")

            logger.warning(f"Discord chat {chat_id} not found for instance {instance.name}")
            return None

        except Exception as e:
            logger.error(f"Failed to fetch Discord chat {chat_id} for instance {instance.name}: {e}")
            return None

    async def get_messages(
        self,
        instance: InstanceConfig,
        chat_id: str,
        page: int = 1,
        page_size: int = 50,
        before_message_id: Optional[str] = None,
    ) -> Tuple[List[OmniMessage], int]:
        """Get messages from a Discord channel in omni format."""
        try:
            logger.debug(
                f"Fetching Discord messages for channel {chat_id} in instance {instance.name} - page: {page}, size: {page_size}"
            )

            if (
                instance.name not in self._bot_instances
                or self._bot_instances[instance.name].status != "connected"
                or not self._bot_instances[instance.name].client
            ):
                logger.warning(f"Discord bot not connected for instance {instance.name}")
                return [], 0

            client = self._bot_instances[instance.name].client
            channel = client.get_channel(int(chat_id))
            if not channel:
                channel = await client.fetch_channel(int(chat_id))

            if not channel or not hasattr(channel, "history"):
                logger.warning(f"Channel {chat_id} not found or does not support message history")
                return [], 0

            messages = []
            limit = page_size
            before = None

            if before_message_id:
                try:
                    before = await channel.fetch_message(int(before_message_id))
                except Exception:
                    pass

            async for message in channel.history(limit=limit, before=before):
                try:
                    message_data = {
                        "id": str(message.id),
                        "channel_id": str(message.channel.id),
                        "content": message.content,
                        "timestamp": message.created_at.isoformat(),
                        "edited_timestamp": message.edited_at.isoformat() if message.edited_at else None,
                        "author": {
                            "id": str(message.author.id),
                            "username": message.author.name,
                            "bot": message.author.bot,
                        },
                        "attachments": [
                            {
                                "url": att.url,
                                "proxy_url": att.proxy_url,
                                "filename": att.filename,
                                "size": att.size,
                                "content_type": att.content_type,
                            }
                            for att in message.attachments
                        ],
                        "sticker_items": [{"id": str(sticker.id)} for sticker in message.stickers],
                        "referenced_message": (
                            {"id": str(message.reference.message_id)} if message.reference else None
                        ),
                    }

                    omni_message = DiscordTransformer.message_to_omni(message_data, instance.name)
                    messages.append(omni_message)
                except Exception as transform_error:
                    logger.warning(f"Failed to transform Discord message: {transform_error}")
                    continue

            total_count = len(messages)

            logger.info(
                f"Successfully fetched {len(messages)} messages for channel {chat_id} in instance {instance.name}"
            )

            return messages, total_count

        except Exception as e:
            logger.error(f"Failed to fetch Discord messages for channel {chat_id} in instance {instance.name}: {e}")
            return [], 0
