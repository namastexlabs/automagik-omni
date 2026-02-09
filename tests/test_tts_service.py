"""
Tests for TTS service and send-tts API endpoint.

Tests cover:
- TTS audio generation via ElevenLabs (mocked)
- MP3 to OGG/Opus conversion
- Dynamic recording presence based on audio duration
- REST API endpoint integration
- Error handling (missing API key, API failures, missing pydub)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.services.tts_service import (
    TTSConfigError,
    TTSError,
    _convert_mp3_to_ogg,
    _get_audio_duration_ms,
    generate_tts_audio,
    send_tts_voice_note,
)


# ===== Fixtures =====


@pytest.fixture
def mock_elevenlabs_response():
    """Fake MP3 bytes for mocking ElevenLabs API response."""
    # Minimal valid MP3 frame header (won't decode as real audio, but works for byte-level tests)
    return b"\xff\xfb\x90\x00" + b"\x00" * 1024


@pytest.fixture
def mock_httpx_elevenlabs(mock_elevenlabs_response):
    """Mock httpx.AsyncClient to return fake ElevenLabs audio."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = mock_elevenlabs_response

    async def mock_post(*args, **kwargs):
        return mock_response

    mock_client = AsyncMock()
    mock_client.post = mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client, mock_response


# ===== Unit Tests: generate_tts_audio =====


