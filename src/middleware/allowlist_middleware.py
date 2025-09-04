"""
Allowlist middleware for filtering incoming messages based on user allowlists.

This middleware integrates with the webhook processing pipeline to check if users
are allowed to interact with instances before processing their messages.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from src.services.allowlist_service import AllowlistService
from src.db.models import InstanceConfig

logger = logging.getLogger(__name__)


class AllowlistMiddleware:
    """Middleware for enforcing user allowlists across channels."""

    def __init__(self, db: Session):
        """Initialize middleware with database session."""
        self.db = db
        self.allowlist_service = AllowlistService(db)

    def should_process_message(
        self, instance_config: InstanceConfig, webhook_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a message should be processed based on allowlist rules.

        Args:
            instance_config: Instance configuration
            webhook_data: Raw webhook data from the channel

        Returns:
            Tuple of (should_process: bool, reason: Optional[str])
        """
        try:
            # Extract user identifier based on channel type
            user_identifier = self._extract_user_identifier(instance_config.channel_type, webhook_data)

            if not user_identifier:
                logger.warning(
                    f"Could not extract user identifier from webhook data for channel {instance_config.channel_type}"
                )
                return True, "Could not extract user identifier - allowing by default"

            # Check if user is allowed
            is_allowed = self.allowlist_service.is_user_allowed(
                instance_name=instance_config.name,
                channel_type=instance_config.channel_type,
                user_identifier=user_identifier,
            )

            if is_allowed:
                return True, None
            else:
                reason = f"User {user_identifier} not in allowlist for instance {instance_config.name}"
                logger.info(f"Message blocked: {reason}")
                return False, reason

        except Exception as e:
            logger.error(f"Error in allowlist middleware: {str(e)}")
            # Fail-safe: allow message processing on error
            return True, f"Allowlist check failed - allowing by default: {str(e)}"

    def _extract_user_identifier(self, channel_type: str, webhook_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract user identifier from webhook data based on channel type.

        Args:
            channel_type: Type of channel (whatsapp, discord, etc.)
            webhook_data: Raw webhook data

        Returns:
            User identifier string or None if not found
        """
        try:
            if channel_type == "whatsapp":
                return self._extract_whatsapp_user_id(webhook_data)
            elif channel_type == "discord":
                return self._extract_discord_user_id(webhook_data)
            else:
                logger.warning(f"Unknown channel type for user extraction: {channel_type}")
                return None

        except Exception as e:
            logger.error(f"Error extracting user identifier for {channel_type}: {str(e)}")
            return None

    def _extract_whatsapp_user_id(self, webhook_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract WhatsApp user identifier from webhook data.

        WhatsApp uses the remoteJid field as the primary identifier.
        """
        try:
            data = webhook_data.get("data", {})

            # Simple extraction - follows same pattern as other services
            remote_jid = data.get("key", {}).get("remoteJid")

            if not remote_jid:
                logger.debug(f"Could not find remoteJid in WhatsApp webhook data: {list(data.keys())}")

            return remote_jid

        except Exception as e:
            logger.error(f"Error extracting WhatsApp user ID: {str(e)}")
            return None

    def _extract_discord_user_id(self, webhook_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract Discord user identifier from webhook data.

        Discord typically uses the user ID from message author.
        """
        try:
            data = webhook_data.get("data", {})

            # Try the most common paths in order
            for path in [
                ("author", "id"),  # Message author (most common)
                ("user", "id"),  # Interaction user
                ("user_id",),  # Direct field
            ]:
                user_id = data
                for key in path:
                    if isinstance(user_id, dict):
                        user_id = user_id.get(key)
                    else:
                        user_id = None
                        break

                if user_id:
                    return str(user_id)

            logger.debug(f"Could not find user ID in Discord webhook data: {list(data.keys())}")
            return None

        except Exception as e:
            logger.error(f"Error extracting Discord user ID: {str(e)}")
            return None

    def log_blocked_message(
        self, instance_config: InstanceConfig, user_identifier: str, reason: str, webhook_data: Dict[str, Any]
    ) -> None:
        """
        Log information about a blocked message for monitoring purposes.

        Args:
            instance_config: Instance configuration
            user_identifier: User identifier that was blocked
            reason: Reason for blocking
            webhook_data: Original webhook data
        """
        try:
            # Extract basic message info for logging
            message_type = "unknown"
            message_text = "N/A"

            data = webhook_data.get("data", {})

            if instance_config.channel_type == "whatsapp":
                message_data = data.get("message", {})
                if "textMessage" in message_data:
                    message_type = "text"
                    message_text = message_data["textMessage"].get("text", "")[:100]  # Truncate
                elif "audioMessage" in message_data:
                    message_type = "audio"
                elif "imageMessage" in message_data:
                    message_type = "image"
                elif "documentMessage" in message_data:
                    message_type = "document"

            logger.info(
                f"BLOCKED MESSAGE - Instance: {instance_config.name}, "
                f"Channel: {instance_config.channel_type}, "
                f"User: {user_identifier}, "
                f"Type: {message_type}, "
                f"Reason: {reason}"
            )

            if message_text and message_text != "N/A":
                logger.debug(f"Blocked message text preview: {message_text}")

        except Exception as e:
            logger.error(f"Error logging blocked message: {str(e)}")

    def get_middleware_stats(self, instance_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about middleware activity.

        Args:
            instance_name: Optional instance name filter

        Returns:
            Dictionary with statistics
        """
        try:
            # This would typically be implemented with proper metrics collection
            # For now, return basic allowlist status
            if instance_name:
                return self.allowlist_service.get_instance_status(instance_name)
            else:
                # Return stats for all instances
                instances = self.db.query(InstanceConfig).all()
                stats = {
                    "total_instances": len(instances),
                    "instances_with_allowlist": sum(1 for i in instances if i.allowlist_enabled),
                    "instances": [],
                }

                for instance in instances:
                    try:
                        instance_stats = self.allowlist_service.get_instance_status(instance.name)
                        stats["instances"].append(instance_stats)
                    except Exception as e:
                        logger.error(f"Error getting stats for instance {instance.name}: {str(e)}")

                return stats

        except Exception as e:
            logger.error(f"Error getting middleware stats: {str(e)}")
            raise
