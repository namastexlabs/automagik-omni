"""
Unit tests for database models and operations.
"""

import pytest
from unittest.mock import patch
from sqlalchemy.exc import IntegrityError

from src.db.models import InstanceConfig
from src.db.bootstrap import ensure_default_instance


class TestInstanceConfigModel:
    """Test InstanceConfig model functionality."""

    def test_create_instance_config(self, test_db):
        """Test creating a new instance configuration."""
        instance = InstanceConfig(
            name="test_instance",
            evolution_url="http://test.com",
            evolution_key="test_key",
            whatsapp_instance="test_whatsapp",
            agent_api_url="http://agent.test.com",
            agent_api_key="agent_key",
            default_agent="test_agent",
            agent_timeout=60,
        )

        test_db.add(instance)
        test_db.commit()
        test_db.refresh(instance)

        assert instance.id is not None
        assert instance.name == "test_instance"
        assert instance.evolution_url == "http://test.com"
        assert instance.agent_timeout == 60
        assert instance.is_default is False
        assert instance.created_at is not None
        assert instance.updated_at is not None

    def test_unique_name_constraint(self, test_db):
        """Test that instance names must be unique."""
        # Create first instance
        instance1 = InstanceConfig(
            name="duplicate_name",
            evolution_url="http://test1.com",
            evolution_key="key1",
            whatsapp_instance="whatsapp1",
            agent_api_url="http://agent1.com",
            agent_api_key="agent_key1",
            default_agent="agent1",
        )
        test_db.add(instance1)
        test_db.commit()

        # Try to create second instance with same name
        instance2 = InstanceConfig(
            name="duplicate_name",
            evolution_url="http://test2.com",
            evolution_key="key2",
            whatsapp_instance="whatsapp2",
            agent_api_url="http://agent2.com",
            agent_api_key="agent_key2",
            default_agent="agent2",
        )
        test_db.add(instance2)

        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_default_values(self, test_db):
        """Test model default values."""
        instance = InstanceConfig(
            name="test_defaults",
            evolution_url="http://test.com",
            evolution_key="test_key",
            whatsapp_instance="test_whatsapp",
            agent_api_url="http://agent.com",
            agent_api_key="agent_key",
            default_agent="test_agent",
            # agent_timeout and is_default should use defaults
        )

        test_db.add(instance)
        test_db.commit()
        test_db.refresh(instance)

        assert instance.agent_timeout == 60  # Default value
        assert instance.is_default is False  # Default value
        assert instance.session_id_prefix is None  # Nullable field

    def test_instance_repr(self, test_db):
        """Test string representation of instance."""
        instance = InstanceConfig(
            name="repr_test",
            evolution_url="http://test.com",
            evolution_key="test_key",
            whatsapp_instance="test_whatsapp",
            agent_api_url="http://agent.com",
            agent_api_key="agent_key",
            default_agent="test_agent",
            is_default=True,
        )

        test_db.add(instance)
        test_db.commit()
        test_db.refresh(instance)

        repr_str = repr(instance)
        assert "repr_test" in repr_str
        assert "is_default=True" in repr_str


class TestBootstrapFunctions:
    """Test database bootstrap functionality."""

    def test_ensure_default_instance_no_instances(self, test_db):
        """Test that ensure_default_instance returns None when no instances exist."""
        # Verify no instances exist
        count = test_db.query(InstanceConfig).count()
        assert count == 0

        # Call ensure_default_instance
        instance = ensure_default_instance(test_db)

        # Should return None since no instances exist and we don't auto-create
        assert instance is None

        # No instances should be created
        count = test_db.query(InstanceConfig).count()
        assert count == 0

    def test_ensure_default_instance_returns_existing(
        self, test_db, default_instance_config
    ):
        """Test that ensure_default_instance returns existing default instance."""
        # Call ensure_default_instance when one already exists
        instance = ensure_default_instance(test_db)

        # Should return the existing instance
        assert instance.id == default_instance_config.id
        assert instance.name == default_instance_config.name

        # Should not create a new instance
        count = test_db.query(InstanceConfig).count()
        assert count == 1

    def test_ensure_default_instance_makes_first_default(self, test_db):
        """Test that when no default exists, the first instance becomes default."""
        # Create a non-default instance
        instance = InstanceConfig(
            name="non_default",
            evolution_url="http://test.com",
            evolution_key="test_key",
            whatsapp_instance="test_whatsapp",
            agent_api_url="http://agent.com",
            agent_api_key="agent_key",
            default_agent="test_agent",
            is_default=False,
        )
        test_db.add(instance)
        test_db.commit()
        test_db.refresh(instance)

        # Call ensure_default_instance
        default_instance = ensure_default_instance(test_db)

        # The existing instance should now be default
        assert default_instance.id == instance.id
        assert default_instance.is_default is True


class TestDatabaseQueries:
    """Test common database query patterns."""

    def test_find_by_name(self, test_db, default_instance_config):
        """Test finding instance by name."""
        instance = test_db.query(InstanceConfig).filter_by(name="default").first()

        assert instance is not None
        assert instance.id == default_instance_config.id

    def test_find_default_instance(self, test_db, default_instance_config):
        """Test finding the default instance."""
        instance = test_db.query(InstanceConfig).filter_by(is_default=True).first()

        assert instance is not None
        assert instance.id == default_instance_config.id

    def test_update_instance(self, test_db, default_instance_config):
        """Test updating instance configuration."""
        # Update the instance
        default_instance_config.agent_timeout = 120
        default_instance_config.session_id_prefix = "updated_"
        test_db.commit()

        # Verify update
        test_db.refresh(default_instance_config)
        assert default_instance_config.agent_timeout == 120
        assert default_instance_config.session_id_prefix == "updated_"
        assert default_instance_config.updated_at > default_instance_config.created_at

    def test_delete_instance(self, test_db):
        """Test deleting an instance."""
        # Create instance to delete
        instance = InstanceConfig(
            name="to_delete",
            evolution_url="http://test.com",
            evolution_key="test_key",
            whatsapp_instance="test_whatsapp",
            agent_api_url="http://agent.com",
            agent_api_key="agent_key",
            default_agent="test_agent",
        )
        test_db.add(instance)
        test_db.commit()
        instance_id = instance.id

        # Delete the instance
        test_db.delete(instance)
        test_db.commit()

        # Verify deletion
        deleted_instance = (
            test_db.query(InstanceConfig).filter_by(id=instance_id).first()
        )
        assert deleted_instance is None

    def test_list_all_instances(self, test_db, default_instance_config):
        """Test listing all instances."""
        # Create additional instances
        for i in range(3):
            instance = InstanceConfig(
                name=f"instance_{i}",
                evolution_url=f"http://test{i}.com",
                evolution_key=f"key{i}",
                whatsapp_instance=f"whatsapp{i}",
                agent_api_url=f"http://agent{i}.com",
                agent_api_key=f"agent_key{i}",
                default_agent=f"agent{i}",
            )
            test_db.add(instance)
        test_db.commit()

        # Query all instances
        instances = test_db.query(InstanceConfig).all()

        # Should have default + 3 new instances = 4 total
        assert len(instances) == 4

        # Verify names
        names = [inst.name for inst in instances]
        assert "default" in names
        assert "instance_0" in names
        assert "instance_1" in names
        assert "instance_2" in names