class TestGenerateTTSAudio:
    """Test the generate_tts_audio function."""

    @pytest.mark.asyncio
    async def test_missing_api_key_raises_config_error(self):
        """Should raise TTSConfigError when XI_API_KEY is not set."""
        with patch.dict("os.environ", {"XI_API_KEY": ""}):
            with pytest.raises(TTSConfigError, match="XI_API_KEY"):
                await generate_tts_audio("Hello world")

    @pytest.mark.asyncio
    async def test_elevenlabs_api_error_raises_tts_error(self):
        """Should raise TTSError when ElevenLabs API returns non-200."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.dict("os.environ", {"XI_API_KEY": "test-key"}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                with pytest.raises(TTSError, match="401"):
                    await generate_tts_audio("Hello")

    @pytest.mark.asyncio
    async def test_successful_generation_returns_bytes_and_duration(self):
        """Should return (mp3_bytes, duration_ms) on success."""
        fake_mp3 = b"\xff\xfb\x90\x00" + b"\x00" * 512

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_mp3

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.dict("os.environ", {"XI_API_KEY": "test-key"}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                with patch("src.services.tts_service._get_audio_duration_ms", return_value=5000):
                    mp3_bytes, duration_ms = await generate_tts_audio("Hello world")

        assert mp3_bytes == fake_mp3
        assert duration_ms == 5000

    @pytest.mark.asyncio
    async def test_uses_env_voice_id_when_none(self):
        """Should use XI_VOICE_ID from env when voice_id is None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"\x00" * 100

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.dict("os.environ", {"XI_API_KEY": "test-key", "XI_VOICE_ID": "custom-voice-123"}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                with patch("src.services.tts_service._get_audio_duration_ms", return_value=1000):
                    await generate_tts_audio("Test")

        # Verify the URL contains the custom voice ID
        call_args = mock_client.post.call_args
        assert "custom-voice-123" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_passes_voice_settings_in_body(self):
        """Should pass stability and similarity_boost in the request body."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"\x00" * 100

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.dict("os.environ", {"XI_API_KEY": "test-key"}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                with patch("src.services.tts_service._get_audio_duration_ms", return_value=1000):
                    await generate_tts_audio("Test", stability=0.8, similarity_boost=0.9)

        call_kwargs = mock_client.post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["voice_settings"]["stability"] == 0.8
        assert body["voice_settings"]["similarity_boost"] == 0.9

    @pytest.mark.asyncio
    async def test_rejects_voice_id_with_path_traversal(self):
        """Should reject voice_id containing path traversal characters."""
        with patch.dict("os.environ", {"XI_API_KEY": "test-key"}):
            with pytest.raises(TTSError, match="Invalid voice_id"):
                await generate_tts_audio("Hello", voice_id="../../v1/models")

    @pytest.mark.asyncio
    async def test_rejects_voice_id_with_slash(self):
        """Should reject voice_id containing slashes."""
        with patch.dict("os.environ", {"XI_API_KEY": "test-key"}):
            with pytest.raises(TTSError, match="Invalid voice_id"):
                await generate_tts_audio("Hello", voice_id="foo/bar")


# ===== Unit Tests: _get_audio_duration_ms =====


class TestGetAudioDurationMs:
    """Test the audio duration measurement function."""

    def test_fallback_when_pydub_not_installed(self):
        """Should return fallback duration when pydub is not available."""
        with patch.dict("sys.modules", {"pydub": None}):
            result = _get_audio_duration_ms(b"\x00" * 100)
            assert result == 3000

    def test_fallback_on_decode_error(self):
        """Should return fallback when audio can't be decoded."""
        result = _get_audio_duration_ms(b"not valid audio data")
        assert result == 3000


# ===== Unit Tests: _convert_mp3_to_ogg =====


class TestConvertMp3ToOgg:
    """Test the MP3 to OGG/Opus conversion."""

    def test_raises_config_error_when_pydub_missing(self):
        """Should raise TTSConfigError when pydub is not installed."""
        with patch.dict("sys.modules", {"pydub": None}):
            with pytest.raises(TTSConfigError, match="pydub"):
                _convert_mp3_to_ogg(b"\x00" * 100)


# ===== Unit Tests: send_tts_voice_note =====


class TestSendTTSVoiceNote:
    """Test the full TTS send flow."""

    @pytest.mark.asyncio
    async def test_successful_send_returns_result(self):
        """Should generate audio, send presence, and return success."""
        evolution_response = {"key": {"id": "msg-123"}}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = evolution_response
        mock_response.raise_for_status = MagicMock()

        # Track all POST calls
        post_calls = []

        async def mock_post(url, **kwargs):
            post_calls.append(url)
            return mock_response

        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.tts_service.generate_tts_audio", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = (b"\x00" * 100, 4500)
            with patch("src.services.tts_service._convert_mp3_to_ogg", return_value=b"\x00" * 80):
                with patch("httpx.AsyncClient", return_value=mock_client):
                    result = await send_tts_voice_note(
                        evolution_url="http://evo.test",
                        evolution_key="evo-key",
                        instance_name="test-instance",
                        recipient="5511999999999@s.whatsapp.net",
                        text="Hello world",
                    )

        assert result["success"] is True
        assert result["message_id"] == "msg-123"
        assert result["duration_ms"] == 4500

        # Verify presence was sent before the media
        assert len(post_calls) == 2
        assert "sendPresence" in post_calls[0]
        assert "sendWhatsAppAudio" in post_calls[1]

    @pytest.mark.asyncio
    async def test_dynamic_presence_delay_matches_audio_duration(self):
        """Presence delay should equal the audio duration in ms."""
        presence_payload = {}

        async def capture_post(url, **kwargs):
            if "sendPresence" in url:
                presence_payload.update(kwargs.get("json", {}))
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"key": {"id": "msg-456"}}
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        audio_duration = 7200  # 7.2 seconds

        with patch("src.services.tts_service.generate_tts_audio", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = (b"\x00" * 100, audio_duration)
            with patch("src.services.tts_service._convert_mp3_to_ogg", return_value=b"\x00" * 80):
                with patch("httpx.AsyncClient", return_value=mock_client):
                    await send_tts_voice_note(
                        evolution_url="http://evo.test",
                        evolution_key="evo-key",
                        instance_name="test",
                        recipient="5511999999999@s.whatsapp.net",
                        text="A longer message",
                    )

        assert presence_payload["options"]["delay"] == audio_duration
        assert presence_payload["options"]["presence"] == "recording"

    @pytest.mark.asyncio
    async def test_evolution_api_error_raises_tts_error(self):
        """Should raise TTSError when Evolution API returns an error."""
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"

        request_mock = MagicMock()
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=request_mock, response=error_response
        )

        call_count = 0

        async def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "sendPresence" in url:
                ok_resp = MagicMock()
                ok_resp.status_code = 200
                return ok_resp
            return error_response

        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.tts_service.generate_tts_audio", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = (b"\x00" * 100, 3000)
            with patch("src.services.tts_service._convert_mp3_to_ogg", return_value=b"\x00" * 80):
                with patch("httpx.AsyncClient", return_value=mock_client):
                    with pytest.raises(TTSError, match="Evolution API error"):
                        await send_tts_voice_note(
                            evolution_url="http://evo.test",
                            evolution_key="evo-key",
                            instance_name="test",
                            recipient="5511999999999@s.whatsapp.net",
                            text="Test",
                        )

    @pytest.mark.asyncio
    async def test_presence_failure_does_not_block_send(self):
        """Should still send audio even if presence request fails."""
        call_count = 0

        async def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "sendPresence" in url:
                raise Exception("Presence failed")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"key": {"id": "msg-789"}}
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.tts_service.generate_tts_audio", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = (b"\x00" * 100, 3000)
            with patch("src.services.tts_service._convert_mp3_to_ogg", return_value=b"\x00" * 80):
                with patch("httpx.AsyncClient", return_value=mock_client):
                    result = await send_tts_voice_note(
                        evolution_url="http://evo.test",
                        evolution_key="evo-key",
                        instance_name="test",
                        recipient="5511999999999@s.whatsapp.net",
                        text="Test",
                    )

        assert result["success"] is True
        assert result["message_id"] == "msg-789"

    @pytest.mark.asyncio
    async def test_custom_presence_delay_overrides_dynamic(self):
        """Should use provided presence_delay instead of audio duration."""
        presence_payload = {}

        async def capture_post(url, **kwargs):
            if "sendPresence" in url:
                presence_payload.update(kwargs.get("json", {}))
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"key": {"id": "msg-fixed"}}
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.tts_service.generate_tts_audio", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = (b"\x00" * 100, 8000)  # audio is 8s
            with patch("src.services.tts_service._convert_mp3_to_ogg", return_value=b"\x00" * 80):
                with patch("httpx.AsyncClient", return_value=mock_client):
                    await send_tts_voice_note(
                        evolution_url="http://evo.test",
                        evolution_key="evo-key",
                        instance_name="test",
                        recipient="5511999999999@s.whatsapp.net",
                        text="Test",
                        presence_delay=2000,  # override to 2s
                    )

        assert presence_payload["options"]["delay"] == 2000

    @pytest.mark.asyncio
    async def test_presence_delay_zero_skips_presence(self):
        """Should skip presence entirely when presence_delay is 0."""
        post_urls = []

        async def capture_post(url, **kwargs):
            post_urls.append(url)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"key": {"id": "msg-no-presence"}}
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.tts_service.generate_tts_audio", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = (b"\x00" * 100, 5000)
            with patch("src.services.tts_service._convert_mp3_to_ogg", return_value=b"\x00" * 80):
                with patch("httpx.AsyncClient", return_value=mock_client):
                    result = await send_tts_voice_note(
                        evolution_url="http://evo.test",
                        evolution_key="evo-key",
                        instance_name="test",
                        recipient="5511999999999@s.whatsapp.net",
                        text="Test",
                        presence_delay=0,
                    )

        assert result["success"] is True
        # Only sendWhatsAppAudio should have been called, no sendPresence
        assert len(post_urls) == 1
        assert "sendWhatsAppAudio" in post_urls[0]


