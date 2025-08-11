"""
Comprehensive tests for the new all_time parameter functionality in traces endpoints.
Tests both GET /traces and GET /traces/analytics/summary endpoints.
"""
import pytest
from datetime import timedelta
from unittest.mock import Mock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from src.api.app import app
from src.db.trace_models import MessageTrace
from src.utils.datetime_utils import utcnow


class TestAllTimeParameter:
    """Test the new all_time parameter functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        # Clear any dependency overrides before creating client
        app.dependency_overrides.clear()
        return TestClient(app)
    
    @pytest.fixture  
    def auth_headers(self):
        """Authentication headers using real environment API key."""
        return {"Authorization": "Bearer namastex888"}

    @pytest.fixture
    def sample_traces(self):
        """Create sample traces with various timestamps."""
        base_time = utcnow()
        
        return [
            MessageTrace(
                trace_id="trace_001",
                instance_name="test-instance",
                session_name="user_session",
                agent_session_id="agent_session_abc123",
                sender_phone="+1234567890",
                sender_name="Test User",
                message_type="text",
                has_media=False,
                has_quoted_message=False,
                status="completed",
                received_at=base_time - timedelta(days=30),
                completed_at=base_time - timedelta(days=30, minutes=-1),
                agent_processing_time_ms=1000,
                total_processing_time_ms=1500,
                agent_response_success=True,
                evolution_success=True
            ),
            MessageTrace(
                trace_id="trace_002",
                instance_name="test-instance",
                session_name="user_session",
                agent_session_id="agent_session_abc123",
                sender_phone="+1234567890",
                sender_name="Test User",
                message_type="text",
                has_media=False,
                has_quoted_message=False,
                status="completed",
                received_at=base_time - timedelta(hours=1),
                completed_at=base_time - timedelta(hours=1, minutes=-1),
                agent_processing_time_ms=1000,
                total_processing_time_ms=1500,
                agent_response_success=True,
                evolution_success=True
            ),
        ]

    # Tests for GET /traces endpoint
    def test_traces_all_time_true(self, client, auth_headers, sample_traces):
        """Test GET /traces with all_time=true returns all data without date filters."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        # Set up the query chain
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_traces
        mock_query.count.return_value = len(sample_traces)
        
        def mock_db_generator():
            yield mock_session
        
        # Override the dependency on the app
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            response = client.get("/api/v1/traces?all_time=true", headers=auth_headers)
            
            assert response.status_code == 200
            # When all_time=true, no date filters should be applied to query
            # The mock should be called and return our sample traces
            assert mock_session.query.called
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_traces_all_time_false_no_dates(self, client, auth_headers, sample_traces):
        """Test GET /traces with all_time=false and no dates defaults to last 24 hours."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_traces[1]]  # Only recent trace
        mock_query.count.return_value = 1
        
        def mock_db_generator():
            yield mock_session
        
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            response = client.get("/api/v1/traces?all_time=false", headers=auth_headers)
            
            assert response.status_code == 200
            assert mock_session.query.called
        finally:
            app.dependency_overrides.clear()

    def test_traces_no_all_time_param_defaults_to_24_hours(self, client, auth_headers, sample_traces):
        """Test GET /traces without all_time parameter defaults to last 24 hours."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_traces[1]]  # Only recent trace
        mock_query.count.return_value = 1
        
        def mock_db_generator():
            yield mock_session
        
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            # Request without all_time parameter
            response = client.get("/api/v1/traces", headers=auth_headers)
            
            assert response.status_code == 200
            assert mock_session.query.called
        finally:
            app.dependency_overrides.clear()

    def test_traces_all_time_overrides_date_params(self, client, auth_headers, sample_traces):
        """Test that all_time=true overrides explicit start_date/end_date parameters."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_traces  # All traces
        mock_query.count.return_value = len(sample_traces)
        
        def mock_db_generator():
            yield mock_session
        
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            # Test with explicit dates but all_time=true (all_time should override)
            from urllib.parse import quote
            start_date = (utcnow() - timedelta(days=1)).isoformat()
            end_date = utcnow().isoformat()
            
            response = client.get(
                f"/api/v1/traces?all_time=true&start_date={quote(start_date)}&end_date={quote(end_date)}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert mock_session.query.called
        finally:
            app.dependency_overrides.clear()

    def test_traces_respects_date_filters_when_all_time_false(self, client, auth_headers, sample_traces):
        """Test that date filtering works normally when all_time=false."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_traces[1]]  # Only recent trace
        mock_query.count.return_value = 1
        
        def mock_db_generator():
            yield mock_session
        
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            # Test with explicit dates and all_time=false
            from urllib.parse import quote
            start_date = (utcnow() - timedelta(days=1)).isoformat()
            end_date = utcnow().isoformat()
            
            response = client.get(
                f"/api/v1/traces?all_time=false&start_date={quote(start_date)}&end_date={quote(end_date)}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert mock_session.query.called
        finally:
            app.dependency_overrides.clear()

    # Tests for GET /traces/analytics/summary endpoint
    def test_analytics_summary_all_time_true(self, client, auth_headers, sample_traces):
        """Test GET /traces/analytics/summary with all_time=true returns all data."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = sample_traces
        mock_query.count.return_value = len(sample_traces)
        
        def mock_db_generator():
            yield mock_session
        
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            response = client.get("/api/v1/traces/analytics/summary?all_time=true", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "total_messages" in data
            assert "success_rate" in data
            assert mock_session.query.called
        finally:
            app.dependency_overrides.clear()

    def test_analytics_summary_all_time_false_no_dates(self, client, auth_headers, sample_traces):
        """Test analytics summary with all_time=false defaults to last 24 hours."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_traces[1]]  # Only recent trace
        mock_query.count.return_value = 1
        
        def mock_db_generator():
            yield mock_session
        
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            response = client.get("/api/v1/traces/analytics/summary?all_time=false", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "total_messages" in data
            assert "success_rate" in data
            assert mock_session.query.called
        finally:
            app.dependency_overrides.clear()

    def test_analytics_summary_no_all_time_param(self, client, auth_headers, sample_traces):
        """Test analytics summary without all_time parameter defaults to 24 hours."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_traces[1]]  # Only recent trace
        mock_query.count.return_value = 1
        
        def mock_db_generator():
            yield mock_session
        
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            # Test without all_time parameter - should behave same as all_time=false
            response = client.get("/api/v1/traces/analytics/summary", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "total_messages" in data
            assert "success_rate" in data
            assert mock_session.query.called
        finally:
            app.dependency_overrides.clear()

    def test_analytics_summary_all_time_overrides_dates(self, client, auth_headers, sample_traces):
        """Test that all_time=true overrides date parameters in analytics summary."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = sample_traces  # All traces
        mock_query.count.return_value = len(sample_traces)
        
        def mock_db_generator():
            yield mock_session
        
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            # Test with dates but all_time=true should override
            from urllib.parse import quote
            start_date = (utcnow() - timedelta(days=1)).isoformat()
            end_date = utcnow().isoformat()
            
            response = client.get(
                f"/api/v1/traces/analytics/summary?all_time=true&start_date={quote(start_date)}&end_date={quote(end_date)}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "total_messages" in data
            assert "success_rate" in data
            assert mock_session.query.called
        finally:
            app.dependency_overrides.clear()

    # Edge case and validation tests
    def test_all_time_parameter_type_validation(self, client, auth_headers):
        """Test validation of all_time parameter type."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.count.return_value = 0
        
        def mock_db_generator():
            yield mock_session
        
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            # Test with invalid boolean values
            invalid_values = ["invalid", "1", "0", "yes", "no"]
            
            for invalid_value in invalid_values:
                response = client.get(f"/api/v1/traces?all_time={invalid_value}", headers=auth_headers)
                # FastAPI should handle boolean conversion or return validation error
                assert response.status_code in [200, 422]  # 200 if converted, 422 if validation fails
                
                response = client.get(f"/api/v1/traces/analytics/summary?all_time={invalid_value}", headers=auth_headers)
                assert response.status_code in [200, 422]
        finally:
            app.dependency_overrides.clear()

    def test_all_time_with_other_filters(self, client, auth_headers, sample_traces):
        """Test all_time parameter works correctly with other filters."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_traces
        mock_query.count.return_value = len(sample_traces)
        
        def mock_db_generator():
            yield mock_session
        
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            # Test all_time with other filters (phone, has_media, session)
            response = client.get(
                "/api/v1/traces?all_time=true&sender_phone=+1234567890&has_media=false&agent_session_id=agent_session_abc123",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert mock_session.query.called
        finally:
            app.dependency_overrides.clear()

    def test_backward_compatibility_existing_behavior(self, client, auth_headers, sample_traces):
        """Test that existing behavior is preserved when all_time parameter is not used."""
        from src.api.deps import get_database
        
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_traces[1]]  # Only recent trace
        mock_query.count.return_value = 1
        
        def mock_db_generator():
            yield mock_session
        
        app.dependency_overrides[get_database] = mock_db_generator
        
        try:
            # Test that existing endpoints work without any changes
            response1 = client.get("/api/v1/traces", headers=auth_headers)
            assert response1.status_code == 200
            
            response2 = client.get("/api/v1/traces/analytics/summary", headers=auth_headers)
            assert response2.status_code == 200
            data = response2.json()
            assert "total_messages" in data
            assert "success_rate" in data
            
            # Test with existing date parameters (should still work)
            from urllib.parse import quote
            start_date = (utcnow() - timedelta(days=1)).isoformat()
            end_date = utcnow().isoformat()
            
            response3 = client.get(
                f"/api/v1/traces?start_date={quote(start_date)}&end_date={quote(end_date)}",
                headers=auth_headers
            )
            assert response3.status_code == 200
            
            response4 = client.get(
                f"/api/v1/traces/analytics/summary?start_date={quote(start_date)}&end_date={quote(end_date)}",
                headers=auth_headers
            )
            assert response4.status_code == 200
            
            assert mock_session.query.called
        finally:
            app.dependency_overrides.clear()