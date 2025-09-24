"""
Comprehensive access control validation tests.

Tests both the service layer and API endpoints with real API calls.
Validates message filtering works correctly with existing WhatsApp instance.
"""

import pytest
import requests
from unittest.mock import patch
from sqlalchemy.orm import Session

from src.db.models import AccessRule, AccessRuleType, InstanceConfig
from src.services.access_control import AccessControlService, access_control_service
from src.services.message_router import MessageRouter


class TestAccessControlService:
    """Test the AccessControlService class directly."""

    def test_service_initialization(self, test_db: Session):
        """Test service can be initialized."""
        service = AccessControlService()
        assert service is not None
        assert not service._cache_loaded

    def test_load_rules_empty_database(self, test_db: Session):
        """Test loading rules from empty database."""
        service = AccessControlService()
        service.load_rules(test_db)
        assert service._cache_loaded
        assert service._cache == {}

    def test_add_global_allow_rule(self, test_db: Session):
        """Test adding a global allow rule."""
        service = AccessControlService()

        rule = service.add_rule(
            phone_number="+1234567890", rule_type=AccessRuleType.ALLOW, instance_name=None, db=test_db
        )

        assert rule.id is not None
        assert rule.phone_number == "+1234567890"
        assert rule.rule_type == "allow"
        assert rule.instance_name is None

    def test_add_instance_block_rule(self, test_db: Session):
        """Test adding an instance-scoped block rule."""
        # Create test instance first
        instance = InstanceConfig(
            name="test-instance",
            channel_type="whatsapp",
            evolution_url="http://test.com",
            evolution_key="test-key",
            whatsapp_instance="test",
            agent_api_url="http://agent.com",
            agent_api_key="key",
            default_agent="agent",
            is_default=False,
        )
        test_db.add(instance)
        test_db.commit()

        service = AccessControlService()

        rule = service.add_rule(
            phone_number="+1234567890", rule_type=AccessRuleType.BLOCK, instance_name="test-instance", db=test_db
        )

        assert rule.id is not None
        assert rule.phone_number == "+1234567890"
        assert rule.rule_type == "block"
        assert rule.instance_name == "test-instance"

    def test_add_wildcard_rule(self, test_db: Session):
        """Test adding wildcard pattern rules."""
        service = AccessControlService()

        rule = service.add_rule(phone_number="+1234*", rule_type=AccessRuleType.BLOCK, instance_name=None, db=test_db)

        assert rule.phone_number == "+1234*"
        assert rule.rule_type == "block"

    def test_check_access_no_rules_allows_all(self, test_db: Session):
        """Test that when no rules exist, access is allowed (backward compatibility)."""
        service = AccessControlService()
        service.load_rules(test_db)

        # Any phone number should be allowed when no rules exist
        assert service.check_access("+1234567890") is True
        assert service.check_access("+9876543210") is True
        assert service.check_access("+1111111111", "any-instance") is True

    def test_check_access_exact_match(self, test_db: Session):
        """Test exact phone number matching."""
        service = AccessControlService()

        # Add a block rule
        service.add_rule("+1234567890", AccessRuleType.BLOCK, db=test_db)

        # Blocked number should be denied
        assert service.check_access("+1234567890") is False

        # Other numbers should be allowed
        assert service.check_access("+1234567891") is True
        assert service.check_access("+9876543210") is True

    def test_check_access_wildcard_pattern(self, test_db: Session):
        """Test wildcard pattern matching."""
        service = AccessControlService()

        # Add wildcard block rule
        service.add_rule("+1234*", AccessRuleType.BLOCK, db=test_db)

        # Numbers matching the pattern should be blocked
        assert service.check_access("+1234567890") is False
        assert service.check_access("+1234000000") is False
        assert service.check_access("+1234999999") is False

        # Numbers not matching should be allowed
        assert service.check_access("+1235567890") is True
        assert service.check_access("+9876543210") is True

    def test_check_access_allow_wins_ties(self, test_db: Session):
        """Test that allow rules win when both allow and block rules match with same specificity."""
        service = AccessControlService()

        # Add both allow and block rules for same number
        service.add_rule("+1234567890", AccessRuleType.BLOCK, db=test_db)
        service.add_rule("+1234567890", AccessRuleType.ALLOW, db=test_db)

        # Allow should win the tie
        assert service.check_access("+1234567890") is True

    def test_check_access_specificity_precedence(self, test_db: Session):
        """Test that more specific rules take precedence."""
        service = AccessControlService()

        # Add wildcard block rule and specific allow rule
        service.add_rule("+1234*", AccessRuleType.BLOCK, db=test_db)
        service.add_rule("+1234567890", AccessRuleType.ALLOW, db=test_db)

        # Specific allow should override wildcard block
        assert service.check_access("+1234567890") is True

        # Other numbers in wildcard should still be blocked
        assert service.check_access("+1234000000") is False

    def test_check_access_instance_scoping(self, test_db: Session):
        """Test that instance-scoped rules work correctly."""
        # Create test instance
        instance = InstanceConfig(
            name="test-instance",
            channel_type="whatsapp",
            evolution_url="http://test.com",
            evolution_key="test-key",
            whatsapp_instance="test",
            agent_api_url="http://agent.com",
            agent_api_key="key",
            default_agent="agent",
            is_default=False,
        )
        test_db.add(instance)
        test_db.commit()

        service = AccessControlService()

        # Test case: instance-specific rule with different specificity
        # Add global wildcard block and instance-specific allow
        service.add_rule("+1234*", AccessRuleType.BLOCK, instance_name=None, db=test_db)
        service.add_rule("+1234567890", AccessRuleType.ALLOW, instance_name="test-instance", db=test_db)

        # Global context should block (wildcard rule)
        assert service.check_access("+1234567890") is False

        # Instance context should allow (more specific instance rule wins)
        assert service.check_access("+1234567890", "test-instance") is True

    def test_remove_rule(self, test_db: Session):
        """Test removing rules and cache updates."""
        service = AccessControlService()

        # Add a rule
        rule = service.add_rule("+1234567890", AccessRuleType.BLOCK, db=test_db)

        # Verify it blocks
        assert service.check_access("+1234567890") is False

        # Remove the rule
        removed = service.remove_rule(rule.id, db=test_db)
        assert removed is True

        # Should now allow
        assert service.check_access("+1234567890") is True

    def test_remove_nonexistent_rule(self, test_db: Session):
        """Test removing non-existent rule returns False."""
        service = AccessControlService()

        removed = service.remove_rule(99999, db=test_db)
        assert removed is False


