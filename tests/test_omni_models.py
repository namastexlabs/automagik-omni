"""
Comprehensive tests for omni database models.
Tests the agent fields and helper methods in InstanceConfig.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from src.db.models import InstanceConfig, User


class TestInstanceConfigAgentFields:
    """Test the agent fields in InstanceConfig model."""

    def test_default_agent_fields(self, test_db):
        """Test that agent fields have correct defaults."""
        instance = InstanceConfig(name="test", agent_api_url="http://test.com", agent_api_key="test-key")
        test_db.add(instance)
        test_db.commit()

        # Test defaults
        assert instance.agent_id == "default"
        assert instance.agent_type == "agent"
        assert instance.agent_timeout == 60
        assert instance.agent_stream_mode is False

    def test_agent_fields_assignment(self, test_db):
        """Test that agent fields can be set correctly."""
        instance = InstanceConfig(
            name="agno-test",
            agent_api_url="https://agno.example.com/api",
            agent_api_key="agno-api-key",
            agent_id="test-agent-123",
            agent_type="team",
            agent_timeout=120,
            agent_stream_mode=True,
        )
        test_db.add(instance)
        test_db.commit()

        assert instance.agent_api_url == "https://agno.example.com/api"
        assert instance.agent_api_key == "agno-api-key"
        assert instance.agent_id == "test-agent-123"
        assert instance.agent_type == "team"
        assert instance.agent_timeout == 120
        assert instance.agent_stream_mode is True

    def test_team_configuration(self, test_db):
        """Test team configuration."""
        instance = InstanceConfig(
            name="team-config",
            agent_api_url="https://agno.api/v1",
            agent_api_key="agno-key",
            agent_id="dev-team",
            agent_type="team",
            agent_stream_mode=True,
        )
        test_db.add(instance)
        test_db.commit()

        assert instance.agent_id == "dev-team"
        assert instance.agent_type == "team"
        assert instance.agent_stream_mode is True


class TestInstanceConfigProperties:
    """Test the property methods for agent configuration."""

    def test_is_team_property(self, test_db):
        """Test is_team property."""
        # Team instance
        team_instance = InstanceConfig(
            name="team",
            agent_api_url="https://agno.com",
            agent_api_key="key",
            agent_type="team",
        )
        test_db.add(team_instance)
        test_db.commit()

        assert team_instance.is_team is True

        # Agent instance
        agent_instance = InstanceConfig(
            name="agent",
            agent_api_url="https://agno.com",
            agent_api_key="key",
            agent_type="agent",
        )
        test_db.add(agent_instance)
        test_db.commit()

        assert agent_instance.is_team is False

    def test_streaming_enabled_property(self, test_db):
        """Test streaming_enabled property."""
        # With streaming enabled
        streaming_instance = InstanceConfig(
            name="streaming",
            agent_api_url="https://agno.com",
            agent_api_key="key",
            agent_stream_mode=True,
        )
        test_db.add(streaming_instance)
        test_db.commit()

        assert streaming_instance.streaming_enabled is True

        # Without streaming
        no_streaming_instance = InstanceConfig(
            name="no-streaming",
            agent_api_url="https://agno.com",
            agent_api_key="key",
            agent_stream_mode=False,
        )
        test_db.add(no_streaming_instance)
        test_db.commit()

        assert no_streaming_instance.streaming_enabled is False


class TestInstanceConfigMethods:
    """Test the helper methods in InstanceConfig."""

    def test_get_agent_config_with_all_fields(self, test_db):
        """Test get_agent_config with all fields set."""
        instance = InstanceConfig(
            name="test-config",
            agent_api_url="https://api.test.com",
            agent_api_key="test-key",
            agent_id="agent-123",
            agent_type="agent",
            agent_timeout=30,
            agent_stream_mode=True,
        )
        test_db.add(instance)
        test_db.commit()

        config = instance.get_agent_config()

        assert config["api_url"] == "https://api.test.com"
        assert config["api_key"] == "test-key"
        assert config["agent_id"] == "agent-123"
        assert config["name"] == "agent-123"
        assert config["agent_type"] == "agent"
        assert config["timeout"] == 30
        assert config["stream_mode"] is True

    def test_get_agent_config_with_defaults(self, test_db):
        """Test get_agent_config with default values."""
        instance = InstanceConfig(
            name="defaults",
            agent_api_url="https://api.test.com",
            agent_api_key="test-key",
        )
        test_db.add(instance)
        test_db.commit()

        config = instance.get_agent_config()

        assert config["agent_id"] == "default"
        assert config["name"] == "default"
        assert config["agent_type"] == "agent"
        assert config["timeout"] == 60
        assert config["stream_mode"] is False


class TestInstanceConfigEdgeCases:
    """Test edge cases and error conditions."""

    def test_null_agent_id_handling(self, test_db):
        """Test handling of null agent_id."""
        instance = InstanceConfig(
            name="null-test",
            agent_api_url="https://api.com",
            agent_api_key="key",
            agent_id=None,
        )
        test_db.add(instance)
        test_db.commit()

        config = instance.get_agent_config()
        # Should fall back to "default"
        assert config["agent_id"] == "default"
        assert config["name"] == "default"

    def test_empty_agent_id(self, test_db):
        """Test handling of empty string agent_id."""
        instance = InstanceConfig(
            name="empty",
            agent_api_url="https://api.com",
            agent_api_key="key",
            agent_id="",
        )
        test_db.add(instance)
        test_db.commit()

        config = instance.get_agent_config()
        # Empty string should be treated as no value
        assert config["agent_id"] == "default"
        assert config["name"] == "default"


class TestInstanceConfigConstraints:
    """Test database constraints and validation."""

    def test_required_fields_constraints(self, test_db):
        """Test that required fields are enforced.

        Note: Only 'name' is required (NOT NULL constraint). Other fields like
        agent_api_url and agent_api_key are now optional (nullable=True) to
        support the wizard flow where they can be configured later.
        """
        # Missing name - should fail
        with pytest.raises(IntegrityError):
            instance = InstanceConfig(agent_api_url="https://api.com", agent_api_key="key")
            test_db.add(instance)
            test_db.commit()
        test_db.rollback()

        # Missing agent_api_url - should succeed (field is now optional)
        instance = InstanceConfig(name="no-url-instance", agent_api_key="key")
        test_db.add(instance)
        test_db.commit()
        assert instance.agent_api_url is None
        test_db.delete(instance)
        test_db.commit()

        # Missing agent_api_key - should succeed (field is now optional)
        instance = InstanceConfig(name="no-key-instance", agent_api_url="https://api.com")
        test_db.add(instance)
        test_db.commit()
        assert instance.agent_api_key is None
        test_db.delete(instance)
        test_db.commit()

    def test_unique_name_constraint(self, test_db):
        """Test that instance names must be unique."""
        # Create first instance
        instance1 = InstanceConfig(name="unique-test", agent_api_url="https://api.com", agent_api_key="key1")
        test_db.add(instance1)
        test_db.commit()

        # Try to create second with same name
        with pytest.raises(IntegrityError):
            instance2 = InstanceConfig(
                name="unique-test",  # Same name
                agent_api_url="https://api2.com",
                agent_api_key="key2",
            )
            test_db.add(instance2)
            test_db.commit()
        test_db.rollback()


class TestUserModel:
    """Test User model for completeness."""

    def test_user_creation(self, test_db):
        """Test basic user creation.

        Note: User.instance_name has a foreign key constraint to InstanceConfig.name,
        so we must create the instance first.
        """
        # Create instance first (required by FK constraint)
        instance = InstanceConfig(name="test-instance")
        test_db.add(instance)
        test_db.commit()

        # Now create user
        user = User(
            phone_number="+1234567890",
            whatsapp_jid="1234567890@s.whatsapp.net",
            instance_name="test-instance",
            display_name="Test User",
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
        instance = InstanceConfig(name="user-instance", agent_api_url="https://api.com", agent_api_key="key")
        test_db.add(instance)
        test_db.commit()

        # Create user with instance
        user = User(
            phone_number="+9876543210",
            whatsapp_jid="9876543210@s.whatsapp.net",
            instance_name=instance.name,
        )
        test_db.add(user)
        test_db.commit()

        assert user.instance_name == instance.name
        assert user.instance == instance
        assert instance.users == [user]
