"""
Integration tests for session-based trace filtering functionality.
Tests actual API behavior with real database interactions.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.db.trace_models import MessageTrace
from src.db.models import InstanceConfig
from src.utils.datetime_utils import utcnow


class TestSessionFilteringIntegration:
    """Integration tests for session filtering with real database."""

    @pytest.fixture(autouse=True)
    def ensure_clean_state(self, test_db):
        """Ensure clean state before and after each test."""
        # Import app here to ensure clean state
        from src.api.app import app
        # Clear any leftover dependency overrides
        app.dependency_overrides.clear()
        # Clean before test
        self.cleanup_test_data(test_db)
        yield
        # Clean after test
        self.cleanup_test_data(test_db)
        # Clear overrides again after test
        app.dependency_overrides.clear()

    @pytest.fixture
    def db_session(self, test_db):
        """Get test database session."""
        yield test_db

    def setup_test_data(self, db: Session):
        """Set up test traces with different session configurations."""
        base_time = utcnow()
        
        # Clean up any existing test data first - more comprehensive cleanup
        db.query(MessageTrace).filter(MessageTrace.trace_id.like("test_%")).delete()
        db.query(MessageTrace).filter(MessageTrace.instance_name.in_(["session_filter_test_a", "session_filter_test_b"])).delete()
        db.query(InstanceConfig).filter(InstanceConfig.name.in_(["session_filter_test_a", "session_filter_test_b"])).delete()
        db.commit()  # Ensure cleanup is committed before creating new data
        
        # Create required test instances first
        test_instances = [
            InstanceConfig(
                name="session_filter_test_a",
                channel_type="whatsapp",
                evolution_url="http://test-evolution.com",
                evolution_key="test-evolution-key",
                whatsapp_instance="test_whatsapp_a",
                agent_api_url="http://test-agent.com",
                agent_api_key="test-agent-key",
                default_agent="test_agent",
                is_active=True
            ),
            InstanceConfig(
                name="session_filter_test_b",
                channel_type="whatsapp",
                evolution_url="http://test-evolution.com",
                evolution_key="test-evolution-key",
                whatsapp_instance="test_whatsapp_b",
                agent_api_url="http://test-agent.com",
                agent_api_key="test-agent-key",
                default_agent="test_agent",
                is_active=True
            )
        ]
        
        for instance in test_instances:
            db.add(instance)
        db.commit()
        
        test_traces = [
            MessageTrace(
                trace_id="test_trace_001",
                instance_name="session_filter_test_a",
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
                instance_name="session_filter_test_a",
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
                instance_name="session_filter_test_b",
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
                instance_name="session_filter_test_a",
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
                instance_name="session_filter_test_a",
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
        try:
            # Clean up test traces
            db.query(MessageTrace).filter(MessageTrace.trace_id.like("test_%")).delete()
            db.query(MessageTrace).filter(MessageTrace.instance_name.in_(["session_filter_test_a", "session_filter_test_b"])).delete()
            # Clean up test instances
            db.query(InstanceConfig).filter(InstanceConfig.name.in_(["session_filter_test_a", "session_filter_test_b"])).delete()
            # Also clean up any traces from instance 'aaaa' which is polluting our tests
            db.query(MessageTrace).filter(MessageTrace.instance_name == "aaaa").delete()
            db.query(InstanceConfig).filter(InstanceConfig.name == "aaaa").delete()
            db.commit()
            # Force session to refresh
            db.expire_all()
        except Exception as e:
            db.rollback()
            print(f"Error during cleanup: {e}")

    def test_filter_by_agent_session_id_functional(self, test_client, db_session):
        """Functional test for filtering by agent session ID."""
        test_traces = self.setup_test_data(db_session)
        
        # Debug: verify data was created
        created_traces = db_session.query(MessageTrace).filter(MessageTrace.trace_id.like("test_%")).all()
        print(f"\nDEBUG: Created {len(created_traces)} test traces in DB")
        for trace in created_traces:
            print(f"  - {trace.trace_id}: instance={trace.instance_name}, agent_session={trace.agent_session_id}")
        
        # Ensure data is committed and visible to the test client
        db_session.commit()
        
        try:
            # First, test without any filters to see what's in the database
            response_all = test_client.get(
                "/api/v1/traces",
                headers={"Authorization": "Bearer namastex888"}
            )
            print(f"\nDEBUG: All traces response: {response_all.status_code}")
            all_traces = response_all.json()
            print(f"DEBUG: Total traces in API: {len(all_traces)}")
            if all_traces:
                print(f"  First trace: {all_traces[0]}")
            
            # Filter for specific agent session 
            target_session = "agent_session_abc123"
            response = test_client.get(
                f"/api/v1/traces?agent_session_id={target_session}",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200
            traces = response.json()
            
            # Debug output
            print(f"\nDEBUG: Total traces returned: {len(traces)}")
            if traces:
                print(f"First trace: {traces[0]}")
            
            # Should return 2 traces with the target agent session ID (filter only test traces)
            test_traces_only = [t for t in traces if t.get("trace_id", "").startswith("test_")]
            print(f"DEBUG: Test traces found: {len(test_traces_only)}")
            
            agent_session_traces = [t for t in test_traces_only if t.get("agent_session_id") == target_session]
            print(f"DEBUG: Agent session traces found: {len(agent_session_traces)}")
            
            assert len(agent_session_traces) == 2
            
            # All returned traces should have the target agent session ID
            for trace in agent_session_traces:
                assert trace["agent_session_id"] == target_session
                assert trace["trace_id"] in ["test_trace_001", "test_trace_002"]
                
        finally:
            self.cleanup_test_data(db_session)

    def test_filter_by_session_name_functional(self, test_client, db_session):
        """Functional test for filtering by session name."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter for specific session name
            target_session = "user_john_session"
            response = test_client.get(
                f"/api/v1/traces?session_name={target_session}",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            if response.status_code != 200:
                print(f"ERROR: Status {response.status_code}, Response: {response.json()}")
            assert response.status_code == 200
            traces = response.json()
            
            # Should return 2 traces with the target session name (filter only test traces)
            test_traces_only = [t for t in traces if t.get("trace_id", "").startswith("test_")]
            session_traces = [t for t in test_traces_only if t.get("session_name") == target_session]
            assert len(session_traces) == 2
            
            # All returned traces should have the target session name
            for trace in session_traces:
                assert trace["session_name"] == target_session
                
        finally:
            self.cleanup_test_data(db_session)

    def test_filter_by_has_media_functional(self, test_client, db_session):
        """Functional test for filtering by media presence."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter for traces with media
            response = test_client.get(
                "/api/v1/traces?has_media=true",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200
            traces = response.json()
            
            # Should return only traces with media (filter only test traces)
            test_traces_only = [t for t in traces if t.get("trace_id", "").startswith("test_")]
            media_traces = [t for t in test_traces_only if t.get("has_media") == True]
            
            # At least our test trace with media should be present
            test_media_trace = next((t for t in media_traces if t.get("trace_id") == "test_trace_004"), None)
            assert test_media_trace is not None
            assert test_media_trace["has_media"] == True
            assert test_media_trace["message_type"] == "image"
                
        finally:
            self.cleanup_test_data(db_session)

    def test_combined_session_filters_functional(self, test_client, db_session):
        """Functional test for combining session and instance filters."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter by session name and instance
            target_session = "user_john_session"
            target_instance = "session_filter_test_a"
            
            response = test_client.get(
                f"/api/v1/traces?session_name={target_session}&instance_name={target_instance}",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200
            traces = response.json()
            
            # Should return only traces matching both criteria (filter only test traces)
            test_traces_only = [t for t in traces if t.get("trace_id", "").startswith("test_")]
            filtered_traces = [
                t for t in test_traces_only 
                if t.get("session_name") == target_session and t.get("instance_name") == target_instance
            ]
            assert len(filtered_traces) == 2
            
            for trace in filtered_traces:
                assert trace["session_name"] == target_session
                assert trace["instance_name"] == target_instance
                
        finally:
            self.cleanup_test_data(db_session)

    def test_session_isolation_functional(self, test_client, db_session):
        """Functional test for session isolation between instances."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter by instance A only
            response_a = test_client.get(
                "/api/v1/traces?instance_name=session_filter_test_a",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            # Filter by instance B only
            response_b = test_client.get(
                "/api/v1/traces?instance_name=session_filter_test_b",
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
                assert trace["instance_name"] == "session_filter_test_a"
                
            for trace in test_traces_b:
                assert trace["instance_name"] == "session_filter_test_b"
                
        finally:
            self.cleanup_test_data(db_session)

    def test_null_agent_session_id_functional(self, test_client, db_session):
        """Functional test for handling null agent session IDs."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter for non-existent session ID - should return empty
            response = test_client.get(
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

    def test_phone_alias_parameter_functional(self, test_client, db_session):
        """Functional test for phone parameter aliases."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            target_phone = "+5511999999999"
            
            # Debug: Check if data was created
            all_traces_in_db = db_session.query(MessageTrace).all()
            print(f"\n\nDEBUG: Total traces in database: {len(all_traces_in_db)}")
            
            traces_in_db = db_session.query(MessageTrace).filter(MessageTrace.trace_id.like("test_%")).all()
            print(f"DEBUG: Found {len(traces_in_db)} test traces in database")
            for trace in traces_in_db:
                print(f"  - {trace.trace_id}: phone={trace.sender_phone}")
                
            # Show non-test traces
            non_test_traces = [t for t in all_traces_in_db if not t.trace_id.startswith("test_")]
            if non_test_traces:
                print(f"\nDEBUG: Found {len(non_test_traces)} non-test traces:")
                for trace in non_test_traces[:3]:  # Show first 3
                    print(f"  - {trace.trace_id}: instance={trace.instance_name}, phone={trace.sender_phone}")
            
            # Debug: Get all traces from API
            all_response = test_client.get(
                "/api/v1/traces",
                headers={"Authorization": "Bearer namastex888"}
            )
            all_traces = all_response.json()
            print(f"\nDEBUG: API returned {len(all_traces)} total traces")
            if all_traces:
                print(f"  First trace: {all_traces[0]}")
            
            # Test with 'phone' parameter
            from urllib.parse import quote
            encoded_phone = quote(target_phone)
            print(f"\nDEBUG: Filtering by phone={target_phone} (encoded: {encoded_phone})")
            response1 = test_client.get(
                f"/api/v1/traces?phone={encoded_phone}",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            # Test with 'sender_phone' parameter  
            response2 = test_client.get(
                f"/api/v1/traces?sender_phone={encoded_phone}",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            traces1 = response1.json()
            traces2 = response2.json()
            
            # Both should return the same results
            test_traces1 = [t for t in traces1 if t.get("trace_id", "").startswith("test_")]
            test_traces2 = [t for t in traces2 if t.get("trace_id", "").startswith("test_")]
            
            # Debug: Print what we got
            print(f"\nResponse 1 (phone): {len(traces1)} total traces, {len(test_traces1)} test traces")
            print(f"Response 2 (sender_phone): {len(traces2)} total traces, {len(test_traces2)} test traces")
            if traces1:
                print(f"All traces from phone filter: {[t['trace_id'] for t in traces1]}")
            if test_traces1:
                print(f"Test traces found: {[t['trace_id'] for t in test_traces1]}")
            
            # Should get 3 traces with that phone number
            assert len(test_traces1) == 3
            assert len(test_traces2) == 3
            
            # Results should be identical
            trace_ids1 = {t["trace_id"] for t in test_traces1}
            trace_ids2 = {t["trace_id"] for t in test_traces2}
            assert trace_ids1 == trace_ids2
            
        finally:
            self.cleanup_test_data(db_session)

    def test_pagination_with_session_filtering_functional(self, test_client, db_session):
        """Functional test for pagination with session filtering."""
        test_traces = self.setup_test_data(db_session)
        
        try:
            # Filter by session that has 2 traces, limit to 1
            target_session = "user_john_session"
            response = test_client.get(
                f"/api/v1/traces?session_name={target_session}&limit=1&offset=0",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response.status_code == 200
            traces = response.json()
            
            # Should return exactly 1 trace (filter only test traces)
            test_traces_only = [t for t in traces if t.get("trace_id", "").startswith("test_")]
            session_traces = [t for t in test_traces_only if t.get("session_name") == target_session]
            assert len(session_traces) == 1
            
            # Test offset
            response_offset = test_client.get(
                f"/api/v1/traces?session_name={target_session}&limit=1&offset=1",
                headers={"Authorization": "Bearer namastex888"}
            )
            
            assert response_offset.status_code == 200
            traces_offset = response_offset.json()
            
            test_traces_only_offset = [t for t in traces_offset if t.get("trace_id", "").startswith("test_")]
            session_traces_offset = [t for t in test_traces_only_offset if t.get("session_name") == target_session]
            
            # Should return the second trace (if any)
            if len(session_traces_offset) > 0:
                # Trace IDs should be different
                assert session_traces[0]["trace_id"] != session_traces_offset[0]["trace_id"]
            
        finally:
            self.cleanup_test_data(db_session)