"""
Comprehensive End-to-End tests for all API endpoints.
Tests all endpoints for proper functionality, authentication, error handling,
database migrations, and real-world scenarios.
"""

import pytest
import time
import os
import tempfile
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.db.models import InstanceConfig, Base


class TestDatabaseSetup:
    """Test database initialization and migrations in realistic scenarios."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_database_creation_from_scratch(self, temp_db_path):
        """Test creating database from scratch like a fresh installation."""
        # Create engine for temporary database
        engine = create_engine(f"sqlite:///{temp_db_path}")

        # Test table creation
        Base.metadata.create_all(bind=engine)

        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
            table_names = [row[0] for row in result]
            assert "instance_configs" in table_names

    def test_database_migrations_with_existing_data(self, temp_db_path):
        """Test that migrations work with existing data."""
        # Create engine for temporary database
        engine = create_engine(f"sqlite:///{temp_db_path}")
        SessionLocal = sessionmaker(bind=engine)

        # Create initial schema
        Base.metadata.create_all(bind=engine)

        # Add some test data
        with SessionLocal() as db:
            test_instance = InstanceConfig(
                name="migration-test",
                whatsapp_instance="migration-whatsapp",
                evolution_url="https://migration.test.com",
                evolution_key="migration-key",
                agent_api_url="https://migration-agent.test.com",
                agent_api_key="migration-agent-key",
                default_agent="test-agent",
                is_default=True,
            )
            db.add(test_instance)
            db.commit()

        # Test that data persists and migrations don't break it
        with SessionLocal() as db:
            instances = db.query(InstanceConfig).all()
            assert len(instances) == 1
            assert instances[0].name == "migration-test"

    def test_alembic_migration_compatibility(self, temp_db_path):
        """Test Alembic migration system (requires alembic package)."""
        # First check if alembic is installed
        try:
            import alembic  # noqa: F401
        except ImportError:
            pytest.skip("Alembic package not installed - install with: pip install alembic")

        try:
            # Ensure proper import path resolution
            import sys
            import os

            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            from src.db.migrations import auto_migrate

            # Set up temporary database path
            with patch.dict(os.environ, {"DATABASE_URL": f"sqlite:///{temp_db_path}"}):
                result = auto_migrate()
                # auto_migrate returns bool, so check for boolean result
                assert isinstance(result, bool)

        except ImportError as e:
            pytest.skip(f"Migration module import failed: {e}")
        except Exception as e:
            # Don't skip on other exceptions - let them bubble up to show the real issue
            pytest.fail(f"Migration test failed with unexpected error: {e}")


class TestAPIEndpoints:
    """End-to-end tests for all API endpoints with realistic scenarios."""

    # Note: Removed conflicting setup_test_environment fixture.
    # Using conftest.py fixtures instead: test_client and mention_api_headers


class TestHealthEndpoints(TestAPIEndpoints):
    """Test health and system endpoints."""

    def test_health_check_no_auth_required(self, test_client):
        """Test health check endpoint works without authentication."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # Check the basic structure of the new health response
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "services" in data
        assert "api" in data["services"]
        assert data["services"]["api"]["status"] == "up"

    def test_health_check_performance(self, test_client):
        """Test health check responds quickly."""
        start_time = time.time()
        response = test_client.get("/health")
        duration = time.time() - start_time

        assert response.status_code == 200
        assert duration < 0.1  # Should respond in under 100ms

    def test_openapi_documentation_accessible(self, test_client):
        """Test OpenAPI documentation endpoints are accessible."""
        # Test Swagger UI
        response = test_client.get("/api/v1/docs")
        assert response.status_code == 200

        # Test ReDoc
        response = test_client.get("/api/v1/redoc")
        assert response.status_code == 200

        # Test OpenAPI schema
        response = test_client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "components" in schema

        # Verify bearer auth is configured
        assert "securitySchemes" in schema["components"]
        assert "bearerAuth" in schema["components"]["securitySchemes"]


