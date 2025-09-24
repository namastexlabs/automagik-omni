import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from src.channels.message_sender import OmniChannelMessageSender
import src.channels.message_sender as message_sender


@pytest.mark.asyncio
async def test_discord_sender_records_success(monkeypatch):
    instance = SimpleNamespace(channel_type="discord", name="qa-instance")
    sender = OmniChannelMessageSender(instance)
    send_mock = AsyncMock(return_value={"success": True, "channel": "discord", "message_id": "mid-1"})
    monkeypatch.setattr(sender, "_send_discord_text", send_mock)
    trace_mock = MagicMock()
    monkeypatch.setattr(message_sender, "TraceService", trace_mock, raising=False)

    result = await sender.send_text_message(
        "1234567890",
        "trace me",
        session_name="discord_dm",
        trace_context=MagicMock(),
    )

    assert result == {"success": True, "channel": "discord", "message_id": "mid-1"}
    send_mock.assert_awaited_once_with("1234567890", "trace me", session_name="discord_dm")
    trace_mock.record_outbound_message.assert_called_once()
    call_kwargs = trace_mock.record_outbound_message.call_args.kwargs
    assert call_kwargs["success"] is True
    assert call_kwargs["payload"]["recipient"] == "1234567890"


@pytest.mark.asyncio
async def test_discord_sender_records_failure(monkeypatch):
    instance = SimpleNamespace(channel_type="discord", name="qa-instance")
    sender = OmniChannelMessageSender(instance)
    send_mock = AsyncMock(side_effect=RuntimeError("ipc unavailable"))
    monkeypatch.setattr(sender, "_send_discord_text", send_mock)
    trace_mock = MagicMock()
    monkeypatch.setattr(message_sender, "TraceService", trace_mock, raising=False)

    result = await sender.send_text_message("1234567890", "trace me")

    assert result["success"] is False
    assert "ipc unavailable" in result["error"]
    send_mock.assert_awaited_once_with("1234567890", "trace me")
    trace_mock.record_outbound_message.assert_called_once()
    call_kwargs = trace_mock.record_outbound_message.call_args.kwargs
    assert call_kwargs["success"] is False
    assert "ipc unavailable" in (call_kwargs.get("error") or "")
