"""
Media Processing Service - orchestrates media content extraction.

Handles:
- Downloading media from URLs (WhatsApp encrypted, Discord CDN)
- Extracting base64 from stored trace payloads (for reprocessing)
- Routing to appropriate processor (audio, image, document)
- Storing results in omni_media_content table
"""

import base64
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

import httpx

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.db.trace_models import MediaContent, MessageTrace, TracePayload
from src.db.database import get_db
from src.services.settings_service import settings_service
from src.utils.datetime_utils import utcnow
from .processors.audio import AudioProcessor
from .processors.image import ImageProcessor
from .processors.document import DocumentProcessor

logger = logging.getLogger(__name__)


class MediaProcessingService:
    """
    Main service for processing media messages.

    Usage:
        result = await media_processing_service.process_audio(...)
        result = await media_processing_service.process_image(...)
    """

    def __init__(self):
        self._audio_processor: Optional[AudioProcessor] = None
        self._image_processor: Optional[ImageProcessor] = None
        self._document_processor: Optional[DocumentProcessor] = None
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
            gemini_key = self._get_setting("gemini_api_key", db) or os.environ.get("GEMINI_API_KEY")

            # Initialize audio processor
            if groq_key or openai_key:
                self._audio_processor = AudioProcessor(
                    groq_api_key=groq_key,
                    openai_api_key=openai_key,
                )
                logger.info("AudioProcessor initialized")

            # Initialize image processor
            if gemini_key:
                self._image_processor = ImageProcessor(
                    gemini_api_key=gemini_key,
                )
                logger.info("ImageProcessor initialized")

            # Initialize document processor (PyMuPDF + Gemini fallback)
            self._document_processor = DocumentProcessor(
                gemini_api_key=gemini_key,  # Optional, for scanned PDF fallback
            )
            logger.info("DocumentProcessor initialized")

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

    async def process_image(
        self,
        instance_name: str,
        message_id: str,
        channel_type: str,
        media_url: str,
        mime_type: str,
        media_key: Optional[str] = None,
        media_size: Optional[int] = None,
        caption: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[MediaContent]:
        """
        Process an image message and store the description.

        Args:
            instance_name: The instance this message belongs to
            message_id: Original message ID
            channel_type: 'whatsapp' or 'discord'
            media_url: URL to download the media from
            mime_type: MIME type of the image
            media_key: WhatsApp media key for decryption
            media_size: Size of the media in bytes
            caption: Original caption (included in context)
            custom_prompt: Custom prompt for description
            db: Database session

        Returns:
            MediaContent record with description
        """
        self._load_settings(db)

        if not self._image_processor:
            logger.error("Image processor not configured (missing GEMINI_API_KEY)")
            return None

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
                    content_type="image_description",
                )
                .first()
            )
            if existing and existing.status == "completed":
                logger.info(f"Image already described for message {message_id}")
                return existing

            # Create or update record
            if existing:
                media_content = existing
            else:
                media_content = MediaContent(
                    instance_name=instance_name,
                    channel_type=channel_type,
                    original_message_id=message_id,
                    content_type="image_description",
                    source_media_type="image",
                    content="",
                    media_url=media_url,
                    media_mime_type=mime_type,
                    media_size_bytes=media_size,
                    media_key=media_key,
                    status="processing",
                )
                db.add(media_content)
                db.commit()
                db.refresh(media_content)

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
                # Build prompt with caption context if available
                prompt = custom_prompt
                if caption and not custom_prompt:
                    prompt = f"The user sent this image with the caption: '{caption}'\n\n{self._image_processor.prompt}"

                # Process the image
                result = await self._image_processor.process(
                    file_path=file_path,
                    mime_type=mime_type,
                    custom_prompt=prompt,
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
                if file_path.exists():
                    file_path.unlink()

        except Exception as e:
            logger.error(f"Error processing image: {e}", exc_info=True)
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

    async def reprocess_audio_from_trace(
        self,
        trace_id: str,
        language: str = "pt",
        db: Optional[Session] = None,
    ) -> Optional[MediaContent]:
        """
        Reprocess audio from a stored trace payload.

        Evolution API stores base64 in the webhook payload, so we can
        extract it directly without needing to re-download.

        Args:
            trace_id: The trace ID to reprocess
            language: Language code for transcription

        Returns:
            MediaContent record with transcription
        """
        self._load_settings(db)

        if not self._audio_processor:
            logger.error("Audio processor not configured (missing API keys)")
            return None

        close_db = False
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            close_db = True

        try:
            # Get trace and payload
            trace = db.query(MessageTrace).filter_by(trace_id=trace_id).first()
            if not trace:
                logger.error(f"Trace {trace_id} not found")
                return None

            if trace.message_type not in ["audio", "audioMessage", "ptt", "voice"]:
                logger.warning(f"Trace {trace_id} is not an audio message: {trace.message_type}")
                return None

            # Get the payload
            payload = db.query(TracePayload).filter_by(trace_id=trace_id, stage="webhook_received").first()
            if not payload:
                logger.error(f"No payload found for trace {trace_id}")
                return None

            payload_data = payload.get_payload()
            if not payload_data:
                logger.error(f"Could not decompress payload for trace {trace_id}")
                return None

            # Extract base64 from payload
            msg = payload_data.get("data", {}).get("message", {})
            b64_data = msg.get("base64")

            if not b64_data:
                logger.error(f"No base64 data in trace {trace_id}")
                return None

            # Get audio metadata
            audio_msg = msg.get("audioMessage", {})
            mime_type = audio_msg.get("mimetype", "audio/ogg")
            # Clean mime type (remove codecs info)
            if ";" in mime_type:
                mime_type = mime_type.split(";")[0].strip()

            duration = audio_msg.get("seconds")
            file_length = audio_msg.get("fileLength", {})
            if isinstance(file_length, dict):
                size_bytes = file_length.get("low", 0)
            else:
                size_bytes = file_length

            # Get or extract message ID
            key_data = payload_data.get("data", {}).get("key", {})
            message_id = key_data.get("id") or trace.whatsapp_message_id or trace_id

            # Decode base64 and save to temp file
            audio_bytes = base64.b64decode(b64_data)
            ext = ".ogg" if "ogg" in mime_type else ".mp3"
            fd, temp_path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(fd, "wb") as f:
                f.write(audio_bytes)

            try:
                # Check if already processed
                existing = (
                    db.query(MediaContent)
                    .filter_by(
                        instance_name=trace.instance_name,
                        original_message_id=message_id,
                        content_type="audio_transcript",
                    )
                    .first()
                )

                if existing and existing.status == "completed":
                    logger.info(f"Audio already transcribed for trace {trace_id}")
                    return existing

                # Create or update record
                if existing:
                    media_content = existing
                else:
                    media_content = MediaContent(
                        instance_name=trace.instance_name,
                        channel_type="whatsapp",
                        original_message_id=message_id,
                        content_type="audio_transcript",
                        source_media_type="audio",
                        content="",
                        media_mime_type=mime_type,
                        media_size_bytes=size_bytes,
                        media_duration_seconds=duration,
                        status="processing",
                    )
                    db.add(media_content)
                    db.commit()
                    db.refresh(media_content)

                media_content.status = "processing"
                db.commit()

                # Process the audio
                result = await self._audio_processor.process(
                    file_path=Path(temp_path),
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
                    logger.info(f"Transcribed trace {trace_id}: {result.content[:50]}...")
                else:
                    media_content.status = "failed"
                    media_content.error_message = result.error_message
                    media_content.retry_count += 1
                    logger.error(f"Failed to transcribe trace {trace_id}: {result.error_message}")

                db.commit()
                db.refresh(media_content)
                return media_content

            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Error reprocessing trace {trace_id}: {e}", exc_info=True)
            return None

        finally:
            if close_db:
                db.close()

    async def batch_reprocess_audio(
        self,
        instance_name: Optional[str] = None,
        days_back: int = 30,
        limit: int = 100,
        language: str = "pt",
        db: Optional[Session] = None,
    ) -> dict:
        """
        Batch reprocess audio messages from traces.

        Args:
            instance_name: Filter by instance (optional)
            days_back: How many days back to look
            limit: Maximum number of messages to process
            language: Language code for transcription

        Returns:
            dict with processing stats
        """
        close_db = False
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            close_db = True

        try:
            # Find audio traces that haven't been processed
            cutoff_date = utcnow() - timedelta(days=days_back)

            query = db.query(MessageTrace).filter(
                and_(
                    MessageTrace.message_type.in_(["audio", "audioMessage", "ptt", "voice"]),
                    MessageTrace.has_media == True,  # noqa: E712
                    MessageTrace.received_at >= cutoff_date,
                )
            )

            if instance_name:
                query = query.filter(MessageTrace.instance_name == instance_name)

            # Exclude already processed
            processed_ids_subq = (
                db.query(MediaContent.original_message_id)
                .filter(
                    MediaContent.content_type == "audio_transcript",
                    MediaContent.status == "completed",
                )
                .scalar_subquery()
            )

            traces = query.filter(~MessageTrace.whatsapp_message_id.in_(processed_ids_subq)).limit(limit).all()

            logger.info(f"Found {len(traces)} audio traces to reprocess")

            stats = {
                "total": len(traces),
                "processed": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
            }

            for trace in traces:
                try:
                    result = await self.reprocess_audio_from_trace(
                        trace_id=trace.trace_id,
                        language=language,
                        db=db,
                    )

                    if result and result.status == "completed":
                        stats["processed"] += 1
                        stats["results"].append(
                            {
                                "trace_id": trace.trace_id,
                                "status": "completed",
                                "content_preview": result.content[:100] if result.content else "",
                            }
                        )
                    elif result:
                        stats["failed"] += 1
                        stats["results"].append(
                            {
                                "trace_id": trace.trace_id,
                                "status": "failed",
                                "error": result.error_message,
                            }
                        )
                    else:
                        stats["skipped"] += 1

                except Exception as e:
                    logger.error(f"Error processing trace {trace.trace_id}: {e}")
                    stats["failed"] += 1
                    stats["results"].append(
                        {
                            "trace_id": trace.trace_id,
                            "status": "error",
                            "error": str(e),
                        }
                    )

            return stats

        finally:
            if close_db:
                db.close()

    async def reprocess_image_from_trace(
        self,
        trace_id: str,
        custom_prompt: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[MediaContent]:
        """
        Reprocess image from a stored trace payload.

        Args:
            trace_id: The trace ID to reprocess
            custom_prompt: Optional custom prompt for description

        Returns:
            MediaContent record with description
        """
        self._load_settings(db)

        if not self._image_processor:
            logger.error("Image processor not configured (missing GEMINI_API_KEY)")
            return None

        close_db = False
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            close_db = True

        try:
            # Get trace and payload
            trace = db.query(MessageTrace).filter_by(trace_id=trace_id).first()
            if not trace:
                logger.error(f"Trace {trace_id} not found")
                return None

            if trace.message_type not in ["image", "imageMessage"]:
                logger.warning(f"Trace {trace_id} is not an image message: {trace.message_type}")
                return None

            # Get the payload
            payload = db.query(TracePayload).filter_by(trace_id=trace_id, stage="webhook_received").first()
            if not payload:
                logger.error(f"No payload found for trace {trace_id}")
                return None

            payload_data = payload.get_payload()
            if not payload_data:
                logger.error(f"Could not decompress payload for trace {trace_id}")
                return None

            # Extract base64 from payload
            msg = payload_data.get("data", {}).get("message", {})
            b64_data = msg.get("base64")

            if not b64_data:
                logger.error(f"No base64 data in trace {trace_id}")
                return None

            # Get image metadata
            image_msg = msg.get("imageMessage", {})
            mime_type = image_msg.get("mimetype", "image/jpeg")
            if ";" in mime_type:
                mime_type = mime_type.split(";")[0].strip()

            caption = image_msg.get("caption")
            file_length = image_msg.get("fileLength", {})
            if isinstance(file_length, dict):
                size_bytes = file_length.get("low", 0)
            else:
                size_bytes = file_length

            # Get message ID
            key_data = payload_data.get("data", {}).get("key", {})
            message_id = key_data.get("id") or trace.whatsapp_message_id or trace_id

            # Decode base64 and save to temp file
            image_bytes = base64.b64decode(b64_data)
            ext = ".jpg" if "jpeg" in mime_type else ".png" if "png" in mime_type else ".webp"
            fd, temp_path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(fd, "wb") as f:
                f.write(image_bytes)

            try:
                # Check if already processed
                existing = (
                    db.query(MediaContent)
                    .filter_by(
                        instance_name=trace.instance_name,
                        original_message_id=message_id,
                        content_type="image_description",
                    )
                    .first()
                )

                if existing and existing.status == "completed":
                    logger.info(f"Image already described for trace {trace_id}")
                    return existing

                # Create or update record
                if existing:
                    media_content = existing
                else:
                    media_content = MediaContent(
                        instance_name=trace.instance_name,
                        channel_type="whatsapp",
                        original_message_id=message_id,
                        content_type="image_description",
                        source_media_type="image",
                        content="",
                        media_mime_type=mime_type,
                        media_size_bytes=size_bytes,
                        status="processing",
                    )
                    db.add(media_content)
                    db.commit()
                    db.refresh(media_content)

                media_content.status = "processing"
                db.commit()

                # Build prompt with caption context
                prompt = custom_prompt
                if caption and not custom_prompt:
                    prompt = f"The user sent this image with the caption: '{caption}'\n\n{self._image_processor.prompt}"

                # Process the image
                result = await self._image_processor.process(
                    file_path=Path(temp_path),
                    mime_type=mime_type,
                    custom_prompt=prompt,
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
                    logger.info(f"Described image trace {trace_id}: {result.content[:50]}...")
                else:
                    media_content.status = "failed"
                    media_content.error_message = result.error_message
                    media_content.retry_count += 1
                    logger.error(f"Failed to describe trace {trace_id}: {result.error_message}")

                db.commit()
                db.refresh(media_content)
                return media_content

            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Error reprocessing image trace {trace_id}: {e}", exc_info=True)
            return None

        finally:
            if close_db:
                db.close()

    async def batch_reprocess_images(
        self,
        instance_name: Optional[str] = None,
        days_back: int = 30,
        limit: int = 100,
        custom_prompt: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict:
        """
        Batch reprocess image messages from traces.

        Args:
            instance_name: Filter by instance (optional)
            days_back: How many days back to look
            limit: Maximum number of messages to process
            custom_prompt: Custom prompt for descriptions

        Returns:
            dict with processing stats
        """
        close_db = False
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            close_db = True

        try:
            cutoff_date = utcnow() - timedelta(days=days_back)

            query = db.query(MessageTrace).filter(
                and_(
                    MessageTrace.message_type.in_(["image", "imageMessage"]),
                    MessageTrace.has_media == True,  # noqa: E712
                    MessageTrace.received_at >= cutoff_date,
                )
            )

            if instance_name:
                query = query.filter(MessageTrace.instance_name == instance_name)

            # Exclude already processed
            processed_ids_subq = (
                db.query(MediaContent.original_message_id)
                .filter(
                    MediaContent.content_type == "image_description",
                    MediaContent.status == "completed",
                )
                .scalar_subquery()
            )

            traces = query.filter(~MessageTrace.whatsapp_message_id.in_(processed_ids_subq)).limit(limit).all()

            logger.info(f"Found {len(traces)} image traces to reprocess")

            stats = {
                "total": len(traces),
                "processed": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
            }

            for trace in traces:
                try:
                    result = await self.reprocess_image_from_trace(
                        trace_id=trace.trace_id,
                        custom_prompt=custom_prompt,
                        db=db,
                    )

                    if result and result.status == "completed":
                        stats["processed"] += 1
                        stats["results"].append(
                            {
                                "trace_id": trace.trace_id,
                                "status": "completed",
                                "content_preview": result.content[:100] if result.content else "",
                            }
                        )
                    elif result:
                        stats["failed"] += 1
                        stats["results"].append(
                            {
                                "trace_id": trace.trace_id,
                                "status": "failed",
                                "error": result.error_message,
                            }
                        )
                    else:
                        stats["skipped"] += 1

                except Exception as e:
                    logger.error(f"Error processing trace {trace.trace_id}: {e}")
                    stats["failed"] += 1
                    stats["results"].append(
                        {
                            "trace_id": trace.trace_id,
                            "status": "error",
                            "error": str(e),
                        }
                    )

            return stats

        finally:
            if close_db:
                db.close()

    async def process_document(
        self,
        instance_name: str,
        message_id: str,
        channel_type: str,
        media_url: str,
        mime_type: str,
        media_key: Optional[str] = None,
        media_size: Optional[int] = None,
        filename: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[MediaContent]:
        """
        Process a document message and store the extracted content.

        Args:
            instance_name: The instance this message belongs to
            message_id: Original message ID
            channel_type: 'whatsapp' or 'discord'
            media_url: URL to download the media from
            mime_type: MIME type of the document
            media_key: WhatsApp media key for decryption
            media_size: Size of the media in bytes
            filename: Original filename
            db: Database session

        Returns:
            MediaContent record with extracted content
        """
        self._load_settings(db)

        if not self._document_processor:
            logger.error("Document processor not initialized")
            return None

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
                    content_type="document_content",
                )
                .first()
            )
            if existing and existing.status == "completed":
                logger.info(f"Document already processed for message {message_id}")
                return existing

            # Create or update record
            if existing:
                media_content = existing
            else:
                media_content = MediaContent(
                    instance_name=instance_name,
                    channel_type=channel_type,
                    original_message_id=message_id,
                    content_type="document_content",
                    source_media_type="document",
                    content="",
                    media_url=media_url,
                    media_mime_type=mime_type,
                    media_size_bytes=media_size,
                    media_key=media_key,
                    status="processing",
                )
                db.add(media_content)
                db.commit()
                db.refresh(media_content)

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
                media_content.error_message = "Failed to download document"
                media_content.retry_count += 1
                db.commit()
                return None

            try:
                # Process the document
                result = await self._document_processor.process(
                    file_path=file_path,
                    mime_type=mime_type,
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
                if file_path.exists():
                    file_path.unlink()

        except Exception as e:
            logger.error(f"Error processing document: {e}", exc_info=True)
            if media_content:
                media_content.status = "failed"
                media_content.error_message = str(e)
                db.commit()
            return None

        finally:
            if close_db:
                db.close()

    async def reprocess_document_from_trace(
        self,
        trace_id: str,
        db: Optional[Session] = None,
    ) -> Optional[MediaContent]:
        """
        Reprocess document from a stored trace payload.

        Args:
            trace_id: The trace ID to reprocess

        Returns:
            MediaContent record with extracted content
        """
        self._load_settings(db)

        if not self._document_processor:
            logger.error("Document processor not initialized")
            return None

        close_db = False
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            close_db = True

        try:
            # Get trace and payload
            trace = db.query(MessageTrace).filter_by(trace_id=trace_id).first()
            if not trace:
                logger.error(f"Trace {trace_id} not found")
                return None

            if trace.message_type not in ["document", "documentMessage"]:
                logger.warning(f"Trace {trace_id} is not a document message: {trace.message_type}")
                return None

            # Get the payload
            payload = db.query(TracePayload).filter_by(trace_id=trace_id, stage="webhook_received").first()
            if not payload:
                logger.error(f"No payload found for trace {trace_id}")
                return None

            payload_data = payload.get_payload()
            if not payload_data:
                logger.error(f"Could not decompress payload for trace {trace_id}")
                return None

            # Extract base64 from payload
            msg = payload_data.get("data", {}).get("message", {})
            b64_data = msg.get("base64")

            if not b64_data:
                logger.error(f"No base64 data in trace {trace_id}")
                return None

            # Get document metadata
            doc_msg = msg.get("documentMessage", {})
            mime_type = doc_msg.get("mimetype", "application/pdf")
            if ";" in mime_type:
                mime_type = mime_type.split(";")[0].strip()

            file_length = doc_msg.get("fileLength", {})
            if isinstance(file_length, dict):
                size_bytes = file_length.get("low", 0)
            else:
                size_bytes = file_length

            # Get message ID
            key_data = payload_data.get("data", {}).get("key", {})
            message_id = key_data.get("id") or trace.whatsapp_message_id or trace_id

            # Decode base64 and save to temp file
            doc_bytes = base64.b64decode(b64_data)
            ext = ".pdf" if "pdf" in mime_type else ".docx" if "word" in mime_type else ".txt"
            fd, temp_path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(fd, "wb") as f:
                f.write(doc_bytes)

            try:
                # Check if already processed
                existing = (
                    db.query(MediaContent)
                    .filter_by(
                        instance_name=trace.instance_name,
                        original_message_id=message_id,
                        content_type="document_content",
                    )
                    .first()
                )

                if existing and existing.status == "completed":
                    logger.info(f"Document already processed for trace {trace_id}")
                    return existing

                # Create or update record
                if existing:
                    media_content = existing
                else:
                    media_content = MediaContent(
                        instance_name=trace.instance_name,
                        channel_type="whatsapp",
                        original_message_id=message_id,
                        content_type="document_content",
                        source_media_type="document",
                        content="",
                        media_mime_type=mime_type,
                        media_size_bytes=size_bytes,
                        status="processing",
                    )
                    db.add(media_content)
                    db.commit()
                    db.refresh(media_content)

                media_content.status = "processing"
                db.commit()

                # Process the document
                result = await self._document_processor.process(
                    file_path=Path(temp_path),
                    mime_type=mime_type,
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
                    logger.info(f"Processed document trace {trace_id}: {result.content[:50]}...")
                else:
                    media_content.status = "failed"
                    media_content.error_message = result.error_message
                    media_content.retry_count += 1
                    logger.error(f"Failed to process document trace {trace_id}: {result.error_message}")

                db.commit()
                db.refresh(media_content)
                return media_content

            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Error reprocessing document trace {trace_id}: {e}", exc_info=True)
            return None

        finally:
            if close_db:
                db.close()

    async def batch_reprocess_documents(
        self,
        instance_name: Optional[str] = None,
        days_back: int = 30,
        limit: int = 100,
        db: Optional[Session] = None,
    ) -> dict:
        """
        Batch reprocess document messages from traces.

        Args:
            instance_name: Filter by instance (optional)
            days_back: How many days back to look
            limit: Maximum number of documents to process

        Returns:
            dict with processing stats
        """
        close_db = False
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            close_db = True

        try:
            cutoff_date = utcnow() - timedelta(days=days_back)

            query = db.query(MessageTrace).filter(
                and_(
                    MessageTrace.message_type.in_(["document", "documentMessage"]),
                    MessageTrace.has_media == True,  # noqa: E712
                    MessageTrace.received_at >= cutoff_date,
                )
            )

            if instance_name:
                query = query.filter(MessageTrace.instance_name == instance_name)

            # Exclude already processed
            processed_ids_subq = (
                db.query(MediaContent.original_message_id)
                .filter(
                    MediaContent.content_type == "document_content",
                    MediaContent.status == "completed",
                )
                .scalar_subquery()
            )

            traces = query.filter(~MessageTrace.whatsapp_message_id.in_(processed_ids_subq)).limit(limit).all()

            logger.info(f"Found {len(traces)} document traces to reprocess")

            stats = {
                "total": len(traces),
                "processed": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
            }

            for trace in traces:
                try:
                    result = await self.reprocess_document_from_trace(
                        trace_id=trace.trace_id,
                        db=db,
                    )

                    if result and result.status == "completed":
                        stats["processed"] += 1
                        stats["results"].append(
                            {
                                "trace_id": trace.trace_id,
                                "status": "completed",
                                "content_preview": result.content[:100] if result.content else "",
                            }
                        )
                    elif result:
                        stats["failed"] += 1
                        stats["results"].append(
                            {
                                "trace_id": trace.trace_id,
                                "status": "failed",
                                "error": result.error_message,
                            }
                        )
                    else:
                        stats["skipped"] += 1

                except Exception as e:
                    logger.error(f"Error processing trace {trace.trace_id}: {e}")
                    stats["failed"] += 1
                    stats["results"].append(
                        {
                            "trace_id": trace.trace_id,
                            "status": "error",
                            "error": str(e),
                        }
                    )

            return stats

        finally:
            if close_db:
                db.close()


# Singleton instance
media_processing_service = MediaProcessingService()
