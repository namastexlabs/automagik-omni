"""
Media Processing Service - orchestrates media content extraction.

Handles:
- Downloading media from URLs (WhatsApp encrypted, Discord CDN)
- Routing to appropriate processor (audio, image, document)
- Storing results in omni_media_content table
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime

import httpx

from sqlalchemy.orm import Session

from src.db.trace_models import MediaContent
from src.db.database import get_db
from src.services.settings_service import settings_service
from .processors.audio import AudioProcessor

logger = logging.getLogger(__name__)


class MediaProcessingService:
    """
    Main service for processing media messages.

    Usage:
        result = await media_processing_service.process_audio(
            instance_name="my-instance",
            message_id="ABC123",
            channel_type="whatsapp",
            media_url="https://...",
            mime_type="audio/ogg",
        )
    """

    def __init__(self):
        self._audio_processor: Optional[AudioProcessor] = None
        self._settings_loaded = False

    def _load_settings(self, db: Optional[Session] = None):
        """Load API keys and settings from database."""
        if self._settings_loaded:
            return

        # Get database session if not provided
        close_db = False
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            close_db = True

        try:
            # Load API keys from settings or environment
            groq_key = self._get_setting("groq_api_key", db) or os.environ.get("GROQ_API_KEY")
            openai_key = self._get_setting("openai_api_key", db) or os.environ.get("OPENAI_API_KEY")
            # gemini_key will be used for image processing (Phase 5)
            # gemini_key = self._get_setting("gemini_api_key", db) or os.environ.get("GEMINI_API_KEY")

            # Initialize processors
            if groq_key or openai_key:
                self._audio_processor = AudioProcessor(
                    groq_api_key=groq_key,
                    openai_api_key=openai_key,
                )
                logger.info("AudioProcessor initialized")

            self._settings_loaded = True

        finally:
            if close_db:
                db.close()

    def _get_setting(self, key: str, db: Session) -> Optional[str]:
        """Get a setting value from the database."""
        try:
            setting = settings_service.get_setting(key, db)
            return setting.value if setting else None
        except Exception:
            return None

    async def process_audio(
        self,
        instance_name: str,
        message_id: str,
        channel_type: str,
        media_url: str,
        mime_type: str,
        media_key: Optional[str] = None,  # For WhatsApp encrypted media
        media_size: Optional[int] = None,
        duration_seconds: Optional[int] = None,
        language: str = "pt",
        db: Optional[Session] = None,
    ) -> Optional[MediaContent]:
        """
        Process an audio message and store the transcription.

        Args:
            instance_name: The instance this message belongs to
            message_id: Original message ID (WhatsApp key.id or Discord message.id)
            channel_type: 'whatsapp' or 'discord'
            media_url: URL to download the media from
            mime_type: MIME type of the audio
            media_key: WhatsApp media key for decryption (base64)
            media_size: Size of the media in bytes
            duration_seconds: Duration of the audio
            language: Language code for transcription
            db: Database session (will create one if not provided)

        Returns:
            MediaContent record with transcription, or None on failure
        """
        self._load_settings(db)

        if not self._audio_processor:
            logger.error("Audio processor not configured (missing API keys)")
            return None

        # Get or create database session
        close_db = False
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            close_db = True

        try:
            # Check if already processed
            existing = (
                db.query(MediaContent)
                .filter_by(
                    instance_name=instance_name,
                    original_message_id=message_id,
                    content_type="audio_transcript",
                )
                .first()
            )
            if existing and existing.status == "completed":
                logger.info(f"Audio already transcribed for message {message_id}")
                return existing

            # Create or update record
            if existing:
                media_content = existing
            else:
                media_content = MediaContent(
                    instance_name=instance_name,
                    channel_type=channel_type,
                    original_message_id=message_id,
                    content_type="audio_transcript",
                    source_media_type="audio",
                    content="",  # Will be updated after processing
                    media_url=media_url,
                    media_mime_type=mime_type,
                    media_size_bytes=media_size,
                    media_duration_seconds=duration_seconds,
                    media_key=media_key,
                    status="processing",
                )
                db.add(media_content)
                db.commit()
                db.refresh(media_content)

            # Update status to processing
            media_content.status = "processing"
            db.commit()

            # Download the media file
            file_path = await self._download_media(
                url=media_url,
                channel_type=channel_type,
                media_key=media_key,
                mime_type=mime_type,
            )

            if not file_path:
                media_content.status = "failed"
                media_content.error_message = "Failed to download media"
                media_content.retry_count += 1
                db.commit()
                return None

            try:
                # Process the audio
                result = await self._audio_processor.process(
                    file_path=file_path,
                    mime_type=mime_type,
                    language=language,
                )

                # Update record with result
                if result.success:
                    media_content.content = result.content or ""
                    media_content.content_format = result.content_format
                    media_content.processor_name = result.processor_name
                    media_content.processor_model = result.processor_model
                    media_content.processing_time_ms = result.processing_time_ms
                    media_content.confidence_score = result.confidence_score
                    media_content.status = "completed"
                    media_content.processed_at = datetime.utcnow()
                else:
                    media_content.status = "failed"
                    media_content.error_message = result.error_message
                    media_content.retry_count += 1

                db.commit()
                db.refresh(media_content)
                return media_content

            finally:
                # Clean up temp file
                if file_path.exists():
                    file_path.unlink()

        except Exception as e:
            logger.error(f"Error processing audio: {e}", exc_info=True)
            if media_content:
                media_content.status = "failed"
                media_content.error_message = str(e)
                db.commit()
            return None

        finally:
            if close_db:
                db.close()

    async def _download_media(
        self,
        url: str,
        channel_type: str,
        media_key: Optional[str] = None,
        mime_type: str = "audio/ogg",
    ) -> Optional[Path]:
        """
        Download media from URL to a temporary file.

        For WhatsApp: Uses decryption if media_key is provided
        For Discord: Direct download from CDN
        """
        # Determine file extension from mime type
        ext_map = {
            "audio/ogg": ".ogg",
            "audio/opus": ".opus",
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/wav": ".wav",
            "audio/webm": ".webm",
            "audio/flac": ".flac",
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        ext = ext_map.get(mime_type, ".bin")

        try:
            if channel_type == "whatsapp" and media_key:
                # Use WhatsApp decryption
                return await self._download_whatsapp_media(url, media_key, ext)
            else:
                # Direct download (Discord CDN or unencrypted)
                return await self._download_direct(url, ext)

        except Exception as e:
            logger.error(f"Error downloading media: {e}", exc_info=True)
            return None

    async def _download_direct(self, url: str, ext: str) -> Optional[Path]:
        """Download media directly from URL."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Create temp file
                fd, path = tempfile.mkstemp(suffix=ext)
                with os.fdopen(fd, "wb") as f:
                    f.write(response.content)

                logger.info(f"Downloaded {len(response.content)} bytes to {path}")
                return Path(path)

        except Exception as e:
            logger.error(f"Direct download failed: {e}")
            return None

    async def _download_whatsapp_media(
        self,
        url: str,
        media_key: str,
        ext: str,
    ) -> Optional[Path]:
        """Download and decrypt WhatsApp media."""
        try:
            from src.channels.whatsapp.whatsapp_media_decrypt import whatsapp_media_decryptor

            # Determine media type from extension
            media_type_map = {
                ".ogg": whatsapp_media_decryptor.MEDIA_TYPE_AUDIO,
                ".opus": whatsapp_media_decryptor.MEDIA_TYPE_AUDIO,
                ".mp3": whatsapp_media_decryptor.MEDIA_TYPE_AUDIO,
                ".m4a": whatsapp_media_decryptor.MEDIA_TYPE_AUDIO,
                ".wav": whatsapp_media_decryptor.MEDIA_TYPE_AUDIO,
                ".jpg": whatsapp_media_decryptor.MEDIA_TYPE_IMAGE,
                ".jpeg": whatsapp_media_decryptor.MEDIA_TYPE_IMAGE,
                ".png": whatsapp_media_decryptor.MEDIA_TYPE_IMAGE,
                ".webp": whatsapp_media_decryptor.MEDIA_TYPE_IMAGE,
                ".mp4": whatsapp_media_decryptor.MEDIA_TYPE_VIDEO,
                ".pdf": whatsapp_media_decryptor.MEDIA_TYPE_DOCUMENT,
            }
            media_type = media_type_map.get(ext, whatsapp_media_decryptor.MEDIA_TYPE_AUDIO)

            # Decrypt and save to temp file
            temp_path = whatsapp_media_decryptor.decrypt_and_save_temp(
                encrypted_url=url,
                media_key_b64=media_key,
                media_type=media_type,
            )

            if temp_path:
                logger.info(f"Decrypted WhatsApp media to {temp_path}")
                return Path(temp_path)
            else:
                logger.error("WhatsApp decryption returned no path")
                return None

        except Exception as e:
            logger.error(f"WhatsApp media decryption failed: {e}", exc_info=True)
            return None

    def get_transcript(
        self,
        instance_name: str,
        message_id: str,
        db: Optional[Session] = None,
    ) -> Optional[str]:
        """
        Get the transcription for a message if it exists.

        Returns:
            Transcription text or None if not available
        """
        close_db = False
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            close_db = True

        try:
            record = (
                db.query(MediaContent)
                .filter_by(
                    instance_name=instance_name,
                    original_message_id=message_id,
                    content_type="audio_transcript",
                    status="completed",
                )
                .first()
            )
            return record.content if record else None

        finally:
            if close_db:
                db.close()


# Singleton instance
media_processing_service = MediaProcessingService()
