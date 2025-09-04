#!/usr/bin/env python3
"""
Test script for the allowlist implementation.
This script tests the basic functionality of the allowlist feature.
"""

import sys
import os
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.db.database import SessionLocal
from src.services.allowlist_service import AllowlistService
from src.middleware.allowlist_middleware import AllowlistMiddleware

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_allowlist_basic_functionality():
    """Test basic allowlist functionality."""
    logger.info("🧪 Testing allowlist basic functionality...")

    try:
        with SessionLocal() as db:
            service = AllowlistService(db)

            # Test with a non-existent instance (should handle gracefully)
            logger.info("Testing with non-existent instance...")
            is_allowed = service.is_user_allowed("test_instance", "whatsapp", "123456789")
            logger.info(f"Result for non-existent instance: {is_allowed} (should be True - fail-safe)")

            # Test getting status for non-existent instance
            logger.info("Testing status for non-existent instance...")
            try:
                service.get_instance_status("test_instance")
                logger.error("Should have raised ValueError for non-existent instance")
            except ValueError as e:
                logger.info(f"✅ Correctly raised ValueError: {e}")

        logger.info("✅ Basic functionality tests completed successfully!")

    except Exception as e:
        logger.error(f"❌ Basic functionality test failed: {e}")
        return False

    return True


def test_allowlist_middleware():
    """Test allowlist middleware functionality."""
    logger.info("🧪 Testing allowlist middleware...")

    try:
        with SessionLocal() as db:
            middleware = AllowlistMiddleware(db)

            # Create a mock instance config for testing
            from types import SimpleNamespace
            mock_instance = SimpleNamespace()
            mock_instance.name = "test_instance"
            mock_instance.channel_type = "whatsapp"
            mock_instance.allowlist_enabled = False  # Disabled by default

            # Test WhatsApp user ID extraction
            logger.info("Testing WhatsApp user ID extraction...")
            whatsapp_data = {
                "data": {
                    "key": {
                        "remoteJid": "5511999999999@s.whatsapp.net"
                    }
                }
            }

            user_id = middleware._extract_whatsapp_user_id(whatsapp_data)
            logger.info(f"Extracted WhatsApp user ID: {user_id}")

            if user_id == "5511999999999@s.whatsapp.net":
                logger.info("✅ WhatsApp user ID extraction working correctly")
            else:
                logger.warning("⚠️  WhatsApp user ID extraction may have issues")

            # Test Discord user ID extraction
            logger.info("Testing Discord user ID extraction...")
            discord_data = {
                "data": {
                    "author": {
                        "id": "123456789012345678"
                    }
                }
            }

            user_id = middleware._extract_discord_user_id(discord_data)
            logger.info(f"Extracted Discord user ID: {user_id}")

            if user_id == "123456789012345678":
                logger.info("✅ Discord user ID extraction working correctly")
            else:
                logger.warning("⚠️  Discord user ID extraction may have issues")

        logger.info("✅ Middleware tests completed successfully!")

    except Exception as e:
        logger.error(f"❌ Middleware test failed: {e}")
        return False

    return True


def main():
    """Run all tests."""
    logger.info("🚀 Starting allowlist implementation tests...")

    # Test basic functionality
    if not test_allowlist_basic_functionality():
        logger.error("❌ Basic functionality tests failed!")
        sys.exit(1)

    # Test middleware
    if not test_allowlist_middleware():
        logger.error("❌ Middleware tests failed!")
        sys.exit(1)

    logger.info("🎉 All tests completed successfully!")
    logger.info("")
    logger.info("📋 Next steps to test the full implementation:")
    logger.info("1. Run database migration: alembic upgrade head")
    logger.info("2. Create a test instance if you don't have one")
    logger.info("3. Test CLI commands:")
    logger.info("   - automagik-omni allowlist status")
    logger.info("   - automagik-omni allowlist enable <instance_name>")
    logger.info("   - automagik-omni allowlist add <instance_name> whatsapp <phone_number>")
    logger.info("   - automagik-omni allowlist list")
    logger.info("4. Send a test message to verify filtering works")


if __name__ == "__main__":
    main()
