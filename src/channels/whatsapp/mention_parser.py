"""
WhatsApp mention parser for @phone functionality.

This module parses @phone mentions in messages and converts them to WhatsApp JID format
for use with the Evolution API mention functionality.
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger("src.channels.whatsapp.mention_parser")


class WhatsAppMentionParser:
    """Parser for @phone mentions in WhatsApp messages."""

    # Regex patterns for different phone formats
    MENTION_PATTERNS = [
        r'@(\+?\d{1,4}\s+\d{2}\s*\d{8,9})(?!\d)',  # @55 11 999999999 or @+55 11 99999999
        r'@(\+\d{8,15})(?!\d)',                         # @+5511999999999
        r'@(\d{8,15})(?!\d)',                           # @5511999999999
    ]

    @classmethod
    def extract_mentions(cls, text: str) -> Tuple[str, List[str]]:
        """
        Extract @phone mentions and return original text + mention list.

        Args:
            text: Message text containing @phone mentions

        Returns:
            tuple: (original_text, list_of_whatsapp_jids)

        Example:
            >>> text = "Hello @5511999999999 and @+5511888888888"
            >>> original, mentions = WhatsAppMentionParser.extract_mentions(text)
            >>> mentions
            ['5511999999999@s.whatsapp.net', '5511888888888@s.whatsapp.net']
        """
        mentioned_jids = []

        for pattern in cls.MENTION_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                phone = match.group(1)
                clean_phone = cls._normalize_phone(phone)
                whatsapp_jid = cls._phone_to_jid(clean_phone)
                if whatsapp_jid not in mentioned_jids:
                    mentioned_jids.append(whatsapp_jid)
                    logger.debug(f"Extracted mention: {match.group(0)} -> {whatsapp_jid}")

        if mentioned_jids:
            logger.info(f"Extracted {len(mentioned_jids)} mentions from text")

        return text, mentioned_jids

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """
        Normalize phone number to international format.

        Args:
            phone: Raw phone number from @mention

        Returns:
            str: Normalized phone number with + prefix
        """
        # Remove spaces and formatting
        clean = re.sub(r'[^\d+]', '', phone)

        # Ensure + prefix
        if not clean.startswith('+'):
            clean = f'+{clean}'

        # Handle Brazilian numbers (if no country code, assume Brazil)
        # This is a common pattern - adjust for your region
        if len(clean) <= 12 and not clean.startswith('+55'):
            # If it's a short number without country code, add Brazil +55
            clean = f'+55{clean.lstrip("+")}'

        logger.debug(f"Normalized phone: {phone} -> {clean}")
        return clean

    @staticmethod
    def _phone_to_jid(phone: str) -> str:
        """
        Convert phone number to WhatsApp JID format.

        Args:
            phone: Normalized phone number (e.g., "+5511999999999")

        Returns:
            str: WhatsApp JID format (e.g., "5511999999999@s.whatsapp.net")
        """
        # Remove + sign for JID format
        number_only = phone.lstrip('+')
        jid = f"{number_only}@s.whatsapp.net"
        logger.debug(f"Converted to JID: {phone} -> {jid}")
        return jid

    @classmethod
    def parse_explicit_mentions(cls, phone_list: List[str]) -> List[str]:
        """
        Convert a list of phone numbers to WhatsApp JID format.

        Args:
            phone_list: List of phone numbers in various formats

        Returns:
            List[str]: List of WhatsApp JIDs
        """
        jids = []
        for phone in phone_list:
            clean_phone = cls._normalize_phone(phone)
            jid = cls._phone_to_jid(clean_phone)
            if jid not in jids:
                jids.append(jid)

        logger.info(f"Converted {len(phone_list)} explicit mentions to {len(jids)} JIDs")
        return jids


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_messages = [
        "Hello @5511999999999, how are you?",
        "Meeting with @+5511888888888 and @5511777777777",
        "Contact @55 11 999999999 for details",
        "No mentions in this message",
        "@5511111111111 @5511222222222 @5511333333333",
    ]

    parser = WhatsAppMentionParser()

    for message in test_messages:
        print(f"\nMessage: {message}")
        original, mentions = parser.extract_mentions(message)
        print(f"Mentions: {mentions}")
