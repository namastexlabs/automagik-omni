# src/channels/whatsapp/omni_evolution_client.py
"""
Extended Evolution API client with omni endpoints support.
"""

import logging
from typing import Dict, Any, List
from urllib.parse import quote
from src.channels.whatsapp.evolution_client import EvolutionClient

logger = logging.getLogger(__name__)


class OmniEvolutionClient(EvolutionClient):
    """Extended Evolution client with omni operations support."""

    async def fetch_contacts(self, instance_name: str, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """
        Fetch contacts for an instance with client-side pagination.

        Note: Evolution v2.3.5 has a bug with pagination params causing Prisma errors.
        We fetch all contacts and implement client-side pagination to ensure consistent behavior.

        Args:
            instance_name: Name of the instance
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Dictionary with paginated contacts and metadata
        """
        # Fetch all contacts from Evolution API (empty body due to pagination bug)
        payload: Dict[str, Any] = {}
        response = await self._request("POST", f"/chat/findContacts/{quote(instance_name, safe='')}", json=payload)

        # Apply client-side pagination
        return self._apply_pagination(response, page, page_size)

    async def fetch_chats(self, instance_name: str, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """
        Fetch chats/conversations for an instance with client-side pagination.

        Evolution API pagination may not work reliably, so we fetch all chats
        and implement client-side pagination for consistent behavior.

        Args:
            instance_name: Name of the instance
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Dictionary with paginated chats and metadata
        """
        # Try to fetch with pagination params, but don't rely on them working
        payload: Dict[str, Any] = {"page": 1, "limit": 10000}  # Fetch all chats
        response = await self._request("POST", f"/chat/findChats/{quote(instance_name, safe='')}", json=payload)

        # Apply client-side pagination
        return self._apply_pagination(response, page, page_size)

    def _apply_pagination(self, response: Any, page: int, page_size: int) -> Dict[str, Any]:
        """
        Apply client-side pagination to Evolution API response.

        Args:
            response: Response from Evolution API (list or dict)
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Dictionary with paginated data and metadata
        """
        # Handle different response formats from Evolution API
        all_items: List[Any]
        total_count: int

        if isinstance(response, list):
            # Direct list response (Evolution v2.3.5+)
            all_items = response
            total_count = len(all_items)
        elif isinstance(response, dict):
            # Dict response with nested data
            all_items = response.get("contacts", response.get("chats", response.get("data", []))) or []
            # Use response total if available, otherwise count items
            total_count = response.get("total", response.get("count", len(all_items))) or 0
        else:
            # Unexpected response format
            logger.warning(f"Unexpected response format: {type(response)}")
            all_items = []
            total_count = 0

        # Calculate pagination offsets
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        # Slice the data for current page
        paginated_items = all_items[start_idx:end_idx] if isinstance(all_items, list) else []

        # Return paginated response with metadata
        if isinstance(response, list):
            # Return as list for list responses
            return {
                "data": paginated_items,
                "total": total_count,
                "page": page,
                "page_size": page_size,
            }
        else:
            # Preserve original structure for dict responses
            result = response.copy() if isinstance(response, dict) else {}
            # Update with paginated data
            if "contacts" in response:
                result["contacts"] = paginated_items
            elif "chats" in response:
                result["chats"] = paginated_items
            else:
                result["data"] = paginated_items

            result["total"] = total_count
            result["page"] = page
            result["page_size"] = page_size
            return result
