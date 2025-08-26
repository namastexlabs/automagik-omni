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
from src.channels.whatsapp.mention_parser import WhatsAppMentionParser
from src.channels.whatsapp.evolution_api_sender import EvolutionApiSender


def _create_postgresql_test_database():
    """Create a temporary PostgreSQL database for testing."""
    import uuid
    from sqlalchemy import create_engine, text
    
    # Database connection details from environment
    postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
    postgres_port = os.environ.get("POSTGRES_PORT", "5432")
    postgres_user = os.environ.get("POSTGRES_USER", "postgres")
    postgres_password = os.environ.get("POSTGRES_PASSWORD", "")
    postgres_db = os.environ.get("POSTGRES_DB", "postgres")
    
    # Create a unique test database name
    test_db_name = f"test_omni_{uuid.uuid4().hex[:8]}"
    
    # Connect to PostgreSQL server to create test database
    server_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    server_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
    
    try:
        # Create test database
        with server_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
        
        # Return connection URL for the test database
        test_db_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{test_db_name}"
        return test_db_url, test_db_name, server_engine
        
    except Exception as e:
        server_engine.dispose()
        raise Exception(f"Failed to create PostgreSQL test database: {e}")


def _cleanup_postgresql_test_database(test_db_name: str, server_engine):
    """Clean up the PostgreSQL test database."""
    try:
        with server_engine.connect() as conn:
            # Terminate active connections to the test database
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{test_db_name}'
                  AND pid <> pg_backend_pid()
            """))
            # Drop the test database
            conn.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}"'))
    except Exception as e:
        print(f"Warning: Failed to cleanup PostgreSQL test database {test_db_name}: {e}")
    finally:
        server_engine.dispose()


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a test database session.
    
    Database selection priority:
    1. TEST_DATABASE_URL environment variable (explicit override)
    2. PostgreSQL if POSTGRES_HOST is set and psycopg2 is available
    3. Temporary file-based SQLite (fallback)
    """
    engine = None
    cleanup_func = None
    
    # Check for explicit test database URL override
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    
    if test_db_url:
        # Use the explicit test database from environment
        if test_db_url.startswith("sqlite"):
            engine = create_engine(
                test_db_url, connect_args={"check_same_thread": False}
            )
        else:
            engine = create_engine(test_db_url)
        print(f"Using explicit test database: {test_db_url}")
        
    elif os.environ.get("POSTGRES_HOST"):
        # Try to use PostgreSQL if configured
        try:
            import psycopg2  # Check if PostgreSQL driver is available
            test_db_url, test_db_name, server_engine = _create_postgresql_test_database()
            engine = create_engine(test_db_url)
            
            # Set up cleanup function
            cleanup_func = lambda: _cleanup_postgresql_test_database(test_db_name, server_engine)
            print(f"Created PostgreSQL test database: {test_db_name}")
            
        except ImportError:
            print("Warning: psycopg2 not available, falling back to SQLite")
            engine = None
        except Exception as e:
            print(f"Warning: PostgreSQL setup failed ({e}), falling back to SQLite")
            engine = None
    
    # Fallback to temporary SQLite database
    if engine is None:
        import tempfile
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        engine = create_engine(
            f"sqlite:///{temp_db.name}", connect_args={"check_same_thread": False}
        )
        engine._test_temp_file = temp_db.name
        print(f"Using temporary SQLite database: {temp_db.name}")

    # Drop and recreate all tables to ensure fresh schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        # Ensure any pending transactions are rolled back
        db.rollback()
        db.close()
        
        # Drop tables for clean state
        try:
            Base.metadata.drop_all(bind=engine)
        except Exception as e:
            print(f"Warning: Failed to drop tables during cleanup: {e}")
        
        # Database-specific cleanup
        if cleanup_func:
            # PostgreSQL: Drop the entire test database
            cleanup_func()
        elif hasattr(engine, '_test_temp_file'):
            # SQLite: Remove temporary file
            try:
                os.unlink(engine._test_temp_file)
            except OSError:
                pass  # File might already be deleted
        
        # Dispose of the engine
        engine.dispose()


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
def test_client(test_db):
    """Create FastAPI test client with overridden database."""
    # Import after environment is set and before app is created
    from src.api.deps import verify_api_key, get_database
    
    # Import app AFTER setting up the test environment
    from src.api.app import app

    # Mock authentication for tests
    def mock_verify_api_key():
        return "test-api-key"

    # Override database dependency to use test database
    # Create a proper generator function that yields the test database session
    def override_db_dependency():
        yield test_db

    # Also override the base get_db function to ensure all database calls use test DB
    def override_base_get_db():
        yield test_db

    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    app.dependency_overrides[get_database] = override_db_dependency
    
    # Import and override the base database dependency too
    from src.db.database import get_db
    app.dependency_overrides[get_db] = override_base_get_db

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
            mock_startup_db.return_value = iter([test_db])

            with patch("src.db.bootstrap.ensure_default_instance") as mock_bootstrap:
                # Create default instance in test database
                default_instance = InstanceConfig(
                    name="test-instance",
                    channel_type="whatsapp",
                    evolution_url="http://test.com",
                    evolution_key="test-key",
                    whatsapp_instance="test-instance",
                    agent_api_url="http://agent.com",
                    agent_api_key="agent-key",
                    default_agent="test_agent",
                    is_default=True,
                )
                test_db.add(default_instance)
                test_db.commit()
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


