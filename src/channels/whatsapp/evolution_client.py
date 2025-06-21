"""
Evolution API client for WhatsApp instance management.
Provides a clean interface to Evolution API endpoints.
"""

import logging
import httpx
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from src.config import config

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
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "apikey": api_key,
            "Content-Type": "application/json"
        }
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Evolution API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    timeout=30.0,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {e}")
                raise Exception(f"Evolution API request failed: {str(e)}")
    
    async def create_instance(self, request: EvolutionCreateRequest) -> Dict[str, Any]:
        """Create a new WhatsApp instance in Evolution API."""
        logger.info(f"Creating Evolution instance: {request.instanceName}")
        
        # Set webhook URL if configured
        if not request.webhook and config.api.host and config.api.port:
            webhook_url = f"http://{config.api.host}:{config.api.port}/webhook/evolution/{request.instanceName}"
            request.webhook = {
                "url": webhook_url,
                "byEvents": True,
                "base64": True,
                "events": [
                    "QRCODE_UPDATED",
                    "CONNECTION_UPDATE", 
                    "MESSAGES_UPSERT",
                    "MESSAGES_UPDATE",
                    "MESSAGES_DELETE",
                    "SEND_MESSAGE",
                    "CONTACTS_UPSERT",
                    "CONTACTS_UPDATE",
                    "PRESENCE_UPDATE",
                    "CHATS_UPSERT",
                    "CHATS_UPDATE",
                    "CHATS_DELETE",
                    "GROUPS_UPSERT",
                    "GROUPS_UPDATE",
                    "GROUP_PARTICIPANTS_UPDATE",
                    "NEW_JWT_TOKEN"
                ]
            }
        
        return await self._request("POST", "/instance/create", json=request.dict())
    
    async def fetch_instances(self, instance_name: Optional[str] = None) -> List[EvolutionInstance]:
        """Fetch Evolution API instances."""
        params = {}
        if instance_name:
            params["instanceName"] = instance_name
            
        data = await self._request("GET", "/instance/fetchInstances", params=params)
        
        # Parse response - Evolution API returns list of instance objects
        instances = []
        if isinstance(data, list):
            for item in data:
                if "instance" in item:
                    instances.append(EvolutionInstance(**item["instance"]))
        
        return instances
    
    async def get_connection_state(self, instance_name: str) -> Dict[str, Any]:
        """Get connection state of an instance."""
        return await self._request("GET", f"/instance/connectionState/{instance_name}")
    
    async def connect_instance(self, instance_name: str) -> Dict[str, Any]:
        """Get connection info and QR code for instance."""
        return await self._request("GET", f"/instance/connect/{instance_name}")
    
    async def restart_instance(self, instance_name: str) -> Dict[str, Any]:
        """Restart a WhatsApp instance."""
        return await self._request("PUT", f"/instance/restart/{instance_name}")
    
    async def logout_instance(self, instance_name: str) -> Dict[str, Any]:
        """Logout a WhatsApp instance."""
        return await self._request("DELETE", f"/instance/logout/{instance_name}")
    
    async def delete_instance(self, instance_name: str) -> Dict[str, Any]:
        """Delete a WhatsApp instance."""
        return await self._request("DELETE", f"/instance/delete/{instance_name}")
    
    async def set_webhook(self, instance_name: str, webhook_url: str, events: List[str] = None) -> Dict[str, Any]:
        """Set webhook URL for an instance."""
        if events is None:
            events = [
                "QRCODE_UPDATED",
                "CONNECTION_UPDATE", 
                "MESSAGES_UPSERT",
                "SEND_MESSAGE"
            ]
        
        webhook_data = {
            "url": webhook_url,
            "byEvents": True,
            "base64": True,
            "events": events
        }
        
        return await self._request("POST", f"/webhook/set/{instance_name}", json=webhook_data)


# Global Evolution client instance
evolution_client = None

def get_evolution_client() -> EvolutionClient:
    """Get global Evolution API client instance."""
    global evolution_client
    
    if evolution_client is None:
        # Use environment variables for Evolution API configuration
        evolution_url = config.get_env("EVOLUTION_API_URL", "http://localhost:8080")
        evolution_key = config.get_env("EVOLUTION_API_KEY", "")
        
        if not evolution_key:
            raise Exception("EVOLUTION_API_KEY not configured")
        
        evolution_client = EvolutionClient(evolution_url, evolution_key)
        logger.info(f"Evolution API client initialized: {evolution_url}")
    
    return evolution_client