"""
Evolution API client for WhatsApp instance management.
Provides a clean interface to Evolution API endpoints.
"""

import logging
import httpx
from typing import Dict, List, Optional, Any
from urllib.parse import quote
from pydantic import BaseModel
from src.config import config
from src.ip_utils import replace_localhost_with_ipv4

logger = logging.getLogger(__name__)


class EvolutionInstance(BaseModel):
    """Evolution API instance model."""

    instanceName: str
    instanceId: Optional[str] = None
    owner: Optional[str] = None
    profileName: Optional[str] = None
    profilePictureUrl: Optional[str] = None
    profileStatus: Optional[str] = None
    status: str  # "open", "close", "connecting", "created"
    serverUrl: Optional[str] = None
    apikey: Optional[str] = None
    integration: Optional[Dict[str, Any]] = None


class EvolutionCreateRequest(BaseModel):
    """Request model for creating Evolution instances."""

    instanceName: str
    integration: str = "WHATSAPP-BAILEYS"  # or "WHATSAPP-BUSINESS"
    token: Optional[str] = None
    qrcode: bool = True
    number: Optional[str] = None
    rejectCall: bool = False
    msgCall: Optional[str] = None
    groupsIgnore: bool = False
    alwaysOnline: bool = False
    readMessages: bool = True
    readStatus: bool = True
    syncFullHistory: bool = False
    webhook: Optional[Dict[str, Any]] = None


