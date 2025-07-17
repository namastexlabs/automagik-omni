"""
Real-world integration test scenarios for the Automagik Omni API.
These tests simulate actual user workflows and integration patterns.
"""

import pytest
import json
import time
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.app import app
from src.db.models import InstanceConfig, Base


class TestRealWorldScenarios:
    """Test realistic user scenarios and integration workflows."""

    @pytest.fixture(autouse=True)
    def setup_realistic_environment(self):
        """Set up environment that mimics real deployment."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()
        
        # Create test engine and session
        self.test_engine = create_engine(f"sqlite:///{self.temp_db_path}")
        TestSession = sessionmaker(bind=self.test_engine)
        
        # Mock realistic external services
        self.evolution_api_responses = {}
        self.agent_api_responses = {}
        
        def get_test_db():
            db = TestSession()
            try:
                yield db
            finally:
                db.close()
        
        # Create tables
        Base.metadata.create_all(bind=self.test_engine)
        
        # Override FastAPI dependency using built-in dependency_overrides
        from src.api.deps import get_database
        app.dependency_overrides[get_database] = get_test_db
        
        # Mock external services to prevent real API calls
        with patch('src.services.message_router.message_router') as mock_router, \
             patch('src.services.agent_api_client.agent_api_client') as mock_agent_client, \
             patch('src.channels.whatsapp.evolution_api_sender.requests.post') as mock_requests, \
             patch('src.channels.whatsapp.evolution_client.EvolutionClient') as mock_evolution_client:
            
            # Setup message router mock
            mock_router.route_message.return_value = {
                "response": "Test response from mocked agent",
                "success": True,
                "user_data": {"user_id": "test-user-123"}
            }
            
            # Setup agent client mock
            mock_agent_client.process_message.return_value = {
                "response": "Test agent response",
                "success": True
            }
            mock_agent_client.health_check.return_value = True
            
            # Setup requests mock for Evolution API
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_requests.return_value = mock_response
            
            # Setup Evolution Client mock
            mock_evolution_instance = AsyncMock()
            mock_evolution_instance.get_connection_state.return_value = {
                "instance": {
                    "state": "connected",
                    "ownerJid": "1234567890@s.whatsapp.net", 
                    "profileName": "Test User",
                    "profilePictureUrl": "https://example.com/profile.jpg"
                }
            }
            mock_evolution_client.return_value = mock_evolution_instance
            
            yield
        
        # Clean up override
        app.dependency_overrides.clear()
        
        # Cleanup database
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
    
    @pytest.fixture
    def client(self):
        """Test client for API calls."""
        return TestClient(app)
    
    @pytest.fixture
    def api_headers(self):
        """Realistic API headers using real environment API key."""
        return {
            "Authorization": "Bearer namastex888",
            "Content-Type": "application/json",
            "User-Agent": "AutomagikOmni-Test/1.0"
        }

    def test_complete_instance_lifecycle(self, client, api_headers):
        """Test complete instance lifecycle: create, configure, use, delete."""
        
        # Step 1: Check no instances exist initially
        response = client.get("/api/v1/instances", headers=api_headers)
        assert response.status_code == 200
        assert response.json() == []
        
        # Step 2: Create new WhatsApp instance
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            # Make create_instance async using AsyncMock
            mock_evo.return_value.create_instance = AsyncMock(return_value={"status": "created", "qr_code": "test-qr"})
            
            instance_data = {
                "name": "production-whatsapp",
                "channel_type": "whatsapp",
                "whatsapp_instance": "prod-wa-001",
                "evolution_url": "http://172.19.209.168:18080",
                "evolution_key": "prod-evolution-key-12345",
                "agent_api_url": "http://172.19.209.168:18881",
                "agent_api_key": "prod-agent-key-67890",
                "default_agent": "production-agent",
                "webhook_base64": True
            }
            
            response = client.post("/api/v1/instances", json=instance_data, headers=api_headers)
            assert response.status_code == 201
            created_instance = response.json()
            assert created_instance["name"] == "production-whatsapp"
            assert created_instance["is_active"] == True
        
        # Step 3: Get QR code for WhatsApp connection
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            from src.channels.base import QRCodeResponse
            mock_evo.return_value.get_qr_code = AsyncMock(return_value=QRCodeResponse(
                instance_name="production-whatsapp",
                channel_type="whatsapp",
                qr_code="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA...",
                status="qr_code",
                message="QR code generated successfully"
            ))
            
            response = client.get("/api/v1/instances/production-whatsapp/qr", headers=api_headers)
            assert response.status_code == 200
            qr_data = response.json()
            assert "qr_code" in qr_data
            assert qr_data["qr_code"].startswith("data:image/")
        
        # Step 4: Check connection status (simulating user connecting WhatsApp)
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            from src.channels.base import ConnectionStatus
            mock_evo.return_value.get_status = AsyncMock(return_value=ConnectionStatus(
                instance_name="production-whatsapp",
                channel_type="whatsapp",
                status="connected",
                channel_data={"connection": "open", "user": {"name": "Test User", "id": "1234567890@s.whatsapp.net"}}
            ))
            
            response = client.get("/api/v1/instances/production-whatsapp/status", headers=api_headers)
            assert response.status_code == 200
            status = response.json()
            assert status["status"] == "connected"
        
        # Step 5: Send a test message
        with patch('src.channels.whatsapp.evolution_api_sender.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "success": True,
                "message_id": "msg_test_12345",
                "timestamp": int(time.time())
            }
            
            message_data = {
                "phone_number": "+1234567890",
                "text": "Hello! This is a test message from our production instance."
            }
            
            response = client.post(
                "/api/v1/instance/production-whatsapp/send-text",
                json=message_data,
                headers=api_headers
            )
            assert response.status_code == 200
            result = response.json()
            assert result["success"] == True
        
        # Step 6: Update instance configuration (e.g., change agent API)
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            mock_evo.return_value.update_instance = AsyncMock(return_value={"status": "updated"})
            
            update_data = {
                "agent_api_url": "https://agent-v2.prod.company.com",
                "webhook_base64": False
            }
            
            response = client.put(
                "/api/v1/instances/production-whatsapp",
                json=update_data,
                headers=api_headers
            )
            assert response.status_code == 200
            updated = response.json()
            assert updated["agent_api_url"] == "https://agent-v2.prod.company.com"
            assert updated["webhook_base64"] == False
        
        # Step 7: Set as default instance
        response = client.post(
            "/api/v1/instances/production-whatsapp/set-default",
            headers=api_headers
        )
        assert response.status_code == 200
        default_instance = response.json()
        assert default_instance["is_default"] == True
        
        # Step 8: List instances to verify configuration
        response = client.get("/api/v1/instances", headers=api_headers)
        assert response.status_code == 200
        instances = response.json()
        assert len(instances) == 1
        assert instances[0]["name"] == "production-whatsapp"
        assert instances[0]["is_default"] == True
        
        # Step 9: Create a second instance to allow deletion of the default one
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            mock_evo.return_value.create_instance = AsyncMock(return_value={"status": "created"})
            
            second_instance_data = {
                "name": "backup-whatsapp",
                "channel_type": "whatsapp", 
                "whatsapp_instance": "backup-wa-001",
                "evolution_url": "http://172.19.209.168:18080",
                "evolution_key": "backup-key-12345",
                "agent_api_url": "http://172.19.209.168:18881",
                "agent_api_key": "backup-agent-key",
                "default_agent": "backup-agent"
            }
            
            response = client.post("/api/v1/instances", json=second_instance_data, headers=api_headers)
            assert response.status_code == 201
        
        # Step 10: Now delete the original instance (should work since it's not the only one)
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            mock_evo.return_value.delete_instance = AsyncMock(return_value={"status": "deleted"})
            
            response = client.delete("/api/v1/instances/production-whatsapp", headers=api_headers)
            assert response.status_code == 204
        
        # Step 11: Verify production instance is gone but backup remains
        response = client.get("/api/v1/instances", headers=api_headers)
        assert response.status_code == 200
        remaining_instances = response.json()
        assert len(remaining_instances) == 1
        assert remaining_instances[0]["name"] == "backup-whatsapp"
        assert remaining_instances[0]["is_default"] == True  # Should become default after original is deleted

    def test_multi_tenant_webhook_workflow(self, client, api_headers):
        """Test realistic multi-tenant webhook processing workflow."""
        
        # Create two different instances for different tenants
        instances_data = [
            {
                "name": "tenant-a-whatsapp",
                "channel_type": "whatsapp", 
                "whatsapp_instance": "tenant-a-wa",
                "evolution_url": "http://172.19.209.168:18080",
                "evolution_key": "tenant-a-key",
                "agent_api_url": "https://agent-tenant-a.com",
                "agent_api_key": "tenant-a-agent-key",
                "default_agent": "tenant-a-agent"
            },
            {
                "name": "tenant-b-whatsapp",
                "channel_type": "whatsapp",
                "whatsapp_instance": "tenant-b-wa", 
                "evolution_url": "http://172.19.209.168:18080",
                "evolution_key": "tenant-b-key",
                "agent_api_url": "https://agent-tenant-b.com",
                "agent_api_key": "tenant-b-agent-key",
                "default_agent": "tenant-b-agent"
            }
        ]
        
        # Create both instances
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            mock_evo.return_value.create_instance = AsyncMock(return_value={"status": "created"})
            
            for instance_data in instances_data:
                response = client.post("/api/v1/instances", json=instance_data, headers=api_headers)
                assert response.status_code == 201
        
        # Simulate webhook from tenant A
        tenant_a_webhook = {
            "event": "messages.upsert",
            "data": {
                "messages": [{
                    "key": {
                        "remoteJid": "1111111111@s.whatsapp.net",
                        "id": "msg_tenant_a_001"
                    },
                    "message": {
                        "conversation": "Hello from Tenant A customer"
                    },
                    "messageTimestamp": int(time.time())
                }]
            },
            "instance": "tenant-a-wa"
        }
        
        with patch('src.api.app._handle_evolution_webhook') as mock_handler:
            mock_handler.return_value = {
                "status": "success",
                "instance": "tenant-a-whatsapp",
                "trace_id": "trace_a_001"
            }
            
            response = client.post(
                "/webhook/evolution/tenant-a-whatsapp",
                json=tenant_a_webhook
            )
            assert response.status_code == 200
            result = response.json()
            assert result["instance"] == "tenant-a-whatsapp"
        
        # Simulate webhook from tenant B with different message
        tenant_b_webhook = {
            "event": "messages.upsert", 
            "data": {
                "messages": [{
                    "key": {
                        "remoteJid": "2222222222@s.whatsapp.net",
                        "id": "msg_tenant_b_001"
                    },
                    "message": {
                        "conversation": "Hello from Tenant B customer"
                    },
                    "messageTimestamp": int(time.time())
                }]
            },
            "instance": "tenant-b-wa"
        }
        
        with patch('src.api.app._handle_evolution_webhook') as mock_handler:
            mock_handler.return_value = {
                "status": "success",
                "instance": "tenant-b-whatsapp", 
                "trace_id": "trace_b_001"
            }
            
            response = client.post(
                "/webhook/evolution/tenant-b-whatsapp",
                json=tenant_b_webhook
            )
            assert response.status_code == 200
            result = response.json()
            assert result["instance"] == "tenant-b-whatsapp"
        
        # Verify both instances are still active
        response = client.get("/api/v1/instances", headers=api_headers)
        assert response.status_code == 200
        instances = response.json()
        assert len(instances) == 2
        instance_names = [inst["name"] for inst in instances]
        assert "tenant-a-whatsapp" in instance_names
        assert "tenant-b-whatsapp" in instance_names

    def test_error_handling_and_recovery(self, client, api_headers):
        """Test realistic error scenarios and recovery patterns."""
        
        # Test 1: Create instance with invalid Evolution API URL
        invalid_instance = {
            "name": "invalid-instance",
            "channel_type": "whatsapp",
            "whatsapp_instance": "invalid-wa",
            "evolution_url": "https://nonexistent-evolution-api.fake",
            "evolution_key": "fake-key",
            "agent_api_url": "https://agent.example.com",
            "agent_api_key": "agent-key",
            "default_agent": "test-agent"
        }
        
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            mock_evo.return_value.create_instance = AsyncMock(side_effect=Exception("Connection failed to Evolution API"))
            
            response = client.post("/api/v1/instances", json=invalid_instance, headers=api_headers)
            # Should handle gracefully with proper error message
            assert response.status_code in [400, 500]
        
        # Test 2: Try to send message to non-existent instance
        message_data = {
            "phone_number": "+1234567890",
            "text": "This should fail"
        }
        
        response = client.post(
            "/api/v1/instance/nonexistent-instance/send-text",
            json=message_data,
            headers=api_headers
        )
        assert response.status_code == 404
        
        # Test 3: Create valid instance for recovery testing
        valid_instance = {
            "name": "recovery-test",
            "channel_type": "whatsapp",
            "whatsapp_instance": "recovery-wa",
            "evolution_url": "http://172.19.209.168:18080",
            "evolution_key": "recovery-key",
            "agent_api_url": "https://agent.recovery.com", 
            "agent_api_key": "recovery-agent-key",
            "default_agent": "recovery-agent"
        }
        
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            mock_evo.return_value.create_instance = AsyncMock(return_value={"status": "created"})
            
            response = client.post("/api/v1/instances", json=valid_instance, headers=api_headers)
            assert response.status_code == 201
        
        # Test 4: Simulate temporary service failure and recovery
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            # First call fails
            mock_evo.return_value.get_status = AsyncMock(side_effect=Exception("Temporary service failure"))
            
            response = client.get("/api/v1/instances/recovery-test/status", headers=api_headers)
            assert response.status_code in [500, 503]
            
            # Second call succeeds (service recovered)
            from src.channels.base import ConnectionStatus
            mock_evo.return_value.get_status = AsyncMock(return_value=ConnectionStatus(
                instance_name="recovery-test",
                channel_type="whatsapp",
                status="connected"
            ))
            
            response = client.get("/api/v1/instances/recovery-test/status", headers=api_headers)
            assert response.status_code == 200

    def test_performance_under_load(self, client, api_headers):
        """Test API performance under realistic load scenarios."""
        
        # Create instance for load testing
        instance_data = {
            "name": "load-test-instance",
            "channel_type": "whatsapp",
            "whatsapp_instance": "load-test-wa",
            "evolution_url": "http://172.19.209.168:18080",
            "evolution_key": "load-key",
            "agent_api_url": "https://agent.load.com",
            "agent_api_key": "load-agent-key",
            "default_agent": "load-test-agent"
        }
        
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            mock_evo.return_value.create_instance = AsyncMock(return_value={"status": "created"})
            
            response = client.post("/api/v1/instances", json=instance_data, headers=api_headers)
            assert response.status_code == 201
        
        # Test rapid health checks (common monitoring pattern)
        health_times = []
        for _ in range(10):
            start = time.time()
            response = client.get("/health")
            end = time.time()
            health_times.append(end - start)
            assert response.status_code == 200
        
        # Health checks should be consistently fast
        avg_health_time = sum(health_times) / len(health_times)
        assert avg_health_time < 0.05  # Under 50ms average
        
        # Test rapid instance listing (common dashboard pattern)
        listing_times = []
        for _ in range(5):
            start = time.time()
            response = client.get("/api/v1/instances", headers=api_headers)
            end = time.time()
            listing_times.append(end - start)
            assert response.status_code == 200
        
        avg_listing_time = sum(listing_times) / len(listing_times)
        assert avg_listing_time < 0.5  # Under 500ms average
        
        # Test concurrent webhook processing (realistic webhook load)
        # Use global mock to prevent actual webhook processing
        with patch('src.api.app._handle_evolution_webhook') as mock_webhook_handler:
            mock_webhook_handler.return_value = {"status": "success"}
            
            import concurrent.futures
            
            def process_webhook(i):
                webhook_data = {
                    "event": "messages.upsert",
                    "data": {
                        "messages": [{
                            "key": {"remoteJid": f"test{i}@s.whatsapp.net", "id": f"msg_{i}"},
                            "message": {"conversation": f"Test message {i}"}
                        }]
                    }
                }
                
                start = time.time()
                response = client.post(
                    "/webhook/evolution/load-test-instance",
                    json=webhook_data
                )
                end = time.time()
                
                return response.status_code, end - start
            
            # Process 10 concurrent webhooks
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_webhook, i) for i in range(10)]
                results = [future.result() for future in futures]
            
            # All webhooks should succeed
            statuses, times = zip(*results)
            assert all(status == 200 for status in statuses)
            
            # Webhook processing should be reasonably fast
            avg_webhook_time = sum(times) / len(times)
            assert avg_webhook_time < 2.0  # Under 2 seconds average

    def test_data_persistence_and_consistency(self, client, api_headers):
        """Test data persistence and consistency across operations."""
        
        # Create multiple instances with different configurations
        instances = [
            {
                "name": "persistence-test-1",
                "channel_type": "whatsapp",
                "whatsapp_instance": "persist-wa-1",
                "evolution_url": "http://172.19.209.168:18080",
                "evolution_key": "persist-key-1",
                "agent_api_url": "https://agent1.persist.com",
                "agent_api_key": "persist-agent-1",
                "webhook_base64": True,
                "default_agent": "persist-agent-1"
            },
            {
                "name": "persistence-test-2", 
                "channel_type": "whatsapp",
                "whatsapp_instance": "persist-wa-2",
                "evolution_url": "http://172.19.209.168:18080",
                "evolution_key": "persist-key-2",
                "agent_api_url": "https://agent2.persist.com",
                "agent_api_key": "persist-agent-2",
                "webhook_base64": False,
                "default_agent": "persist-agent-2"
            }
        ]
        
        # Create instances
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            mock_evo.return_value.create_instance = AsyncMock(return_value={"status": "created"})
            
            created_instances = []
            for instance_data in instances:
                response = client.post("/api/v1/instances", json=instance_data, headers=api_headers)
                assert response.status_code == 201
                created_instances.append(response.json())
        
        # Verify all instances are listed correctly
        response = client.get("/api/v1/instances", headers=api_headers)
        assert response.status_code == 200
        listed_instances = response.json()
        assert len(listed_instances) == 2
        
        # Verify data consistency
        instance_names = [inst["name"] for inst in listed_instances]
        assert "persistence-test-1" in instance_names
        assert "persistence-test-2" in instance_names
        
        # Verify configuration differences are preserved
        inst1 = next(inst for inst in listed_instances if inst["name"] == "persistence-test-1")
        inst2 = next(inst for inst in listed_instances if inst["name"] == "persistence-test-2")
        
        assert inst1["webhook_base64"] == True
        assert inst2["webhook_base64"] == False
        assert inst1["evolution_key"] == "persist-key-1"
        assert inst2["evolution_key"] == "persist-key-2"
        
        # Test individual instance retrieval
        response = client.get("/api/v1/instances/persistence-test-1", headers=api_headers)
        assert response.status_code == 200
        individual_inst = response.json()
        assert individual_inst["name"] == "persistence-test-1"
        assert individual_inst["webhook_base64"] == True
        
        # Test update operation and verify persistence
        with patch('src.channels.base.ChannelHandlerFactory.get_handler') as mock_evo:
            mock_evo.return_value.update_instance = AsyncMock(return_value={"status": "updated"})
            
            update_data = {"webhook_base64": False}
            response = client.put(
                "/api/v1/instances/persistence-test-1",
                json=update_data,
                headers=api_headers
            )
            assert response.status_code == 200
        
        # Verify update persisted
        response = client.get("/api/v1/instances/persistence-test-1", headers=api_headers)
        assert response.status_code == 200
        updated_inst = response.json()
        assert updated_inst["webhook_base64"] == False  # Should be updated
        
        # Verify other instance unchanged
        response = client.get("/api/v1/instances/persistence-test-2", headers=api_headers)
        assert response.status_code == 200
        unchanged_inst = response.json()
        assert unchanged_inst["webhook_base64"] == False  # Should remain the same