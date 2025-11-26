"""Multimodal tools - Audio, voice, and multimedia capabilities."""

import logging
import os
from pathlib import Path
from typing import Callable, Optional
import httpx
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
    
        ctx: Optional[Context] = None,) -> str:
        """Generate speech and send as WhatsApp voice message. Supports audio tags [happy], [laughs], etc. Shows "recording" presence automatically. Args: to, text (supports [tags]), voice_id, model_id (default: eleven_v3), stability (0-1, default 0.5), similarity_boost (0-1, default 0.75), instance_name, quoted_message_id, delay, mentioned, mentions_every_one. Returns: confirmation with delivery status."""
        config = get_config(ctx)
        client = get_client(ctx)

        # Get API key
        api_key = os.getenv("XI_API_KEY")
        if not api_key:
            return "❌ ElevenLabs API key not found. Set XI_API_KEY environment variable."

        # Get voice ID from environment or use provided
        if voice_id is None:
            voice_id = os.getenv("XI_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")

        # Set default voice settings if not provided
        if stability is None:
            stability = 0.5
        if similarity_boost is None:
            similarity_boost = 0.75

        # Create output directory (use configured folder + voice-messages subdirectory)
        output_dir = Path(config.media_download_folder) / "voice-messages"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate temporary filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"talk_{timestamp}.mp3"
        output_path = output_dir / filename

        # Step 1: Generate speech using ElevenLabs
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

        try:
            # Generate audio
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    url,
                    headers=headers,
                    json=body,
                    params=params,
                    timeout=60.0,
                )

                if response.status_code != 200:
                    return f"❌ ElevenLabs API error: {response.status_code}\n{response.text}"

                # Save audio file and prepare for sending
                audio_content = response.content
                with open(output_path, "wb") as f:
                    f.write(audio_content)

                file_size = len(audio_content) / 1024

            # Step 2: Send to WhatsApp with automatic presence (recording)
            # Show "recording" presence before sending
            try:
                await client.evolution_send_presence(
                    instance_name=instance_name,
                    remote_jid=to,
                    presence="recording",
                    delay=1200  # ~1 second
                )
            except Exception as e:
                logger.warning(f"Failed to send presence: {e}")

            # Send audio via Evolution API directly (bypassing Omni server)
            try:
                # Get Evolution API credentials
                instance = await client.get_instance(instance_name, include_status=False)

                if not instance.evolution_url or not instance.evolution_key:
                    return (
                        f"✅ Speech generated ({file_size:.2f} KB)\n"
                        f"❌ Evolution API not configured for instance '{instance_name}'\n"
                        f"Audio saved at: {output_path}"
                    )

                # Convert MP3 to OGG/Opus for WhatsApp voice notes
                from pydub import AudioSegment
                import base64

                # Convert to OGG/Opus format (WhatsApp native voice note format)
                ogg_path = output_path.with_suffix(".ogg")
                audio = AudioSegment.from_mp3(str(output_path))
                audio.export(
                    str(ogg_path),
                    format="ogg",
                    codec="libopus",
                    parameters=["-ar", "16000", "-ac", "1", "-b:a", "32k"]  # WhatsApp optimal settings
                )

                # Read the converted audio
                with open(ogg_path, "rb") as f:
                    audio_content = f.read()

                # Encode audio as base64
                audio_base64 = base64.b64encode(audio_content).decode("utf-8")

                # Call Evolution API directly
                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    evolution_url = f"{instance.evolution_url}/message/sendMedia/{instance_name}"

                    # Build payload with required fields
                    payload = {
                        "number": to,
                        "mediatype": "audio",
                        "media": audio_base64,
                        "mimetype": "audio/ogg; codecs=opus",  # WhatsApp voice note format
                        "ptt": True
                    }

                    # Add optional WhatsApp features
                    if delay is not None:
                        payload["delay"] = delay

                    if quoted_message_id:
                        payload["quoted"] = {
                            "key": {
                                "id": quoted_message_id
                            }
                        }

                    if mentions_every_one:
                        payload["mentionsEveryOne"] = True

                    if mentioned and len(mentioned) > 0:
                        payload["mentioned"] = mentioned

                    headers = {
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    }

                    logger.info(f"Sending audio to Evolution API: {evolution_url}")

                    response = await http_client.post(
                        evolution_url,
                        headers=headers,
                        json=payload
                    )

                    response.raise_for_status()
                    result = response.json()

                    logger.info(f"Evolution API response: {result}")

                    # Extract message ID from Evolution API response
                    message_id = result.get("key", {}).get("id") if isinstance(result, dict) else None

                    if message_id:
                        return (
                            f"🎙️ Talked to {to} successfully!\n"
                            f"Speech: {text[:80]}{'...' if len(text) > 80 else ''}\n"
                            f"Audio size: {file_size:.2f} KB\n"
                            f"Presence shown: Recording\n"
                            f"Message ID: {message_id}\n"
                            f"Status: Delivered ✅"
                        )
                    else:
                        return (
                            f"✅ Speech generated ({file_size:.2f} KB)\n"
                            f"✅ Sent via Evolution API\n"
                            f"Response: {result}\n"
                            f"Audio saved at: {output_path}"
                        )

            except httpx.HTTPStatusError as http_error:
                logger.error(f"Evolution API HTTP error: {http_error.response.status_code} - {http_error.response.text}")
                return (
                    f"✅ Speech generated ({file_size:.2f} KB)\n"
                    f"❌ Evolution API error: {http_error.response.status_code}\n"
                    f"Response: {http_error.response.text}\n"
                    f"Audio saved at: {output_path}"
                )
            except Exception as send_error:
                logger.error(f"Exception during WhatsApp send: {send_error}", exc_info=True)
                return (
                    f"✅ Speech generated ({file_size:.2f} KB)\n"
                    f"❌ WhatsApp send error: {str(send_error)}\n"
                    f"Audio saved at: {output_path}"
                )

        except Exception as e:
            logger.error(f"Error in talk: {e}")
            return f"❌ Failed to talk: {str(e)}"