class EvolutionClient:
    """Client for Evolution API operations."""

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize Evolution API client.

        Args:
            base_url: Evolution API base URL
            api_key: Evolution API authentication key
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"apikey": api_key, "Content-Type": "application/json"}

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Evolution API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # DEBUG logging for request details
        logger.debug(f"Evolution API Request: {method} {url}")
        logger.debug(f"Request headers: {self.headers}")
        if "json" in kwargs:
            logger.debug(f"Request body: {kwargs['json']}")
        if "params" in kwargs:
            logger.debug(f"Request params: {kwargs['params']}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method, url=url, headers=self.headers, timeout=30.0, **kwargs
                )

                # DEBUG logging for response details
                logger.debug(f"Evolution API Response: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response body size: {len(response.text)} characters")

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_text = e.response.text
                logger.error(
                    f"Evolution API error {e.response.status_code}: {error_text}"
                )
                logger.debug(f"Failed request details - URL: {url}, Method: {method}")
                logger.debug(f"Failed request headers: {self.headers}")
                if "json" in kwargs:
                    logger.debug(f"Failed request body: {kwargs['json']}")
                raise Exception(
                    f"Evolution API error: {e.response.status_code} - {error_text}"
                )
            except Exception as e:
                logger.error(f"Evolution API request failed: {e}")
                logger.debug(f"Failed request details - URL: {url}, Method: {method}")
                logger.debug(f"Exception type: {type(e).__name__}")
                raise Exception(f"Evolution API request failed: {str(e)}")

    async def create_instance(self, request: EvolutionCreateRequest) -> Dict[str, Any]:
        """Create a new WhatsApp instance in Evolution API."""
        logger.info(f"Creating Evolution instance: {request.instanceName}")
        logger.debug(f"Instance creation request: {request.dict()}")

        # Set webhook URL if configured
        if not request.webhook and config.api.host and config.api.port:
            webhook_url = replace_localhost_with_ipv4(
                f"http://{config.api.host}:{config.api.port}/webhook/evolution/{quote(request.instanceName, safe='')}"
            )
            logger.debug(f"Auto-configuring webhook URL: {webhook_url}")
            request.webhook = {
                "enabled": True,
                "url": webhook_url,
                "webhookByEvents": True,
                "webhookBase64": True,
                "events": ["MESSAGES_UPSERT"],
            }
            logger.debug(f"Webhook configuration: {request.webhook}")
        else:
            logger.debug(f"Using provided webhook config: {request.webhook}")

        # Convert to dict and exclude None values to avoid Evolution API validation errors
        payload = request.dict(exclude_none=True)

        # Remove optional fields that cause validation issues if empty
        optional_fields_to_remove = ["token", "msgCall", "number"]
        for field in optional_fields_to_remove:
            if field in payload and not payload[field]:
                del payload[field]

        logger.debug(f"Final instance creation payload: {payload}")
        return await self._request("POST", "/instance/create", json=payload)

    async def fetch_instances(
        self, instance_name: Optional[str] = None
    ) -> List[EvolutionInstance]:
        """Fetch Evolution API instances."""
        params = {}
        if instance_name:
            params["instanceName"] = instance_name

        data = await self._request("GET", "/instance/fetchInstances", params=params)

        # Parse response - Evolution API returns list of instance objects
        instances: List[EvolutionInstance] = []
        if isinstance(data, list):
            for item in data:
                if "instance" in item:
                    instances.append(EvolutionInstance(**item["instance"]))

        return instances

    async def get_connection_state(self, instance_name: str) -> Dict[str, Any]:
        """Get connection state of an instance."""
        return await self._request(
            "GET", f"/instance/connectionState/{quote(instance_name, safe='')}"
        )

    async def connect_instance(self, instance_name: str) -> Dict[str, Any]:
        """Get connection info and QR code for instance."""
        return await self._request(
            "GET", f"/instance/connect/{quote(instance_name, safe='')}"
        )

    async def restart_instance(self, instance_name: str) -> Dict[str, Any]:
        """
        Restart a WhatsApp instance.

        Note: This endpoint might not be available in all Evolution API versions.
        If it fails with 404, the instance might need to be recreated.
        """
        try:
            return await self._request(
                "PUT", f"/instance/restart/{quote(instance_name, safe='')}"
            )
        except Exception as e:
            # If restart endpoint doesn't exist, log but don't fail catastrophically
            if "404" in str(e):
                logger.warning(
                    f"Restart endpoint not available for instance '{instance_name}'. This Evolution API version might not support instance restart."
                )
                # Return a mock successful response
                return {
                    "status": "warning",
                    "message": "Restart endpoint not available, instance may need manual reconnection",
                }
            raise

    async def logout_instance(self, instance_name: str) -> Dict[str, Any]:
        """Logout a WhatsApp instance."""
        return await self._request(
            "DELETE", f"/instance/logout/{quote(instance_name, safe='')}"
        )

    async def delete_instance(self, instance_name: str) -> Dict[str, Any]:
        """Delete a WhatsApp instance."""
        return await self._request(
            "DELETE", f"/instance/delete/{quote(instance_name, safe='')}"
        )

    async def set_webhook(
        self,
        instance_name: str,
        webhook_url: str,
        events: Optional[List[str]] = None,
        webhook_base64: bool = True,
    ) -> Dict[str, Any]:
        """Set webhook URL for an instance."""
        if events is None:
            events = ["MESSAGES_UPSERT"]

        webhook_data = {
            "enabled": True,
            "url": webhook_url,
            "webhookByEvents": True,
            "webhookBase64": webhook_base64,
            "events": events,
        }

        return await self._request(
            "POST", f"/webhook/set/{quote(instance_name, safe='')}", json=webhook_data
        )

    async def set_settings(
        self, instance_name: str, settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Set settings for an instance."""
        if settings is None:
            settings = {
                "rejectCall": False,
                "msgCall": "Call rejected automatically",
                "groupsIgnore": False,
                "alwaysOnline": False,
                "readMessages": True,
                "readStatus": True,
                "syncFullHistory": True,
            }

        return await self._request(
            "POST", f"/settings/set/{quote(instance_name, safe='')}", json=settings
        )


# Global Evolution client instance
evolution_client = None


def get_evolution_client() -> EvolutionClient:
    """Get global Evolution API client instance."""
    global evolution_client

    if evolution_client is None:
        # Use environment variables for Evolution API configuration
        evolution_url = replace_localhost_with_ipv4(
            config.get_env("EVOLUTION_API_URL", "http://localhost:8080")
        )
        evolution_key = config.get_env("EVOLUTION_API_KEY", "")

        logger.debug(f"Evolution API configuration - URL: {evolution_url}")
        logger.debug(
            f"Evolution API configuration - Key: {'*' * len(evolution_key) if evolution_key else 'NOT SET'}"
        )

        if not evolution_key:
            logger.error("EVOLUTION_API_KEY not configured in environment")
            raise Exception("EVOLUTION_API_KEY not configured")

        evolution_client = EvolutionClient(evolution_url, evolution_key)
        logger.info(f"Evolution API client initialized: {evolution_url}")
        logger.debug(f"Evolution API client headers: {evolution_client.headers}")

    return evolution_client
