"""Discord parity regression tests for trace persistence and identity linking."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, ANY

import pytest

from src.channels.discord.channel_handler import DiscordChannelHandler
import src.channels.discord.channel_handler as channel_handler
from src.channels.message_sender import OmniChannelMessageSender
import src.channels.message_sender as message_sender


class _AsyncTypingContext:
    """Minimal async context manager used to fake Discord's typing indicator."""

    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


def _build_discord_message(client_user, content: str) -> SimpleNamespace:
    """Create a lightweight Discord message stub for handler testing."""

    channel = MagicMock()
    channel.send = AsyncMock()
    channel.typing.return_value = _AsyncTypingContext()
    channel.name = "general"

    author = SimpleNamespace(
        id=321987654,
        name="TraceSeeker",
        display_name="TraceSeeker",
        discriminator="0420",
        bot=False,
    )

    guild = SimpleNamespace(id=555777999, name="ParityGuild")

    return SimpleNamespace(
        author=author,
        content=content,
        mentions=[client_user],
        channel=channel,
        guild=guild,
    )


@pytest.mark.asyncio
async def test_discord_inbound_creates_trace_payload(monkeypatch):
    """Discord inbound path should create message traces and payload logs like WhatsApp."""

    handler = DiscordChannelHandler()
    instance_config = SimpleNamespace(name="discord-parity-instance")

    client_user = MagicMock()
    client_user.id = 999001337
    client_user.mentioned_in.return_value = True

    client = SimpleNamespace(user=client_user)
    message = _build_discord_message(client_user, f"<@{client_user.id}> persist me")

    trace_context = MagicMock()
    trace_service_mock = MagicMock()
    trace_service_mock.create_trace.return_value = trace_context
    monkeypatch.setattr(channel_handler, "TraceService", trace_service_mock, raising=False)

    route_mock = MagicMock(return_value={"message": "pong", "user_id": "agent-user-123"})
    monkeypatch.setattr(channel_handler.message_router, "route_message", route_mock)

    await handler._handle_message(message, instance_config, client)

    trace_service_mock.create_trace.assert_called_once()
    trace_context.log_stage.assert_any_call("webhook_received", ANY, "webhook")


@pytest.mark.asyncio
async def test_discord_outbound_writes_trace_payload(monkeypatch):
    """Outbound Discord sends should record trace + payload rows to mirror WhatsApp."""

    instance_config = MagicMock()
    instance_config.channel_type = "discord"
    instance_config.name = "discord-parity-instance"

    sender = OmniChannelMessageSender(instance_config)

    trace_service_mock = MagicMock()
    trace_service_mock.record_outbound_message = MagicMock()
    monkeypatch.setattr(message_sender, "TraceService", trace_service_mock, raising=False)

    send_mock = AsyncMock(return_value={"success": True, "channel": "discord"})
    monkeypatch.setattr(sender, "_send_discord_text", send_mock)

    result = await sender.send_text_message("1234567890", "trace this outbound")

    assert result == {"success": True, "channel": "discord"}
    send_mock.assert_awaited_once_with("1234567890", "trace this outbound")
    trace_service_mock.record_outbound_message.assert_called_once()


@pytest.mark.asyncio
async def test_discord_identity_links_agent_user_id(monkeypatch):
    """Discord handler should reuse agent user_id across messages for parity identity linking."""

    handler = DiscordChannelHandler()
    instance_config = SimpleNamespace(name="discord-parity-instance")

    client_user = MagicMock()
    client_user.id = 424242
    client_user.mentioned_in.return_value = True

    client = SimpleNamespace(user=client_user)
    first_message = _build_discord_message(client_user, f"<@{client_user.id}> first ping")
    second_message = _build_discord_message(client_user, f"<@{client_user.id}> second ping")

    route_mock = MagicMock(
        side_effect=[
            {"message": "hello", "user_id": "agent-user-123"},
            {"message": "welcome back", "user_id": "agent-user-123"},
        ]
    )
    monkeypatch.setattr(channel_handler.message_router, "route_message", route_mock)

    await handler._handle_message(first_message, instance_config, client)
    await handler._handle_message(second_message, instance_config, client)

    assert route_mock.call_count == 2
    second_call_kwargs = route_mock.call_args_list[1].kwargs
    assert second_call_kwargs["user_id"] == "agent-user-123"
