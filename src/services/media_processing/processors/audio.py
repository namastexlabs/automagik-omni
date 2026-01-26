"""Audio processor using Groq Whisper for transcription."""

import logging
import time
from pathlib import Path
from typing import Optional

from .base import BaseProcessor, ProcessingResult

logger = logging.getLogger(__name__)


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

    async def process(
        self,
        file_path: Path,
        mime_type: str,
        language: Optional[str] = None,
        **kwargs,
    ) -> ProcessingResult:
        """
        Transcribe audio file using Groq Whisper.

        Args:
            file_path: Path to the audio file
            mime_type: MIME type of the audio
            language: Language code (e.g., 'pt', 'en'). Defaults to Portuguese.

        Returns:
            ProcessingResult with transcription
        """
        start_time = time.time()
        language = language or self.default_language

        # Try Groq first (faster and cheaper)
        result = await self._transcribe_with_groq(file_path, language)

        # If Groq fails, try OpenAI fallback
        if not result.success and self.openai_api_key:
            logger.info("Groq transcription failed, trying OpenAI fallback...")
            result = await self._transcribe_with_openai(file_path, language)

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        result.processing_time_ms = processing_time_ms

        if result.success:
            logger.info(f"Audio transcription successful in {processing_time_ms}ms")
        else:
            logger.error(f"Audio transcription failed: {result.error_message}")

        return result

    async def _transcribe_with_groq(
        self,
        file_path: Path,
        language: str,
    ) -> ProcessingResult:
        """Transcribe using Groq Whisper API."""
        client = self._get_groq_client()
        if not client:
            return ProcessingResult(
                success=False,
                error_message="Groq client not configured (missing API key or package)",
            )

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
            logger.error(f"Groq transcription error: {e}")
            return ProcessingResult(
                success=False,
                processor_name="groq_whisper",
                processor_model="whisper-large-v3-turbo",
                error_message=str(e),
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
