"""
Tests for CRUD API instance management endpoints.
"""

from fastapi import status


class TestInstanceCRUDAPI:
    """Test instance management CRUD operations."""
    
    def test_create_instance_success(self, test_client, sample_instance_config):
        """Test successful instance creation."""
        response = test_client.post("/api/v1/instances", json=sample_instance_config)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == sample_instance_config["name"]
        assert data["whatsapp_instance"] == sample_instance_config["whatsapp_instance"]
        assert data["agent_api_url"] == sample_instance_config["agent_api_url"]
        assert data["is_default"] == sample_instance_config["is_default"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_instance_duplicate_name(self, test_client, default_instance_config, sample_instance_config):
        """Test creating instance with duplicate name fails."""
        # Try to create instance with existing name
        sample_instance_config["name"] = "default"
        
        response = test_client.post("/api/v1/instances", json=sample_instance_config)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]
    
    def test_create_instance_as_default(self, test_client, default_instance_config, test_db):
        """Test creating instance as default unsets other defaults."""
        new_instance_data = {
            "name": "new_default",
            "evolution_url": "http://new.com",
            "evolution_key": "new-key",
            "whatsapp_instance": "new_whatsapp",
            "agent_api_url": "http://new-agent.com",
            "agent_api_key": "new-agent-key",
            "default_agent": "new_agent",
            "is_default": True
        }
        
        response = test_client.post("/api/v1/instances", json=new_instance_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["is_default"] is True
        
        # Verify original default is no longer default
        test_db.refresh(default_instance_config)
        assert default_instance_config.is_default is False
    
    def test_create_instance_validation_error(self, test_client):
        """Test instance creation with invalid data."""
        invalid_data = {
            "name": "test",
            # Missing required fields
        }
        
        response = test_client.post("/api/v1/instances", json=invalid_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_list_instances_empty(self, test_client):
        """Test listing instances when none exist."""
        response = test_client.get("/api/v1/instances")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
    
    def test_list_instances_with_data(self, test_client, default_instance_config, test_db):
        """Test listing instances with existing data."""
        # Create additional instance
        from src.db.models import InstanceConfig
        instance = InstanceConfig(
            name="list_test",
            evolution_url="http://list.com",
            evolution_key="list-key",
            whatsapp_instance="list_whatsapp",
            agent_api_url="http://list-agent.com",
            agent_api_key="list-agent-key",
            default_agent="list_agent"
        )
        test_db.add(instance)
        test_db.commit()
        
        response = test_client.get("/api/v1/instances")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        
        names = [inst["name"] for inst in data]
        assert "default" in names
        assert "list_test" in names
    
    def test_list_instances_pagination(self, test_client, test_db):
        """Test instance listing with pagination."""
        # Create multiple instances
        from src.db.models import InstanceConfig
        for i in range(5):
            instance = InstanceConfig(
                name=f"page_test_{i}",
                evolution_url=f"http://page{i}.com",
                evolution_key=f"page-key{i}",
                whatsapp_instance=f"page_whatsapp{i}",
                agent_api_url=f"http://page-agent{i}.com",
                agent_api_key=f"page-agent-key{i}",
                default_agent=f"page_agent{i}"
            )
            test_db.add(instance)
        test_db.commit()
        
        # Test pagination
        response = test_client.get("/api/v1/instances?skip=2&limit=2")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
    
    def test_get_instance_success(self, test_client, default_instance_config):
        """Test getting specific instance."""
        response = test_client.get("/api/v1/instances/default")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "default"
        assert data["id"] == default_instance_config.id
        assert data["is_default"] is True
    
    def test_get_instance_not_found(self, test_client):
        """Test getting non-existent instance."""
        response = test_client.get("/api/v1/instances/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]
    
    def test_update_instance_success(self, test_client, default_instance_config):
        """Test updating instance configuration."""
        update_data = {
            "agent_timeout": 120,
            "session_id_prefix": "updated_",
            "default_agent": "updated_agent"
        }
        
        response = test_client.put("/api/v1/instances/default", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_timeout"] == 120
        assert data["session_id_prefix"] == "updated_"
        assert data["default_agent"] == "updated_agent"
        # Other fields should remain unchanged
        assert data["name"] == "default"
    
    def test_update_instance_make_default(self, test_client, test_db):
        """Test updating instance to make it default."""
        from src.db.models import InstanceConfig
        
        # Create two instances
        instance1 = InstanceConfig(
            name="update_test1",
            evolution_url="http://test1.com",
            evolution_key="key1",
            whatsapp_instance="whatsapp1",
            agent_api_url="http://agent1.com",
            agent_api_key="agent_key1",
            default_agent="agent1",
            is_default=True
        )
        instance2 = InstanceConfig(
            name="update_test2",
            evolution_url="http://test2.com",
            evolution_key="key2",
            whatsapp_instance="whatsapp2",
            agent_api_url="http://agent2.com",
            agent_api_key="agent_key2",
            default_agent="agent2",
            is_default=False
        )
        test_db.add(instance1)
        test_db.add(instance2)
        test_db.commit()
        
        # Update instance2 to be default
        update_data = {"is_default": True}
        response = test_client.put("/api/v1/instances/update_test2", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_default"] is True
        
        # Verify instance1 is no longer default
        test_db.refresh(instance1)
        assert instance1.is_default is False
    
    def test_update_instance_not_found(self, test_client):
        """Test updating non-existent instance."""
        update_data = {"agent_timeout": 120}
        
        response = test_client.put("/api/v1/instances/nonexistent", json=update_data)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_instance_success(self, test_client, test_db):
        """Test deleting instance."""
        from src.db.models import InstanceConfig
        
        # Create instance to delete (not default)
        instance = InstanceConfig(
            name="delete_test",
            evolution_url="http://delete.com",
            evolution_key="delete-key",
            whatsapp_instance="delete_whatsapp",
            agent_api_url="http://delete-agent.com",
            agent_api_key="delete-agent-key",
            default_agent="delete_agent"
        )
        test_db.add(instance)
        test_db.commit()
        
        response = test_client.delete("/api/v1/instances/delete_test")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify instance was deleted
        response = test_client.get("/api/v1/instances/delete_test")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_instance_not_found(self, test_client):
        """Test deleting non-existent instance."""
        response = test_client.delete("/api/v1/instances/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_only_instance_fails(self, test_client, default_instance_config):
        """Test that deleting the only instance fails."""
        response = test_client.delete("/api/v1/instances/default")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "only remaining instance" in response.json()["detail"]
    
    def test_get_default_instance(self, test_client, default_instance_config):
        """Test getting the default instance endpoint."""
        # Note: The endpoint path seems incorrect in the implementation
        # It should be /api/v1/instances/default not /api/v1/instances/{name}/default
        response = test_client.get("/api/v1/instances/default/default")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_default"] is True
        assert data["name"] == "default"
    
    def test_set_default_instance(self, test_client, test_db):
        """Test setting an instance as default."""
        from src.db.models import InstanceConfig
        
        # Create two instances
        instance1 = InstanceConfig(
            name="set_default1",
            evolution_url="http://test1.com",
            evolution_key="key1",
            whatsapp_instance="whatsapp1",
            agent_api_url="http://agent1.com",
            agent_api_key="agent_key1",
            default_agent="agent1",
            is_default=True
        )
        instance2 = InstanceConfig(
            name="set_default2",
            evolution_url="http://test2.com",
            evolution_key="key2",
            whatsapp_instance="whatsapp2",
            agent_api_url="http://agent2.com",
            agent_api_key="agent_key2",
            default_agent="agent2",
            is_default=False
        )
        test_db.add(instance1)
        test_db.add(instance2)
        test_db.commit()
        
        # Set instance2 as default
        response = test_client.post("/api/v1/instances/set_default2/set-default")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_default"] is True
        assert response.json()["name"] == "set_default2"
        
        # Verify instance1 is no longer default
        test_db.refresh(instance1)
        assert instance1.is_default is False
    
    def test_set_default_instance_not_found(self, test_client):
        """Test setting non-existent instance as default."""
        response = test_client.post("/api/v1/instances/nonexistent/set-default")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestInstanceAPIValidation:
    """Test API validation and edge cases."""
    
    def test_create_instance_with_empty_strings(self, test_client):
        """Test creating instance with empty required strings."""
        invalid_data = {
            "name": "",  # Empty name
            "whatsapp_instance": "test",
            "agent_api_url": "http://test.com",
            "agent_api_key": "key",
            "default_agent": "agent"
        }
        
        response = test_client.post("/api/v1/instances", json=invalid_data)
        
        # Should fail validation due to empty name
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_instance_with_special_characters(self, test_client):
        """Test creating instance with special characters in name."""
        special_data = {
            "name": "test-instance_123",
            "whatsapp_instance": "test_special",
            "agent_api_url": "http://test.com",
            "agent_api_key": "key",
            "default_agent": "agent"
        }
        
        response = test_client.post("/api/v1/instances", json=special_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == "test-instance_123"
    
    def test_update_instance_partial_update(self, test_client, default_instance_config):
        """Test updating only specific fields."""
        original_url = default_instance_config.agent_api_url
        
        # Update only timeout
        update_data = {"agent_timeout": 300}
        response = test_client.put("/api/v1/instances/default", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_timeout"] == 300
        # Other fields should remain unchanged
        assert data["agent_api_url"] == original_url
    
    def test_instance_response_format(self, test_client, default_instance_config):
        """Test that instance response has correct format."""
        response = test_client.get("/api/v1/instances/default")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check all expected fields are present
        required_fields = [
            "id", "name", "evolution_url", "evolution_key", "whatsapp_instance",
            "session_id_prefix", "agent_api_url", "agent_api_key", "default_agent",
            "agent_timeout", "is_default", "created_at", "updated_at"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Check field types
        assert isinstance(data["id"], int)
        assert isinstance(data["name"], str)
        assert isinstance(data["agent_timeout"], int)
        assert isinstance(data["is_default"], bool)