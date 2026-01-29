"""Audio processor using Groq Whisper for transcription with OpenAI fallback."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

from .base import BaseProcessor, ProcessingResult
from ..pricing import calculate_processing_cost

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2  # seconds
MAX_RETRY_DELAY = 30  # seconds


class AudioProcessor(BaseProcessor):
    """
    Audio transcription processor using Groq Whisper.

    Groq's Whisper is extremely fast (216x real-time) and cost-effective.
    Falls back to OpenAI Whisper if Groq is unavailable.
    """

    # Supported audio formats
    SUPPORTED_MIME_TYPES = [
        "audio/*",  # Catch-all for audio types
        "audio/ogg",
        "audio/opus",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/wav",
        "audio/webm",
        "audio/flac",
        "audio/m4a",
        "audio/x-m4a",
    ]

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        default_language: str = "pt",  # Default to Portuguese
    ):
        super().__init__()
        self.groq_api_key = groq_api_key
        self.openai_api_key = openai_api_key
        self.default_language = default_language
        self._groq_client = None
        self._openai_client = None

    @property
    def processor_name(self) -> str:
        return "groq_whisper"

    @property
    def supported_mime_types(self) -> list[str]:
        return self.SUPPORTED_MIME_TYPES

    def _get_groq_client(self):
        """Lazy initialization of Groq client."""
        if self._groq_client is None and self.groq_api_key:
            try:
                from groq import Groq

                self._groq_client = Groq(api_key=self.groq_api_key)
                logger.info("Groq client initialized successfully")
            except ImportError:
                logger.warning("groq package not installed. Run: pip install groq")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
        return self._groq_client

    def _get_openai_client(self):
        """Lazy initialization of OpenAI client for fallback."""
        if self._openai_client is None and self.openai_api_key:
            try:
                from openai import OpenAI

                self._openai_client = OpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized successfully (fallback)")
            except ImportError:
                logger.warning("openai package not installed. Run: pip install openai")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        return self._openai_client

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if the error is a rate limit error (429)."""
        error_str = str(error).lower()
        return "429" in error_str or "rate limit" in error_str or "too many requests" in error_str

    async def process(
        self,
        file_path: Path,
        mime_type: str,
        language: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        **kwargs,
    ) -> ProcessingResult:
        """
        Transcribe audio file using Groq Whisper.

        Args:
            file_path: Path to the audio file
            mime_type: MIME type of the audio
            language: Language code (e.g., 'pt', 'en'). Defaults to Portuguese.
            duration_seconds: Duration of audio in seconds (for cost calculation)

        Returns:
            ProcessingResult with transcription and cost
        """
        start_time = time.time()
        language = language or self.default_language

        # Try to get duration if not provided
        if duration_seconds is None:
            duration_seconds = self._get_audio_duration(file_path)

        # Try Groq first (faster and cheaper)
        result = await self._transcribe_with_groq(file_path, language)

        # If Groq fails, try OpenAI fallback
        if not result.success and self.openai_api_key:
            logger.info("Groq transcription failed, trying OpenAI fallback...")
            result = await self._transcribe_with_openai(file_path, language)

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        result.processing_time_ms = processing_time_ms

        # Calculate cost if we have duration
        if result.success and duration_seconds:
            cost_info = calculate_processing_cost(
                processor_name=result.processor_name,
                model=result.processor_model,
                duration_seconds=duration_seconds,
            )
            result.cost_input_usd = cost_info["input_cost_usd"]
            result.cost_output_usd = cost_info["output_cost_usd"]
            result.cost_total_usd = cost_info["total_cost_usd"]
            result.pricing_model = cost_info["pricing_model"]
            result.pricing_rate_input = cost_info["pricing_rate_input"]
            result.pricing_rate_output = cost_info["pricing_rate_output"]

        if result.success:
            cost_str = f"${float(result.cost_total_usd):.6f}" if result.cost_total_usd else "N/A"
            logger.info(f"Audio transcription successful in {processing_time_ms}ms, cost: {cost_str}")
        else:
            logger.error(f"Audio transcription failed: {result.error_message}")

        return result

    def _get_audio_duration(self, file_path: Path) -> Optional[int]:
        """Try to get audio duration from file."""
        try:
            # Try mutagen first (lightweight)
            from mutagen import File as MutagenFile

            audio = MutagenFile(file_path)
            if audio and audio.info:
                return int(audio.info.length)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Could not get duration with mutagen: {e}")

        try:
            # Fallback to pydub
            from pydub import AudioSegment

            audio = AudioSegment.from_file(file_path)
            return int(len(audio) / 1000)  # pydub gives milliseconds
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Could not get duration with pydub: {e}")

        return None

    async def _transcribe_with_groq(
        self,
        file_path: Path,
        language: str,
    ) -> ProcessingResult:
        """Transcribe using Groq Whisper API with retry on rate limits."""
        client = self._get_groq_client()
        if not client:
            return ProcessingResult(
                success=False,
                error_message="Groq client not configured (missing API key or package)",
            )

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                with open(file_path, "rb") as audio_file:
                    # Use whisper-large-v3-turbo for best speed/quality balance
                    transcription = client.audio.transcriptions.create(
                        file=(file_path.name, audio_file),
                        model="whisper-large-v3-turbo",
                        language=language,
                        response_format="text",
                    )

                # Groq returns the text directly when response_format="text"
                text = transcription if isinstance(transcription, str) else transcription.text

                return ProcessingResult(
                    success=True,
                    content=text.strip() if text else "",
                    content_format="text",
                    processor_name="groq_whisper",
                    processor_model="whisper-large-v3-turbo",
                    confidence_score=95,  # Groq Whisper is highly accurate
                )

            except Exception as e:
                last_error = e
                if self._is_rate_limit_error(e):
                    # Rate limit - retry with exponential backoff
                    retry_delay = min(INITIAL_RETRY_DELAY * (2**attempt), MAX_RETRY_DELAY)
                    logger.warning(
                        f"Groq rate limit hit (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {retry_delay}s..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    # Other error - don't retry, let fallback handle it
                    logger.error(f"Groq transcription error: {e}")
                    break

        return ProcessingResult(
            success=False,
            processor_name="groq_whisper",
            processor_model="whisper-large-v3-turbo",
            error_message=str(last_error) if last_error else "Transcription failed",
        )

    async def _transcribe_with_openai(
        self,
        file_path: Path,
        language: str,
    ) -> ProcessingResult:
        """Transcribe using OpenAI Whisper API (fallback)."""
        client = self._get_openai_client()
        if not client:
            return ProcessingResult(
                success=False,
                error_message="OpenAI client not configured (missing API key or package)",
            )

        try:
            with open(file_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1",
                    language=language,
                    response_format="text",
                )

            text = transcription if isinstance(transcription, str) else transcription.text

            return ProcessingResult(
                success=True,
                content=text.strip() if text else "",
                content_format="text",
                processor_name="openai_whisper",
                processor_model="whisper-1",
                confidence_score=90,
            )

        except Exception as e:
            logger.error(f"OpenAI transcription error: {e}")
            return ProcessingResult(
                success=False,
                processor_name="openai_whisper",
                processor_model="whisper-1",
                error_message=str(e),
            )