class TestAccessControlAPI:
    """Test access control via API endpoints."""

    API_BASE = "http://localhost:28882/api/v1"
    API_HEADERS = {"x-api-key": "namastex888", "Content-Type": "application/json"}

    def test_api_connectivity(self):
        """Test basic API connectivity."""
        try:
            response = requests.get("http://localhost:28882/health", timeout=5)
            assert response.status_code == 200
            health_data = response.json()
            assert health_data["status"] == "healthy"
        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not available at {self.API_BASE}: {e}")

    def test_list_access_rules_empty(self):
        """Test listing access rules when none exist."""
        try:
            response = requests.get(f"{self.API_BASE}/access/rules", headers=self.API_HEADERS)

            if response.status_code == 404:
                pytest.skip("Access API endpoints not available (route not found)")

            assert response.status_code == 200
            rules = response.json()
            # Should return empty list or existing rules
            assert isinstance(rules, list)

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API access test failed: {e}")

    def test_create_and_list_access_rule(self):
        """Test creating and listing access rules via API."""
        try:
            # Create a rule
            rule_data = {"phone_number": "+1234567890", "rule_type": "block", "instance_name": None}

            response = requests.post(f"{self.API_BASE}/access/rules", headers=self.API_HEADERS, json=rule_data)

            if response.status_code == 404:
                pytest.skip("Access API endpoints not available")

            assert response.status_code == 201
            created_rule = response.json()
            assert created_rule["phone_number"] == "+1234567890"
            assert created_rule["rule_type"] == "block"

            # List rules to verify it's there
            response = requests.get(f"{self.API_BASE}/access/rules", headers=self.API_HEADERS)
            assert response.status_code == 200
            rules = response.json()

            # Find our rule
            our_rule = next((r for r in rules if r["phone_number"] == "+1234567890"), None)
            assert our_rule is not None
            assert our_rule["rule_type"] == "block"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API access test failed: {e}")

    def test_delete_access_rule(self):
        """Test deleting access rules via API."""
        try:
            # First create a rule
            rule_data = {"phone_number": "+9999999999", "rule_type": "allow"}

            response = requests.post(f"{self.API_BASE}/access/rules", headers=self.API_HEADERS, json=rule_data)

            if response.status_code == 404:
                pytest.skip("Access API endpoints not available")

            assert response.status_code == 201
            created_rule = response.json()
            rule_id = created_rule["id"]

            # Delete the rule
            response = requests.delete(f"{self.API_BASE}/access/rules/{rule_id}", headers=self.API_HEADERS)
            assert response.status_code == 204

            # Verify it's gone by listing rules
            response = requests.get(f"{self.API_BASE}/access/rules", headers=self.API_HEADERS)
            assert response.status_code == 200
            rules = response.json()

            # Should not find our deleted rule
            our_rule = next((r for r in rules if r["id"] == rule_id), None)
            assert our_rule is None

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API access test failed: {e}")