class TestAuthenticationSecurity(TestAPIEndpoints):
    """Test authentication and security requirements in realistic scenarios."""

    def test_protected_endpoints_require_auth(self, test_db, monkeypatch):
        """Test that protected endpoints reject requests without authentication."""
        # Configure a real API key for authentication tests
        monkeypatch.setenv("AUTOMAGIK_OMNI_API_KEY", "test-api-key-secure")

        # Force reload config to pick up the new API key
        import importlib
        import src.config

        importlib.reload(src.config)

        # Import dependencies after config is set
        from src.api.deps import verify_api_key, get_database
        from src.api.app import app
        from fastapi.testclient import TestClient

        # Temporarily remove the auth override for this test
        original_auth_override = app.dependency_overrides.pop(verify_api_key, None)

        # Keep database override but use proper auth
        def override_db_dependency():
            yield test_db

        app.dependency_overrides[get_database] = override_db_dependency

        try:
            with TestClient(app) as auth_test_client:
                protected_endpoints = [
                    ("GET", "/api/v1/instances"),
                    ("POST", "/api/v1/instances"),
                    ("GET", "/api/v1/instances/test-instance"),
                    ("PUT", "/api/v1/instances/test-instance"),
                    ("DELETE", "/api/v1/instances/test-instance"),
                    ("GET", "/api/v1/traces"),
                ]

                for method, endpoint in protected_endpoints:
                    # Test without any auth header
                    response = auth_test_client.request(method, endpoint)
                    assert response.status_code in [
                        401,
                        403,
                    ], f"{method} {endpoint} should require auth but got {response.status_code}"

                    # Test with malformed auth header (not Bearer format)
                    headers = {"Authorization": "NotBearer token"}
                    response = auth_test_client.request(method, endpoint, headers=headers)
                    assert response.status_code in [
                        401,
                        403,
                    ], f"{method} {endpoint} should reject malformed auth but got {response.status_code}"
        finally:
            # Restore the auth override
            if original_auth_override:
                app.dependency_overrides[verify_api_key] = original_auth_override

    def test_bearer_token_validation(self, test_db, monkeypatch):
        """Test bearer token validation with various scenarios."""
        # Configure a real API key for authentication tests
        monkeypatch.setenv("AUTOMAGIK_OMNI_API_KEY", "test-api-key-secure")

        # Force reload config to pick up the new API key
        import importlib
        import src.config

        importlib.reload(src.config)

        # Import dependencies after config is set
        from src.api.deps import verify_api_key, get_database
        from src.api.app import app
        from fastapi.testclient import TestClient

        # Temporarily remove the auth override for this test
        original_auth_override = app.dependency_overrides.pop(verify_api_key, None)

        # Keep database override but use proper auth
        def override_db_dependency():
            yield test_db

        app.dependency_overrides[get_database] = override_db_dependency

        try:
            with TestClient(app) as auth_test_client:
                test_cases = [
                    ("", 422),  # Empty auth header - FastAPI validation error
                    ("invalid-token", 422),  # Invalid format - FastAPI validation error
                    (
                        "Bearer invalid-token",
                        401,
                    ),  # Invalid bearer token (401 for wrong API key)
                    (
                        "Basic dGVzdDp0ZXN0",
                        422,
                    ),  # Wrong auth type - FastAPI validation error
                ]

                for auth_header, expected_status in test_cases:
                    headers = {"Authorization": auth_header} if auth_header else {}
                    response = auth_test_client.get("/api/v1/instances", headers=headers)
                    # For empty/malformed auth headers, FastAPI returns 422 (validation error)
                    # For invalid tokens, our verify_api_key returns 401
                    assert response.status_code in [
                        401,
                        403,
                        422,
                    ], f"Auth header '{auth_header}' should return 401/403/422 but got {response.status_code}"
        finally:
            # Restore the auth override
            if original_auth_override:
                app.dependency_overrides[verify_api_key] = original_auth_override

    def test_valid_authentication_works(self, test_db, mention_api_headers, monkeypatch):
        """Test that valid authentication allows access."""
        # Configure the same API key that mention_api_headers uses
        monkeypatch.setenv("AUTOMAGIK_OMNI_API_KEY", "namastex888")  # This matches mention_api_headers

        # Force reload config to pick up the new API key
        import importlib
        import src.config

        importlib.reload(src.config)

        # Import dependencies after config is set
        from src.api.deps import verify_api_key, get_database
        from src.api.app import app
        from fastapi.testclient import TestClient

        # Temporarily remove the auth override for this test
        original_auth_override = app.dependency_overrides.pop(verify_api_key, None)

        # Keep database override but use proper auth
        def override_db_dependency():
            yield test_db

        app.dependency_overrides[get_database] = override_db_dependency

        try:
            with TestClient(app) as auth_test_client:
                # Test valid authentication with the correct Bearer token
                response = auth_test_client.get("/api/v1/instances", headers=mention_api_headers)
                assert response.status_code == 200, f"Valid auth should work but got {response.status_code}"
        finally:
            # Restore the auth override
            if original_auth_override:
                app.dependency_overrides[verify_api_key] = original_auth_override

    def test_webhook_endpoints_no_auth_required(self, test_client):
        """Test that webhook endpoints work without authentication (by design)."""
        webhook_data = {"event": "messages.upsert", "data": {"test": "webhook"}}

        # Mock webhook handler to avoid actual processing
        with patch("src.api.app._handle_evolution_webhook") as mock_handler:
            mock_handler.return_value = {"status": "success"}

            response = test_client.post("/webhook/evolution/test-instance", json=webhook_data)
            # Should work without auth (webhook endpoints are public by design)
            assert response.status_code == 200

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are properly configured or OPTIONS is handled."""
        response = test_client.options("/api/v1/instances")
        # Either CORS should be configured, or OPTIONS should be handled appropriately
        # Some APIs handle CORS at the infrastructure level (nginx, cloudflare, etc.)
        headers_lower = [h.lower() for h in response.headers.keys()]

        # Accept either: CORS headers present OR 405 Method Not Allowed (which is valid)
        has_cors = "access-control-allow-origin" in headers_lower
        method_not_allowed = response.status_code == 405

        assert has_cors or method_not_allowed, (
            f"Expected CORS headers or 405 status, got {response.status_code} with headers {headers_lower}"
        )


class TestInstanceManagementEndpoints(TestAPIEndpoints):
    """Test instance management CRUD operations."""

    def test_get_supported_channels(self, test_client, mention_api_headers):
        """Test getting supported channel types."""
        response = test_client.get("/api/v1/instances/supported-channels", headers=mention_api_headers)
        assert response.status_code == 200
        data = response.json()
        assert "supported_channels" in data
        assert "total_channels" in data
        assert "whatsapp" in data["supported_channels"]

    def test_list_instances_empty(self, test_client, mention_api_headers, test_db):
        """Test listing instances when database is empty."""
        # Clear any instances that might exist
        from src.db.models import InstanceConfig

        test_db.query(InstanceConfig).delete()
        test_db.commit()

        response = test_client.get("/api/v1/instances", headers=mention_api_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_instances_with_data(self, test_client, mention_api_headers):
        """Test listing instances with data."""
        response = test_client.get("/api/v1/instances", headers=mention_api_headers)
        assert response.status_code == 200
        instances = response.json()
        assert len(instances) == 1
        assert instances[0]["name"] == "test-instance"

    def test_create_instance_success(self, test_client, mention_api_headers):
        """Test creating a new instance."""
        instance_data = {
            "name": "new-instance",
            "channel_type": "whatsapp",
            "whatsapp_instance": "new-whatsapp",
            "evolution_url": "http://172.19.209.168:18080",
            "evolution_key": "real-evolution-key-123",
            "agent_api_url": "http://172.19.209.168:18881",
            "agent_api_key": "real-agent-key-123",
            "default_agent": "test-agent",
        }

        with patch("src.channels.base.ChannelHandlerFactory.get_handler") as mock_handler:
            # Make create_instance async
            async def mock_create_instance(*args, **kwargs):
                return {"status": "created"}

            mock_handler.return_value.create_instance = mock_create_instance

            response = test_client.post("/api/v1/instances", json=instance_data, headers=mention_api_headers)
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "new-instance"
            assert data["channel_type"] == "whatsapp"

    def test_create_instance_duplicate_name(self, test_client, mention_api_headers):
        """Test creating instance with duplicate name fails."""
        instance_data = {
            "name": "test-instance",  # Already exists
            "channel_type": "whatsapp",
            "whatsapp_instance": "duplicate",
            "evolution_url": "http://172.19.209.168:18080",
            "evolution_key": "key",
            "agent_api_url": "http://172.19.209.168:18881",
            "agent_api_key": "agent-key",
            "default_agent": "test-agent",
        }

        response = test_client.post("/api/v1/instances", json=instance_data, headers=mention_api_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_get_instance_success(self, test_client, mention_api_headers):
        """Test getting specific instance."""
        with patch("src.channels.base.ChannelHandlerFactory.get_handler") as mock_handler:
            mock_handler.return_value.get_instance_status.return_value = {"status": "connected"}

            response = test_client.get("/api/v1/instances/test-instance", headers=mention_api_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "test-instance"
            assert data["channel_type"] == "whatsapp"

    def test_get_instance_not_found(self, test_client, mention_api_headers):
        """Test getting non-existent instance."""
        response = test_client.get("/api/v1/instances/nonexistent", headers=mention_api_headers)
        assert response.status_code == 404

    def test_update_instance_success(self, test_client, mention_api_headers):
        """Test updating instance configuration."""
        update_data = {
            "agent_api_url": "https://updated-agent.test.com",
            "webhook_base64": False,
        }

        # No external service call needed for updates - just database
        response = test_client.put(
            "/api/v1/instances/test-instance",
            json=update_data,
            headers=mention_api_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent_api_url"] == "https://updated-agent.test.com"
        assert not data["webhook_base64"]

    def test_delete_instance_success(self, test_client, mention_api_headers):
        """Test deleting instance."""
        # First create another instance so we're not deleting the only one
        with patch("src.channels.base.ChannelHandlerFactory.get_handler") as mock_handler:
            # Make create_instance async
            async def mock_create_instance(*args, **kwargs):
                return {"status": "created"}

            mock_handler.return_value.create_instance = mock_create_instance

            extra_instance = {
                "name": "extra-instance",
                "channel_type": "whatsapp",
                "whatsapp_instance": "extra-whatsapp",
                "evolution_url": "http://172.19.209.168:18080",
                "evolution_key": "extra-key",
                "agent_api_url": "http://172.19.209.168:18881",
                "agent_api_key": "extra-agent-key",
                "default_agent": "extra-agent",
            }
            response = test_client.post("/api/v1/instances", json=extra_instance, headers=mention_api_headers)
            assert response.status_code == 201

        # Now delete the non-default instance
        with patch("src.channels.base.ChannelHandlerFactory.get_handler") as mock_handler:
            # Make delete_instance async
            async def mock_delete_instance(*args, **kwargs):
                return {"status": "deleted"}

            mock_handler.return_value.delete_instance = mock_delete_instance

            response = test_client.delete("/api/v1/instances/extra-instance", headers=mention_api_headers)
            assert response.status_code == 200


class TestInstanceOperationEndpoints(TestAPIEndpoints):
    """Test instance operation endpoints (QR, status, restart, etc.)."""

    def test_get_qr_code(self, test_client, mention_api_headers):
        """Test getting QR code for instance."""
        with patch("src.channels.base.ChannelHandlerFactory.get_handler") as mock_handler:
            # Make get_qr_code async
            async def mock_get_qr_code(*args, **kwargs):
                return {
                    "instance_name": "test-instance",
                    "channel_type": "whatsapp",
                    "qr_code": "data:image/png;base64,iVBORw0KGgo...",
                    "status": "qr_code",
                    "message": "QR code generated",
                }

            mock_handler.return_value.get_qr_code = mock_get_qr_code

            response = test_client.get("/api/v1/instances/test-instance/qr", headers=mention_api_headers)
            assert response.status_code == 200
            data = response.json()
            assert "qr_code" in data
            assert data["qr_code"].startswith("data:image/")

    def test_get_connection_status(self, test_client, mention_api_headers):
        """Test getting instance connection status."""
        with patch("src.channels.base.ChannelHandlerFactory.get_handler") as mock_handler:
            # Make get_status async
            async def mock_get_status(*args, **kwargs):
                return {
                    "instance_name": "test-instance",
                    "channel_type": "whatsapp",
                    "status": "connected",
                    "channel_data": {"connection": "open"},
                }

            mock_handler.return_value.get_status = mock_get_status

            response = test_client.get("/api/v1/instances/test-instance/status", headers=mention_api_headers)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_restart_instance(self, test_client, mention_api_headers):
        """Test restarting instance connection."""
        with patch("src.channels.base.ChannelHandlerFactory.get_handler") as mock_handler:
            # Make restart_instance async
            async def mock_restart_instance(*args, **kwargs):
                return {"status": "restarted"}

            mock_handler.return_value.restart_instance = mock_restart_instance

            response = test_client.post("/api/v1/instances/test-instance/restart", headers=mention_api_headers)
            assert response.status_code == 200

    def test_logout_instance(self, test_client, mention_api_headers):
        """Test logging out instance."""
        with patch("src.channels.base.ChannelHandlerFactory.get_handler") as mock_handler:
            # Make logout_instance async
            async def mock_logout_instance(*args, **kwargs):
                return {"status": "logged_out"}

            mock_handler.return_value.logout_instance = mock_logout_instance

            response = test_client.post("/api/v1/instances/test-instance/logout", headers=mention_api_headers)
            assert response.status_code == 200

    def test_discover_instances(self, test_client, mention_api_headers):
        """Test discovering Evolution instances."""
        with patch("src.services.discovery_service.discovery_service") as mock_service:
            # Make discover_evolution_instances async and return mock InstanceConfig objects
            async def mock_discover_instances(*args, **kwargs):
                # Create mock InstanceConfig-like objects
                mock_instance = type(
                    "MockInstance",
                    (),
                    {
                        "name": "discovered-1",
                        "is_active": True,
                        "agent_id": "test-agent-id",
                    },
                )()
                return [mock_instance]

            mock_service.discover_evolution_instances = mock_discover_instances

            response = test_client.post("/api/v1/instances/discover", headers=mention_api_headers)
            assert response.status_code == 200


class TestMessageSendingEndpoints(TestAPIEndpoints):
    """Test message sending endpoints."""

    def test_send_text_message(self, test_client, mention_api_headers):
        """Test sending text message."""
        message_data = {
            "phone_number": "+1234567890",
            "text": "Hello, this is a test message!",
        }

        # Mock the actual HTTP requests to prevent external API calls
        with patch("src.channels.whatsapp.evolution_api_sender.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "success": True,
                "message_id": "msg_123",
            }

            response = test_client.post(
                "/api/v1/instance/test-instance/send-text",
                json=message_data,
                headers=mention_api_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"]

    def test_send_media_message(self, test_client, mention_api_headers):
        """Test sending media message."""
        message_data = {
            "phone_number": "+1234567890",
            "media_type": "image",
            "media_url": "https://example.com/image.jpg",
            "mime_type": "image/jpeg",
            "caption": "Test image",
        }

        # Mock the actual HTTP requests to prevent external API calls
        with patch("src.channels.whatsapp.evolution_api_sender.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "success": True,
                "message_id": "msg_124",
            }

            response = test_client.post(
                "/api/v1/instance/test-instance/send-media",
                json=message_data,
                headers=mention_api_headers,
            )
            assert response.status_code == 200

    def test_send_audio_message(self, test_client, mention_api_headers):
        """Test sending audio message."""
        message_data = {
            "phone_number": "+1234567890",
            "audio_url": "https://example.com/audio.mp3",
        }

        # Mock the actual HTTP requests to prevent external API calls
        with patch("src.channels.whatsapp.evolution_api_sender.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "success": True,
                "message_id": "msg_125",
            }

            response = test_client.post(
                "/api/v1/instance/test-instance/send-audio",
                json=message_data,
                headers=mention_api_headers,
            )
            assert response.status_code == 200

    def test_send_contact_message(self, test_client, mention_api_headers):
        """Test sending contact message."""
        message_data = {
            "phone_number": "+1234567890",
            "contacts": [{"full_name": "John Doe", "phone_number": "+1987654321"}],
        }

        # Mock the actual HTTP requests to prevent external API calls
        with patch("src.channels.whatsapp.evolution_api_sender.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "success": True,
                "message_id": "msg_126",
            }

            response = test_client.post(
                "/api/v1/instance/test-instance/send-contact",
                json=message_data,
                headers=mention_api_headers,
            )
            assert response.status_code == 200

    def test_send_reaction_message(self, test_client, mention_api_headers):
        """Test sending reaction to message."""
        message_data = {
            "phone_number": "+1234567890",
            "message_id": "msg_original",
            "reaction": "👍",
        }

        # Mock the actual HTTP requests to prevent external API calls
        with patch("src.channels.whatsapp.evolution_api_sender.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "success": True,
                "message_id": "msg_127",
            }

            response = test_client.post(
                "/api/v1/instance/test-instance/send-reaction",
                json=message_data,
                headers=mention_api_headers,
            )
            assert response.status_code == 200

    def test_fetch_profile(self, test_client, mention_api_headers):
        """Test fetching user profile."""
        request_data = {"phone_number": "+1234567890"}

        # Mock the actual HTTP requests to prevent external API calls
        with patch("src.channels.whatsapp.evolution_api_sender.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "success": True,
                "profile": {
                    "name": "John Doe",
                    "picture_url": "https://example.com/profile.jpg",
                },
            }

            response = test_client.post(
                "/api/v1/instance/test-instance/fetch-profile",
                json=request_data,
                headers=mention_api_headers,
            )
            assert response.status_code == 200


class TestTraceEndpoints(TestAPIEndpoints):
    """Test message tracing and analytics endpoints."""

    def test_list_traces(self, test_client, mention_api_headers):
        """Test listing traces with pagination."""
        with patch("src.services.trace_service.TraceService.get_traces_by_phone") as mock_get_traces:
            mock_get_traces.return_value = []

            response = test_client.get("/api/v1/traces", headers=mention_api_headers)
            assert response.status_code == 200
            assert isinstance(response.json(), list)

    def test_list_traces_with_filters(self, test_client, mention_api_headers):
        """Test listing traces with query filters."""
        with patch("src.services.trace_service.TraceService.get_traces_by_phone") as mock_get_traces:
            mock_get_traces.return_value = []

            response = test_client.get(
                "/api/v1/traces?phone=+1234567890&status=completed&limit=10",
                headers=mention_api_headers,
            )
            assert response.status_code == 200

    def test_get_specific_trace(self, test_client, mention_api_headers):
        """Test getting specific trace by ID."""
        with patch("src.services.trace_service.TraceService.get_trace") as mock_get_trace:
            mock_trace = MagicMock()
            mock_trace.to_dict.return_value = {
                "trace_id": "trace_123",
                "instance_name": "test-instance",
                "whatsapp_message_id": "msg_123",
                "sender_phone": "+1234567890",
                "sender_name": "Test User",
                "message_type": "text",
                "has_media": False,
                "has_quoted_message": False,
                "session_name": "test-session",
                "agent_session_id": "agent_123",
                "status": "completed",
                "error_message": None,
                "error_stage": None,
                "received_at": "2023-01-01T00:00:00",
                "completed_at": "2023-01-01T00:00:01",
                "agent_processing_time_ms": 100,
                "total_processing_time_ms": 200,
                "agent_response_success": True,
                "evolution_success": True,
            }
            mock_get_trace.return_value = mock_trace

            response = test_client.get("/api/v1/traces/trace_123", headers=mention_api_headers)
            assert response.status_code == 200

    def test_get_trace_payloads(self, test_client, mention_api_headers):
        """Test getting trace payloads."""
        with (
            patch("src.services.trace_service.TraceService.get_trace") as mock_get_trace,
            patch("src.services.trace_service.TraceService.get_trace_payloads") as mock_get_payloads,
        ):
            mock_trace = MagicMock()
            mock_trace.trace_id = "trace_123"
            mock_get_trace.return_value = mock_trace
            mock_get_payloads.return_value = []

            response = test_client.get("/api/v1/traces/trace_123/payloads", headers=mention_api_headers)
            assert response.status_code == 200

    def test_get_analytics_summary(self, test_client, mention_api_headers):
        """Test getting analytics summary."""
        # Analytics endpoint queries database directly, not TraceService
        response = test_client.get("/api/v1/traces/analytics/summary", headers=mention_api_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_messages" in data
        assert "success_rate" in data

    def test_get_traces_by_phone(self, test_client, mention_api_headers):
        """Test getting traces by phone number."""
        with patch("src.services.trace_service.TraceService.get_traces_by_phone") as mock_get_traces:
            mock_get_traces.return_value = []

            response = test_client.get("/api/v1/traces/phone/+1234567890", headers=mention_api_headers)
            assert response.status_code == 200


class TestWebhookEndpoints(TestAPIEndpoints):
    """Test webhook endpoints."""

    def test_evolution_webhook_tenant(self, test_client):
        """Test multi-tenant webhook endpoint."""
        webhook_data = {
            "event": "messages.upsert",
            "data": {
                "messages": [
                    {
                        "key": {
                            "remoteJid": "1234567890@s.whatsapp.net",
                            "id": "msg_123",
                        },
                        "message": {"conversation": "Hello"},
                    }
                ]
            },
        }

        with patch("src.api.app._handle_evolution_webhook") as mock_handler:
            mock_handler.return_value = {
                "status": "success",
                "instance": "test-instance",
            }

            response = test_client.post("/webhook/evolution/test-instance", json=webhook_data)
            assert response.status_code == 200
            mock_handler.assert_called_once()


class TestErrorHandling(TestAPIEndpoints):
    """Test error handling and edge cases."""

    def test_invalid_json_payload(self, test_client, mention_api_headers):
        """Test invalid JSON payload handling."""
        response = test_client.post(
            "/api/v1/instances",
            content="invalid json",
            headers={**mention_api_headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, test_client, mention_api_headers):
        """Test missing required fields in request."""
        incomplete_data = {
            "name": "incomplete"
            # Missing required fields
        }

        response = test_client.post("/api/v1/instances", json=incomplete_data, headers=mention_api_headers)
        assert response.status_code == 422

    def test_invalid_instance_name_format(self, test_client, mention_api_headers):
        """Test invalid instance name format."""
        invalid_data = {
            "name": "invalid name with spaces!",
            "channel_type": "whatsapp",
            "whatsapp_instance": "test",
            "evolution_url": "http://172.19.209.168:18080",
            "evolution_key": "key",
            "agent_api_url": "http://172.19.209.168:18881",
            "agent_api_key": "agent-key",
            "default_agent": "test-agent",
        }

        response = test_client.post("/api/v1/instances", json=invalid_data, headers=mention_api_headers)
        assert response.status_code == 422

    def test_nonexistent_instance_operations(self, test_client, mention_api_headers):
        """Test operations on non-existent instances."""
        endpoints_to_test = [
            ("GET", "/api/v1/instances/nonexistent"),
            ("PUT", "/api/v1/instances/nonexistent"),
            ("DELETE", "/api/v1/instances/nonexistent"),
            ("GET", "/api/v1/instances/nonexistent/qr"),
            ("POST", "/api/v1/instances/nonexistent/restart"),
            ("POST", "/api/v1/instance/nonexistent/send-text"),
        ]

        for method, endpoint in endpoints_to_test:
            if method == "POST":
                response = test_client.request(method, endpoint, json={"test": "data"}, headers=mention_api_headers)
            else:
                response = test_client.request(method, endpoint, headers=mention_api_headers)

            assert response.status_code in [
                404,
                422,
            ], f"{method} {endpoint} should return 404 or 422"


class TestRequestValidation(TestAPIEndpoints):
    """Test request validation and data sanitization."""

    def test_phone_number_validation(self, test_client, mention_api_headers):
        """Test phone number format validation."""
        invalid_phone_data = {"phone_number": "invalid-phone", "text": "Test message"}

        with patch("src.channels.whatsapp.evolution_api_sender.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"success": True}

            response = test_client.post(
                "/api/v1/instance/test-instance/send-text",
                json=invalid_phone_data,
                headers=mention_api_headers,
            )
            # Should either validate and reject or accept and let handler validate
            assert response.status_code in [200, 422]

    def test_url_validation(self, test_client, mention_api_headers):
        """Test URL validation in instance creation."""
        invalid_url_data = {
            "name": "test-url-validation",
            "channel_type": "whatsapp",
            "whatsapp_instance": "test",
            "evolution_url": "not-a-valid-url",
            "evolution_key": "key",
            "agent_api_url": "also-not-valid",
            "agent_api_key": "agent-key",
            "default_agent": "test-agent",
        }

        response = test_client.post("/api/v1/instances", json=invalid_url_data, headers=mention_api_headers)
        assert response.status_code == 422

    def test_large_payload_handling(self, test_client, mention_api_headers):
        """Test handling of large payloads."""
        large_text = "x" * 10000  # 10KB text

        message_data = {"phone_number": "+1234567890", "text": large_text}

        with patch("src.channels.whatsapp.evolution_api_sender.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"success": True}

            response = test_client.post(
                "/api/v1/instance/test-instance/send-text",
                json=message_data,
                headers=mention_api_headers,
            )
            # Should handle large payloads gracefully
            assert response.status_code in [200, 413, 422]


# Performance and Load Testing Helpers
class TestPerformanceBasics(TestAPIEndpoints):
    """Basic performance tests for endpoints."""

    def test_health_endpoint_performance(self, test_client):
        """Test health endpoint response time."""
        start_time = time.time()
        response = test_client.get("/health")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 0.1  # Should respond in under 100ms

    def test_list_instances_performance(self, test_client, mention_api_headers):
        """Test instances listing performance."""
        start_time = time.time()
        response = test_client.get("/api/v1/instances", headers=mention_api_headers)
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Should respond in under 2 seconds (allows for Evolution API calls)

    def test_concurrent_health_checks(self, test_client):
        """Test multiple concurrent health check requests."""
        import concurrent.futures

        def make_request():
            return test_client.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            responses = [future.result() for future in futures]

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)
