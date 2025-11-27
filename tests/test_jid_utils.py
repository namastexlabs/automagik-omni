"""Tests for JID/phone number utilities."""

from src.mcp_tools.genie_omni.client import normalize_jid
from src.services.trace_service import TraceService


class TestNormalizeJid:
    """Tests for normalize_jid function."""

    def test_individual_phone_number(self):
        """Individual phone numbers get @s.whatsapp.net suffix."""
        assert normalize_jid("5511999999999") == "5511999999999@s.whatsapp.net"

    def test_group_number(self):
        """Group numbers starting with 120363 get @g.us suffix."""
        assert normalize_jid("120363421396472428") == "120363421396472428@g.us"

    def test_already_formatted_individual_jid(self):
        """Already formatted individual JIDs pass through unchanged."""
        assert normalize_jid("5511999999999@s.whatsapp.net") == "5511999999999@s.whatsapp.net"

    def test_already_formatted_group_jid(self):
        """Already formatted group JIDs pass through unchanged."""
        assert normalize_jid("120363421396472428@g.us") == "120363421396472428@g.us"

    def test_already_formatted_lid(self):
        """LID format JIDs pass through unchanged."""
        assert normalize_jid("5511999999999@lid") == "5511999999999@lid"


class TestExtractPhone:
    """Tests for _extract_phone function."""

    def test_extract_from_whatsapp_net(self):
        """Extract phone from @s.whatsapp.net JID."""
        assert TraceService._extract_phone("5511999999999@s.whatsapp.net") == "5511999999999"

    def test_extract_from_group_jid(self):
        """Extract ID from @g.us JID."""
        assert TraceService._extract_phone("120363421396472428@g.us") == "120363421396472428"

    def test_extract_from_lid(self):
        """Extract phone from @lid JID."""
        assert TraceService._extract_phone("5511999999999@lid") == "5511999999999"

    def test_plain_phone_passthrough(self):
        """Plain phone numbers without @ pass through unchanged."""
        assert TraceService._extract_phone("5511999999999") == "5511999999999"
