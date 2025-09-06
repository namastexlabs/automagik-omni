"""
Tests for session-based trace filtering functionality.
Tests edge cases like cross-instance sessions and data isolation.
"""

import pytest
from datetime import timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.api.app import app
from src.db.trace_models import MessageTrace
from src.utils.datetime_utils import utcnow


class TestSessionFilteringAPI:
    """Test session-based filtering in the traces API."""

    @pytest.fixture
    def client(self):
        # Clear any dependency overrides before creating client
        app.dependency_overrides.clear()
        return TestClient(app)

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        mock_session = Mock(spec=Session)
        mock_query = Mock()

        # Set up the query chain
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.count.return_value = 0

        yield mock_session

    @pytest.fixture
    def sample_traces(self):
        """Create sample traces with different session configurations."""
        base_time = utcnow()

        return [
            # Instance A traces
            MessageTrace(
                trace_id="trace_001",
                instance_name="instance_a",
                session_name="user_john_session",
                agent_session_id="agent_session_abc123",
                sender_phone="+5511999999999",
                sender_name="John Doe",
                message_type="text",
                has_media=False,
                has_quoted_message=False,
                status="completed",
                received_at=base_time - timedelta(minutes=30),
                completed_at=base_time - timedelta(minutes=29),
            ),
            MessageTrace(
                trace_id="trace_002",
                instance_name="instance_a",
                session_name="user_john_session",
                agent_session_id="agent_session_abc123",
                sender_phone="+5511999999999",
                sender_name="John Doe",
                message_type="text",
                has_media=False,
                has_quoted_message=False,
                status="completed",
                received_at=base_time - timedelta(minutes=25),
                completed_at=base_time - timedelta(minutes=24),
            ),
            # Instance B traces (same user, different instance)
            MessageTrace(
                trace_id="trace_003",
                instance_name="instance_b",
                session_name="user_john_session_b",
                agent_session_id="agent_session_def456",
                sender_phone="+5511999999999",
                sender_name="John Doe",
                message_type="text",
                has_media=False,
                has_quoted_message=False,
                status="completed",
                received_at=base_time - timedelta(minutes=20),
                completed_at=base_time - timedelta(minutes=19),
            ),
            # Different user same instance A
            MessageTrace(
                trace_id="trace_004",
                instance_name="instance_a",
                session_name="user_jane_session",
                agent_session_id="agent_session_ghi789",
                sender_phone="+5511888888888",
                sender_name="Jane Smith",
                message_type="text",
                has_media=True,
                has_quoted_message=False,
                status="completed",
                received_at=base_time - timedelta(minutes=15),
                completed_at=base_time - timedelta(minutes=14),
            ),
            # Cross-session trace (no agent session id)
            MessageTrace(
                trace_id="trace_005",
                instance_name="instance_a",
                session_name="anonymous_session",
                agent_session_id=None,
                sender_phone="+5511777777777",
                sender_name="Anonymous",
                message_type="text",
                has_media=False,
                has_quoted_message=False,
                status="failed",
                received_at=base_time - timedelta(minutes=10),
                error_message="Agent API timeout",
            ),
        ]

    def test_filter_by_agent_session_id(self, client, sample_traces, mock_db_session):
        """Test filtering traces by agent session ID."""
        from src.api.deps import get_database
        from unittest.mock import Mock

        # Mock the database dependency
        client.app.dependency_overrides[get_database] = lambda: mock_db_session

        # Configure mock to return only traces with the specific agent session ID
        target_agent_session = "agent_session_abc123"
        expected_traces = [
            trace
            for trace in sample_traces
            if trace.agent_session_id == target_agent_session
        ]

        # Create mock trace objects with to_dict method
        mock_traces = []
        for trace in expected_traces:
            mock_trace = Mock()
            mock_trace.to_dict.return_value = {
                "trace_id": trace.trace_id,
                "instance_name": trace.instance_name,
                "whatsapp_message_id": trace.whatsapp_message_id,
                "sender_phone": trace.sender_phone,
                "sender_name": trace.sender_name,
                "message_type": trace.message_type,
                "has_media": trace.has_media,
                "has_quoted_message": trace.has_quoted_message,
                "session_name": trace.session_name,
                "agent_session_id": trace.agent_session_id,
                "status": trace.status,
                "error_message": trace.error_message,
                "error_stage": trace.error_stage,
                "received_at": (
                    trace.received_at.isoformat() if trace.received_at else None
                ),
                "completed_at": (
                    trace.completed_at.isoformat() if trace.completed_at else None
                ),
                "agent_processing_time_ms": trace.agent_processing_time_ms,
                "total_processing_time_ms": trace.total_processing_time_ms,
                "agent_response_success": trace.agent_response_success,
                "evolution_success": trace.evolution_success,
            }
            mock_traces.append(mock_trace)

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            mock_traces
        )
        mock_db_session.query.return_value.filter.return_value.count.return_value = len(
            mock_traces
        )

        # Make the API request
        response = client.get(
            f"/api/v1/traces?agent_session_id={target_agent_session}",
            headers={"x-api-key": "namastex888"},
        )

        # Verify the response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # trace_001 and trace_002 both have agent_session_abc123

        # Verify all returned traces have the correct agent session ID
        for trace in data:
            assert trace["agent_session_id"] == target_agent_session

    def test_filter_by_session_name(self, client, sample_traces, mock_db_session):
        """Test filtering traces by session name."""
        from src.api.deps import get_database
        from unittest.mock import Mock

        # Mock the database dependency
        client.app.dependency_overrides[get_database] = lambda: mock_db_session

        # Configure mock to return only traces with the specific session name
        target_session_name = "user_john_session"
        expected_traces = [
            trace
            for trace in sample_traces
            if trace.session_name == target_session_name
        ]

        # Create mock trace objects with to_dict method
        mock_traces = []
        for trace in expected_traces:
            mock_trace = Mock()
            mock_trace.to_dict.return_value = {
                "trace_id": trace.trace_id,
                "instance_name": trace.instance_name,
                "whatsapp_message_id": trace.whatsapp_message_id,
                "sender_phone": trace.sender_phone,
                "sender_name": trace.sender_name,
                "message_type": trace.message_type,
                "has_media": trace.has_media,
                "has_quoted_message": trace.has_quoted_message,
                "session_name": trace.session_name,
                "agent_session_id": trace.agent_session_id,
                "status": trace.status,
                "error_message": trace.error_message,
                "error_stage": trace.error_stage,
                "received_at": (
                    trace.received_at.isoformat() if trace.received_at else None
                ),
                "completed_at": (
                    trace.completed_at.isoformat() if trace.completed_at else None
                ),
                "agent_processing_time_ms": trace.agent_processing_time_ms,
                "total_processing_time_ms": trace.total_processing_time_ms,
                "agent_response_success": trace.agent_response_success,
                "evolution_success": trace.evolution_success,
            }
            mock_traces.append(mock_trace)

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            mock_traces
        )
        mock_db_session.query.return_value.filter.return_value.count.return_value = len(
            mock_traces
        )

        # Make the API request
        response = client.get(
            f"/api/v1/traces?session_name={target_session_name}",
            headers={"x-api-key": "namastex888"},
        )

        # Verify the response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # trace_001 and trace_002 both have user_john_session

        # Verify all returned traces have the correct session name
        for trace in data:
            assert trace["session_name"] == target_session_name

    def test_filter_by_has_media(self, client, sample_traces, mock_db_session):
        """Test filtering traces by media presence."""
        from src.api.deps import get_database
        from unittest.mock import Mock

        # Mock the database dependency
        client.app.dependency_overrides[get_database] = lambda: mock_db_session

        # Configure mock to return only traces with media
        expected_traces = [trace for trace in sample_traces if trace.has_media]

        # Create mock trace objects with to_dict method
        mock_traces = []
        for trace in expected_traces:
            mock_trace = Mock()
            mock_trace.to_dict.return_value = {
                "trace_id": trace.trace_id,
                "instance_name": trace.instance_name,
                "whatsapp_message_id": trace.whatsapp_message_id,
                "sender_phone": trace.sender_phone,
                "sender_name": trace.sender_name,
                "message_type": trace.message_type,
                "has_media": trace.has_media,
                "has_quoted_message": trace.has_quoted_message,
                "session_name": trace.session_name,
                "agent_session_id": trace.agent_session_id,
                "status": trace.status,
                "error_message": trace.error_message,
                "error_stage": trace.error_stage,
                "received_at": (
                    trace.received_at.isoformat() if trace.received_at else None
                ),
                "completed_at": (
                    trace.completed_at.isoformat() if trace.completed_at else None
                ),
                "agent_processing_time_ms": trace.agent_processing_time_ms,
                "total_processing_time_ms": trace.total_processing_time_ms,
                "agent_response_success": trace.agent_response_success,
                "evolution_success": trace.evolution_success,
            }
            mock_traces.append(mock_trace)

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            mock_traces
        )
        mock_db_session.query.return_value.filter.return_value.count.return_value = len(
            mock_traces
        )

        # Make the API request
        response = client.get(
            "/api/v1/traces?has_media=true",
            headers={"x-api-key": "namastex888"},
        )

        # Verify the response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Only trace_004 has media

        # Verify all returned traces have media
        for trace in data:
            assert trace["has_media"]

    def test_combined_session_filters(self, client, sample_traces, mock_db_session):
        """Test combining session_name and instance_name filters."""
        from src.api.deps import get_database
        from unittest.mock import Mock

        # Mock the database dependency
        client.app.dependency_overrides[get_database] = lambda: mock_db_session

        # Configure mock to return only traces matching both filters
        target_session_name = "user_john_session"
        target_instance_name = "instance_a"
        expected_traces = [
            trace
            for trace in sample_traces
            if trace.session_name == target_session_name
            and trace.instance_name == target_instance_name
        ]

        # Create mock trace objects with to_dict method
        mock_traces = []
        for trace in expected_traces:
            mock_trace = Mock()
            mock_trace.to_dict.return_value = {
                "trace_id": trace.trace_id,
                "instance_name": trace.instance_name,
                "whatsapp_message_id": trace.whatsapp_message_id,
                "sender_phone": trace.sender_phone,
                "sender_name": trace.sender_name,
                "message_type": trace.message_type,
                "has_media": trace.has_media,
                "has_quoted_message": trace.has_quoted_message,
                "session_name": trace.session_name,
                "agent_session_id": trace.agent_session_id,
                "status": trace.status,
                "error_message": trace.error_message,
                "error_stage": trace.error_stage,
                "received_at": (
                    trace.received_at.isoformat() if trace.received_at else None
                ),
                "completed_at": (
                    trace.completed_at.isoformat() if trace.completed_at else None
                ),
                "agent_processing_time_ms": trace.agent_processing_time_ms,
                "total_processing_time_ms": trace.total_processing_time_ms,
                "agent_response_success": trace.agent_response_success,
                "evolution_success": trace.evolution_success,
            }
            mock_traces.append(mock_trace)

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            mock_traces
        )
        mock_db_session.query.return_value.filter.return_value.count.return_value = len(
            mock_traces
        )

        # Make the API request with combined filters
        response = client.get(
            f"/api/v1/traces?session_name={target_session_name}&instance_name={target_instance_name}",
            headers={"x-api-key": "namastex888"},
        )

        # Verify the response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # trace_001 and trace_002 match both criteria

        # Verify all returned traces match both criteria
        for trace in data:
            assert trace["session_name"] == target_session_name
            assert trace["instance_name"] == target_instance_name

    def test_session_isolation_between_instances(
        self, client, sample_traces, mock_db_session
    ):
        """Test that sessions are isolated between instances."""
        from src.api.deps import get_database
        from unittest.mock import Mock

        # Mock the database dependency
        client.app.dependency_overrides[get_database] = lambda: mock_db_session

        # Configure mock to return only traces from instance_a
        target_instance = "instance_a"
        expected_traces = [
            trace for trace in sample_traces if trace.instance_name == target_instance
        ]

        # Create mock trace objects with to_dict method
        mock_traces = []
        for trace in expected_traces:
            mock_trace = Mock()
            mock_trace.to_dict.return_value = {
                "trace_id": trace.trace_id,
                "instance_name": trace.instance_name,
                "whatsapp_message_id": trace.whatsapp_message_id,
                "sender_phone": trace.sender_phone,
                "sender_name": trace.sender_name,
                "message_type": trace.message_type,
                "has_media": trace.has_media,
                "has_quoted_message": trace.has_quoted_message,
                "session_name": trace.session_name,
                "agent_session_id": trace.agent_session_id,
                "status": trace.status,
                "error_message": trace.error_message,
                "error_stage": trace.error_stage,
                "received_at": (
                    trace.received_at.isoformat() if trace.received_at else None
                ),
                "completed_at": (
                    trace.completed_at.isoformat() if trace.completed_at else None
                ),
                "agent_processing_time_ms": trace.agent_processing_time_ms,
                "total_processing_time_ms": trace.total_processing_time_ms,
                "agent_response_success": trace.agent_response_success,
                "evolution_success": trace.evolution_success,
            }
            mock_traces.append(mock_trace)

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            mock_traces
        )
        mock_db_session.query.return_value.filter.return_value.count.return_value = len(
            mock_traces
        )

        # Make the API request filtering by instance
        response = client.get(
            f"/api/v1/traces?instance_name={target_instance}",
            headers={"x-api-key": "namastex888"},
        )

        # Verify the response
        assert response.status_code == 200
        data = response.json()
        assert (
            len(data) == 4
        )  # trace_001, trace_002, trace_004, trace_005 are from instance_a

        # Verify all returned traces are from the target instance only
        for trace in data:
            assert trace["instance_name"] == target_instance

        # Verify no traces from instance_b are returned
        instance_b_traces = [
            trace for trace in data if trace["instance_name"] == "instance_b"
        ]
        assert len(instance_b_traces) == 0

    def test_null_agent_session_id_handling(self, client, sample_traces):
        """Test handling of traces with null agent_session_id."""
        from src.api.deps import get_database

        mock_session = Mock(spec=Session)
        mock_query = Mock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []  # No matches

        def mock_db_generator():
            yield mock_session

        # Override the dependency on the app
        app.dependency_overrides[get_database] = mock_db_generator

        try:
            # Filter should handle null values gracefully
            non_existent_session = "nonexistent_session_id"

            response = client.get(
                f"/api/v1/traces?agent_session_id={non_existent_session}",
                headers={"x-api-key": "namastex888"},
            )

            assert response.status_code == 200
            # Should return empty list, not error
            assert response.json() == []
        finally:
            # Clean up
            app.dependency_overrides.clear()

    def test_phone_alias_parameter(self, client, sample_traces):
        """Test that both 'phone' and 'sender_phone' parameters work."""
        from src.api.deps import get_database

        target_phone = "+5511999999999"

        # Create mock traces with proper to_dict method
        mock_traces = []
        for i, trace in enumerate(
            [t for t in sample_traces if t.sender_phone == target_phone]
        ):
            mock_trace = Mock()
            mock_trace.to_dict.return_value = {
                "trace_id": f"trace_{i:03d}",
                "instance_name": "test_instance",
                "whatsapp_message_id": None,
                "sender_phone": target_phone,
                "sender_name": "Test User",
                "message_type": "text",
                "has_media": False,
                "has_quoted_message": False,
                "session_name": "test_session",
                "agent_session_id": None,
                "status": "completed",
                "error_message": None,
                "error_stage": None,
                "received_at": "2023-01-01T10:00:00",
                "completed_at": "2023-01-01T10:01:00",
                "agent_processing_time_ms": 1000,
                "total_processing_time_ms": 2000,
                "agent_response_success": True,
                "evolution_success": True,
            }
            mock_traces.append(mock_trace)

        mock_session = Mock(spec=Session)
        mock_query = Mock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_traces

        def mock_db_generator():
            yield mock_session

        # Override the dependency on the app
        app.dependency_overrides[get_database] = mock_db_generator

        try:
            # Test with 'phone' parameter
            response1 = client.get(
                f"/api/v1/traces?phone={target_phone}",
                headers={"x-api-key": "namastex888"},
            )

            # Test with 'sender_phone' parameter
            response2 = client.get(
                f"/api/v1/traces?sender_phone={target_phone}",
                headers={"x-api-key": "namastex888"},
            )

            assert response1.status_code == 200
            assert response2.status_code == 200
        finally:
            # Clean up
            app.dependency_overrides.clear()

    def test_session_filtering_with_pagination(
        self, client, sample_traces, mock_db_session
    ):
        """Test session filtering works with pagination."""
        from src.api.deps import get_database
        from unittest.mock import Mock

        # Mock the database dependency
        client.app.dependency_overrides[get_database] = lambda: mock_db_session

        # Configure mock to return traces with pagination
        target_session_name = "user_john_session"
        all_matching_traces = [
            trace
            for trace in sample_traces
            if trace.session_name == target_session_name
        ]

        # Simulate pagination: limit=1, offset=0 (first page)
        paginated_traces = all_matching_traces[:1]  # Only first trace

        # Create mock trace objects with to_dict method
        mock_traces = []
        for trace in paginated_traces:
            mock_trace = Mock()
            mock_trace.to_dict.return_value = {
                "trace_id": trace.trace_id,
                "instance_name": trace.instance_name,
                "whatsapp_message_id": trace.whatsapp_message_id,
                "sender_phone": trace.sender_phone,
                "sender_name": trace.sender_name,
                "message_type": trace.message_type,
                "has_media": trace.has_media,
                "has_quoted_message": trace.has_quoted_message,
                "session_name": trace.session_name,
                "agent_session_id": trace.agent_session_id,
                "status": trace.status,
                "error_message": trace.error_message,
                "error_stage": trace.error_stage,
                "received_at": (
                    trace.received_at.isoformat() if trace.received_at else None
                ),
                "completed_at": (
                    trace.completed_at.isoformat() if trace.completed_at else None
                ),
                "agent_processing_time_ms": trace.agent_processing_time_ms,
                "total_processing_time_ms": trace.total_processing_time_ms,
                "agent_response_success": trace.agent_response_success,
                "evolution_success": trace.evolution_success,
            }
            mock_traces.append(mock_trace)

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            mock_traces
        )
        mock_db_session.query.return_value.filter.return_value.count.return_value = len(
            all_matching_traces
        )  # Total count

        # Make the API request with pagination
        response = client.get(
            f"/api/v1/traces?session_name={target_session_name}&limit=1&offset=0",
            headers={"x-api-key": "namastex888"},
        )

        # Verify the response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Only one trace due to limit=1

        # Verify the returned trace matches the session name
        assert data[0]["session_name"] == target_session_name

        # Test second page: offset=1
        second_page_traces = all_matching_traces[1:2]  # Second trace

        # Create mock trace objects for second page
        mock_traces_page2 = []
        for trace in second_page_traces:
            mock_trace = Mock()
            mock_trace.to_dict.return_value = {
                "trace_id": trace.trace_id,
                "instance_name": trace.instance_name,
                "whatsapp_message_id": trace.whatsapp_message_id,
                "sender_phone": trace.sender_phone,
                "sender_name": trace.sender_name,
                "message_type": trace.message_type,
                "has_media": trace.has_media,
                "has_quoted_message": trace.has_quoted_message,
                "session_name": trace.session_name,
                "agent_session_id": trace.agent_session_id,
                "status": trace.status,
                "error_message": trace.error_message,
                "error_stage": trace.error_stage,
                "received_at": (
                    trace.received_at.isoformat() if trace.received_at else None
                ),
                "completed_at": (
                    trace.completed_at.isoformat() if trace.completed_at else None
                ),
                "agent_processing_time_ms": trace.agent_processing_time_ms,
                "total_processing_time_ms": trace.total_processing_time_ms,
                "agent_response_success": trace.agent_response_success,
                "evolution_success": trace.evolution_success,
            }
            mock_traces_page2.append(mock_trace)

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            mock_traces_page2
        )

        response_page2 = client.get(
            f"/api/v1/traces?session_name={target_session_name}&limit=1&offset=1",
            headers={"x-api-key": "namastex888"},
        )

        assert response_page2.status_code == 200
        data_page2 = response_page2.json()
        assert len(data_page2) == 1
        assert data_page2[0]["session_name"] == target_session_name

        # Verify different traces were returned on each page
        assert data[0]["trace_id"] != data_page2[0]["trace_id"]

    def test_invalid_boolean_parameter(self, client):
        """Test handling of invalid boolean values for has_media parameter."""
        with patch("src.api.deps.get_database") as mock_get_db:
            mock_session = Mock(spec=Session)
            mock_query = Mock()

            mock_session.query.return_value = mock_query

            def mock_db_generator():
                yield mock_session

            mock_get_db.return_value = mock_db_generator()

            # Test with invalid boolean value
            response = client.get(
                "/api/v1/traces?has_media=invalid_bool",
                headers={"x-api-key": "namastex888"},
            )

            # Should return 422 for validation error
            assert response.status_code == 422


