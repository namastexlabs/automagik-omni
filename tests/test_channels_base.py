"""Tests for src/channels/base.py module."""

import pytest
from src.channels.base import (
    QRCodeResponse,
    ConnectionStatus,
    ChannelHandler,
    ChannelHandlerFactory,
)
from src.db.models import InstanceConfig


class MockChannelHandler(ChannelHandler):
    """Mock implementation for testing."""

    async def create_instance(self, instance: InstanceConfig, **kwargs):
        return {"status": "created"}

    async def get_qr_code(self, instance: InstanceConfig):
        return QRCodeResponse(
            instance_name=instance.name,
            channel_type=instance.channel_type,
            qr_code="mock_qr",
            status="ready",
            message="Mock QR code",
        )

    async def get_status(self, instance: InstanceConfig):
        return ConnectionStatus(
            instance_name=instance.name,
            channel_type=instance.channel_type,
            status="connected",
        )

    async def restart_instance(self, instance: InstanceConfig):
        return {"status": "restarted"}

    async def logout_instance(self, instance: InstanceConfig):
        return {"status": "logged_out"}

    async def delete_instance(self, instance: InstanceConfig):
        return {"status": "deleted"}


def test_qr_code_response_creation():
    """Test QRCodeResponse model instantiation."""
    response = QRCodeResponse(
        instance_name="test",
        channel_type="whatsapp",
        qr_code="test_qr_code",
        auth_url="https://auth.example.com",
        invite_url="https://invite.example.com",
        status="ready",
        message="QR code generated",
    )
    assert response.instance_name == "test"
    assert response.channel_type == "whatsapp"
    assert response.qr_code == "test_qr_code"
    assert response.auth_url == "https://auth.example.com"
    assert response.invite_url == "https://invite.example.com"
    assert response.status == "ready"


def test_qr_code_response_optional_fields():
    """Test QRCodeResponse with optional fields as None."""
    response = QRCodeResponse(
        instance_name="test",
        channel_type="discord",
        status="pending",
        message="Waiting for auth",
    )
    assert response.qr_code is None
    assert response.auth_url is None
    assert response.invite_url is None


def test_connection_status_creation():
    """Test ConnectionStatus model instantiation."""
    status = ConnectionStatus(
        instance_name="test",
        channel_type="whatsapp",
        status="connected",
        channel_data={"user": "test_user", "phone": "+1234567890"},
    )
    assert status.instance_name == "test"
    assert status.channel_type == "whatsapp"
    assert status.status == "connected"
    assert status.channel_data["user"] == "test_user"


def test_connection_status_without_channel_data():
    """Test ConnectionStatus without optional channel_data."""
    status = ConnectionStatus(instance_name="test", channel_type="discord", status="disconnected")
    assert status.channel_data is None


def test_channel_handler_factory_register_and_get():
    """Test registering and retrieving a channel handler."""
    ChannelHandlerFactory.register_handler("test_channel", MockChannelHandler)
    handler = ChannelHandlerFactory.get_handler("test_channel")
    assert isinstance(handler, MockChannelHandler)


def test_channel_handler_factory_unsupported_channel():
    """Test retrieving an unsupported channel type raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported channel type: nonexistent"):
        ChannelHandlerFactory.get_handler("nonexistent")


def test_channel_handler_factory_get_supported_channels():
    """Test retrieving list of supported channels."""
    ChannelHandlerFactory.register_handler("channel_a", MockChannelHandler)
    ChannelHandlerFactory.register_handler("channel_b", MockChannelHandler)
    supported = ChannelHandlerFactory.get_supported_channels()
    assert "channel_a" in supported
    assert "channel_b" in supported


@pytest.mark.asyncio
async def test_mock_handler_lifecycle():
    """Test full lifecycle of mock channel handler."""
    instance = InstanceConfig(
        name="test_instance",
        channel_type="mock",
        agent_api_url="http://test.api",
        agent_api_key="test_key",
    )

    handler = MockChannelHandler()

    # Test create
    result = await handler.create_instance(instance)
    assert result["status"] == "created"

    # Test get_qr_code
    qr_response = await handler.get_qr_code(instance)
    assert qr_response.instance_name == "test_instance"
    assert qr_response.qr_code == "mock_qr"

    # Test get_status
    status = await handler.get_status(instance)
    assert status.status == "connected"

    # Test restart
    result = await handler.restart_instance(instance)
    assert result["status"] == "restarted"

    # Test logout
    result = await handler.logout_instance(instance)
    assert result["status"] == "logged_out"

    # Test delete
    result = await handler.delete_instance(instance)
    assert result["status"] == "deleted"