class TestMessageRouterIntegration:
    """Test access control integration with message routing."""

    def test_message_router_access_check_allow(self):
        """Test message router allows when no blocking rules exist."""
        router = MessageRouter()

        # Mock the access control service to always allow
        with patch.object(access_control_service, "check_access", return_value=True):
            with patch("src.services.message_router.agent_api_client") as mock_client:
                mock_client.process_message.return_value = "Response from agent"

                response = router.route_message(
                    message_text="Hello", user={"phone_number": "+1234567890"}, session_name="test-session"
                )

                # Should not be blocked
                assert response != "AUTOMAGIK:ACCESS_DENIED"

    def test_message_router_access_check_block(self):
        """Test message router blocks when blocking rules exist."""
        router = MessageRouter()

        # Mock the access control service to block
        with patch.object(access_control_service, "check_access", return_value=False):
            response = router.route_message(
                message_text="Hello", user={"phone_number": "+1234567890"}, session_name="test-session"
            )

            # Should be blocked with special sentinel
            assert response == "AUTOMAGIK:ACCESS_DENIED"

    def test_message_router_whatsapp_jid_extraction(self):
        """Test phone number extraction from WhatsApp JID format."""
        router = MessageRouter()

        # Mock WhatsApp payload with remoteJid
        whatsapp_payload = {"data": {"key": {"remoteJid": "5511999999999@s.whatsapp.net"}}}

        with patch.object(access_control_service, "check_access") as mock_check:
            mock_check.return_value = True

            with patch("src.services.message_router.agent_api_client") as mock_client:
                mock_client.process_message.return_value = "Response"

                router.route_message(
                    message_text="Hello", whatsapp_raw_payload=whatsapp_payload, session_name="test-session"
                )

                # Verify check_access was called with normalized phone number
                mock_check.assert_called_once()
                call_args = mock_check.call_args[0]
                assert call_args[0] == "+5511999999999"  # Normalized E164 format

    def test_message_router_no_phone_defaults_allow(self):
        """Test message router allows when no phone number is available."""
        router = MessageRouter()

        with patch.object(access_control_service, "check_access") as mock_check:
            with patch("src.services.message_router.agent_api_client") as mock_client:
                mock_client.process_message.return_value = "Response"

                response = router.route_message(message_text="Hello", session_name="test-session")

                # Should not call access control when no phone available
                mock_check.assert_not_called()

                # Should not be blocked
                assert response != "AUTOMAGIK:ACCESS_DENIED"

    def test_message_router_access_control_error_allows(self):
        """Test message router allows when access control throws error."""
        router = MessageRouter()

        # Mock the access control service to throw an error
        with patch.object(access_control_service, "check_access", side_effect=Exception("Database error")):
            with patch("src.services.message_router.agent_api_client") as mock_client:
                mock_client.process_message.return_value = "Response"

                response = router.route_message(
                    message_text="Hello", user={"phone_number": "+1234567890"}, session_name="test-session"
                )

                # Should not be blocked (fail open)
                assert response != "AUTOMAGIK:ACCESS_DENIED"


