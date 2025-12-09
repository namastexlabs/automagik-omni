# src/channels/handlers/whatsapp_chat_handler.py
"""
WhatsApp unified channel handler implementation.
"""

import logging
from typing import List, Optional, Tuple
from src.channels.omni_base import OmniChannelHandler
from src.channels.whatsapp.channel_handler import WhatsAppChannelHandler
from src.channels.whatsapp.omni_evolution_client import OmniEvolutionClient
from src.api.schemas.omni import OmniContact, OmniChat, OmniChannelInfo, OmniMessage
from src.services.omni_transformers import WhatsAppTransformer
from src.db.models import InstanceConfig
from src.config import config
from src.ip_utils import replace_localhost_with_ipv4

logger = logging.getLogger(__name__)


class WhatsAppChatHandler(WhatsAppChannelHandler, OmniChannelHandler):
    """WhatsApp channel handler with unified operations support."""

    def _get_omni_evolution_client(self, instance: InstanceConfig) -> OmniEvolutionClient:
        """Get unified Evolution client for this specific instance."""
        from src.services.settings_service import get_evolution_api_key_global

        # Get bootstrap key from database (with .env fallback)
        evolution_url = instance.evolution_url or replace_localhost_with_ipv4(
            config.get_env("EVOLUTION_API_URL", "http://localhost:8080")
        )
        bootstrap_key = get_evolution_api_key_global()

        # Validate configuration (same as parent class)
        if evolution_url.lower() in ["string", "null", "undefined", ""]:
            logger.error(
                f"Invalid Evolution URL detected: '{evolution_url}'. Please provide a valid URL like 'http://localhost:8080'"
            )
            raise Exception(
                f"Invalid Evolution URL: '{evolution_url}'. Please provide a valid URL like 'http://localhost:8080'"
            )

        if not bootstrap_key or bootstrap_key.lower() in [
            "string",
            "null",
            "undefined",
            "",
        ]:
            logger.error("Invalid Evolution API key detected. Please provide a valid API key.")
            raise Exception("Invalid Evolution API key. Please provide a valid API key.")

        if not evolution_url.startswith(("http://", "https://")):
            logger.error(f"Evolution URL missing protocol: '{evolution_url}'. Must start with http:// or https://")
            raise Exception(f"Evolution URL missing protocol: '{evolution_url}'. Must start with http:// or https://")

        # Pass instance name for logging/debugging only (auth uses bootstrap key)
        whatsapp_instance_name = instance.whatsapp_instance or instance.name
        return OmniEvolutionClient(evolution_url, bootstrap_key, whatsapp_instance_name)

    async def get_contacts(
        self,
        instance: InstanceConfig,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> Tuple[List[OmniContact], int]:
        """
        Get contacts from WhatsApp in unified format with pagination.

        Note: When using search_query or status_filter, client-side filtering is applied
        AFTER pagination, which may result in fewer items per page than requested.
        For accurate page sizes with filters, consider fetching without filters first.
        """
        try:
            logger.debug(f"Fetching WhatsApp contacts for instance {instance.name} - page: {page}, size: {page_size}")

            evolution_client = self._get_omni_evolution_client(instance)

            # Fetch paginated contacts from Evolution API (with client-side pagination)
            contacts_response = await evolution_client.fetch_contacts(
                instance_name=instance.name, page=page, page_size=page_size
            )

            logger.debug(f"Evolution API contacts response: {contacts_response}")

            # Parse response and transform to unified format
            contacts = []
            total_count = 0

            # Evolution client now returns dict with pagination metadata
            if isinstance(contacts_response, dict):
                # Get paginated contact list from response
                contact_list = contacts_response.get("contacts", contacts_response.get("data", []))
                # CRITICAL: Use total from client, not len(contact_list) which is paginated
                total_count = contacts_response.get("total", 0)
            elif isinstance(contacts_response, list):
                # Fallback for direct list response (shouldn't happen with updated client)
                contact_list = contacts_response
                total_count = len(contact_list)
                logger.warning("Received unpaginated list response from Evolution client")
            else:
                contact_list = []
                total_count = 0

            if isinstance(contact_list, list):
                for contact_data in contact_list:
                    try:
                        # Normalize Evolution v2.3.5 field names to match transformer expectations
                        # Always use remoteJid as id for consistent contact identification
                        # Evolution v2.3.5 returns both 'id' (database ID) and 'remoteJid' (WhatsApp JID)
                        if "remoteJid" in contact_data:
                            contact_data["id"] = contact_data["remoteJid"]
                        # Ensure id is always a string, never None
                        if not contact_data.get("id"):
                            contact_data["id"] = ""

                        # Apply search filter if provided (post-pagination filtering)
                        if search_query:
                            name = contact_data.get("pushName") or contact_data.get("name", "")
                            if search_query.lower() not in name.lower():
                                continue

                        # Apply status filter if provided (post-pagination filtering)
                        if status_filter and contact_data.get("presence") != status_filter:
                            continue

                        omni_contact = WhatsAppTransformer.contact_to_omni(contact_data, instance.name)
                        contacts.append(omni_contact)
                    except Exception as e:
                        logger.warning(f"Failed to transform contact data: {e}")
                        continue

            # NOTE: When filters are applied post-pagination, total_count represents
            # the total number of contacts before filtering, not after.
            # This is intentional to maintain consistent pagination behavior.
            # Client-side filtering may result in fewer items per page.

            logger.info(
                f"Successfully fetched {len(contacts)} WhatsApp contacts (total: {total_count}) for instance {instance.name}"
            )
            return contacts, total_count

        except Exception as e:
            logger.error(f"Failed to fetch WhatsApp contacts for instance {instance.name}: {e}")
            raise

    async def get_chats(
        self,
        instance: InstanceConfig,
        page: int = 1,
        page_size: int = 50,
        chat_type_filter: Optional[str] = None,
        archived: Optional[bool] = None,
    ) -> Tuple[List[OmniChat], int]:
        """
        Get chats/conversations from WhatsApp in unified format with pagination.

        Filters are applied BEFORE pagination to ensure accurate results.
        """
        try:
            logger.debug(f"Fetching WhatsApp chats for instance {instance.name} - page: {page}, size: {page_size}")

            evolution_client = self._get_omni_evolution_client(instance)

            # Fetch ALL chats from Evolution API (pagination will be applied after filtering)
            chats_response = await evolution_client.fetch_chats(instance_name=instance.name, page=1, page_size=10000)

            logger.debug(f"Evolution API chats response: {chats_response}")

            # Parse response and collect all chats for filtering
            all_chats = []

            # Evolution client returns dict with pagination metadata
            if isinstance(chats_response, dict):
                # Get chat list from response
                chat_list = chats_response.get("chats", chats_response.get("data", []))
            elif isinstance(chats_response, list):
                # Fallback for direct list response
                chat_list = chats_response
                logger.warning("Received unpaginated list response from Evolution client")
            else:
                chat_list = []

            # Transform and filter chats
            if isinstance(chat_list, list):
                for chat_data in chat_list:
                    try:
                        # Normalize Evolution v2.3.5 field names to match transformer expectations
                        # CRITICAL: Always use remoteJid as id for chat type detection
                        # Evolution v2.3.5 returns both 'id' (database ID) and 'remoteJid' (WhatsApp JID)
                        # The transformer needs remoteJid to detect groups (@g.us) vs direct chats
                        if "remoteJid" in chat_data:
                            chat_data["id"] = chat_data["remoteJid"]
                        # Ensure id is always a string, never None
                        if not chat_data.get("id"):
                            chat_data["id"] = ""

                        # Apply chat type filter if provided (pre-pagination filtering)
                        # CRITICAL: Filter logic must match transformer logic in omni_transformers.py
                        # - @g.us = group
                        # - @broadcast = channel
                        # - everything else (including @s.whatsapp.net) = direct
                        if chat_type_filter:
                            chat_id = chat_data.get("id") or ""
                            is_group = chat_id.endswith("@g.us")
                            is_channel = chat_id.endswith("@broadcast")
                            is_direct = not is_group and not is_channel

                            if chat_type_filter == "direct" and not is_direct:
                                continue
                            elif chat_type_filter == "group" and not is_group:
                                continue
                            elif chat_type_filter == "channel" and not is_channel:
                                continue

                        # Apply archived filter if provided (pre-pagination filtering)
                        if archived is not None and chat_data.get("isArchived", False) != archived:
                            continue

                        omni_chat = WhatsAppTransformer.chat_to_omni(chat_data, instance.name)
                        all_chats.append(omni_chat)
                    except Exception as e:
                        logger.warning(f"Failed to transform chat data: {e}")
                        continue

            # Apply pagination to filtered results
            total_count = len(all_chats)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            chats = all_chats[start_idx:end_idx]

            logger.info(
                f"Successfully fetched {len(chats)} WhatsApp chats (total: {total_count}) for instance {instance.name}"
            )
            return chats, total_count

        except Exception as e:
            # Check if this is the known Evolution API SQL bug
            error_message = str(e)
            if 'near "ON": syntax error' in error_message or "prisma.$queryRaw" in error_message:
                logger.warning(
                    f"Evolution API SQL bug detected for instance {instance.name}. "
                    f"Returning empty chats list as workaround. "
                    f"This is a known issue in Evolution API's Prisma SQLite query. "
                    f"Error: {error_message}"
                )
                # Return empty results instead of crashing
                return [], 0

            # For other errors, re-raise
            logger.error(f"Failed to fetch WhatsApp chats for instance {instance.name}: {e}")
            raise

    async def get_channel_info(self, instance: InstanceConfig) -> OmniChannelInfo:
        """
        Get WhatsApp channel information in unified format.
        """
        try:
            logger.debug(f"Fetching WhatsApp channel info for instance {instance.name}")

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

            # Use instance config data
            instance_config = {
                "display_name": f"WhatsApp - {instance.name}",
                "instance_name": instance.name,
            }

            omni_channel_info = WhatsAppTransformer.channel_to_omni(instance.name, status_data, instance_config)

            logger.info(f"Successfully fetched WhatsApp channel info for instance {instance.name}")
            return omni_channel_info

        except Exception as e:
            logger.error(f"Failed to fetch WhatsApp channel info for instance {instance.name}: {e}")
            raise

    async def get_contact_by_id(self, instance: InstanceConfig, contact_id: str) -> Optional[OmniContact]:
        """
        Get a specific WhatsApp contact by ID in unified format.
        """
        try:
            logger.debug(f"Fetching WhatsApp contact {contact_id} for instance {instance.name}")

            # For now, we'll search through contacts
            # In a real implementation, you might have a direct API endpoint
            contacts, _ = await self.get_contacts(instance, page_size=1000)

            for contact in contacts:
                if contact.id == contact_id:
                    logger.info(f"Found WhatsApp contact {contact_id} for instance {instance.name}")
                    return contact

            logger.warning(f"WhatsApp contact {contact_id} not found for instance {instance.name}")
            return None

        except Exception as e:
            logger.error(f"Failed to fetch WhatsApp contact {contact_id} for instance {instance.name}: {e}")
            return None

    async def get_chat_by_id(self, instance: InstanceConfig, chat_id: str) -> Optional[OmniChat]:
        """
        Get a specific WhatsApp chat by ID in unified format.
        """
        try:
            logger.debug(f"Fetching WhatsApp chat {chat_id} for instance {instance.name}")

            # For now, we'll search through chats
            # In a real implementation, you might have a direct API endpoint
            chats, _ = await self.get_chats(instance, page_size=1000)

            for chat in chats:
                if chat.id == chat_id:
                    logger.info(f"Found WhatsApp chat {chat_id} for instance {instance.name}")
                    return chat

            logger.warning(f"WhatsApp chat {chat_id} not found for instance {instance.name}")
            return None

        except Exception as e:
            logger.error(f"Failed to fetch WhatsApp chat {chat_id} for instance {instance.name}: {e}")
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
        Get messages from a WhatsApp chat in omni format.
        """
        try:
            logger.debug(
                f"Fetching WhatsApp messages for chat {chat_id} in instance {instance.name} - page: {page}, size: {page_size}"
            )

            evolution_client = self._get_omni_evolution_client(instance)

            # Fetch messages from Evolution API
            messages_response = await evolution_client.fetch_messages(
                instance_name=instance.name, chat_id=chat_id, page=page, page_size=page_size, limit=200
            )

            logger.debug(f"Evolution API messages response: {messages_response}")

            # Parse response and transform to omni format
            messages = []
            total_count = 0

            if isinstance(messages_response, dict):
                # Get paginated message list from response
                message_list = messages_response.get("messages", messages_response.get("data", []))
                total_count = messages_response.get("total", 0)
            elif isinstance(messages_response, list):
                # Fallback for direct list response
                message_list = messages_response
                total_count = len(message_list)
                logger.warning("Received unpaginated list response from Evolution client")
            else:
                message_list = []
                total_count = 0

            # Transform each message to omni format
            for msg in message_list:
                try:
                    omni_message = WhatsAppTransformer.message_to_omni(msg, instance.name)
                    messages.append(omni_message)
                except Exception as transform_error:
                    logger.warning(f"Failed to transform WhatsApp message: {transform_error}")
                    continue

            logger.info(
                f"Successfully fetched {len(messages)} messages (total: {total_count}) for chat {chat_id} in instance {instance.name}"
            )

            return messages, total_count

        except Exception as e:
            logger.error(f"Failed to fetch WhatsApp messages for chat {chat_id} in instance {instance.name}: {e}")
            return [], 0
