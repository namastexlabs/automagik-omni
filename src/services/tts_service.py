"""
TTS (Text-to-Speech) service using ElevenLabs API.

Generates speech audio and sends as WhatsApp voice notes via Evolution API.
Used by both the REST API endpoint and MCP talk() tool.
"""

import base64
import io
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL_ID = "eleven_v3"
DEFAULT_STABILITY = 0.5
DEFAULT_SIMILARITY_BOOST = 0.75


class TTSError(Exception):
    """Base error for TTS operations."""


class TTSConfigError(TTSError):
    """Missing configuration (API keys, dependencies)."""


async def generate_tts_audio(
    text: str,
    voice_id: Optional[str] = None,
    model_id: str = DEFAULT_MODEL_ID,
    stability: float = DEFAULT_STABILITY,
    similarity_boost: float = DEFAULT_SIMILARITY_BOOST,
) -> tuple[bytes, int]:
    """Generate speech audio from text using ElevenLabs.

    Args:
        text: Text to convert to speech. Supports ElevenLabs audio tags like [happy], [laughs].
        voice_id: ElevenLabs voice ID. Defaults to XI_VOICE_ID env var or built-in default.
        model_id: ElevenLabs model ID.
        stability: Voice stability (0-1).
        similarity_boost: Voice similarity boost (0-1).

    Returns:
        Tuple of (mp3_bytes, duration_ms).

    Raises:
        TTSConfigError: If XI_API_KEY is not set.
        TTSError: If ElevenLabs API call fails.
    """
    api_key = os.getenv("XI_API_KEY")
    if not api_key:
        raise TTSConfigError("ElevenLabs API key not found. Set XI_API_KEY environment variable.")

    if voice_id is None:
        voice_id = os.getenv("XI_VOICE_ID", DEFAULT_VOICE_ID)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
        },
    }
    params = {"output_format": "mp3_44100_128"}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body, params=params, timeout=60.0)
        if response.status_code != 200:
            raise TTSError(f"ElevenLabs API error: {response.status_code} - {response.text}")
        mp3_bytes = response.content

    # Measure audio duration with pydub
    duration_ms = _get_audio_duration_ms(mp3_bytes)
    return mp3_bytes, duration_ms


def _get_audio_duration_ms(mp3_bytes: bytes) -> int:
    """Get audio duration in milliseconds from MP3 bytes."""
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        return len(audio)
    except ImportError:
        # Fallback: estimate ~150 words/min, ~5 chars/word
        logger.warning("pydub not installed, estimating duration from text length")
        return 3000
    except Exception as e:
        logger.warning(f"Failed to measure audio duration: {e}, using fallback")
        return 3000


def _convert_mp3_to_ogg(mp3_bytes: bytes) -> bytes:
    """Convert MP3 bytes to OGG/Opus format for WhatsApp voice notes.

    Raises:
        TTSConfigError: If pydub is not installed.
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        raise TTSConfigError("pydub not installed. Install with: pip install 'automagik-omni[whatsapp]'")

    audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
    ogg_buffer = io.BytesIO()
    audio.export(
        ogg_buffer,
        format="ogg",
        codec="libopus",
        parameters=["-ar", "16000", "-ac", "1", "-b:a", "32k"],
    )
    return ogg_buffer.getvalue()


async def send_tts_voice_note(
    evolution_url: str,
    evolution_key: str,
    instance_name: str,
    recipient: str,
    text: str,
    voice_id: Optional[str] = None,
    model_id: str = DEFAULT_MODEL_ID,
    stability: float = DEFAULT_STABILITY,
    similarity_boost: float = DEFAULT_SIMILARITY_BOOST,
    presence_delay: Optional[int] = None,
) -> dict:
    """Generate TTS audio and send as WhatsApp voice note.

    Shows "recording" presence before sending the voice note.

    Args:
        evolution_url: Evolution API base URL.
        evolution_key: Evolution API key.
        instance_name: WhatsApp instance name.
        recipient: Recipient JID (e.g. 5511999999999@s.whatsapp.net).
        text: Text to convert to speech.
        voice_id: ElevenLabs voice ID.
        model_id: ElevenLabs model ID.
        stability: Voice stability (0-1).
        similarity_boost: Voice similarity boost (0-1).
        presence_delay: Recording presence delay in ms. None = auto (audio duration).
            0 = skip presence entirely.

    Returns:
        Dict with success, message_id, audio_size_kb, duration_ms.

    Raises:
        TTSConfigError: If API keys or dependencies are missing.
        TTSError: If generation or sending fails.
    """
    # 1. Generate audio
    mp3_bytes, duration_ms = await generate_tts_audio(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        stability=stability,
        similarity_boost=similarity_boost,
    )

    # 2. Convert MP3 to OGG/Opus
    ogg_bytes = _convert_mp3_to_ogg(mp3_bytes)
    audio_size_kb = len(ogg_bytes) / 1024

    # 3. Send "recording" presence (skip if presence_delay == 0)
    effective_delay = duration_ms if presence_delay is None else presence_delay
    async with httpx.AsyncClient(timeout=30.0) as client:
        if effective_delay > 0:
            try:
                await client.post(
                    f"{evolution_url}/chat/sendPresence/{instance_name}",
                    headers={"apikey": evolution_key, "Content-Type": "application/json"},
                    json={
                        "number": recipient,
                        "options": {
                            "delay": effective_delay,
                            "presence": "recording",
                            "number": recipient,
                        },
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to send recording presence: {e}")

        # 4. Send voice note via Evolution API
        audio_base64 = base64.b64encode(ogg_bytes).decode("utf-8")
        payload = {
            "number": recipient,
            "mediatype": "audio",
            "media": audio_base64,
            "mimetype": "audio/ogg; codecs=opus",
            "ptt": True,
        }

        try:
            response = await client.post(
                f"{evolution_url}/message/sendMedia/{instance_name}",
                headers={"apikey": evolution_key, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as e:
            raise TTSError(f"Evolution API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise TTSError(f"Failed to send voice note: {e}")

    message_id = result.get("key", {}).get("id") if isinstance(result, dict) else None

    return {
        "success": True,
        "message_id": message_id,
        "audio_size_kb": round(audio_size_kb, 2),
        "duration_ms": duration_ms,
    }