class TestSessionFilteringEdgeCases:
    """Test edge cases for session filtering functionality."""

    def test_empty_session_parameters(self):
        """Test behavior with empty session parameters."""
        from src.api.deps import get_database

        client = TestClient(app)

        mock_session = Mock(spec=Session)
        mock_query = Mock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        def mock_db_generator():
            yield mock_session

        # Override the dependency on the app
        app.dependency_overrides[get_database] = mock_db_generator

        try:
            # Empty session_name parameter should be ignored
            response = client.get(
                "/api/v1/traces?session_name=",
                headers={"x-api-key": "namastex888"},
            )

            assert response.status_code == 200
        finally:
            # Clean up
            app.dependency_overrides.clear()

    def test_unicode_session_names(self):
        """Test handling of unicode characters in session names."""
        from src.api.deps import get_database

        client = TestClient(app)

        mock_session = Mock(spec=Session)
        mock_query = Mock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        def mock_db_generator():
            yield mock_session

        # Override the dependency on the app
        app.dependency_overrides[get_database] = mock_db_generator

        try:
            # Unicode session name
            unicode_session = "用户_会话_测试"
            response = client.get(
                f"/api/v1/traces?session_name={unicode_session}",
                headers={"x-api-key": "namastex888"},
            )

            assert response.status_code == 200
        finally:
            # Clean up
            app.dependency_overrides.clear()

    def test_very_long_session_ids(self):
        """Test handling of very long session identifiers."""
        from src.api.deps import get_database

        client = TestClient(app)

        mock_session = Mock(spec=Session)
        mock_query = Mock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        def mock_db_generator():
            yield mock_session

        # Override the dependency on the app
        app.dependency_overrides[get_database] = mock_db_generator

        try:
            # Very long session ID (1000 characters)
            long_session_id = "a" * 1000
            response = client.get(
                f"/api/v1/traces?agent_session_id={long_session_id}",
                headers={"x-api-key": "namastex888"},
            )

            assert response.status_code == 200
        finally:
            # Clean up
            app.dependency_overrides.clear()
