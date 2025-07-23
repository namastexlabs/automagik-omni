"""
Tests for session-based trace filtering functionality.
Tests edge cases like cross-instance sessions and data isolation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.api.app import app
from src.db.trace_models import MessageTrace
from src.db.models import InstanceConfig
from src.utils.datetime_utils import utcnow


class TestSessionFilteringAPI:
    """Test session-based filtering in the traces API."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_db_session(self):
        with patch('src.api.deps.get_database') as mock_get_db:
            mock_session = Mock(spec=Session)
            mock_get_db.return_value = mock_session
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
                status="completed",
                received_at=base_time - timedelta(minutes=30),
                completed_at=base_time - timedelta(minutes=29)
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
                status="completed",
                received_at=base_time - timedelta(minutes=25),
                completed_at=base_time - timedelta(minutes=24)
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
                status="completed",
                received_at=base_time - timedelta(minutes=20),
                completed_at=base_time - timedelta(minutes=19)
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
                status="completed",
                received_at=base_time - timedelta(minutes=15),
                completed_at=base_time - timedelta(minutes=14)
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
                status="failed",
                received_at=base_time - timedelta(minutes=10),
                error_message="Agent API timeout"
            )
        ]

    def test_filter_by_agent_session_id(self, client, mock_db_session, sample_traces):
        """Test filtering traces by agent session ID."""
        # Mock query chain
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        
        # Filter for specific agent session
        target_session = "agent_session_abc123"
        expected_traces = [t for t in sample_traces if t.agent_session_id == target_session]
        
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = expected_traces
        
        # Make API request
        response = client.get(
            f"/api/v1/traces?agent_session_id={target_session}",
            headers={"Authorization": "Bearer namastex888"}
        )
        
        assert response.status_code == 200
        
        # Verify the filter was called correctly
        mock_query.filter.assert_called()
        filter_calls = mock_query.filter.call_args_list
        
        # Should have called filter with agent_session_id condition
        found_agent_session_filter = False
        for call in filter_calls:
            call_str = str(call)
            if "agent_session_id" in call_str and target_session in call_str:
                found_agent_session_filter = True
                break
        
        assert found_agent_session_filter, "agent_session_id filter not applied"

    def test_filter_by_session_name(self, client, mock_db_session, sample_traces):
        """Test filtering traces by session name."""
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        
        target_session = "user_john_session"
        expected_traces = [t for t in sample_traces if t.session_name == target_session]
        
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = expected_traces
        
        response = client.get(
            f"/api/v1/traces?session_name={target_session}",
            headers={"Authorization": "Bearer namastex888"}
        )
        
        assert response.status_code == 200
        
        # Verify session_name filter was applied
        mock_query.filter.assert_called()
        filter_calls = mock_query.filter.call_args_list
        
        found_session_name_filter = False
        for call in filter_calls:
            call_str = str(call)
            if "session_name" in call_str and target_session in call_str:
                found_session_name_filter = True
                break
                
        assert found_session_name_filter, "session_name filter not applied"

    def test_filter_by_has_media(self, client, mock_db_session, sample_traces):
        """Test filtering traces by media presence."""
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        
        # Filter for traces with media
        expected_traces = [t for t in sample_traces if t.has_media == True]
        
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = expected_traces
        
        response = client.get(
            "/api/v1/traces?has_media=true",
            headers={"Authorization": "Bearer namastex888"}
        )
        
        assert response.status_code == 200
        mock_query.filter.assert_called()

    def test_combined_session_filters(self, client, mock_db_session, sample_traces):
        """Test combining session_name and instance_name filters."""
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        
        target_session = "user_john_session"
        target_instance = "instance_a"
        
        expected_traces = [
            t for t in sample_traces 
            if t.session_name == target_session and t.instance_name == target_instance
        ]
        
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = expected_traces
        
        response = client.get(
            f"/api/v1/traces?session_name={target_session}&instance_name={target_instance}",
            headers={"Authorization": "Bearer namastex888"}
        )
        
        assert response.status_code == 200
        
        # Should have multiple filter calls
        assert mock_query.filter.call_count >= 2

    def test_session_isolation_between_instances(self, client, mock_db_session, sample_traces):
        """Test that session filtering properly isolates data between instances."""
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        
        # Filter by session_name that exists in multiple instances
        # Should return different results for different instances
        base_session_name = "user_john_session"
        
        # Mock separate calls for different instances
        instance_a_traces = [
            t for t in sample_traces 
            if t.session_name.startswith(base_session_name) and t.instance_name == "instance_a"
        ]
        
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = instance_a_traces
        
        response = client.get(
            f"/api/v1/traces?session_name={base_session_name}&instance_name=instance_a",
            headers={"Authorization": "Bearer namastex888"}
        )
        
        assert response.status_code == 200
        
        # Verify both session_name and instance_name filters were applied
        filter_calls = mock_query.filter.call_args_list
        assert len(filter_calls) >= 2  # At least session_name and instance_name filters

    def test_null_agent_session_id_handling(self, client, mock_db_session, sample_traces):
        """Test handling of traces with null agent_session_id."""
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        
        # Filter should handle null values gracefully
        non_existent_session = "nonexistent_session_id"
        
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = []  # No matches
        
        response = client.get(
            f"/api/v1/traces?agent_session_id={non_existent_session}",
            headers={"Authorization": "Bearer namastex888"}
        )
        
        assert response.status_code == 200
        # Should return empty list, not error
        assert response.json() == []

    def test_phone_alias_parameter(self, client, mock_db_session, sample_traces):
        """Test that both 'phone' and 'sender_phone' parameters work."""
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        
        target_phone = "+5511999999999"
        expected_traces = [t for t in sample_traces if t.sender_phone == target_phone]
        
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = expected_traces
        
        # Test with 'phone' parameter
        response1 = client.get(
            f"/api/v1/traces?phone={target_phone}",
            headers={"Authorization": "Bearer namastex888"}
        )
        
        # Test with 'sender_phone' parameter  
        response2 = client.get(
            f"/api/v1/traces?sender_phone={target_phone}",
            headers={"Authorization": "Bearer namastex888"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200

    def test_session_filtering_with_pagination(self, client, mock_db_session, sample_traces):
        """Test session filtering works correctly with pagination."""
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        
        target_session = "user_john_session"
        
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = sample_traces[:2]  # First 2 results
        
        response = client.get(
            f"/api/v1/traces?session_name={target_session}&limit=2&offset=0",
            headers={"Authorization": "Bearer namastex888"}
        )
        
        assert response.status_code == 200
        
        # Verify pagination was applied after filtering
        mock_query.offset.assert_called_with(0)
        mock_query.limit.assert_called_with(2)

    def test_invalid_boolean_parameter(self, client, mock_db_session):
        """Test handling of invalid boolean values for has_media parameter."""
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        
        # Test with invalid boolean value
        response = client.get(
            "/api/v1/traces?has_media=invalid_bool",
            headers={"Authorization": "Bearer namastex888"}
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422


class TestSessionFilteringEdgeCases:
    """Test edge cases for session filtering functionality."""

    def test_empty_session_parameters(self):
        """Test behavior with empty session parameters."""
        client = TestClient(app)
        
        with patch('src.api.deps.get_database') as mock_get_db:
            mock_session = Mock(spec=Session)
            mock_get_db.return_value = mock_session
            
            mock_query = Mock()
            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = []
            
            # Empty session_name parameter should be ignored
            response = client.get(
                "/api/v1/traces?session_name=",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200

    def test_unicode_session_names(self):
        """Test handling of unicode characters in session names."""
        client = TestClient(app)
        
        with patch('src.api.deps.get_database') as mock_get_db:
            mock_session = Mock(spec=Session)
            mock_get_db.return_value = mock_session
            
            mock_query = Mock()
            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = []
            
            # Unicode session name
            unicode_session = "用户_会话_测试"
            response = client.get(
                f"/api/v1/traces?session_name={unicode_session}",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200

    def test_very_long_session_ids(self):
        """Test handling of very long session identifiers."""
        client = TestClient(app)
        
        with patch('src.api.deps.get_database') as mock_get_db:
            mock_session = Mock(spec=Session)
            mock_get_db.return_value = mock_session
            
            mock_query = Mock()
            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = []
            
            # Very long session ID (1000 characters)
            long_session_id = "a" * 1000
            response = client.get(
                f"/api/v1/traces?agent_session_id={long_session_id}",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200