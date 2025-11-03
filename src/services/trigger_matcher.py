"""Service for determining if agent should respond based on trigger configuration."""

import json
import logging
from typing import Any, Dict, Optional

from src.db.models import InstanceConfig

logger = logging.getLogger(__name__)


class TriggerMatcher:
    """
    Determines if an agent should respond to a message based on instance trigger configuration.

    Supports keyword matching plus mention detection across WhatsApp and Discord.
    """

    def should_respond(
        self,
        message_text: str,
        instance_config: Optional[InstanceConfig] = None,
        channel_payload: Optional[Dict[str, Any]] = None,
        channel_type: str = "whatsapp",
        channel_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Determine if agent should respond based on trigger configuration.

        Args:
            message_text: The message text to check
            instance_config: Instance configuration (optional, fails open if missing)
            channel_payload: Raw channel payload (WhatsApp only)
            channel_type: Channel type ("whatsapp" or "discord")
            channel_metadata: Additional channel metadata (Discord mentions, DM status, bot ID)
                Expected Discord metadata format:
                {
                    "mentions": [{"id": "123", "username": "bot"}],  # List of mentioned users
                    "is_dm": False,  # Whether this is a direct message
                    "bot_id": "123456",  # Bot's user ID for comparison
                    "guild_id": "789"  # Guild ID (None for DMs)
                }

        Returns:
            True if agent should respond, False to suppress response
        """
        # Fail open if no instance config available (backward compatibility)
        if not instance_config:
            logger.warning(
                "TriggerMatcher.should_respond called without instance_config - "
                "failing open (responding). This may indicate an older test or "
                "direct router invocation that needs updating."
            )
            return True

        keyword_match = self._check_keywords(message_text, instance_config)
        mention_match = self._check_mention(instance_config, channel_payload, channel_type, channel_metadata)

        if keyword_match:
            logger.info("Trigger matched via keyword")
            return True
        if mention_match:
            logger.info("Trigger matched via mention")
            return True

        logger.info("Trigger conditions not met (no keyword or mention)")
        return False

    def _check_keywords(self, message_text: str, instance_config: InstanceConfig) -> bool:
        """Check if message contains any configured keywords."""
        if not instance_config.trigger_keywords:
            logger.info("No trigger keywords configured - fallback to mention-only behavior")
            return False

        try:
            keywords = json.loads(instance_config.trigger_keywords)
            if not isinstance(keywords, list):
                logger.error("trigger_keywords is not a list - ignoring keyword matches")
                return False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse trigger_keywords JSON: {e} - ignoring keyword matches")
            return False

        search_text = message_text.lower()

        # Check each keyword
        for keyword in keywords:
            if not isinstance(keyword, str):
                continue
            search_keyword = keyword.lower().strip()
            if not search_keyword:
                continue
            if search_keyword in search_text:
                logger.info(f"Trigger keyword matched: '{keyword}'")
                return True

        logger.info("No trigger keywords matched")
        return False

    def _check_mention(
        self,
        instance_config: InstanceConfig,
        channel_payload: Optional[Dict[str, Any]],
        channel_type: str,
        channel_metadata: Optional[Dict[str, Any]],
    ) -> bool:
        """Check if instance was mentioned in the message."""
        if channel_type == "whatsapp":
            return self._check_whatsapp_mention(instance_config, channel_payload)
        elif channel_type == "discord":
            return self._check_discord_mention(instance_config, channel_metadata)
        else:
            logger.warning(f"Unknown channel_type '{channel_type}' for mention check - failing open")
            return True

    def _check_whatsapp_mention(
        self, instance_config: InstanceConfig, channel_payload: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if instance was mentioned in WhatsApp message."""
        if not channel_payload:
            logger.warning("No channel_payload provided for WhatsApp mention check - failing open")
            return True

        try:
            # Extract message data
            data = channel_payload.get("data", {})
            if not isinstance(data, dict):
                logger.warning("WhatsApp payload 'data' is not a dict - failing open")
                return True

            # Check if this is a DM (triggers are ignored in DMs; keep existing behavior)
            # DM detection: message from/to owner without group context
            is_group = data.get("key", {}).get("remoteJid", "").endswith("@g.us")
            if not is_group:
                logger.info("WhatsApp DM detected - triggers bypassed (responding)")
                return True

            # Extract mentioned JIDs from group message
            message_obj = data.get("message", {})
            extended_text = message_obj.get("extendedTextMessage", {})
            context_info = extended_text.get("contextInfo", {})
            mentioned_jids = context_info.get("mentionedJid", [])

            if not isinstance(mentioned_jids, list):
                logger.warning("mentionedJid is not a list - failing open")
                return True

            # Check if owner_jid is mentioned
            owner_jid = instance_config.owner_jid
            if not owner_jid:
                logger.warning(
                    "No owner_jid configured for instance - cannot check mentions, defaulting to keyword-only behavior"
                )
                return False

            is_mentioned = owner_jid in mentioned_jids
            if is_mentioned:
                logger.info(f"WhatsApp instance mentioned: {owner_jid}")
            else:
                logger.info(f"WhatsApp instance NOT mentioned (owner_jid: {owner_jid})")

            return is_mentioned

        except Exception as e:
            logger.error(f"Error checking WhatsApp mention: {e} - failing open", exc_info=True)
            return True

    def _check_discord_mention(
        self, instance_config: InstanceConfig, channel_metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if instance was mentioned in Discord message."""
        if not channel_metadata:
            logger.warning("No channel_metadata provided for Discord mention check - failing open")
            return True

        try:
            # DMs keep existing behavior (triggers ignored)
            is_dm = channel_metadata.get("is_dm", False)
            if is_dm:
                logger.info("Discord DM detected - triggers bypassed (responding)")
                return True

            # Extract mentions and bot ID
            mentions = channel_metadata.get("mentions", [])
            bot_id = channel_metadata.get("bot_id")

            if not bot_id:
                logger.warning(
                    "No bot_id in Discord metadata - cannot check mentions, defaulting to keyword-only behavior"
                )
                return False

            if not isinstance(mentions, list):
                logger.warning("Discord mentions is not a list - failing open")
                return True

            # Check if bot is mentioned
            bot_id_str = str(bot_id)
            is_mentioned = any(str(m.get("id")) == bot_id_str for m in mentions if isinstance(m, dict))

            if is_mentioned:
                logger.info(f"Discord bot mentioned: {bot_id}")
            else:
                logger.info(f"Discord bot NOT mentioned (bot_id: {bot_id})")

            return is_mentioned

        except Exception as e:
            logger.error(f"Error checking Discord mention: {e} - failing open", exc_info=True)
            return True


# Singleton instance
trigger_matcher = TriggerMatcher()