class TestAccessControlEdgeCases:
    """Test edge cases and error conditions."""

    def test_wildcard_patterns_complex(self, test_db: Session):
        """Test complex wildcard pattern scenarios."""
        service = AccessControlService()

        # Add multiple overlapping patterns
        service.add_rule("+1*", AccessRuleType.BLOCK, db=test_db)
        service.add_rule("+123*", AccessRuleType.ALLOW, db=test_db)
        service.add_rule("+1234567890", AccessRuleType.BLOCK, db=test_db)

        # Most specific should win
        assert service.check_access("+1234567890") is False  # Exact block wins
        assert service.check_access("+1234567891") is True  # +123* allow wins over +1* block
        assert service.check_access("+1999999999") is False  # +1* block wins

    def test_phone_number_normalization(self, test_db: Session):
        """Test phone number string handling."""
        service = AccessControlService()

        # Add rule with spaces (should be stripped)
        service.add_rule("  +1234567890  ", AccessRuleType.BLOCK, db=test_db)

        # Check with various formats
        assert service.check_access("+1234567890") is False
        assert service.check_access("  +1234567890  ") is False

    def test_empty_phone_number_handling(self, test_db: Session):
        """Test handling of empty/invalid phone numbers."""
        service = AccessControlService()

        # Should not crash with empty phone numbers
        assert service.check_access("", db=test_db) is True
        assert service.check_access("   ", db=test_db) is True

    def test_rule_type_string_conversion(self, test_db: Session):
        """Test rule type string conversion."""
        service = AccessControlService()

        # Should accept string rule types
        rule = service.add_rule("+1234567890", "block", db=test_db)
        assert rule.rule_type == "block"

        rule2 = service.add_rule("+1234567891", "allow", db=test_db)
        assert rule2.rule_type == "allow"

    def test_cache_persistence_across_operations(self, test_db: Session):
        """Test that cache remains consistent across multiple operations."""
        service = AccessControlService()

        # Load rules to ensure clean state
        service.load_rules(test_db)

        # Initial state - should be allowed when no rules exist
        assert service.check_access("+1234567890") is True

        # Add rule
        service.add_rule("+1234567890", AccessRuleType.BLOCK, db=test_db)
        assert service.check_access("+1234567890") is False

        # Add another rule
        service.add_rule("+1234567891", AccessRuleType.BLOCK, db=test_db)
        assert service.check_access("+1234567891") is False
        assert service.check_access("+1234567890") is False  # Still blocked

        # Remove first rule
        rules = test_db.query(AccessRule).filter(AccessRule.phone_number == "+1234567890").all()
        service.remove_rule(rules[0].id, db=test_db)

        assert service.check_access("+1234567890") is True  # Now allowed
        assert service.check_access("+1234567891") is False  # Still blocked


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_customer_support_whitelist(self, test_db: Session):
        """Test scenario: customer support team with allowed numbers."""
        service = AccessControlService()

        # Block all international calls except support team
        service.add_rule("+1*", AccessRuleType.BLOCK, db=test_db)
        service.add_rule("+12345*", AccessRuleType.ALLOW, db=test_db)  # Support team prefix
        service.add_rule("+1234567890", AccessRuleType.ALLOW, db=test_db)  # Manager direct line

        # Test scenarios
        assert service.check_access("+19999999999") is False  # Random US number blocked
        assert service.check_access("+12345123456") is True  # Support team allowed
        assert service.check_access("+1234567890") is True  # Manager allowed
        assert service.check_access("+447123456789") is True  # International allowed (no rule)

    def test_spam_protection_blacklist(self, test_db: Session):
        """Test scenario: spam protection with known bad numbers."""
        service = AccessControlService()

        # Block known spam ranges
        service.add_rule("+1800*", AccessRuleType.BLOCK, db=test_db)  # Toll-free spam
        service.add_rule("+1900*", AccessRuleType.BLOCK, db=test_db)  # Premium rate
        service.add_rule("+15551234567", AccessRuleType.BLOCK, db=test_db)  # Specific spammer

        # Allow legitimate toll-free
        service.add_rule("+18005551212", AccessRuleType.ALLOW, db=test_db)  # Directory assistance

        # Test scenarios
        assert service.check_access("+18001234567") is False  # Toll-free spam blocked
        assert service.check_access("+19001234567") is False  # Premium rate blocked
        assert service.check_access("+18005551212") is True  # Legitimate toll-free allowed
        assert service.check_access("+15551234567") is False  # Specific spammer blocked
        assert service.check_access("+15551234568") is True  # Similar but not blocked

    def test_instance_isolation(self, test_db: Session):
        """Test scenario: different rules for different instances."""
        # Create test instances
        prod_instance = InstanceConfig(
            name="production",
            channel_type="whatsapp",
            evolution_url="http://prod.com",
            evolution_key="prod-key",
            whatsapp_instance="prod",
            agent_api_url="http://agent.com",
            agent_api_key="key",
            default_agent="agent",
            is_default=False,
        )
        test_instance = InstanceConfig(
            name="testing",
            channel_type="whatsapp",
            evolution_url="http://test.com",
            evolution_key="test-key",
            whatsapp_instance="test",
            agent_api_url="http://agent.com",
            agent_api_key="key",
            default_agent="agent",
            is_default=False,
        )
        test_db.add(prod_instance)
        test_db.add(test_instance)
        test_db.commit()

        service = AccessControlService()

        # Production: strict rules
        service.add_rule("+1555*", AccessRuleType.BLOCK, instance_name="production", db=test_db)

        # Testing: allow internal test numbers
        service.add_rule("+15551234567", AccessRuleType.ALLOW, instance_name="testing", db=test_db)

        # Test number behavior differs by instance
        test_number = "+15551234567"

        # Global context (no instance rules apply)
        assert service.check_access(test_number) is True

        # Production context (blocked by wildcard)
        assert service.check_access(test_number, "production") is False

        # Testing context (explicitly allowed)
        assert service.check_access(test_number, "testing") is True
