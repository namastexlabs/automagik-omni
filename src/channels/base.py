"""
Base channel handler interface for omnichannel support.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
from src.db.models import InstanceConfig


class QRCodeResponse(BaseModel):
    """Generic QR code/connection response."""

    instance_name: str
    channel_type: str
    qr_code: Optional[str] = None
    auth_url: Optional[str] = None  # For OAuth flows like Slack
    invite_url: Optional[str] = None  # For invite flows like Discord
    status: str
    message: str


class ConnectionStatus(BaseModel):
    """Generic connection status response."""

    instance_name: str
    channel_type: str
    status: str  # connected|disconnected|connecting|error
    channel_data: Optional[Dict[str, Any]] = None


class ChannelHandler(ABC):
    """Abstract base class for channel handlers."""

    @abstractmethod
    async def create_instance(
        self, instance: InstanceConfig, **kwargs
    ) -> Dict[str, Any]:
        """Create a new instance in the external service."""
        pass

    @abstractmethod
    async def get_qr_code(self, instance: InstanceConfig) -> QRCodeResponse:
        """Get QR code or connection info for the instance."""
        pass

    @abstractmethod
    async def get_status(self, instance: InstanceConfig) -> ConnectionStatus:
        """Get connection status of the instance."""
        pass

    @abstractmethod
    async def restart_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Restart the instance connection."""
        pass

    @abstractmethod
    async def logout_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Logout/disconnect the instance."""
        pass

    @abstractmethod
    async def delete_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Delete the instance from external service."""
        pass


class ChannelHandlerFactory:
    """Factory for creating channel-specific handlers."""

    _handlers = {}

    @classmethod
    def register_handler(cls, channel_type: str, handler_class):
        """Register a channel handler."""
        cls._handlers[channel_type] = handler_class

    @classmethod
    def get_handler(cls, channel_type: str) -> ChannelHandler:
        """Get handler for the specified channel type."""
        if channel_type not in cls._handlers:
            raise ValueError(f"Unsupported channel type: {channel_type}")

        return cls._handlers[channel_type]()

    @classmethod
    def get_supported_channels(cls) -> list:
        """Get list of supported channel types."""
        return list(cls._handlers.keys())
