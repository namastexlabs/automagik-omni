"""
Comprehensive integration tests for omnichannel architecture.
Tests core functionality without complex FastAPI client dependency issues.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock, Mock

# Set test environment before any imports
os.environ["ENVIRONMENT"] = "test"
os.environ["AUTOMAGIK_OMNI_API_KEY"] = ""

from src.db.database import Base
from src.db.models import InstanceConfig
from src.channels.base import ChannelHandlerFactory
from src.channels.whatsapp.channel_handler import WhatsAppChannelHandler
from src.api.routes.instances import InstanceConfigCreate


class TestOmnichannelIntegration:
    """Integration tests for omnichannel architecture."""

    @pytest.fixture
    def db_session(self):
        """Create test database session."""
        engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def test_database_model_creation(self, db_session):
        """Test that instance models can be created with new schema."""
        instance = InstanceConfig(
            name="test_instance",
            channel_type="whatsapp",
            evolution_url="http://test.com",
            evolution_key="test-key",
            whatsapp_instance="test_whatsapp",
            session_id_prefix="test_",
            agent_api_url="http://agent.com",
            agent_api_key="agent-key",
            default_agent="test_agent",
            agent_timeout=60,
            is_default=False,
        )

        db_session.add(instance)
        db_session.commit()
        db_session.refresh(instance)

        assert instance.id is not None
        assert instance.name == "test_instance"
        assert instance.channel_type == "whatsapp"
        assert instance.evolution_url == "http://test.com"
        assert instance.created_at is not None

    def test_channel_handler_factory(self):
        """Test channel handler factory functionality."""
        # Test supported channels
        supported = ChannelHandlerFactory.get_supported_channels()
        assert "whatsapp" in supported

        # Test getting handler
        handler = ChannelHandlerFactory.get_handler("whatsapp")
        assert isinstance(handler, WhatsAppChannelHandler)

        # Test invalid channel
        with pytest.raises(ValueError):
            ChannelHandlerFactory.get_handler("invalid")

    def test_pydantic_schema_validation(self):
        """Test API schema validation."""
        # Valid data
        valid_data = {
            "name": "test_instance",
            "channel_type": "whatsapp",
            "evolution_url": "http://test.com",
            "evolution_key": "test-key",
            "whatsapp_instance": "test_whatsapp",
            "session_id_prefix": "test_",
            "phone_number": "+5511999999999",
            "auto_qr": True,
            "integration": "WHATSAPP-BAILEYS",
            "agent_api_url": "http://agent.com",
            "agent_api_key": "agent-key",
            "default_agent": "test_agent",
            "agent_timeout": 60,
            "is_default": False,
        }

        schema = InstanceConfigCreate(**valid_data)
        assert schema.name == "test_instance"
        assert schema.channel_type == "whatsapp"
        assert schema.phone_number == "+5511999999999"

        # Invalid data (missing required fields)
        invalid_data = {"name": "test"}
        with pytest.raises(Exception):  # Pydantic validation error
            InstanceConfigCreate(**invalid_data)

    @pytest.mark.asyncio
    @patch("src.channels.whatsapp.channel_handler.EvolutionClient")
    async def test_whatsapp_handler_create_instance(
        self, mock_evolution_client, db_session
    ):
        """Test WhatsApp channel handler instance creation."""
        # Setup mock
        mock_client = Mock()
        mock_client.fetch_instances = AsyncMock(return_value=[])
        mock_client.create_instance = AsyncMock(
            return_value={
                "instance": {"instanceId": "test-123"},
                "hash": {"apikey": "test-key"},
            }
        )
        mock_evolution_client.return_value = mock_client

        # Create instance config
        instance = InstanceConfig(
            name="test_whatsapp",
            channel_type="whatsapp",
            evolution_url="http://test.com",
            evolution_key="test-key",
            whatsapp_instance="test_whatsapp",
            agent_api_url="http://agent.com",
            agent_api_key="agent-key",
            default_agent="test_agent",
        )

        # Test handler
        handler = WhatsAppChannelHandler()
        result = await handler.create_instance(
            instance,
            phone_number="+5511999999999",
            auto_qr=True,
            integration="WHATSAPP-BAILEYS",
        )

        assert "evolution_instance_id" in result
        assert result["evolution_instance_id"] == "test-123"
        assert not result["existing_instance"]

        # Verify Evolution client was called
        mock_client.fetch_instances.assert_called_once()
        mock_client.create_instance.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.channels.whatsapp.channel_handler.EvolutionClient")
    async def test_whatsapp_handler_existing_instance(
        self, mock_evolution_client, db_session
    ):
        """Test WhatsApp handler reusing existing Evolution instance."""
        # Setup mock with existing instance
        existing_instance = Mock()
        existing_instance.instanceName = (
            "existing_whatsapp"  # Match the instance name we're testing
        )
        existing_instance.instanceId = "existing-123"
        existing_instance.apikey = "existing-key"
        existing_instance.dict.return_value = {"instanceId": "existing-123"}

        mock_client = Mock()
        mock_client.fetch_instances = AsyncMock(return_value=[existing_instance])
        mock_client.set_webhook = AsyncMock(return_value={"status": "success"})
        mock_evolution_client.return_value = mock_client

        # Create instance config
        instance = InstanceConfig(
            name="existing_whatsapp",
            channel_type="whatsapp",
            evolution_url="http://test.com",
            evolution_key="test-key",
            whatsapp_instance="existing_whatsapp",
            agent_api_url="http://agent.com",
            agent_api_key="agent-key",
            default_agent="test_agent",
        )

        # Test handler
        handler = WhatsAppChannelHandler()
        result = await handler.create_instance(instance)

        assert "evolution_instance_id" in result
        assert result["evolution_instance_id"] == "existing-123"
        assert result["existing_instance"] is True

        # Verify only fetch was called, not create
        mock_client.fetch_instances.assert_called_once()
        mock_client.create_instance.assert_not_called()
        mock_client.set_webhook.assert_called_once()

    def test_instance_crud_operations(self, db_session):
        """Test basic CRUD operations on instances."""
        # Create
        instance = InstanceConfig(
            name="crud_test",
            channel_type="whatsapp",
            evolution_url="http://test.com",
            evolution_key="test-key",
            whatsapp_instance="crud_test",
            agent_api_url="http://agent.com",
            agent_api_key="agent-key",
            default_agent="test_agent",
        )
        db_session.add(instance)
        db_session.commit()
        db_session.refresh(instance)

        # Read
        found = db_session.query(InstanceConfig).filter_by(name="crud_test").first()
        assert found is not None
        assert found.name == "crud_test"
        assert found.channel_type == "whatsapp"

        # Update
        found.agent_timeout = 120
        db_session.commit()
        db_session.refresh(found)
        assert found.agent_timeout == 120

        # Delete
        db_session.delete(found)
        db_session.commit()

        deleted = db_session.query(InstanceConfig).filter_by(name="crud_test").first()
        assert deleted is None

    def test_default_instance_management(self, db_session):
        """Test default instance flag management."""
        # Create first instance as default
        instance1 = InstanceConfig(
            name="default_test1",
            channel_type="whatsapp",
            evolution_url="http://test1.com",
            evolution_key="test-key1",
            whatsapp_instance="test1",
            agent_api_url="http://agent1.com",
            agent_api_key="agent-key1",
            default_agent="test_agent1",
            is_default=True,
        )
        db_session.add(instance1)
        db_session.commit()

        # Create second instance
        instance2 = InstanceConfig(
            name="default_test2",
            channel_type="whatsapp",
            evolution_url="http://test2.com",
            evolution_key="test-key2",
            whatsapp_instance="test2",
            agent_api_url="http://agent2.com",
            agent_api_key="agent-key2",
            default_agent="test_agent2",
            is_default=False,
        )
        db_session.add(instance2)
        db_session.commit()

        # Verify first is default
        default = db_session.query(InstanceConfig).filter_by(is_default=True).first()
        assert default.name == "default_test1"

        # Set second as default
        db_session.query(InstanceConfig).filter_by(is_default=True).update(
            {"is_default": False}
        )
        instance2.is_default = True
        db_session.commit()

        # Verify only second is default
        defaults = db_session.query(InstanceConfig).filter_by(is_default=True).all()
        assert len(defaults) == 1
        assert defaults[0].name == "default_test2"

    def test_channel_type_variations(self, db_session):
        """Test different channel types."""
        # WhatsApp instance
        whatsapp = InstanceConfig(
            name="whatsapp_test",
            channel_type="whatsapp",
            evolution_url="http://test.com",
            evolution_key="test-key",
            whatsapp_instance="test_whatsapp",
            agent_api_url="http://agent.com",
            agent_api_key="agent-key",
            default_agent="test_agent",
        )
        db_session.add(whatsapp)

        # Future Slack instance (nullable Evolution fields)
        slack = InstanceConfig(
            name="slack_test",
            channel_type="slack",
            evolution_url=None,  # Not used for Slack
            evolution_key=None,  # Not used for Slack
            whatsapp_instance=None,  # Not used for Slack
            agent_api_url="http://agent.com",
            agent_api_key="agent-key",
            default_agent="test_agent",
        )
        db_session.add(slack)

        db_session.commit()

        # Verify both can be created and queried
        instances = db_session.query(InstanceConfig).all()
        assert len(instances) == 2

        whatsapp_found = (
            db_session.query(InstanceConfig).filter_by(channel_type="whatsapp").first()
        )
        assert whatsapp_found.evolution_url == "http://test.com"

        slack_found = (
            db_session.query(InstanceConfig).filter_by(channel_type="slack").first()
        )
        assert slack_found.evolution_url is None
