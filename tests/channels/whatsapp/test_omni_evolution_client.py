"""
Tests for OmniEvolutionClient - WhatsApp Omni API client with pagination.
Tests the client-side pagination implementation introduced in PR #105.
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.channels.whatsapp.omni_evolution_client import OmniEvolutionClient


@pytest.fixture
def mock_evolution_client():
    """Create a mock OmniEvolutionClient for testing."""
    client = OmniEvolutionClient(
        base_url="https://test-evolution.api",
        api_key="test-api-key"
    )
    return client


@pytest.mark.asyncio
class TestOmniEvolutionClientPagination:
    """Test pagination functionality for Omni Evolution client."""

    async def test_fetch_contacts_list_response_format(self, mock_evolution_client):
        """Test pagination with Evolution v2.3.5+ list response format."""
        # Mock response - direct list (v2.3.5+ format)
        mock_contacts = [
            {"id": "5551234567@s.whatsapp.net", "pushName": "Contact 1"},
            {"id": "5559876543@s.whatsapp.net", "pushName": "Contact 2"},
            {"id": "5551111111@s.whatsapp.net", "pushName": "Contact 3"},
            {"id": "5552222222@s.whatsapp.net", "pushName": "Contact 4"},
            {"id": "5553333333@s.whatsapp.net", "pushName": "Contact 5"},
        ]

        with patch.object(mock_evolution_client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_contacts

            # Test first page with 2 items per page
            result = await mock_evolution_client.fetch_contacts("test_instance", page=1, page_size=2)

            # Verify pagination was applied correctly
            assert result["total"] == 5
            assert result["page"] == 1
            assert result["page_size"] == 2
            assert len(result["data"]) == 2
            assert result["data"][0]["pushName"] == "Contact 1"
            assert result["data"][1]["pushName"] == "Contact 2"

    async def test_fetch_contacts_dict_response_format(self, mock_evolution_client):
        """Test pagination with older Evolution API dict response format."""
        # Mock response - dict format (older versions)
        mock_response = {
            "contacts": [
                {"id": "5551234567@s.whatsapp.net", "pushName": "Contact 1"},
                {"id": "5559876543@s.whatsapp.net", "pushName": "Contact 2"},
                {"id": "5551111111@s.whatsapp.net", "pushName": "Contact 3"},
            ],
            "total": 3,
        }

        with patch.object(mock_evolution_client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # Test with page_size larger than total
            result = await mock_evolution_client.fetch_contacts("test_instance", page=1, page_size=10)

            # Verify all contacts returned
            assert result["total"] == 3
            assert result["page"] == 1
            assert result["page_size"] == 10
            assert len(result["contacts"]) == 3

    async def test_fetch_chats_pagination_second_page(self, mock_evolution_client):
        """Test fetching second page of chats."""
        # Mock response with many chats
        mock_chats = [
            {"id": f"chat_{i}@g.us", "name": f"Chat {i}"} for i in range(15)
        ]

        with patch.object(mock_evolution_client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_chats

            # Test page 2 with 5 items per page
            result = await mock_evolution_client.fetch_chats("test_instance", page=2, page_size=5)

            # Verify correct slice returned (items 5-9, 0-indexed)
            assert result["total"] == 15
            assert result["page"] == 2
            assert result["page_size"] == 5
            assert len(result["data"]) == 5
            assert result["data"][0]["name"] == "Chat 5"
            assert result["data"][4]["name"] == "Chat 9"

    async def test_fetch_chats_pagination_last_page(self, mock_evolution_client):
        """Test fetching last page with fewer items than page_size."""
        # Mock response with 12 chats
        mock_chats = [
            {"id": f"chat_{i}@g.us", "name": f"Chat {i}"} for i in range(12)
        ]

        with patch.object(mock_evolution_client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_chats

            # Test page 3 with 5 items per page (should return only 2 items)
            result = await mock_evolution_client.fetch_chats("test_instance", page=3, page_size=5)

            # Verify last page with partial results
            assert result["total"] == 12
            assert result["page"] == 3
            assert result["page_size"] == 5
            assert len(result["data"]) == 2  # Only 2 items on last page
            assert result["data"][0]["name"] == "Chat 10"
            assert result["data"][1]["name"] == "Chat 11"

    async def test_fetch_contacts_empty_response(self, mock_evolution_client):
        """Test handling of empty contacts list."""
        with patch.object(mock_evolution_client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = []

            result = await mock_evolution_client.fetch_contacts("test_instance", page=1, page_size=10)

            assert result["total"] == 0
            assert result["page"] == 1
            assert result["page_size"] == 10
            assert len(result["data"]) == 0

    async def test_apply_pagination_unexpected_format(self, mock_evolution_client):
        """Test _apply_pagination with unexpected response format."""
        # Test with None response
        result = mock_evolution_client._apply_pagination(None, page=1, page_size=5)

        assert result["total"] == 0
        assert result["page"] == 1
        assert result["page_size"] == 5
        assert result["data"] == []

    async def test_fetch_chats_page_out_of_range(self, mock_evolution_client):
        """Test fetching a page number beyond available data."""
        mock_chats = [
            {"id": f"chat_{i}@g.us", "name": f"Chat {i}"} for i in range(5)
        ]

        with patch.object(mock_evolution_client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_chats

            # Request page 10 when only 1 page exists
            result = await mock_evolution_client.fetch_chats("test_instance", page=10, page_size=5)

            # Should return empty data but correct metadata
            assert result["total"] == 5
            assert result["page"] == 10
            assert result["page_size"] == 5
            assert len(result["data"]) == 0

    async def test_fetch_contacts_preserves_dict_structure(self, mock_evolution_client):
        """Test that dict responses preserve original structure."""
        mock_response = {
            "contacts": [
                {"id": "contact1", "name": "Test 1"},
                {"id": "contact2", "name": "Test 2"},
            ],
            "metadata": {"some_field": "value"},
            "total": 2,
        }

        with patch.object(mock_evolution_client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await mock_evolution_client.fetch_contacts("test_instance", page=1, page_size=10)

            # Verify original structure preserved
            assert "contacts" in result
            assert "metadata" in result
            assert result["metadata"]["some_field"] == "value"
            assert result["total"] == 2

    async def test_fetch_chats_with_nested_data_key(self, mock_evolution_client):
        """Test pagination with response using 'data' key instead of 'chats'."""
        mock_response = {
            "data": [
                {"id": "chat1", "name": "Chat 1"},
                {"id": "chat2", "name": "Chat 2"},
                {"id": "chat3", "name": "Chat 3"},
            ],
            "count": 3,
        }

        with patch.object(mock_evolution_client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await mock_evolution_client.fetch_chats("test_instance", page=1, page_size=2)

            # Verify pagination applied to 'data' key
            assert result["total"] == 3  # Uses 'count' from response
            assert len(result["data"]) == 2
            assert result["data"][0]["name"] == "Chat 1"

    async def test_pagination_calculates_correct_indices(self, mock_evolution_client):
        """Test that pagination indices are calculated correctly for various scenarios."""
        items = [f"item_{i}" for i in range(100)]

        # Test various page/page_size combinations
        test_cases = [
            (1, 10, 0, 10),    # First page, 10 items
            (2, 10, 10, 20),   # Second page, 10 items
            (5, 20, 80, 100),  # Fifth page, 20 items per page
            (1, 100, 0, 100),  # Single page with all items
        ]

        for page, page_size, expected_start, expected_end in test_cases:
            with patch.object(mock_evolution_client, '_request', new_callable=AsyncMock) as mock_request:
                mock_request.return_value = items

                result = await mock_evolution_client.fetch_chats("test_instance", page=page, page_size=page_size)

                # Verify correct slice
                expected_items = items[expected_start:expected_end]
                assert len(result["data"]) == len(expected_items)
                assert result["data"] == expected_items
