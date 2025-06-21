"""
Tests for CLI instance management commands.
"""

import pytest
from unittest.mock import patch
from typer.testing import CliRunner

from src.cli.instance_cli import app as cli_app
from src.db.models import InstanceConfig


class TestInstanceCLI:
    """Test CLI instance management commands."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_db_session(self, test_db):
        """Mock database session for CLI tests."""
        with patch('src.cli.instance_cli.SessionLocal', return_value=test_db):
            with patch('src.cli.instance_cli.create_tables'):
                yield test_db
    
    def test_list_instances_empty(self, cli_runner, mock_db_session):
        """Test listing instances when none exist."""
        result = cli_runner.invoke(cli_app, ["list"])
        
        assert result.exit_code == 0
        assert "No instances found" in result.stdout
    
    def test_list_instances_with_data(self, cli_runner, mock_db_session, default_instance_config):
        """Test listing instances with existing data."""
        result = cli_runner.invoke(cli_app, ["list"])
        
        assert result.exit_code == 0
        assert "Instance Configurations" in result.stdout
        assert "default" in result.stdout
        assert "✓" in result.stdout  # Default indicator
    
    def test_show_instance_success(self, cli_runner, mock_db_session, default_instance_config):
        """Test showing specific instance details."""
        result = cli_runner.invoke(cli_app, ["show", "default"])
        
        assert result.exit_code == 0
        assert "Instance Configuration: default" in result.stdout
        assert f"ID: {default_instance_config.id}" in result.stdout
        assert "Is Default: True" in result.stdout
    
    def test_show_instance_not_found(self, cli_runner, mock_db_session):
        """Test showing non-existent instance."""
        result = cli_runner.invoke(cli_app, ["show", "nonexistent"])
        
        assert result.exit_code == 1
        assert "Instance 'nonexistent' not found" in result.stdout
    
    def test_add_instance_success(self, cli_runner, mock_db_session):
        """Test adding new instance."""
        result = cli_runner.invoke(cli_app, [
            "add", "test_instance",
            "--whatsapp-instance", "test_whatsapp",
            "--agent-api-url", "http://test-agent.com",
            "--agent-api-key", "test-key",
            "--default-agent", "test_agent"
        ])
        
        assert result.exit_code == 0
        assert "Instance 'test_instance' created successfully" in result.stdout
        
        # Verify instance was created
        instance = mock_db_session.query(InstanceConfig).filter_by(name="test_instance").first()
        assert instance is not None
        assert instance.whatsapp_instance == "test_whatsapp"
        assert instance.agent_api_url == "http://test-agent.com"
    
    def test_add_instance_with_optional_params(self, cli_runner, mock_db_session):
        """Test adding instance with all optional parameters."""
        result = cli_runner.invoke(cli_app, [
            "add", "full_test",
            "--evolution-url", "http://evolution.com",
            "--evolution-key", "evo-key",
            "--whatsapp-instance", "full_whatsapp",
            "--session-id-prefix", "full_",
            "--agent-api-url", "http://full-agent.com", 
            "--agent-api-key", "full-key",
            "--default-agent", "full_agent",
            "--agent-timeout", "120",
            "--default"
        ])
        
        assert result.exit_code == 0
        assert "Instance 'full_test' created successfully" in result.stdout
        assert "Instance 'full_test' set as default" in result.stdout
        
        # Verify instance was created with all parameters
        instance = mock_db_session.query(InstanceConfig).filter_by(name="full_test").first()
        assert instance is not None
        assert instance.evolution_url == "http://evolution.com"
        assert instance.session_id_prefix == "full_"
        assert instance.agent_timeout == 120
        assert instance.is_default is True
    
    def test_add_instance_duplicate_name(self, cli_runner, mock_db_session, default_instance_config):
        """Test adding instance with duplicate name."""
        result = cli_runner.invoke(cli_app, [
            "add", "default",
            "--whatsapp-instance", "test",
            "--agent-api-url", "http://test.com",
            "--agent-api-key", "key",
            "--default-agent", "agent"
        ])
        
        assert result.exit_code == 1
        assert "Instance 'default' already exists" in result.stdout
    
    def test_update_instance_success(self, cli_runner, mock_db_session, default_instance_config):
        """Test updating instance configuration."""
        result = cli_runner.invoke(cli_app, [
            "update", "default",
            "--agent-timeout", "180",
            "--session-id-prefix", "updated_"
        ])
        
        assert result.exit_code == 0
        assert "Instance 'default' updated successfully" in result.stdout
        
        # Verify updates
        mock_db_session.refresh(default_instance_config)
        assert default_instance_config.agent_timeout == 180
        assert default_instance_config.session_id_prefix == "updated_"
    
    def test_update_instance_make_default(self, cli_runner, mock_db_session, test_db):
        """Test updating instance to make it default."""
        # Create two instances
        instance1 = InstanceConfig(
            name="update1",
            whatsapp_instance="test1",
            agent_api_url="http://agent1.com",
            agent_api_key="key1",
            default_agent="agent1",
            is_default=True
        )
        instance2 = InstanceConfig(
            name="update2",
            whatsapp_instance="test2",
            agent_api_url="http://agent2.com",
            agent_api_key="key2",
            default_agent="agent2",
            is_default=False
        )
        test_db.add(instance1)
        test_db.add(instance2)
        test_db.commit()
        
        result = cli_runner.invoke(cli_app, [
            "update", "update2",
            "--default"
        ])
        
        assert result.exit_code == 0
        assert "Instance 'update2' updated successfully" in result.stdout
        assert "Instance 'update2' set as default" in result.stdout
        
        # Verify default change
        test_db.refresh(instance1)
        test_db.refresh(instance2)
        assert instance1.is_default is False
        assert instance2.is_default is True
    
    def test_update_instance_not_found(self, cli_runner, mock_db_session):
        """Test updating non-existent instance."""
        result = cli_runner.invoke(cli_app, [
            "update", "nonexistent",
            "--agent-timeout", "120"
        ])
        
        assert result.exit_code == 1
        assert "Instance 'nonexistent' not found" in result.stdout
    
    def test_delete_instance_success(self, cli_runner, mock_db_session, test_db):
        """Test deleting instance with confirmation."""
        # Create instance to delete (not default)
        instance = InstanceConfig(
            name="delete_me",
            whatsapp_instance="delete_test",
            agent_api_url="http://delete.com",
            agent_api_key="delete_key",
            default_agent="delete_agent"
        )
        test_db.add(instance)
        test_db.commit()
        
        # Delete with force flag (no confirmation)
        result = cli_runner.invoke(cli_app, [
            "delete", "delete_me", "--force"
        ])
        
        assert result.exit_code == 0
        assert "Instance 'delete_me' deleted successfully" in result.stdout
        
        # Verify deletion
        deleted = test_db.query(InstanceConfig).filter_by(name="delete_me").first()
        assert deleted is None
    
    def test_delete_instance_with_confirmation(self, cli_runner, mock_db_session, test_db):
        """Test deleting instance with interactive confirmation."""
        # Create instance to delete
        instance = InstanceConfig(
            name="confirm_delete",
            whatsapp_instance="confirm_test",
            agent_api_url="http://confirm.com",
            agent_api_key="confirm_key",
            default_agent="confirm_agent"
        )
        test_db.add(instance)
        test_db.commit()
        
        # Delete with confirmation (simulate 'y' input)
        result = cli_runner.invoke(cli_app, [
            "delete", "confirm_delete"
        ], input="y\n")
        
        assert result.exit_code == 0
        assert "Delete instance 'confirm_delete'?" in result.stdout
        assert "Instance 'confirm_delete' deleted successfully" in result.stdout
    
    def test_delete_instance_cancel_confirmation(self, cli_runner, mock_db_session, test_db):
        """Test canceling instance deletion."""
        # Create instance
        instance = InstanceConfig(
            name="cancel_delete",
            whatsapp_instance="cancel_test",
            agent_api_url="http://cancel.com",
            agent_api_key="cancel_key",
            default_agent="cancel_agent"
        )
        test_db.add(instance)
        test_db.commit()
        
        # Cancel deletion (simulate 'n' input)
        result = cli_runner.invoke(cli_app, [
            "delete", "cancel_delete"
        ], input="n\n")
        
        assert result.exit_code == 0
        assert "Deletion cancelled" in result.stdout
        
        # Verify instance still exists
        existing = test_db.query(InstanceConfig).filter_by(name="cancel_delete").first()
        assert existing is not None
    
    def test_delete_only_instance_fails(self, cli_runner, mock_db_session, default_instance_config):
        """Test that deleting the only instance fails."""
        result = cli_runner.invoke(cli_app, [
            "delete", "default", "--force"
        ])
        
        assert result.exit_code == 1
        assert "Cannot delete the only remaining instance" in result.stdout
    
    def test_delete_instance_not_found(self, cli_runner, mock_db_session):
        """Test deleting non-existent instance."""
        result = cli_runner.invoke(cli_app, [
            "delete", "nonexistent", "--force"
        ])
        
        assert result.exit_code == 1
        assert "Instance 'nonexistent' not found" in result.stdout
    
    def test_set_default_instance(self, cli_runner, mock_db_session, test_db):
        """Test setting an instance as default."""
        # Create two instances
        instance1 = InstanceConfig(
            name="set_default1",
            whatsapp_instance="test1",
            agent_api_url="http://agent1.com",
            agent_api_key="key1",
            default_agent="agent1",
            is_default=True
        )
        instance2 = InstanceConfig(
            name="set_default2",
            whatsapp_instance="test2",
            agent_api_url="http://agent2.com",
            agent_api_key="key2",
            default_agent="agent2",
            is_default=False
        )
        test_db.add(instance1)
        test_db.add(instance2)
        test_db.commit()
        
        result = cli_runner.invoke(cli_app, ["set-default", "set_default2"])
        
        assert result.exit_code == 0
        assert "Instance 'set_default2' set as default" in result.stdout
        
        # Verify default change
        test_db.refresh(instance1)
        test_db.refresh(instance2)
        assert instance1.is_default is False
        assert instance2.is_default is True
    
    def test_set_default_instance_not_found(self, cli_runner, mock_db_session):
        """Test setting non-existent instance as default."""
        result = cli_runner.invoke(cli_app, ["set-default", "nonexistent"])
        
        assert result.exit_code == 1
        assert "Instance 'nonexistent' not found" in result.stdout
    
    def test_bootstrap_from_env(self, cli_runner, mock_db_session):
        """Test creating instance from environment variables."""
        result = cli_runner.invoke(cli_app, ["bootstrap"])
        
        assert result.exit_code == 0
        assert "Instance 'default' created from environment variables" in result.stdout
        assert "Instance 'default' set as default" in result.stdout
        
        # Verify instance was created
        instance = mock_db_session.query(InstanceConfig).filter_by(name="default").first()
        assert instance is not None
        assert instance.is_default is True
    
    def test_bootstrap_custom_name(self, cli_runner, mock_db_session):
        """Test bootstrapping with custom instance name."""
        result = cli_runner.invoke(cli_app, [
            "bootstrap",
            "--name", "custom_env",
            "--make-default", "false"
        ])
        
        assert result.exit_code == 0
        assert "Instance 'custom_env' created from environment variables" in result.stdout
        
        # Verify instance was created
        instance = mock_db_session.query(InstanceConfig).filter_by(name="custom_env").first()
        assert instance is not None
        assert instance.is_default is False


class TestCLIHelp:
    """Test CLI help and documentation."""
    
    def test_main_help(self, cli_runner):
        """Test main CLI help."""
        result = cli_runner.invoke(cli_app, ["--help"])
        
        assert result.exit_code == 0
        assert "Instance management commands" in result.stdout
    
    def test_add_command_help(self, cli_runner):
        """Test add command help."""
        result = cli_runner.invoke(cli_app, ["add", "--help"])
        
        assert result.exit_code == 0
        assert "Add a new instance configuration" in result.stdout
        assert "--whatsapp-instance" in result.stdout
        assert "--agent-api-url" in result.stdout
    
    def test_list_command_help(self, cli_runner):
        """Test list command help."""
        result = cli_runner.invoke(cli_app, ["list", "--help"])
        
        assert result.exit_code == 0
        assert "List all instance configurations" in result.stdout