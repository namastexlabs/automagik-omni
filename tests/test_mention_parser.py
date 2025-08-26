"""
Unit tests for WhatsApp mention parser functionality.
"""

import pytest
from typing import List

from src.channels.whatsapp.mention_parser import WhatsAppMentionParser


class TestWhatsAppMentionParser:
    """Test suite for WhatsApp mention parser."""

    def test_extract_mentions_basic_format(self):
        """Test basic @phone format without country code."""
        text = "Hello @5511999999999, how are you?"
        original, mentions = WhatsAppMentionParser.extract_mentions(text)
        
        assert original == text
        assert len(mentions) == 1
        assert mentions[0] == "5511999999999@s.whatsapp.net"

    def test_extract_mentions_international_format(self):
        """Test @+phone format with country code."""
        text = "Contact @+5511888888888 for details"
        original, mentions = WhatsAppMentionParser.extract_mentions(text)
        
        assert original == text  
        assert len(mentions) == 1
        assert mentions[0] == "5511888888888@s.whatsapp.net"

    def test_extract_mentions_space_format(self):
        """Test @phone format with spaces."""
        text = "Meeting with @55 11 999999999 at 3pm"
        original, mentions = WhatsAppMentionParser.extract_mentions(text)
        
        assert original == text
        assert len(mentions) == 1
        assert mentions[0] == "5511999999999@s.whatsapp.net"

    def test_extract_mentions_international_space_format(self):
        """Test @+phone format with spaces."""
        text = "Call @+55 11 888888888 tomorrow"
        original, mentions = WhatsAppMentionParser.extract_mentions(text)
        
        assert original == text
        assert len(mentions) == 1
        assert mentions[0] == "5511888888888@s.whatsapp.net"

    def test_extract_mentions_multiple_mentions(self):
        """Test multiple mentions in one message."""
        text = "Meeting with @5511999999999 and @+5511888888888 at 3pm"
        original, mentions = WhatsAppMentionParser.extract_mentions(text)
        
        assert original == text
        assert len(mentions) == 2
        assert "5511999999999@s.whatsapp.net" in mentions
        assert "5511888888888@s.whatsapp.net" in mentions

    def test_extract_mentions_no_mentions(self):
        """Test text without any mentions."""
        text = "This is a normal message without mentions"
        original, mentions = WhatsAppMentionParser.extract_mentions(text)
        
        assert original == text
        assert len(mentions) == 0

    def test_extract_mentions_duplicate_mentions(self):
        """Test that duplicate mentions are deduplicated."""
        text = "Contact @5511999999999 or @5511999999999 for help"
        original, mentions = WhatsAppMentionParser.extract_mentions(text)
        
        assert original == text
        assert len(mentions) == 1
        assert mentions[0] == "5511999999999@s.whatsapp.net"

    def test_extract_mentions_invalid_format(self):
        """Test that invalid @formats are ignored."""
        text = "Email me at user@domain.com or contact @support"
        original, mentions = WhatsAppMentionParser.extract_mentions(text)
        
        assert original == text
        assert len(mentions) == 0

    def test_extract_mentions_mixed_valid_invalid(self):
        """Test mixed valid and invalid mentions."""
        text = "Contact @5511999999999 or email user@domain.com"
        original, mentions = WhatsAppMentionParser.extract_mentions(text)
        
        assert original == text
        assert len(mentions) == 1
        assert mentions[0] == "5511999999999@s.whatsapp.net"

    def test_normalize_phone_basic(self):
        """Test phone number normalization."""
        phone = "5511999999999"
        normalized = WhatsAppMentionParser._normalize_phone(phone)
        assert normalized == "+5511999999999"

    def test_normalize_phone_with_plus(self):
        """Test phone number already with plus."""
        phone = "+5511999999999"  
        normalized = WhatsAppMentionParser._normalize_phone(phone)
        assert normalized == "+5511999999999"

    def test_normalize_phone_with_spaces(self):
        """Test phone number with spaces."""
        phone = "55 11 999999999"
        normalized = WhatsAppMentionParser._normalize_phone(phone)
        assert normalized == "+5511999999999"

    def test_normalize_phone_short_number(self):
        """Test short number gets Brazil country code."""
        phone = "11999999999"
        normalized = WhatsAppMentionParser._normalize_phone(phone)
        assert normalized == "+5511999999999"

    def test_phone_to_jid_conversion(self):
        """Test phone to WhatsApp JID conversion."""
        phone = "+5511999999999"
        jid = WhatsAppMentionParser._phone_to_jid(phone)
        assert jid == "5511999999999@s.whatsapp.net"

    def test_parse_explicit_mentions(self):
        """Test parsing explicit mention list."""
        phone_list = ["+5511999999999", "5511888888888", "+55 11 777777777"]
        jids = WhatsAppMentionParser.parse_explicit_mentions(phone_list)
        
        assert len(jids) == 3
        assert "5511999999999@s.whatsapp.net" in jids
        assert "5511888888888@s.whatsapp.net" in jids
        assert "5511777777777@s.whatsapp.net" in jids

    def test_parse_explicit_mentions_duplicates(self):
        """Test explicit mentions with duplicates."""
        phone_list = ["+5511999999999", "5511999999999", "+55 11 999999999"]
        jids = WhatsAppMentionParser.parse_explicit_mentions(phone_list)
        
        assert len(jids) == 1
        assert jids[0] == "5511999999999@s.whatsapp.net"

    def test_parse_explicit_mentions_empty_list(self):
        """Test empty explicit mention list."""
        phone_list = []
        jids = WhatsAppMentionParser.parse_explicit_mentions(phone_list)
        assert len(jids) == 0

    @pytest.mark.parametrize("input_text,expected_count,expected_jids", [
        ("@5511999999999", 1, ["5511999999999@s.whatsapp.net"]),
        ("@+5511999999999", 1, ["5511999999999@s.whatsapp.net"]),
        ("@55 11 999999999", 1, ["5511999999999@s.whatsapp.net"]),
        ("@+55 11 999999999", 1, ["5511999999999@s.whatsapp.net"]),
        ("@5511111111111 @5511222222222", 2, ["5511111111111@s.whatsapp.net", "5511222222222@s.whatsapp.net"]),
        ("No mentions here", 0, []),
        ("user@domain.com", 0, []),
        ("@123", 0, []),  # Too short
        ("@12345678901234567", 0, []),  # Too long for basic pattern
    ])
    def test_extract_mentions_parametrized(self, input_text: str, expected_count: int, expected_jids: List[str]):
        """Parametrized test for various mention formats."""
        original, mentions = WhatsAppMentionParser.extract_mentions(input_text)
        
        assert original == input_text
        assert len(mentions) == expected_count
        
        for expected_jid in expected_jids:
            assert expected_jid in mentions

    def test_real_world_scenarios(self):
        """Test real-world usage scenarios."""
        scenarios = [
            {
                "text": "Team meeting with @5511999999999, @5511888888888, and @5511777777777 at 3pm",
                "expected_count": 3
            },
            {
                "text": "Contact @+55 11 999999999 or @+55 11 888888888 for support",
                "expected_count": 2
            },
            {
                "text": "Hello @5511999999999! Please check the document that @5511888888888 sent.",
                "expected_count": 2
            },
            {
                "text": "Email support@company.com or call @5511999999999",
                "expected_count": 1
            }
        ]
        
        for scenario in scenarios:
            original, mentions = WhatsAppMentionParser.extract_mentions(scenario["text"])
            assert len(mentions) == scenario["expected_count"]
            
            # Verify all mentions are valid JIDs
            for mention in mentions:
                assert mention.endswith("@s.whatsapp.net")
                assert len(mention.split("@")[0]) >= 10  # Reasonable phone number length


if __name__ == "__main__":
    # Run tests manually if needed
    test_instance = TestWhatsAppMentionParser()
    
    # Run a few key tests
    test_instance.test_extract_mentions_basic_format()
    test_instance.test_extract_mentions_multiple_mentions()
    test_instance.test_parse_explicit_mentions()
    
    print("✅ All manual tests passed!")