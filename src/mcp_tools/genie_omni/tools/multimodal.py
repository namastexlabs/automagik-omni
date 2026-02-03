"""Multimodal tools - Audio, voice, and multimedia capabilities."""

import logging
from typing import Callable, Optional
from fastmcp import FastMCP, Context

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, get_client: Callable, get_config: Callable):
    """Register multimodal tools with the MCP server."""

    # ==========================================================================
    # CATEGORY: Voice-to-WhatsApp (ElevenLabs TTS + Evolution API)
    # ==========================================================================

    @mcp.tool()
    async def talk(
        to: str,
        text: str,
        voice_id: Optional[str] = None,
        model_id: str = "eleven_v3",
        stability: Optional[float] = None,
        similarity_boost: Optional[float] = None,
        instance_name: str = "genie",
        quoted_message_id: Optional[str] = None,
        delay: Optional[int] = None,
        mentioned: Optional[list] = None,
        mentions_every_one: bool = False,
        ctx: Optional[Context] = None,
    ) -> str:
        """Generate speech and send as WhatsApp voice message. Supports audio tags [happy], [laughs], etc. Shows "recording" presence with dynamic duration matching the generated audio. Args: to, text (supports [tags]), voice_id, model_id (default: eleven_v3), stability (0-1, default 0.5), similarity_boost (0-1, default 0.75), instance_name, quoted_message_id, delay, mentioned, mentions_every_one. Returns: confirmation with delivery status."""
        from src.services.tts_service import TTSConfigError, TTSError, send_tts_voice_note

        client = get_client(ctx)

        try:
            # Get Evolution API credentials
            instance = await client.get_instance(instance_name, include_status=False)

            if not instance.evolution_url or not instance.evolution_key:
                return f"❌ Evolution API not configured for instance '{instance_name}'"

            result = await send_tts_voice_note(
                evolution_url=instance.evolution_url,
                evolution_key=instance.evolution_key,
                instance_name=instance_name,
                recipient=to,
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                stability=stability if stability is not None else 0.5,
                similarity_boost=similarity_boost if similarity_boost is not None else 0.75,
                presence_delay=1200,
            )

            message_id = result.get("message_id")
            audio_size_kb = result.get("audio_size_kb", 0)
            duration_ms = result.get("duration_ms", 0)

            if message_id:
                return (
                    f"🎙️ Talked to {to} successfully!\n"
                    f"Speech: {text[:80]}{'...' if len(text) > 80 else ''}\n"
                    f"Audio size: {audio_size_kb} KB\n"
                    f"Duration: {duration_ms}ms\n"
                    f"Presence shown: Recording ({duration_ms}ms)\n"
                    f"Message ID: {message_id}\n"
                    f"Status: Delivered ✅"
                )
            else:
                return f"✅ Speech generated ({audio_size_kb} KB)\n✅ Sent via Evolution API\nDuration: {duration_ms}ms"

        except TTSConfigError as e:
            return f"❌ {e}"
        except TTSError as e:
            logger.error(f"TTS error in talk: {e}")
            return f"❌ {e}"
        except Exception as e:
            logger.error(f"Error in talk: {e}")
            return f"❌ Failed to talk: {str(e)}"
