#!/usr/bin/env python3
"""
Test message filtering functionality with actual webhook simulation.
"""

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.db.database import SessionLocal
from src.services.allowlist_service import AllowlistService
from src.middleware.allowlist_middleware import AllowlistMiddleware
from src.db.models import InstanceConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def simulate_webhook_test():
    """Simulate a real webhook message filtering scenario."""
    print("🧪 TESTING MESSAGE FILTERING WITH WEBHOOK SIMULATION")
    print("=" * 60)

    try:
        with SessionLocal() as db:
            # Get the jack instance (mentioned in context)
            instance = db.query(InstanceConfig).filter(InstanceConfig.name == "jack").first()
            if not instance:
                print("❌ Jack instance not found, using first available instance")
                instance = db.query(InstanceConfig).first()
                if not instance:
                    print("❌ No instances found")
                    return False

            print(f"🧪 Testing with instance: {instance.name}")
            print(f"📊 Allowlist enabled: {instance.allowlist_enabled}")

            # Create services
            service = AllowlistService(db)
            middleware = AllowlistMiddleware(db)

            # Test WhatsApp message from allowed user
            whatsapp_webhook_allowed = {
                "data": {
                    "key": {
                        "remoteJid": "5511999999999@s.whatsapp.net"
                    },
                    "message": {
                        "textMessage": {
                            "text": "Hello from allowed user"
                        }
                    },
                    "instance": {
                        "name": instance.name
                    }
                }
            }

            print("\n📱 Testing WhatsApp message from allowed user...")
            should_process, reason = middleware.should_process_message(instance, whatsapp_webhook_allowed)
            print(f"   Result: {should_process}, Reason: {reason}")

            # Test WhatsApp message from blocked user
            whatsapp_webhook_blocked = {
                "data": {
                    "key": {
                        "remoteJid": "5511888888888@s.whatsapp.net"
                    },
                    "message": {
                        "textMessage": {
                            "text": "Hello from blocked user"
                        }
                    },
                    "instance": {
                        "name": instance.name
                    }
                }
            }

            print("\n🚫 Testing WhatsApp message from blocked user...")
            should_process, reason = middleware.should_process_message(instance, whatsapp_webhook_blocked)
            print(f"   Result: {should_process}, Reason: {reason}")

            # Test with malformed webhook data
            malformed_webhook = {
                "data": {
                    "invalid_structure": True
                }
            }

            print("\n🔍 Testing malformed webhook data...")
            should_process, reason = middleware.should_process_message(instance, malformed_webhook)
            print(f"   Result: {should_process}, Reason: {reason}")

            # Test with allowlist disabled
            print("\n⚙️ Testing with allowlist disabled...")
            original_state = instance.allowlist_enabled
            service.disable_allowlist(instance.name)

            should_process, reason = middleware.should_process_message(instance, whatsapp_webhook_blocked)
            print(f"   Result (disabled): {should_process}, Reason: {reason}")

            # Restore original state
            if original_state:
                service.enable_allowlist(instance.name)

            print("\n✅ Message filtering simulation completed")
            return True

    except Exception as e:
        logger.exception("Test failed with exception:")
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    simulate_webhook_test()