# ===== MENTION TESTING FIXTURES =====

@pytest.fixture
def mention_parser():
    """WhatsApp mention parser instance for testing."""
    return WhatsAppMentionParser()


@pytest.fixture
def mock_evolution_sender():
    """Mock Evolution API sender configured for testing."""
    sender = Mock(spec=EvolutionApiSender)
    sender.server_url = "https://test-evolution.com"
    sender.api_key = "test-evolution-key"
    sender.instance_name = "test-instance"
    sender.send_text_message.return_value = True
    return sender


@pytest.fixture
def mock_instance_config():
    """Mock instance configuration for mention testing."""
    config = Mock(spec=InstanceConfig)
    config.name = "test-instance"
    config.evolution_url = "https://test-evolution.com"
    config.evolution_key = "test-evolution-key"
    config.whatsapp_instance = "test-whatsapp-instance"
    config.agent_api_url = "https://test-agent.com"
    config.agent_api_key = "test-agent-key"
    config.default_agent = "test-agent"
    return config


@pytest.fixture
def sample_mention_texts():
    """Sample texts with various mention formats for testing."""
    return {
        "basic": "Hello @5511999999999, how are you?",
        "international": "Contact @+5511888888888 for support",
        "with_spaces": "Meeting with @55 11 999999999 at 3pm",
        "multiple": "Team: @5511111111111, @5511222222222, @5511333333333",
        "mixed": "Call @5511999999999 or email user@domain.com",
        "no_mentions": "Regular message without any mentions",
        "split_message": "First part with @5511999999999\n\nSecond part without mentions"
    }


@pytest.fixture
def expected_mention_jids():
    """Expected WhatsApp JIDs for sample mention texts."""
    return {
        "basic": ["5511999999999@s.whatsapp.net"],
        "international": ["5511888888888@s.whatsapp.net"],
        "with_spaces": ["5511999999999@s.whatsapp.net"],
        "multiple": [
            "5511111111111@s.whatsapp.net",
            "5511222222222@s.whatsapp.net", 
            "5511333333333@s.whatsapp.net"
        ],
        "mixed": ["5511999999999@s.whatsapp.net"],
        "no_mentions": [],
        "split_message": ["5511999999999@s.whatsapp.net"]
    }


@pytest.fixture
def mock_evolution_response():
    """Mock successful Evolution API HTTP response."""
    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = {"status": "success", "message": "sent"}
    return response


@pytest.fixture
def mention_api_headers():
    """Standard headers for mention API testing."""
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer namastex888"
    }
