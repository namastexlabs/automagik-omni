# src/channels/handlers/whatsapp_chat_handler.py
"""
WhatsApp unified channel handler implementation.
"""

import logging
from typing import List, Optional, Tuple
from src.channels.omni_base import OmniChannelHandler
from src.channels.whatsapp.channel_handler import WhatsAppChannelHandler
from src.channels.whatsapp.omni_evolution_client import OmniEvolutionClient
from src.api.schemas.omni import OmniContact, OmniChat, OmniChannelInfo
from src.services.omni_transformers import WhatsAppTransformer
from src.db.models import InstanceConfig
from src.config import config
from src.ip_utils import replace_localhost_with_ipv4

logger = logging.getLogger(__name__)


class WhatsAppChatHandler(WhatsAppChannelHandler, OmniChannelHandler):
    """WhatsApp channel handler with unified operations support."""

    def _get_omni_evolution_client(self, instance: InstanceConfig) -> OmniEvolutionClient:
        """Get unified Evolution client for this specific instance."""
        # Use instance-specific credentials if available, otherwise fall back to global
        evolution_url = instance.evolution_url or replace_localhost_with_ipv4(
            config.get_env("EVOLUTION_API_URL", "http://localhost:8080")
        )
        evolution_key = instance.evolution_key or config.get_env("EVOLUTION_API_KEY", "")

        # Validate configuration (same as parent class)
        if evolution_url.lower() in ["string", "null", "undefined", ""]:
            logger.error(
                f"Invalid Evolution URL detected: '{evolution_url}'. Please provide a valid URL like 'http://localhost:8080'"
            )
            raise Exception(
                f"Invalid Evolution URL: '{evolution_url}'. Please provide a valid URL like 'http://localhost:8080'"
            )

        if not evolution_key or evolution_key.lower() in [
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

        return OmniEvolutionClient(evolution_url, evolution_key)

    async def get_contacts(
        self,
        instance: InstanceConfig,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> Tuple[List[OmniContact], int]:
        """
        Get contacts from WhatsApp in unified format.
        """
        try:
            logger.debug(f"Fetching WhatsApp contacts for instance {instance.name} - page: {page}, size: {page_size}")

            evolution_client = self._get_omni_evolution_client(instance)

            # Fetch contacts from Evolution API
            contacts_response = await evolution_client.fetch_contacts(
                instance_name=instance.name, page=page, page_size=page_size
            )

            logger.debug(f"Evolution API contacts response: {contacts_response}")

            # Parse response and transform to unified format
            contacts = []
            total_count = 0

            # Evolution v2.3.5+ returns a list directly, older versions return dict
            if isinstance(contacts_response, list):
                # Direct list response from Evolution v2.3.5+
                contact_list = contacts_response
                total_count = len(contact_list)
            elif isinstance(contacts_response, dict):
                # Handle paginated response from older Evolution versions
                contact_list = contacts_response.get("contacts", contacts_response.get("data", []))
                total_count = contacts_response.get("total", contacts_response.get("count", len(contact_list)))
            else:
                contact_list = []

            if isinstance(contact_list, list):
                for contact_data in contact_list:
                    try:
                        # Normalize Evolution v2.3.5 field names to match transformer expectations
                        if "remoteJid" in contact_data and "id" not in contact_data:
                            contact_data["id"] = contact_data["remoteJid"]

                        # Apply search filter if provided
                        if search_query:
                            name = contact_data.get("pushName") or contact_data.get("name", "")
                            if search_query.lower() not in name.lower():
                                continue

                        # Apply status filter if provided (WhatsApp may have presence data)
                        if status_filter and contact_data.get("presence") != status_filter:
                            continue

                        omni_contact = WhatsAppTransformer.contact_to_omni(contact_data, instance.name)
                        contacts.append(omni_contact)
                    except Exception as e:
                        logger.warning(f"Failed to transform contact data: {e}")
                        continue

            # Adjust total count if we applied client-side filtering
            if search_query or status_filter:
                total_count = len(contacts)

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
        Get chats/conversations from WhatsApp in unified format.
        """
        try:
            logger.debug(f"Fetching WhatsApp chats for instance {instance.name} - page: {page}, size: {page_size}")

            evolution_client = self._get_omni_evolution_client(instance)

            # Fetch chats from Evolution API
            chats_response = await evolution_client.fetch_chats(
                instance_name=instance.name, page=page, page_size=page_size
            )

            logger.debug(f"Evolution API chats response: {chats_response}")

            # Parse response and transform to unified format
            chats = []
            total_count = 0

            # Evolution v2.3.5+ returns a list directly, older versions return dict
            if isinstance(chats_response, list):
                # Direct list response from Evolution v2.3.5+
                chat_list = chats_response
                total_count = len(chat_list)
            elif isinstance(chats_response, dict):
                # Handle paginated response from older Evolution versions
                chat_list = chats_response.get("chats", chats_response.get("data", []))
                total_count = chats_response.get("total", chats_response.get("count", len(chat_list)))
            else:
                chat_list = []

            if isinstance(chat_list, list):
                for chat_data in chat_list:
                    try:
                        # Normalize Evolution v2.3.5 field names to match transformer expectations
                        if "remoteJid" in chat_data and "id" not in chat_data:
                            chat_data["id"] = chat_data["remoteJid"]

                        # Apply chat type filter if provided
                        if chat_type_filter:
                            chat_id = chat_data.get("id", "")
                            if chat_type_filter == "direct" and not chat_id.endswith("@c.us"):
                                continue
                            elif chat_type_filter == "group" and not chat_id.endswith("@g.us"):
                                continue
                            elif chat_type_filter == "channel" and not chat_id.endswith("@broadcast"):
                                continue

                        # Apply archived filter if provided
                        if archived is not None and chat_data.get("isArchived", False) != archived:
                            continue

                        omni_chat = WhatsAppTransformer.chat_to_omni(chat_data, instance.name)
                        chats.append(omni_chat)
                    except Exception as e:
                        logger.warning(f"Failed to transform chat data: {e}")
                        continue

            # Adjust total count if we applied client-side filtering
            if chat_type_filter or archived is not None:
                total_count = len(chats)

            logger.info(
                f"Successfully fetched {len(chats)} WhatsApp chats (total: {total_count}) for instance {instance.name}"
            )
            return chats, total_count

        except Exception as e:
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
