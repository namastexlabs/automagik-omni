"""
Tests for EvolutionClient - base Evolution API client.
Tests the core Evolution API client methods introduced for v2.3.5+ compatibility.
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.channels.whatsapp.evolution_client import (
    EvolutionClient,
    EvolutionCreateRequest,
    EvolutionInstance,
    get_evolution_client,
)


@pytest.fixture
def evolution_client():
    """Create an EvolutionClient for testing."""
    return EvolutionClient(base_url="https://test-evolution.api", api_key="test-api-key")


@pytest.fixture
def create_request():
    """Create a sample EvolutionCreateRequest."""
    return EvolutionCreateRequest(
        instanceName="test_instance",
        integration="WHATSAPP-BAILEYS",
        qrcode=True,
        readMessages=True,
        readStatus=True,
    )


@pytest.mark.asyncio
class TestEvolutionClientInstanceManagement:
    """Test Evolution API instance management operations."""

    async def test_create_instance_basic(self, evolution_client, create_request):
        """Test creating an instance with basic configuration."""
        mock_response = {"instance": {"name": "test_instance", "status": "created"}}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await evolution_client.create_instance(create_request)

            assert result == mock_response
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "/instance/create"

    async def test_create_instance_with_webhook_autoconfiguration(self, evolution_client, create_request):
        """Test that webhook is auto-configured when not provided."""
        mock_response = {"instance": {"name": "test_instance"}}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            with patch("src.channels.whatsapp.evolution_client.config") as mock_config:
                mock_config.api.host = "localhost"
                mock_config.api.port = 3000

                mock_request.return_value = mock_response

                await evolution_client.create_instance(create_request)

                # Verify webhook was added to the request
                call_args = mock_request.call_args
                payload = call_args[1]["json"]
                assert "webhook" in payload
                assert payload["webhook"]["enabled"] is True
                assert "MESSAGES_UPSERT" in payload["webhook"]["events"]

    async def test_create_instance_preserves_provided_webhook(self, evolution_client, create_request):
        """Test that provided webhook configuration is preserved."""
        create_request.webhook = {
            "enabled": True,
            "url": "https://custom-webhook.com",
            "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"],
        }

        mock_response = {"instance": {"name": "test_instance"}}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await evolution_client.create_instance(create_request)

            # Verify custom webhook was preserved
            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload["webhook"]["url"] == "https://custom-webhook.com"
            assert "CONNECTION_UPDATE" in payload["webhook"]["events"]

    async def test_create_instance_removes_empty_optional_fields(self, evolution_client):
        """Test that empty optional fields are removed from payload."""
        create_request = EvolutionCreateRequest(
            instanceName="test_instance",
            token="",  # Empty token should be removed
            msgCall="",  # Empty msgCall should be removed
            number="",  # Empty number should be removed
        )

        mock_response = {"instance": {"name": "test_instance"}}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await evolution_client.create_instance(create_request)

            # Verify empty fields were removed
            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert "token" not in payload
            assert "msgCall" not in payload
            assert "number" not in payload

    async def test_fetch_instances_all(self, evolution_client):
        """Test fetching all instances."""
        mock_response = [
            {
                "name": "instance1",
                "id": "id1",
                "ownerJid": "owner1@s.whatsapp.net",
                "profileName": "Instance 1",
                "connectionStatus": "open",
            },
            {
                "name": "instance2",
                "id": "id2",
                "ownerJid": "owner2@s.whatsapp.net",
                "profileName": "Instance 2",
                "connectionStatus": "close",
            },
        ]

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await evolution_client.fetch_instances()

            assert len(result) == 2
            assert isinstance(result[0], EvolutionInstance)
            assert result[0].instanceName == "instance1"
            assert result[0].status == "open"
            assert result[1].instanceName == "instance2"
            assert result[1].status == "close"

    async def test_fetch_instances_by_name(self, evolution_client):
        """Test fetching a specific instance by name."""
        mock_response = [
            {
                "name": "test_instance",
                "id": "test_id",
                "ownerJid": "owner@s.whatsapp.net",
                "connectionStatus": "open",
            }
        ]

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await evolution_client.fetch_instances(instance_name="test_instance")

            assert len(result) == 1
            assert result[0].instanceName == "test_instance"
            # Verify instance name was passed as parameter
            call_args = mock_request.call_args
            assert call_args[1]["params"]["instanceName"] == "test_instance"

    async def test_fetch_instances_empty_response(self, evolution_client):
        """Test handling empty instance list."""
        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = []

            result = await evolution_client.fetch_instances()

            assert len(result) == 0

    async def test_get_connection_state(self, evolution_client):
        """Test getting connection state for an instance."""
        mock_response = {"state": "open", "isConnected": True}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await evolution_client.get_connection_state("test_instance")

            assert result == mock_response
            call_args = mock_request.call_args
            assert "test_instance" in call_args[0][1]

    async def test_connect_instance(self, evolution_client):
        """Test connecting an instance and getting QR code."""
        mock_response = {"qrcode": "data:image/png;base64,abcd1234", "status": "connecting"}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await evolution_client.connect_instance("test_instance")

            assert result == mock_response
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert "connect/test_instance" in call_args[0][1]

    async def test_restart_instance_success(self, evolution_client):
        """Test successfully restarting an instance."""
        mock_response = {"status": "restarted"}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await evolution_client.restart_instance("test_instance")

            assert result == mock_response
            call_args = mock_request.call_args
            assert call_args[0][0] == "PUT"
            assert "restart/test_instance" in call_args[0][1]

    async def test_restart_instance_404_fallback(self, evolution_client):
        """Test restart fallback when endpoint is not available (404)."""
        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("Evolution API error: 404 - Not Found")

            result = await evolution_client.restart_instance("test_instance")

            # Should return warning response instead of failing
            assert result["status"] == "warning"
            assert "not available" in result["message"]

    async def test_restart_instance_other_error_raises(self, evolution_client):
        """Test that non-404 errors during restart are raised."""
        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("Evolution API error: 500 - Server Error")

            with pytest.raises(Exception) as exc_info:
                await evolution_client.restart_instance("test_instance")

            assert "500" in str(exc_info.value)

    async def test_logout_instance(self, evolution_client):
        """Test logging out an instance."""
        mock_response = {"status": "logged_out"}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await evolution_client.logout_instance("test_instance")

            assert result == mock_response
            call_args = mock_request.call_args
            assert call_args[0][0] == "DELETE"
            assert "logout/test_instance" in call_args[0][1]

    async def test_delete_instance(self, evolution_client):
        """Test deleting an instance."""
        mock_response = {"status": "deleted"}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await evolution_client.delete_instance("test_instance")

            assert result == mock_response
            call_args = mock_request.call_args
            assert call_args[0][0] == "DELETE"
            assert "delete/test_instance" in call_args[0][1]


@pytest.mark.asyncio
class TestEvolutionClientWebhookConfiguration:
    """Test webhook and settings configuration."""

    async def test_set_webhook_default_events(self, evolution_client):
        """Test setting webhook with default events."""
        mock_response = {"webhook": {"enabled": True}}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await evolution_client.set_webhook(
                instance_name="test_instance", webhook_url="https://webhook.example.com"
            )

            assert result == mock_response
            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload["webhook"]["url"] == "https://webhook.example.com"
            assert payload["webhook"]["enabled"] is True
            assert "MESSAGES_UPSERT" in payload["webhook"]["events"]
            assert payload["webhook"]["base64"] is True
            assert payload["webhook"]["byEvents"] is False

    async def test_set_webhook_custom_events(self, evolution_client):
        """Test setting webhook with custom events."""
        mock_response = {"webhook": {"enabled": True}}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await evolution_client.set_webhook(
                instance_name="test_instance",
                webhook_url="https://webhook.example.com",
                events=["MESSAGES_UPSERT", "CONNECTION_UPDATE", "QRCODE_UPDATED"],
                webhook_base64=False,
            )

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert len(payload["webhook"]["events"]) == 3
            assert "CONNECTION_UPDATE" in payload["webhook"]["events"]
            assert payload["webhook"]["base64"] is False

    async def test_set_settings_default(self, evolution_client):
        """Test setting default settings for an instance."""
        mock_response = {"settings": {"updated": True}}

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await evolution_client.set_settings("test_instance")

            assert result == mock_response
            call_args = mock_request.call_args
            settings = call_args[1]["json"]
            assert settings["readMessages"] is True
            assert settings["readStatus"] is True
            assert settings["rejectCall"] is False
            assert settings["syncFullHistory"] is True

    async def test_set_settings_custom(self, evolution_client):
        """Test setting custom settings for an instance."""
        mock_response = {"settings": {"updated": True}}
        custom_settings = {
            "rejectCall": True,
            "msgCall": "Custom reject message",
            "groupsIgnore": True,
            "alwaysOnline": True,
        }

        with patch.object(evolution_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await evolution_client.set_settings("test_instance", settings=custom_settings)

            call_args = mock_request.call_args
            settings = call_args[1]["json"]
            assert settings["rejectCall"] is True
            assert settings["groupsIgnore"] is True
            assert settings["alwaysOnline"] is True


class TestGetEvolutionClient:
    """Test the get_evolution_client factory function."""

    def test_get_evolution_client_creates_singleton(self):
        """Test that get_evolution_client returns a singleton."""
        with patch("src.channels.whatsapp.evolution_client.config") as mock_config:
            mock_config.get_env.side_effect = lambda k, d: {
                "EVOLUTION_API_URL": "http://test.api:8080",
                "EVOLUTION_API_KEY": "test-key-123",
            }.get(k, d)

            # Reset the global singleton
            import src.channels.whatsapp.evolution_client as client_module

            client_module.evolution_client = None

            # First call should create the client
            client1 = get_evolution_client()
            assert client1 is not None

            # Second call should return the same instance
            client2 = get_evolution_client()
            assert client1 is client2

            # Clean up
            client_module.evolution_client = None

    def test_get_evolution_client_missing_api_key_raises(self):
        """Test that missing API key raises an exception."""
        with patch("src.channels.whatsapp.evolution_client.config") as mock_config:
            mock_config.get_env.side_effect = lambda k, d: {
                "EVOLUTION_API_URL": "http://test.api:8080",
                "EVOLUTION_API_KEY": "",  # Empty key
            }.get(k, d)

            # Reset the global singleton
            import src.channels.whatsapp.evolution_client as client_module

            client_module.evolution_client = None

            with pytest.raises(Exception) as exc_info:
                get_evolution_client()

            assert "EVOLUTION_API_KEY not configured" in str(exc_info.value)

            # Clean up
            client_module.evolution_client = None

    def test_get_evolution_client_configuration(self):
        """Test that client is configured with correct URL and key."""
        with patch("src.channels.whatsapp.evolution_client.config") as mock_config:
            mock_config.get_env.side_effect = lambda k, d: {
                "EVOLUTION_API_URL": "http://custom.api:9000",
                "EVOLUTION_API_KEY": "custom-key-456",
            }.get(k, d)

            # Reset the global singleton
            import src.channels.whatsapp.evolution_client as client_module

            client_module.evolution_client = None

            client = get_evolution_client()

            # Verify configuration - base_url has trailing slash stripped
            assert "custom.api:9000" in client.base_url
            assert client.api_key == "custom-key-456"
            assert client.headers["apikey"] == "custom-key-456"

            # Clean up
            client_module.evolution_client = None
