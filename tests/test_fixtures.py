"""
Comprehensive test fixtures for omni-hub API testing.
"""

import os
import pytest
from typing import Generator
from unittest.mock import patch, AsyncMock, Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test environment before any imports
os.environ["ENVIRONMENT"] = "test"
os.environ["OMNI_HUB_API_KEY"] = ""
os.environ["EVOLUTION_API_URL"] = "http://test-evolution"
os.environ["EVOLUTION_API_KEY"] = "test-key"

from src.db.database import Base
from src.db.models import InstanceConfig


@pytest.fixture(scope="function")
def test_db_session() -> Generator[Session, None, None]:
    """Create isolated test database session."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_client_with_db(test_db_session):
    """Create FastAPI test client with proper database and auth mocking."""
    from src.api.app import app
    from src.api.deps import verify_api_key, get_database
    
    # Mock authentication
    def mock_verify_api_key():
        return "test-api-key"
    
    # Mock database dependency
    def mock_get_database():
        yield test_db_session
    
    # Override dependencies
    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    app.dependency_overrides[get_database] = mock_get_database
    
    # Mock Evolution API calls
    with patch('src.channels.whatsapp.channel_handler.get_evolution_client') as mock_client:
        mock_evolution = Mock()
        
        # Mock fetch_instances for existing instance check
        mock_evolution.fetch_instances = AsyncMock(return_value=[])
        
        # Mock create_instance for new instance creation
        mock_evolution.create_instance = AsyncMock(return_value={
            "instance": {"instanceId": "test-123"},
            "hash": {"apikey": "test-key"}
        })
        
        # Mock other Evolution API methods
        mock_evolution.set_webhook = AsyncMock(return_value={"status": "success"})
        mock_evolution.connect_instance = AsyncMock(return_value={"qr": "test-qr-code"})
        mock_evolution.get_connection_state = AsyncMock(return_value={"state": "open"})
        mock_evolution.restart_instance = AsyncMock(return_value={"status": "restarted"})
        mock_evolution.logout_instance = AsyncMock(return_value={"status": "logged_out"})
        mock_evolution.delete_instance = AsyncMock(return_value={"status": "deleted"})
        
        mock_client.return_value = mock_evolution
        
        # Mock startup database operations to prevent real DB access
        with patch('src.db.database.get_db') as mock_startup_db:
            mock_startup_db.return_value = iter([test_db_session])
            
            with patch('src.db.bootstrap.ensure_default_instance') as mock_bootstrap:
                # Create a test default instance
                default_instance = InstanceConfig(
                    name="test-default",
                    channel_type="whatsapp",
                    evolution_url="http://test.com",
                    evolution_key="test-key",
                    whatsapp_instance="test-default",
                    agent_api_url="http://agent.com",
                    agent_api_key="agent-key",
                    default_agent="test_agent",
                    is_default=True
                )
                test_db_session.add(default_instance)
                test_db_session.commit()
                mock_bootstrap.return_value = default_instance
                
                try:
                    yield TestClient(app)
                finally:
                    # Clean up dependency overrides
                    app.dependency_overrides.clear()


@pytest.fixture
def sample_instance_data():
    """Sample instance data for API testing."""
    return {
        "name": "test_instance",
        "channel_type": "whatsapp",
        "evolution_url": "http://test-evolution.com",
        "evolution_key": "test-evolution-key",
        "whatsapp_instance": "test_whatsapp",
        "session_id_prefix": "test_",
        "phone_number": "+5511999999999",
        "auto_qr": True,
        "integration": "WHATSAPP-BAILEYS",
        "agent_api_url": "http://test-agent.com",
        "agent_api_key": "test-agent-key",
        "default_agent": "test_agent",
        "agent_timeout": 60,
        "is_default": False
    }


@pytest.fixture
def sample_webhook_payload():
    """Sample webhook payload for testing."""
    return {
        "event": "messages.upsert",
        "instance": "test-instance",
        "data": {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False,
                "id": "test-message-id"
            },
            "message": {
                "conversation": "Hello, this is a test message"
            },
            "messageTimestamp": 1640995200,
            "pushName": "Test User"
        },
        "server_url": "http://test-evolution.com",
        "apikey": "test-evolution-key"
    }


@pytest.fixture
def default_instance_in_db(test_db_session):
    """Create a default instance in the test database."""
    instance = InstanceConfig(
        name="default",
        channel_type="whatsapp",
        evolution_url="http://default-evolution.com",
        evolution_key="default-evolution-key",
        whatsapp_instance="default_whatsapp",
        session_id_prefix="default_",
        agent_api_url="http://default-agent.com",
        agent_api_key="default-agent-key",
        default_agent="default_agent",
        agent_timeout=60,
        is_default=True
    )
    test_db_session.add(instance)
    test_db_session.commit()
    test_db_session.refresh(instance)
    return instance