# ===== Integration Tests: REST API endpoint =====


class TestSendTTSEndpoint:
    """Test the POST /api/v1/instance/{name}/send-tts endpoint."""

    def test_send_tts_success(self, test_client):
        """Should return 200 with message_id on successful TTS send."""
        tts_result = {
            "success": True,
            "message_id": "msg-tts-001",
            "audio_size_kb": 12.5,
            "duration_ms": 4500,
        }

        with patch("src.services.tts_service.send_tts_voice_note", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = tts_result

            response = test_client.post(
                "/api/v1/instance/test-instance/send-tts",
                json={
                    "phone_number": "+5511999999999",
                    "text": "Hello from TTS",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message_id"] == "msg-tts-001"
        assert data["status"] == "sent"
        assert data["evolution_response"]["duration_ms"] == 4500
        assert data["evolution_response"]["audio_size_kb"] == 12.5

    def test_send_tts_missing_text(self, test_client):
        """Should return 422 when text field is missing."""
        response = test_client.post(
            "/api/v1/instance/test-instance/send-tts",
            json={"phone_number": "+5511999999999"},
        )
        assert response.status_code == 422

    def test_send_tts_missing_recipient(self, test_client):
        """Should return 400 when neither user_id nor phone_number is provided."""
        with patch("src.services.tts_service.send_tts_voice_note", new_callable=AsyncMock):
            response = test_client.post(
                "/api/v1/instance/test-instance/send-tts",
                json={"text": "Hello"},
            )
        assert response.status_code == 400

    def test_send_tts_invalid_instance(self, test_client):
        """Should return 404 for non-existent instance."""
        response = test_client.post(
            "/api/v1/instance/nonexistent/send-tts",
            json={"phone_number": "+5511999999999", "text": "Hello"},
        )
        assert response.status_code == 404

    def test_send_tts_missing_api_key_returns_503(self, test_client):
        """Should return 503 when ElevenLabs API key is not configured."""
        with patch(
            "src.services.tts_service.send_tts_voice_note",
            new_callable=AsyncMock,
            side_effect=TTSConfigError("ElevenLabs API key not found. Set XI_API_KEY environment variable."),
        ):
            response = test_client.post(
                "/api/v1/instance/test-instance/send-tts",
                json={"phone_number": "+5511999999999", "text": "Hello"},
            )
        assert response.status_code == 503
        assert "XI_API_KEY" in response.json()["detail"]

    def test_send_tts_elevenlabs_error_returns_error(self, test_client):
        """Should return error status when ElevenLabs API fails."""
        with patch(
            "src.services.tts_service.send_tts_voice_note",
            new_callable=AsyncMock,
            side_effect=TTSError("ElevenLabs API error: 429 - Rate limited"),
        ):
            response = test_client.post(
                "/api/v1/instance/test-instance/send-tts",
                json={"phone_number": "+5511999999999", "text": "Hello"},
            )
        assert response.status_code == 200  # HTTP 200 with success=False
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "error"
        assert "429" in data["error"]

    def test_send_tts_custom_voice_params(self, test_client):
        """Should pass custom voice parameters to the service."""
        tts_result = {
            "success": True,
            "message_id": "msg-custom",
            "audio_size_kb": 10.0,
            "duration_ms": 3000,
        }

        with patch("src.services.tts_service.send_tts_voice_note", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = tts_result

            response = test_client.post(
                "/api/v1/instance/test-instance/send-tts",
                json={
                    "phone_number": "+5511999999999",
                    "text": "[happy] Great news everyone!",
                    "voice_id": "custom-voice-id",
                    "model_id": "eleven_v3",
                    "stability": 0.8,
                    "similarity_boost": 0.9,
                },
            )

        assert response.status_code == 200
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["voice_id"] == "custom-voice-id"
        assert call_kwargs["stability"] == 0.8
        assert call_kwargs["similarity_boost"] == 0.9

    def test_send_tts_with_presence_delay(self, test_client):
        """Should pass presence_delay to the service."""
        tts_result = {
            "success": True,
            "message_id": "msg-delay",
            "audio_size_kb": 10.0,
            "duration_ms": 5000,
        }

        with patch("src.services.tts_service.send_tts_voice_note", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = tts_result

            response = test_client.post(
                "/api/v1/instance/test-instance/send-tts",
                json={
                    "phone_number": "+5511999999999",
                    "text": "Hello",
                    "presence_delay": 2000,
                },
            )

        assert response.status_code == 200
        assert mock_send.call_args.kwargs["presence_delay"] == 2000

    def test_send_tts_with_presence_delay_zero(self, test_client):
        """Should pass presence_delay=0 to disable presence."""
        tts_result = {
            "success": True,
            "message_id": "msg-no-pres",
            "audio_size_kb": 10.0,
            "duration_ms": 5000,
        }

        with patch("src.services.tts_service.send_tts_voice_note", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = tts_result

            response = test_client.post(
                "/api/v1/instance/test-instance/send-tts",
                json={
                    "phone_number": "+5511999999999",
                    "text": "Hello",
                    "presence_delay": 0,
                },
            )

        assert response.status_code == 200
        assert mock_send.call_args.kwargs["presence_delay"] == 0

    def test_send_tts_without_presence_delay_defaults_none(self, test_client):
        """Should default presence_delay to None (auto) when not provided."""
        tts_result = {
            "success": True,
            "message_id": "msg-auto",
            "audio_size_kb": 10.0,
            "duration_ms": 5000,
        }

        with patch("src.services.tts_service.send_tts_voice_note", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = tts_result

            response = test_client.post(
                "/api/v1/instance/test-instance/send-tts",
                json={
                    "phone_number": "+5511999999999",
                    "text": "Hello",
                },
            )

        assert response.status_code == 200
        assert mock_send.call_args.kwargs["presence_delay"] is None

    def test_send_tts_stability_out_of_range(self, test_client):
        """Should return 422 when stability is outside 0-1 range."""
        response = test_client.post(
            "/api/v1/instance/test-instance/send-tts",
            json={
                "phone_number": "+5511999999999",
                "text": "Hello",
                "stability": 1.5,
            },
        )
        assert response.status_code == 422

    def test_send_tts_similarity_boost_out_of_range(self, test_client):
        """Should return 422 when similarity_boost is outside 0-1 range."""
        response = test_client.post(
            "/api/v1/instance/test-instance/send-tts",
            json={
                "phone_number": "+5511999999999",
                "text": "Hello",
                "similarity_boost": -0.1,
            },
        )
        assert response.status_code == 422
