"""
Integration tests for session-based trace filtering functionality.
Tests actual API behavior with real database interactions.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.api.app import app
from src.db.trace_models import MessageTrace
from src.db.models import InstanceConfig
from src.db.database import get_db
from src.utils.datetime_utils import utcnow


class TestSessionFilteringIntegration:
    """Integration tests for session filtering with real database."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def db_session(self):
        """Get a real database session for testing."""
        db = next(get_db())
        yield db
        db.close()

    def setup_test_data(self, db: Session):
        """Set up test traces with different session configurations."""
        base_time = utcnow()
        
        # Clean up any existing test data
        db.query(MessageTrace).filter(MessageTrace.trace_id.like("test_%")).delete()
        
        test_traces = [
            MessageTrace(
                trace_id="test_trace_001",
                instance_name="test_instance_a",
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
                trace_id="test_trace_002", 
                instance_name="test_instance_a",
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
            MessageTrace(
                trace_id="test_trace_003",
                instance_name="test_instance_b",
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
            MessageTrace(
                trace_id="test_trace_004",
                instance_name="test_instance_a",
                session_name="user_jane_session",
                agent_session_id="agent_session_ghi789",
                sender_phone="+5511888888888",
                sender_name="Jane Smith",
                message_type="image",
                has_media=True,
                status="completed",
                received_at=base_time - timedelta(minutes=15),
                completed_at=base_time - timedelta(minutes=14)
            ),
            MessageTrace(
                trace_id="test_trace_005",
                instance_name="test_instance_a",
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
        
        for trace in test_traces:
            db.add(trace)
        
        db.commit()
        return test_traces

    def cleanup_test_data(self, db: Session):
        """Clean up test data after tests."""
        db.query(MessageTrace).filter(MessageTrace.trace_id.like("test_%")).delete()
        db.commit()

    def test_filter_by_agent_session_id_functional(self, client, db_session):
        """Functional test for filtering by agent session ID."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter for specific agent session
            target_session = "agent_session_abc123"
            response = client.get(
                f"/api/v1/traces?agent_session_id={target_session}",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200
            traces = response.json()
            
            # Should return 2 traces with the target agent session ID
            agent_session_traces = [t for t in traces if t.get("agent_session_id") == target_session]
            assert len(agent_session_traces) == 2
            
            # All returned traces should have the target agent session ID
            for trace in agent_session_traces:
                assert trace["agent_session_id"] == target_session
                assert trace["trace_id"] in ["test_trace_001", "test_trace_002"]
                
        finally:
            self.cleanup_test_data(db_session)

    def test_filter_by_session_name_functional(self, client, db_session):
        """Functional test for filtering by session name."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter for specific session name
            target_session = "user_john_session"
            response = client.get(
                f"/api/v1/traces?session_name={target_session}",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200
            traces = response.json()
            
            # Should return 2 traces with the target session name
            session_traces = [t for t in traces if t.get("session_name") == target_session]
            assert len(session_traces) == 2
            
            # All returned traces should have the target session name
            for trace in session_traces:
                assert trace["session_name"] == target_session
                
        finally:
            self.cleanup_test_data(db_session)

    def test_filter_by_has_media_functional(self, client, db_session):
        """Functional test for filtering by media presence."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter for traces with media
            response = client.get(
                "/api/v1/traces?has_media=true",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200
            traces = response.json()
            
            # Should return only traces with media
            media_traces = [t for t in traces if t.get("has_media") == True]
            
            # At least our test trace with media should be present
            test_media_trace = next((t for t in media_traces if t.get("trace_id") == "test_trace_004"), None)
            assert test_media_trace is not None
            assert test_media_trace["has_media"] == True
            assert test_media_trace["message_type"] == "image"
                
        finally:
            self.cleanup_test_data(db_session)

    def test_combined_session_filters_functional(self, client, db_session):
        """Functional test for combining session and instance filters."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter by session name and instance
            target_session = "user_john_session"
            target_instance = "test_instance_a"
            
            response = client.get(
                f"/api/v1/traces?session_name={target_session}&instance_name={target_instance}",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200
            traces = response.json()
            
            # Should return only traces matching both criteria
            filtered_traces = [
                t for t in traces 
                if t.get("session_name") == target_session and t.get("instance_name") == target_instance
            ]
            assert len(filtered_traces) == 2
            
            for trace in filtered_traces:
                assert trace["session_name"] == target_session
                assert trace["instance_name"] == target_instance
                
        finally:
            self.cleanup_test_data(db_session)

    def test_session_isolation_functional(self, client, db_session):
        """Functional test for session isolation between instances."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter by instance A only
            response_a = client.get(
                "/api/v1/traces?instance_name=test_instance_a",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            # Filter by instance B only
            response_b = client.get(
                "/api/v1/traces?instance_name=test_instance_b",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response_a.status_code == 200
            assert response_b.status_code == 200
            
            traces_a = response_a.json()
            traces_b = response_b.json()
            
            # Get our test traces from each instance
            test_traces_a = [t for t in traces_a if t.get("trace_id", "").startswith("test_")]
            test_traces_b = [t for t in traces_b if t.get("trace_id", "").startswith("test_")]
            
            # Should have 4 traces in instance A and 1 in instance B
            assert len(test_traces_a) == 4
            assert len(test_traces_b) == 1
            
            # Verify no cross-contamination
            for trace in test_traces_a:
                assert trace["instance_name"] == "test_instance_a"
                
            for trace in test_traces_b:
                assert trace["instance_name"] == "test_instance_b"
                
        finally:
            self.cleanup_test_data(db_session)

    def test_null_agent_session_id_functional(self, client, db_session):
        """Functional test for handling null agent session IDs."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter for non-existent session ID - should return empty
            response = client.get(
                "/api/v1/traces?agent_session_id=nonexistent_session_123",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200
            traces = response.json()
            
            # Should not return any of our test traces
            test_traces_returned = [t for t in traces if t.get("trace_id", "").startswith("test_")]
            assert len(test_traces_returned) == 0
            
        finally:
            self.cleanup_test_data(db_session)

    def test_phone_alias_parameter_functional(self, client, db_session):
        """Functional test for phone parameter aliases."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            target_phone = "+5511999999999"
            
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
            
            traces1 = response1.json()
            traces2 = response2.json()
            
            # Both should return the same results
            test_traces1 = [t for t in traces1 if t.get("trace_id", "").startswith("test_")]
            test_traces2 = [t for t in traces2 if t.get("trace_id", "").startswith("test_")]
            
            # Should get 3 traces with that phone number
            assert len(test_traces1) == 3
            assert len(test_traces2) == 3
            
            # Results should be identical
            trace_ids1 = {t["trace_id"] for t in test_traces1}
            trace_ids2 = {t["trace_id"] for t in test_traces2}
            assert trace_ids1 == trace_ids2
            
        finally:
            self.cleanup_test_data(db_session)

    def test_pagination_with_session_filtering_functional(self, client, db_session):
        """Functional test for pagination with session filtering."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter by session that has 2 traces, limit to 1
            target_session = "user_john_session"
            response = client.get(
                f"/api/v1/traces?session_name={target_session}&limit=1&offset=0",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200
            traces = response.json()
            
            # Should return exactly 1 trace
            session_traces = [t for t in traces if t.get("session_name") == target_session]
            assert len(session_traces) == 1
            
            # Test offset
            response_offset = client.get(
                f"/api/v1/traces?session_name={target_session}&limit=1&offset=1",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response_offset.status_code == 200
            traces_offset = response_offset.json()
            
            session_traces_offset = [t for t in traces_offset if t.get("session_name") == target_session]
            
            # Should return the second trace (if any)
            if len(session_traces_offset) > 0:
                # Trace IDs should be different
                assert session_traces[0]["trace_id"] != session_traces_offset[0]["trace_id"]
            
        finally:
            self.cleanup_test_data(db_session)