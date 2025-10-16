# src/channels/whatsapp/omni_evolution_client.py
"""
Extended Evolution API client with omni endpoints support.
"""

import logging
from typing import Dict, Any
from urllib.parse import quote
from src.channels.whatsapp.evolution_client import EvolutionClient

logger = logging.getLogger(__name__)


class OmniEvolutionClient(EvolutionClient):
    """Extended Evolution client with omni operations support."""

    async def fetch_contacts(self, instance_name: str, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """
        Fetch contacts for an instance.

        Note: Evolution v2.3.5 has a bug with pagination params causing Prisma errors.
        Sending empty body returns all contacts successfully.
        """
        # Send empty body due to Evolution v2.3.5 pagination bug
        payload = {}
        return await self._request("POST", f"/chat/findContacts/{quote(instance_name, safe='')}", json=payload)

    async def fetch_chats(self, instance_name: str, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Fetch chats/conversations for an instance."""
        payload = {"page": page, "limit": page_size}
        return await self._request("POST", f"/chat/findChats/{quote(instance_name, safe='')}", json=payload)
