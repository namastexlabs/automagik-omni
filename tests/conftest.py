"""
Shared test fixtures and utilities for omni-hub tests.
"""

import pytest
import os
from typing import Dict, Any, Generator
from unittest.mock import patch, AsyncMock, Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test environment variables BEFORE any imports
os.environ["ENVIRONMENT"] = "test"
os.environ["AGENT_API_URL"] = "http://test-agent-api"
os.environ["AGENT_API_KEY"] = "test-key"
os.environ["DEFAULT_AGENT_NAME"] = "test-agent"
os.environ["WHATSAPP_INSTANCE"] = "test-instance"
os.environ["SESSION_ID_PREFIX"] = "test-"
os.environ["LOG_LEVEL"] = "ERROR"  # Reduce log noise in tests
os.environ["AUTOMAGIK_OMNI_API_KEY"] = ""  # Disable API key for tests
os.environ["EVOLUTION_API_URL"] = "http://test-evolution-api"
os.environ["EVOLUTION_API_KEY"] = "test-evolution-key"

# Override config for tests
import sys

if "src.config" in sys.modules:
    # Reload config module to pick up test environment
    import importlib

    importlib.reload(sys.modules["src.config"])

# Import after setting environment
from src.db.database import Base
from src.db.models import InstanceConfig  # Import models to register with Base


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a test database session.
    
    Uses database from environment configuration if TEST_DATABASE_URL is set,
    otherwise defaults to in-memory SQLite for isolation.
    """
    # Check for test-specific database URL first
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    
    if test_db_url:
        # Use the test database from environment
        if test_db_url.startswith("sqlite"):
            engine = create_engine(
                test_db_url, connect_args={"check_same_thread": False}
            )
        else:
            engine = create_engine(test_db_url)
    else:
        # Default to in-memory SQLite for test isolation
        engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )

    # Drop and recreate all tables to ensure fresh schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def override_get_db(test_db: Session):
    """Override the database dependency for testing."""

    def _override_get_db():
        yield test_db

    # Patch the dependency
    with patch("src.api.deps.get_database", side_effect=_override_get_db):
        with patch("src.api.app.get_database", side_effect=_override_get_db):
            yield test_db


@pytest.fixture
def test_client(override_get_db):
    """Create FastAPI test client with overridden database."""
    from src.api.app import app
    from src.api.deps import verify_api_key, get_database

    # Mock authentication for tests
    def mock_verify_api_key():
        return "test-api-key"

    # Override database dependency to use test database
    def override_db_dependency():
        yield override_get_db

    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    app.dependency_overrides[get_database] = override_db_dependency

    # Mock Evolution API calls to prevent external dependencies
    with patch(
        "src.channels.whatsapp.evolution_client.get_evolution_client"
    ) as mock_client:
        mock_evolution = Mock()

        # Fixed mock for create_instance to return correct structure
        mock_evolution.create_instance = AsyncMock(
            return_value={
                "instance": {"instanceId": "test-123"},
                "hash": {"apikey": "test-key"},
            }
        )

        # Fix the mock to handle parameters properly
        async def mock_fetch_instances(instance_name=None):
            return []

        mock_evolution.fetch_instances = mock_fetch_instances

        # Add other methods that might be called
        mock_evolution.set_webhook = AsyncMock(return_value={"status": "success"})
        mock_evolution.connect_instance = AsyncMock(return_value={"qr": "test-qr"})
        mock_evolution.get_connection_state = AsyncMock(return_value={"state": "open"})
        mock_evolution.restart_instance = AsyncMock(return_value={"status": "success"})
        mock_evolution.logout_instance = AsyncMock(return_value={"status": "success"})
        mock_evolution.delete_instance = AsyncMock(return_value={"status": "success"})

        mock_client.return_value = mock_evolution

        # Mock startup database operations properly
        with patch("src.db.database.get_db") as mock_startup_db:
            mock_startup_db.return_value = iter([override_get_db])

            with patch("src.db.bootstrap.ensure_default_instance") as mock_bootstrap:
                # Create default instance in test database
                default_instance = InstanceConfig(
                    name="test-default",
                    channel_type="whatsapp",
                    evolution_url="http://test.com",
                    evolution_key="test-key",
                    whatsapp_instance="test-default",
                    agent_api_url="http://agent.com",
                    agent_api_key="agent-key",
                    default_agent="test_agent",
                    is_default=True,
                )
                override_get_db.add(default_instance)
                override_get_db.commit()
                mock_bootstrap.return_value = default_instance

                try:
                    yield TestClient(app)
                finally:
                    # Clean up override
                    app.dependency_overrides.clear()


@pytest.fixture
def sample_instance_config() -> Dict[str, Any]:
    """Sample instance configuration data for InstanceConfigCreate schema."""
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
        "is_default": False,
    }


@pytest.fixture
def default_instance_config(test_db: Session) -> InstanceConfig:
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
        is_default=True,
    )
    test_db.add(instance)
    test_db.commit()
    test_db.refresh(instance)
    return instance


@pytest.fixture
def sample_webhook_payload() -> Dict[str, Any]:
    """Sample webhook payload from Evolution API."""
    return {
        "event": "messages.upsert",
        "instance": "test-instance",
        "data": {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False,
                "id": "test-message-id",
            },
            "message": {"conversation": "Hello, this is a test message"},
            "messageTimestamp": 1640995200,
            "pushName": "Test User",
        },
        "server_url": "http://test-evolution.com",
        "apikey": "test-evolution-key",
    }


@pytest.fixture
def mock_agent_response():
    """Mock successful agent API response."""
    return {
        "response": "Hello! I'm a test response from the agent.",
        "session_id": "test-session-123",
    }


@pytest.fixture
def mock_evolution_response():
    """Mock successful Evolution API response."""
    return {
        "key": {
            "remoteJid": "5511999999999@s.whatsapp.net",
            "fromMe": True,
            "id": "response-message-id",
        },
        "status": "success",
    }


@pytest.fixture
def mock_agent_api_client():
    """Mock AgentApiClient for testing."""
    with patch("src.services.agent_api_client.AgentApiClient") as mock_class:
        mock_instance = mock_class.return_value
        mock_instance.health_check = Mock(return_value=True)
        mock_instance.process_message = AsyncMock(return_value="Mock agent response")
        mock_instance.run_agent = AsyncMock(
            return_value={"response": "Mock agent response"}
        )
        yield mock_instance


@pytest.fixture
def mock_evolution_api_sender():
    """Mock EvolutionApiSender for testing."""
    with patch(
        "src.channels.whatsapp.evolution_api_sender.EvolutionApiSender"
    ) as mock_class:
        mock_instance = mock_class.return_value
        mock_instance.send_text_message = AsyncMock(return_value=True)
        mock_instance.send_presence = AsyncMock(return_value=True)
        mock_instance.update_from_webhook = Mock()
        yield mock_instance


@pytest.fixture
def mock_message_router():
    """Mock MessageRouter to prevent external agent API calls."""
    with patch("src.services.message_router.message_router") as mock_router:
        mock_router.route_message.return_value = {
            "response": "Test response from mocked agent",
            "success": True,
            "user_data": {"user_id": "test-user-123"}
        }
        yield mock_router


@pytest.fixture
def mock_agent_api_client():
    """Mock AgentApiClient to prevent external API calls."""
    with patch("src.services.agent_api_client.agent_api_client") as mock_client:
        mock_client.process_message.return_value = {
            "response": "Test agent response",
            "success": True
        }
        mock_client.health_check.return_value = True
        yield mock_client


@pytest.fixture
def mock_requests():
    """Mock requests library for HTTP calls."""
    with patch("requests.post") as mock_post:
        with patch("requests.get") as mock_get:
            # Setup default successful responses
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_response.text = "Success"

            mock_post.return_value = mock_response
            mock_get.return_value = mock_response

            yield {"post": mock_post, "get": mock_get, "response": mock_response}


@pytest.fixture
def cli_runner():
    """Create CLI runner for testing Typer commands."""
    from typer.testing import CliRunner

    return CliRunner()


class AsyncMockResponse:
    """Helper class for async HTTP response mocking."""

    def __init__(self, json_data: Dict[str, Any], status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = str(json_data)

    async def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            from httpx import HTTPStatusError

            raise HTTPStatusError(
                f"HTTP {self.status_code}", request=None, response=self
            )


@pytest.fixture
def async_mock_response():
    """Factory for creating async mock responses."""
    return AsyncMockResponse
