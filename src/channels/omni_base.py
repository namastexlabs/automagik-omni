# src/channels/omni_base.py
from abc import abstractmethod
from typing import List, Optional, Tuple
from src.channels.base import ChannelHandler
from src.api.schemas.omni import OmniContact, OmniChat, OmniChannelInfo, OmniMessage
from src.db.models import InstanceConfig


class OmniChannelHandler(ChannelHandler):
    """Extended channel handler with omni operations support."""

    @abstractmethod
    async def get_contacts(
        self,
        instance: InstanceConfig,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> Tuple[List[OmniContact], int]:
        """
        Get contacts from this channel in omni format.

        Args:
            instance: The instance configuration
            page: Page number for pagination (1-based)
            page_size: Number of items per page
            search_query: Optional search query to filter contacts
            status_filter: Optional status filter (online, offline, etc.)

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
        archived: Optional[bool] = None,
    ) -> Tuple[List[OmniChat], int]:
        """
        Get chats/conversations from this channel in omni format.

        Args:
            instance: The instance configuration
            page: Page number for pagination (1-based)
            page_size: Number of items per page
            chat_type_filter: Optional chat type filter (direct, group, channel, thread)
            archived: Optional filter for archived chats (True, False, None for all)

        Returns:
            Tuple of (chats_list, total_count)
        """
        pass

    @abstractmethod
    async def get_channel_info(self, instance: InstanceConfig) -> OmniChannelInfo:
        """
        Get channel information in omni format.

        Args:
            instance: The instance configuration

        Returns:
            OmniChannelInfo with channel status and capabilities
        """
        pass

    # Optional methods for future extensibility
    async def get_contact_by_id(self, instance: InstanceConfig, contact_id: str) -> Optional[OmniContact]:
        """
        Get a specific contact by ID in omni format.

        Args:
            instance: The instance configuration
            contact_id: The contact identifier

        Returns:
            OmniContact or None if not found
        """
        # Default implementation returns None - handlers can override
        return None

    async def get_chat_by_id(self, instance: InstanceConfig, chat_id: str) -> Optional[OmniChat]:
        """
        Get a specific chat by ID in omni format.

        Args:
            instance: The instance configuration
            chat_id: The chat identifier

        Returns:
            OmniChat or None if not found
        """
        # Default implementation returns None - handlers can override
        return None

    async def get_messages(
        self,
        instance: InstanceConfig,
        chat_id: str,
        page: int = 1,
        page_size: int = 50,
        before_message_id: Optional[str] = None,
    ) -> Tuple[List[OmniMessage], int]:
        """
        Get messages from a chat in omni format.

        Args:
            instance: The instance configuration
            chat_id: The chat identifier
            page: Page number for pagination (1-based)
            page_size: Number of items per page
            before_message_id: Optional message ID to fetch messages before (for cursor-based pagination)

        Returns:
            Tuple of (messages_list, total_count)
        """
        # Default implementation returns empty list - handlers must override
        return [], 0


# Type alias for backward compatibility and clarity
OmniHandler = OmniChannelHandler
