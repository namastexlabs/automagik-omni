import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import src.channels.discord.channel_handler as channel_handler
from src.channels.discord.channel_handler import DiscordChannelHandler


class _AsyncTypingContext:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _build_message(content: str, client_user, *, guild=None, channel_name="general") -> SimpleNamespace:
    channel = MagicMock()
    channel.send = AsyncMock()
    channel.typing.return_value = _AsyncTypingContext()
    channel.name = channel_name
    channel.id = 987654321
    author = SimpleNamespace(
        id=111222333,
        name="HumanSender",
        display_name="HumanSender",
        discriminator="0001",
        bot=False,
    )
    return SimpleNamespace(
        author=author,
        content=content,
        mentions=[client_user],
        channel=channel,
        guild=guild,
        attachments=[],
    )


@pytest.fixture(autouse=True)
def _patch_infrastructure(monkeypatch):
    fake_session = MagicMock(close=MagicMock(), commit=MagicMock(), refresh=MagicMock())
    monkeypatch.setattr(channel_handler, "SessionLocal", MagicMock(return_value=fake_session))
    trace_context = SimpleNamespace(
        initial_stage_logged=False,
        log_stage=MagicMock(),
        update_trace_status=MagicMock(),
        db_session=MagicMock(close=MagicMock()),
    )
    trace_service_mock = MagicMock(
        create_trace=MagicMock(return_value=trace_context),
        record_outbound_message=MagicMock(),
    )
    monkeypatch.setattr(channel_handler, "TraceService", trace_service_mock, raising=False)
    return trace_service_mock


@pytest.mark.asyncio
async def test_handler_logs_agent_response(monkeypatch):
    handler = DiscordChannelHandler()
    instance = SimpleNamespace(name="qa-instance")
    client_user = MagicMock()
    client_user.id = 123456789
    client_user.mentioned_in.return_value = True
    client = SimpleNamespace(user=client_user)
    message = _build_message(f"<@{client_user.id}> hello", client_user)
    route_mock = MagicMock(return_value={"message": "hi there", "user_id": "agent-7"})
    monkeypatch.setattr(channel_handler.message_router, "route_message", route_mock)
    send_response = AsyncMock()
    monkeypatch.setattr(handler, "_send_response_to_discord", send_response)

    await handler._handle_message(message, instance, client)

    send_response.assert_awaited_once()
    route_mock.assert_called_once()
    assert handler._get_cached_agent_user_id(instance.name, str(message.author.id)) == "agent-7"


@pytest.mark.asyncio
async def test_handler_sends_fallback_on_route_error(monkeypatch):
    handler = DiscordChannelHandler()
    instance = SimpleNamespace(name="qa-instance")
    client_user = MagicMock()
    client_user.id = 222333444
    client_user.mentioned_in.return_value = True
    client = SimpleNamespace(user=client_user)
    guild = SimpleNamespace(id=555000111, name="GuildQA")
    message = _build_message(f"<@{client_user.id}> payload", client_user, guild=guild)
    route_mock = MagicMock(side_effect=RuntimeError("router exploded"))
    monkeypatch.setattr(channel_handler.message_router, "route_message", route_mock)

    await handler._handle_message(message, instance, client)

    message.channel.send.assert_awaited_once()
    fallback_text = message.channel.send.await_args.args[0]
    assert "encountered an error" in fallback_text
    route_mock.assert_called_once()
