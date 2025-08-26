"""
Comprehensive tests for unified database models.
Tests the unified agent fields and helper methods in InstanceConfig.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.db.models import InstanceConfig, User


class TestInstanceConfigUnifiedFields:
    """Test the unified agent fields in InstanceConfig model."""
    
    def test_default_unified_fields(self, test_db):
        """Test that unified fields have correct defaults."""
        instance = InstanceConfig(
            name="test",
            agent_api_url="http://test.com",
            agent_api_key="test-key"
        )
        test_db.add(instance)
        test_db.commit()
        
        # Test defaults
        assert instance.agent_instance_type == "automagik"
        assert instance.agent_id == "default"
        assert instance.agent_type == "agent"
        assert instance.agent_timeout == 60
        assert instance.agent_stream_mode is False
        assert instance.default_agent is None
    
    def test_unified_fields_assignment(self, test_db):
        """Test that unified fields can be set correctly."""
        instance = InstanceConfig(
            name="hive-test",
            agent_instance_type="hive",
            agent_api_url="https://hive.example.com/api",
            agent_api_key="hive-api-key",
            agent_id="test-agent-123",
            agent_type="team",
            agent_timeout=120,
            agent_stream_mode=True
        )
        test_db.add(instance)
        test_db.commit()
        
        assert instance.agent_instance_type == "hive"
        assert instance.agent_api_url == "https://hive.example.com/api"
        assert instance.agent_api_key == "hive-api-key"
        assert instance.agent_id == "test-agent-123"
        assert instance.agent_type == "team"
        assert instance.agent_timeout == 120
        assert instance.agent_stream_mode is True
    
    def test_backward_compatibility(self, test_db):
        """Test backward compatibility with legacy fields."""
        instance = InstanceConfig(
            name="legacy",
            agent_api_url="http://automagik.com",
            agent_api_key="key",
            default_agent="my-agent",
            agent_timeout=90
        )
        test_db.add(instance)
        test_db.commit()
        
        # Should use default_agent when agent_id is not set
        config = instance.get_agent_config()
        assert config["agent_id"] in ["my-agent", "default"]
        assert config["instance_type"] == "automagik"
        assert config["agent_type"] == "agent"
    
    def test_hive_team_configuration(self, test_db):
        """Test Hive team configuration."""
        instance = InstanceConfig(
            name="hive-team",
            agent_instance_type="hive",
            agent_api_url="https://hive.api/v1",
            agent_api_key="hive-key",
            agent_id="dev-team",
            agent_type="team",
            agent_stream_mode=True
        )
        test_db.add(instance)
        test_db.commit()
        
        assert instance.agent_instance_type == "hive"
        assert instance.agent_id == "dev-team"
        assert instance.agent_type == "team"
        assert instance.agent_stream_mode is True
    
    def test_legacy_hive_fields(self, test_db):
        """Test that legacy hive fields still work."""
        instance = InstanceConfig(
            name="legacy-hive",
            agent_api_url="http://automagik.com",
            agent_api_key="key",
            hive_enabled=True,
            hive_api_url="https://hive.com",
            hive_api_key="hive-key",
            hive_agent_id="hive-agent",
            hive_team_id=None,
            hive_timeout=45,
            hive_stream_mode=True
        )
        test_db.add(instance)
        test_db.commit()
        
        # Legacy fields should be accessible
        assert instance.hive_enabled is True
        assert instance.hive_api_url == "https://hive.com"
        assert instance.hive_api_key == "hive-key"
        assert instance.hive_agent_id == "hive-agent"
        assert instance.hive_timeout == 45
        assert instance.hive_stream_mode is True


class TestInstanceConfigProperties:
    """Test the property methods for unified configuration."""
    
    def test_is_hive_property(self, test_db):
        """Test is_hive property."""
        # Hive instance
        hive_instance = InstanceConfig(
            name="hive",
            agent_instance_type="hive",
            agent_api_url="https://hive.com",
            agent_api_key="key"
        )
        test_db.add(hive_instance)
        test_db.commit()
        
        assert hive_instance.is_hive is True
        assert hive_instance.is_automagik is False
        
        # Automagik instance
        automagik_instance = InstanceConfig(
            name="automagik",
            agent_instance_type="automagik",
            agent_api_url="https://automagik.com",
            agent_api_key="key"
        )
        test_db.add(automagik_instance)
        test_db.commit()
        
        assert automagik_instance.is_hive is False
        assert automagik_instance.is_automagik is True
    
    def test_is_team_property(self, test_db):
        """Test is_team property."""
        # Hive team
        hive_team = InstanceConfig(
            name="hive-team",
            agent_instance_type="hive",
            agent_api_url="https://hive.com",
            agent_api_key="key",
            agent_type="team"
        )
        test_db.add(hive_team)
        test_db.commit()
        
        assert hive_team.is_team is True
        
        # Hive agent
        hive_agent = InstanceConfig(
            name="hive-agent",
            agent_instance_type="hive",
            agent_api_url="https://hive.com",
            agent_api_key="key",
            agent_type="agent"
        )
        test_db.add(hive_agent)
        test_db.commit()
        
        assert hive_agent.is_team is False
        
        # Automagik (never team)
        automagik = InstanceConfig(
            name="automagik-agent",
            agent_instance_type="automagik",
            agent_api_url="https://automagik.com",
            agent_api_key="key",
            agent_type="team"  # Even if set to team
        )
        test_db.add(automagik)
        test_db.commit()
        
        assert automagik.is_team is False  # Automagik can't be team
    
    def test_streaming_enabled_property(self, test_db):
        """Test streaming_enabled property."""
        # Hive with streaming
        hive_streaming = InstanceConfig(
            name="hive-stream",
            agent_instance_type="hive",
            agent_api_url="https://hive.com",
            agent_api_key="key",
            agent_stream_mode=True
        )
        test_db.add(hive_streaming)
        test_db.commit()
        
        assert hive_streaming.streaming_enabled is True
        
        # Hive without streaming
        hive_no_stream = InstanceConfig(
            name="hive-no-stream",
            agent_instance_type="hive",
            agent_api_url="https://hive.com",
            agent_api_key="key",
            agent_stream_mode=False
        )
        test_db.add(hive_no_stream)
        test_db.commit()
        
        assert hive_no_stream.streaming_enabled is False
        
        # Automagik with streaming (still false because automagik doesn't support it)
        automagik_stream = InstanceConfig(
            name="automagik-stream",
            agent_instance_type="automagik",
            agent_api_url="https://automagik.com",
            agent_api_key="key",
            agent_stream_mode=True
        )
        test_db.add(automagik_stream)
        test_db.commit()
        
        assert automagik_stream.streaming_enabled is False  # Automagik doesn't support streaming


class TestInstanceConfigMethods:
    """Test the helper methods in InstanceConfig."""
    
    def test_get_agent_config_with_unified_fields(self, test_db):
        """Test get_agent_config with unified fields."""
        instance = InstanceConfig(
            name="test-config",
            agent_instance_type="hive",
            agent_api_url="https://api.test.com",
            agent_api_key="test-key",
            agent_id="agent-123",
            agent_type="agent",
            agent_timeout=30,
            agent_stream_mode=True
        )
        test_db.add(instance)
        test_db.commit()
        
        config = instance.get_agent_config()
        
        assert config["instance_type"] == "hive"
        assert config["api_url"] == "https://api.test.com"
        assert config["api_key"] == "test-key"
        assert config["agent_id"] == "agent-123"
        assert config["agent_type"] == "agent"
        assert config["timeout"] == 30
        assert config["stream_mode"] is True
    
    def test_get_agent_config_with_defaults(self, test_db):
        """Test get_agent_config with default values."""
        instance = InstanceConfig(
            name="defaults",
            agent_api_url="https://api.test.com",
            agent_api_key="test-key"
        )
        test_db.add(instance)
        test_db.commit()
        
        config = instance.get_agent_config()
        
        assert config["instance_type"] == "automagik"
        assert config["agent_id"] == "default"
        assert config["agent_type"] == "agent"
        assert config["timeout"] == 60
        assert config["stream_mode"] is False
    
    def test_get_agent_config_fallback_to_default_agent(self, test_db):
        """Test get_agent_config falls back to default_agent."""
        instance = InstanceConfig(
            name="fallback",
            agent_api_url="https://api.test.com",
            agent_api_key="test-key",
            default_agent="fallback-agent"
        )
        test_db.add(instance)
        test_db.commit()
        
        config = instance.get_agent_config()
        assert config["agent_id"] == "fallback-agent"
    
    def test_has_hive_config_unified(self, test_db):
        """Test has_hive_config with unified fields."""
        # Complete hive config
        complete = InstanceConfig(
            name="complete-hive",
            agent_instance_type="hive",
            agent_api_url="https://hive.com",
            agent_api_key="key",
            agent_id="agent-123"
        )
        test_db.add(complete)
        test_db.commit()
        
        assert complete.has_hive_config() is True
        
        # Incomplete hive config (missing agent_id)
        incomplete = InstanceConfig(
            name="incomplete-hive",
            agent_instance_type="hive",
            agent_api_url="https://hive.com",
            agent_api_key="key"
        )
        test_db.add(incomplete)
        test_db.commit()
        
        # With default agent_id, should still be valid
        assert incomplete.has_hive_config() is True  # agent_id defaults to "default"
    
    def test_has_hive_config_legacy(self, test_db):
        """Test has_hive_config with legacy fields."""
        # Complete legacy config
        legacy = InstanceConfig(
            name="legacy-hive",
            agent_api_url="https://automagik.com",
            agent_api_key="key",
            hive_enabled=True,
            hive_api_url="https://hive.com",
            hive_api_key="hive-key",
            hive_agent_id="hive-agent"
        )
        test_db.add(legacy)
        test_db.commit()
        
        assert legacy.has_hive_config() is True
    
    def test_get_hive_config_unified(self, test_db):
        """Test get_hive_config with unified fields."""
        instance = InstanceConfig(
            name="hive-config",
            agent_instance_type="hive",
            agent_api_url="https://hive.com",
            agent_api_key="hive-key",
            agent_id="agent-123",
            agent_type="team",
            agent_timeout=45,
            agent_stream_mode=True
        )
        test_db.add(instance)
        test_db.commit()
        
        config = instance.get_hive_config()
        
        assert config["instance_type"] == "hive"
        assert config["api_url"] == "https://hive.com"
        assert config["api_key"] == "hive-key"
        assert config["agent_id"] == "agent-123"
        assert config["agent_type"] == "team"
        assert config["timeout"] == 45
        assert config["stream_mode"] is True
    
    def test_get_hive_config_legacy(self, test_db):
        """Test get_hive_config with legacy fields."""
        instance = InstanceConfig(
            name="legacy-hive-config",
            agent_api_url="https://automagik.com",
            agent_api_key="key",
            hive_enabled=True,
            hive_api_url="https://hive.com",
            hive_api_key="hive-key",
            hive_agent_id="hive-agent",
            hive_timeout=30,
            hive_stream_mode=True
        )
        test_db.add(instance)
        test_db.commit()
        
        config = instance.get_hive_config()
        
        # Should return legacy format
        assert config["api_url"] == "https://hive.com"
        assert config["api_key"] == "hive-key"
        assert config["agent_id"] == "hive-agent"
        assert config["timeout"] == 30
        assert config["stream_mode"] is True


class TestInstanceConfigEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_null_values_handling(self, test_db):
        """Test handling of null values in unified fields."""
        instance = InstanceConfig(
            name="null-test",
            agent_api_url="https://api.com",
            agent_api_key="key",
            agent_id=None,  # Explicitly null
            default_agent=None  # Also null
        )
        test_db.add(instance)
        test_db.commit()
        
        config = instance.get_agent_config()
        # Should fall back to "default"
        assert config["agent_id"] == "default"
    
    def test_mixed_configuration(self, test_db):
        """Test instance with both unified and legacy fields."""
        instance = InstanceConfig(
            name="mixed",
            agent_instance_type="hive",
            agent_api_url="https://new.com",
            agent_api_key="new-key",
            agent_id="new-agent",
            hive_api_url="https://old.com",
            hive_api_key="old-key",
            hive_agent_id="old-agent"
        )
        test_db.add(instance)
        test_db.commit()
        
        # Unified fields should take precedence
        config = instance.get_agent_config()
        assert config["api_url"] == "https://new.com"
        assert config["api_key"] == "new-key"
        assert config["agent_id"] == "new-agent"
    
    def test_invalid_instance_type(self, test_db):
        """Test handling of invalid instance type."""
        instance = InstanceConfig(
            name="invalid-type",
            agent_api_url="https://api.com",
            agent_api_key="key"
        )
        test_db.add(instance)
        test_db.commit()
        
        # Manually set invalid type (simulating data corruption)
        instance.agent_instance_type = "invalid"
        test_db.commit()
        
        # Properties should handle gracefully
        assert instance.is_hive is False
        assert instance.is_automagik is False
        assert instance.is_team is False
        assert instance.streaming_enabled is False
    
    def test_empty_strings(self, test_db):
        """Test handling of empty strings in fields."""
        instance = InstanceConfig(
            name="empty",
            agent_api_url="https://api.com",
            agent_api_key="key",
            agent_id="",  # Empty string
            default_agent=""  # Also empty
        )
        test_db.add(instance)
        test_db.commit()
        
        config = instance.get_agent_config()
        # Should fall back to "default" for empty strings
        assert config["agent_id"] == "default"


class TestInstanceConfigConstraints:
    """Test database constraints and validation."""
    
    def test_required_fields_constraints(self, test_db):
        """Test that required fields are enforced."""
        # Missing name
        with pytest.raises(IntegrityError):
            instance = InstanceConfig(
                agent_api_url="https://api.com",
                agent_api_key="key"
            )
            test_db.add(instance)
            test_db.commit()
        test_db.rollback()
        
        # Missing agent_api_url
        with pytest.raises(IntegrityError):
            instance = InstanceConfig(
                name="no-url",
                agent_api_key="key"
            )
            test_db.add(instance)
            test_db.commit()
        test_db.rollback()
        
        # Missing agent_api_key
        with pytest.raises(IntegrityError):
            instance = InstanceConfig(
                name="no-key",
                agent_api_url="https://api.com"
            )
            test_db.add(instance)
            test_db.commit()
        test_db.rollback()
    
    def test_unique_name_constraint(self, test_db):
        """Test that instance names must be unique."""
        # Create first instance
        instance1 = InstanceConfig(
            name="unique-test",
            agent_api_url="https://api.com",
            agent_api_key="key1"
        )
        test_db.add(instance1)
        test_db.commit()
        
        # Try to create second with same name
        with pytest.raises(IntegrityError):
            instance2 = InstanceConfig(
                name="unique-test",  # Same name
                agent_api_url="https://api2.com",
                agent_api_key="key2"
            )
            test_db.add(instance2)
            test_db.commit()
        test_db.rollback()


class TestUserModel:
    """Test User model for completeness."""
    
    def test_user_creation(self, test_db):
        """Test basic user creation."""
        user = User(
            phone_number="+1234567890",
            whatsapp_jid="1234567890@s.whatsapp.net",
            instance_name="test-instance",
            display_name="Test User"
        )
        test_db.add(user)
        test_db.commit()
        
        assert user.id is not None
        assert user.phone_number == "+1234567890"
        assert user.whatsapp_jid == "1234567890@s.whatsapp.net"
        assert user.display_name == "Test User"
        assert user.instance_name == "test-instance"
    
    def test_user_with_instance(self, test_db):
        """Test user associated with an instance."""
        # Create instance
        instance = InstanceConfig(
            name="user-instance",
            agent_api_url="https://api.com",
            agent_api_key="key"
        )
        test_db.add(instance)
        test_db.commit()
        
        # Create user with instance
        user = User(
            phone_number="+9876543210",
            whatsapp_jid="9876543210@s.whatsapp.net",
            instance_name=instance.name
        )
        test_db.add(user)
        test_db.commit()
        
        assert user.instance_name == instance.name
        assert user.instance == instance
        assert instance.users == [user]