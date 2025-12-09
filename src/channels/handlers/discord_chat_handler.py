# src/channels/handlers/discord_chat_handler.py
"""
Discord unified channel handler implementation.

This module is guarded - it only provides a functional handler when discord.py is installed.
"""

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Guard the import - discord is optional
try:
    from src.channels.discord.channel_handler import DiscordChannelHandler
    from src.channels.omni_base import OmniChannelHandler
    from src.api.schemas.omni import OmniContact, OmniChat, OmniChannelInfo, OmniMessage
    from src.services.omni_transformers import DiscordTransformer
    from src.db.models import InstanceConfig
    DISCORD_HANDLER_AVAILABLE = True
except (ImportError, AttributeError) as e:
    logger.warning(f"Discord chat handler not available: {e}")
    DISCORD_HANDLER_AVAILABLE = False
    DiscordChannelHandler = object  # Placeholder for class inheritance
    OmniChannelHandler = object

# Only define the full class if discord is available
if DISCORD_HANDLER_AVAILABLE:
    from src.channels.omni_base import OmniChannelHandler
    from src.api.schemas.omni import OmniContact, OmniChat, OmniChannelInfo, OmniMessage
    from src.services.omni_transformers import DiscordTransformer
    from src.db.models import InstanceConfig

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
            """Get contacts from Discord in unified format."""
            try:
                logger.debug(f"Fetching Discord contacts for instance {instance.name}")
                if instance.name not in self._bot_instances:
                    return [], 0
                bot_instance = self._bot_instances[instance.name]
                if bot_instance.status != "connected" or not bot_instance.client:
                    return [], 0
                client = bot_instance.client
                contacts = []
                all_users = set()
                for guild in client.guilds:
                    for member in guild.members:
                        if member.bot:
                            continue
                        all_users.add(member)
                user_list = list(all_users)
                if search_query:
                    search_lower = search_query.lower()
                    user_list = [u for u in user_list if search_lower in (u.global_name or u.display_name or u.name).lower()]
                if status_filter:
                    user_list = [u for u in user_list if hasattr(u, "status") and str(u.status) == status_filter]
                total_count = len(user_list)
                start_idx = (page - 1) * page_size
                paginated_users = user_list[start_idx:start_idx + page_size]
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
                        contacts.append(DiscordTransformer.contact_to_omni(user_data, instance.name))
                    except Exception as e:
                        logger.warning(f"Failed to transform Discord user: {e}")
                return contacts, total_count
            except Exception as e:
                logger.error(f"Failed to fetch Discord contacts: {e}")
                return [], 0

        async def get_chats(
            self,
            instance: InstanceConfig,
            page: int = 1,
            page_size: int = 50,
            chat_type_filter: Optional[str] = None,
            archived: Optional[bool] = None,
        ) -> Tuple[List[OmniChat], int]:
            """Get chats from Discord in unified format."""
            try:
                if instance.name not in self._bot_instances:
                    return [], 0
                bot_instance = self._bot_instances[instance.name]
                if bot_instance.status != "connected" or not bot_instance.client:
                    return [], 0
                client = bot_instance.client
                all_channels = []
                for guild in client.guilds:
                    for channel in guild.channels:
                        if hasattr(channel, "type"):
                            all_channels.append(channel)
                if hasattr(client, "private_channels"):
                    all_channels.extend(client.private_channels)
                total_count = len(all_channels)
                start_idx = (page - 1) * page_size
                paginated_channels = all_channels[start_idx:start_idx + page_size]
                chats = []
                for channel in paginated_channels:
                    try:
                        channel_data = {
                            "id": getattr(channel, "id", ""),
                            "name": getattr(channel, "name", "") or f"Channel-{getattr(channel, id, )}",
                            "type": getattr(channel, "type", 0).value if hasattr(getattr(channel, "type", 0), "value") else 0,
                        }
                        chats.append(DiscordTransformer.chat_to_omni(channel_data, instance.name))
                    except Exception as e:
                        logger.warning(f"Failed to transform Discord channel: {e}")
                return chats, total_count
            except Exception as e:
                logger.error(f"Failed to fetch Discord chats: {e}")
                return [], 0

        async def get_channel_info(self, instance: InstanceConfig) -> OmniChannelInfo:
            """Get Discord channel info in unified format."""
            status_response = await self.get_status(instance)
            status_data = {
                "status": status_response.status,
                "instance_name": status_response.instance_name,
                "channel_type": status_response.channel_type,
            }
            return DiscordTransformer.channel_to_omni(instance.name, status_data, {"display_name": f"Discord - {instance.name}"})

        async def get_contact_by_id(self, instance: InstanceConfig, contact_id: str) -> Optional[OmniContact]:
            """Get a specific Discord contact by ID."""
            return None  # Simplified - implement as needed

        async def get_chat_by_id(self, instance: InstanceConfig, chat_id: str) -> Optional[OmniChat]:
            """Get a specific Discord chat by ID."""
            return None  # Simplified - implement as needed

        async def get_messages(
            self,
            instance: InstanceConfig,
            chat_id: str,
            page: int = 1,
            page_size: int = 50,
            before_message_id: Optional[str] = None,
        ) -> Tuple[List[OmniMessage], int]:
            """Get messages from a Discord channel."""
            return [], 0  # Simplified - implement as needed
else:
    # Stub class when discord is not available
    class DiscordChatHandler:
        """Stub Discord chat handler when discord.py is not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Discord chat handler requires discord.py. "
                "Install with: uv sync --extra discord"
            )
