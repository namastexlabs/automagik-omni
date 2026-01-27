"""
WhatsApp message handlers.
Processes incoming messages from the Evolution API.
Uses the Automagik API for user and session management.
"""

import hashlib
import logging
import threading
import time
from typing import Dict, Any, Optional, List
from collections import defaultdict
import queue
import requests
import json
import os
import base64

from src.services.message_router import message_router
from src.services.user_service import user_service
from src.channels.whatsapp.audio_transcriber import AudioTranscriptionService
from src.services.media_processing import media_processing_service
from src.services.settings_service import settings_service
from src.utils.datetime_utils import now, datetime_utcnow
from datetime import datetime

# Remove the circular import
# from src.channels.whatsapp.client import whatsapp_client, PresenceUpdater

# Configure logging
logger = logging.getLogger("src.channels.whatsapp.handlers")


class WhatsAppMessageHandler:
    """Handler for WhatsApp messages."""

    def __init__(self, send_response_callback=None):
        """Initialize the WhatsApp message handler.

        Args:
            send_response_callback: Callback function to send responses
        """
        self.message_queue = queue.Queue()
        self.processing_thread = None
        self.is_running = False
        self.send_response_callback = send_response_callback
        self.audio_transcriber = AudioTranscriptionService()

        # Debounce management (per-instance, per-user)
        # Structure: {instance_name: {user_key: [messages]}}
        self._debounce_buffers: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        # Structure: {instance_name: {user_key: Timer}}
        self._debounce_timers: Dict[str, Dict[str, threading.Timer]] = defaultdict(dict)
        # Structure: {instance_name: Lock}
        self._debounce_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)

    def start(self):
        """Start the message processing thread."""
        if self.processing_thread is None or not self.processing_thread.is_alive():
            self.is_running = True
            self.processing_thread = threading.Thread(target=self._process_messages_loop)
            self.processing_thread.daemon = True
            self.processing_thread.start()

    def stop(self):
        """Stop the message processing thread."""
        self.is_running = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)

        # Cancel all pending debounce timers
        for instance_timers in self._debounce_timers.values():
            for timer in instance_timers.values():
                timer.cancel()

    def _get_user_key(self, message: Dict[str, Any]) -> str:
        """Extract user key (remoteJid) from message for per-user debounce buffering."""
        data = message.get("data", {})
        if "key" in data and "remoteJid" in data["key"]:
            return data["key"]["remoteJid"]
        return message.get("sender", "unknown")

    def _buffer_message(self, message: Dict[str, Any], instance_config, trace_context, debounce_seconds: int):
        """Buffer a message and start/restart the debounce timer.

        Args:
            message: The WhatsApp message data
            instance_config: Instance configuration
            trace_context: TraceContext for message lifecycle tracking
            debounce_seconds: Number of seconds to wait before flushing
        """
        instance_name = instance_config.name if instance_config else "default"
        user_key = self._get_user_key(message)

        with self._debounce_locks[instance_name]:
            # Add message to buffer
            self._debounce_buffers[instance_name][user_key].append(
                {
                    "message": message,
                    "instance_config": instance_config,
                    "trace_context": trace_context,
                }
            )

            # Cancel existing timer if any
            if user_key in self._debounce_timers[instance_name]:
                self._debounce_timers[instance_name][user_key].cancel()

            # Start new timer
            timer = threading.Timer(debounce_seconds, self._flush_user_buffer, args=(instance_name, user_key))
            timer.daemon = True
            timer.start()
            self._debounce_timers[instance_name][user_key] = timer

            buffer_count = len(self._debounce_buffers[instance_name][user_key])
            logger.debug(
                f"Buffered message for {user_key} (instance: {instance_name}), "
                f"buffer size: {buffer_count}, timer: {debounce_seconds}s"
            )

    def _flush_user_buffer(self, instance_name: str, user_key: str):
        """Flush the debounce buffer for a user and queue aggregated message.

        This is called when the debounce timer expires.
        """
        with self._debounce_locks[instance_name]:
            # Get and clear the buffer
            buffered_messages = self._debounce_buffers[instance_name].pop(user_key, [])

            # Clean up timer reference
            self._debounce_timers[instance_name].pop(user_key, None)

        if not buffered_messages:
            return

        logger.info(f"Flushing {len(buffered_messages)} buffered messages for {user_key}")

        # Aggregate messages
        aggregated = self._aggregate_messages(buffered_messages)

        # Queue the aggregated message for processing
        self.message_queue.put(aggregated)

    def _aggregate_messages(self, buffered_messages: List[Dict]) -> Dict:
        """Aggregate multiple buffered messages into a single message.

        Args:
            buffered_messages: List of message dicts with message, instance_config, trace_context

        Returns:
            Single aggregated message dict ready for processing
        """
        if len(buffered_messages) == 1:
            return buffered_messages[0]

        # Use the first message as the base
        first = buffered_messages[0]
        last = buffered_messages[-1]

        # Create aggregated message based on first message structure
        aggregated_message = first["message"].copy()
        aggregated_data = aggregated_message.get("data", {}).copy()

        # Extract text content from all messages
        text_parts = []
        for buf_msg in buffered_messages:
            msg = buf_msg["message"]
            msg_data = msg.get("data", {})
            msg_obj = msg_data.get("message", {})

            text = ""
            if isinstance(msg_obj, dict):
                if "conversation" in msg_obj:
                    text = msg_obj["conversation"]
                elif "extendedTextMessage" in msg_obj:
                    text = msg_obj["extendedTextMessage"].get("text", "")
                elif "imageMessage" in msg_obj:
                    text = msg_obj["imageMessage"].get("caption", "")
                elif "videoMessage" in msg_obj:
                    text = msg_obj["videoMessage"].get("caption", "")
                elif "documentMessage" in msg_obj:
                    text = msg_obj["documentMessage"].get("caption", "")

            if text:
                text_parts.append(text)

        # Combine text with separator
        aggregated_text = "\n---\n".join(text_parts)

        # Update the message object with aggregated text
        if "message" in aggregated_data:
            msg_obj = aggregated_data["message"].copy() if isinstance(aggregated_data.get("message"), dict) else {}
            # Set as conversation type for simplicity
            msg_obj["conversation"] = aggregated_text
            # Remove other text fields to avoid confusion
            msg_obj.pop("extendedTextMessage", None)
            aggregated_data["message"] = msg_obj
        else:
            aggregated_data["message"] = {"conversation": aggregated_text}

        aggregated_message["data"] = aggregated_data

        logger.info(f"Aggregated {len(buffered_messages)} messages into single message")

        # Use last message's trace context (most recent)
        return {
            "message": aggregated_message,
            "instance_config": first["instance_config"],
            "trace_context": last["trace_context"],
        }

    def handle_message(self, message: Dict[str, Any], instance_config=None, trace_context=None):
        """Queue a message for processing, with optional debounce buffering."""
        # Check if debounce is enabled for this instance
        debounce_seconds = getattr(instance_config, "message_debounce_seconds", 0) if instance_config else 0

        if debounce_seconds > 0:
            # Buffer the message with debounce
            self._buffer_message(message, instance_config, trace_context, debounce_seconds)
            logger.debug(f"Message buffered for debounce ({debounce_seconds}s): {message.get('event')}")
        else:
            # No debounce - queue directly
            message_with_config = {
                "message": message,
                "instance_config": instance_config,
                "trace_context": trace_context,
            }
            self.message_queue.put(message_with_config)
            logger.debug(f"Message queued for processing: {message.get('event')}")

        if instance_config:
            logger.debug(f"Using instance config: {instance_config.name} -> Agent: {instance_config.agent_id}")
        if trace_context:
            logger.debug(f"Message trace ID: {trace_context.trace_id}")

    def _process_messages_loop(self):
        """Process messages from the queue in a loop."""
        while self.is_running:
            try:
                # Get message with timeout to allow for clean shutdown
                message_data = self.message_queue.get(timeout=1.0)

                # Extract message, instance config, and trace context
                if isinstance(message_data, dict) and "message" in message_data:
                    message = message_data["message"]
                    instance_config = message_data.get("instance_config")
                    trace_context = message_data.get("trace_context")
                else:
                    # Backward compatibility for direct message data
                    message = message_data
                    instance_config = None
                    trace_context = None

                self._process_message(message, instance_config, trace_context)
                self.message_queue.task_done()
            except queue.Empty:
                # No messages, continue waiting
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)

    def _save_webhook_debug(self, message: Dict[str, Any], message_id: str):
        """Save webhook JSON and download media files when debug mode is enabled."""
        # Debug mode disabled - this feature has been removed
        return

        try:
            # Create debug directory
            debug_dir = "./webhook_debug"
            os.makedirs(debug_dir, exist_ok=True)

            # Save webhook JSON
            timestamp = now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"{timestamp}_{message_id}_webhook.json"
            json_path = os.path.join(debug_dir, json_filename)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(message, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved webhook JSON: {json_path}")

            # Download and save media files if base64 is present
            data = message.get("data", {})
            message_obj = data.get("message", {})

            # Check for base64 data in message
            base64_data = None
            if "base64" in message_obj:
                base64_data = message_obj["base64"]

            if base64_data:
                # Get media metadata for filename and type
                media_meta = {}
                media_type = "unknown"

                for media_type_key in [
                    "imageMessage",
                    "videoMessage",
                    "documentMessage",
                    "audioMessage",
                ]:
                    if media_type_key in message_obj:
                        media_meta = message_obj[media_type_key]
                        media_type = media_type_key.replace("Message", "")
                        break

                # Determine file extension from mimetype
                mime_type = media_meta.get("mimetype", "application/octet-stream")
                file_extension = self._get_file_extension_from_mime(mime_type)

                # Create filename
                filename = media_meta.get("fileName") or f"{timestamp}_{message_id}_{media_type}"
                if not filename.endswith(file_extension):
                    filename += file_extension

                # Save media file
                media_path = os.path.join(debug_dir, filename)
                try:
                    decoded_data = base64.b64decode(base64_data)
                    with open(media_path, "wb") as f:
                        f.write(decoded_data)
                    logger.info(f"Downloaded media file: {media_path} ({len(decoded_data)} bytes)")
                except Exception as e:
                    logger.error(f"Failed to save media file {media_path}: {e}")

        except Exception as e:
            logger.error(f"Failed to save webhook debug data: {e}")

    def _get_file_extension_from_mime(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/webm": ".webm",
            "audio/ogg": ".ogg",
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "audio/wav": ".wav",
            "application/pdf": ".pdf",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "text/plain": ".txt",
        }
        return mime_to_ext.get(mime_type, ".bin")

    def _process_media_content(
        self,
        message: Dict[str, Any],
        instance_config,
        is_audio_message: bool,
        is_media_message: bool,
        message_type: str,
    ) -> Optional[str]:
        """
        Process media content (audio/image) to extract text description.

        This method:
        - Checks if media processing is enabled
        - Transcribes audio messages using Groq/OpenAI Whisper
        - Describes images using Gemini Vision
        - Returns the processed text to be included in the message

        Args:
            message: The WhatsApp message data
            instance_config: Instance configuration
            is_audio_message: True if this is an audio message
            is_media_message: True if this is any media message
            message_type: The specific message type string

        Returns:
            Processed text content or None if processing not applicable/failed
        """
        import asyncio
        import tempfile
        import os as os_module

        try:
            # Check if media processing is enabled
            from src.db.database import get_db

            db_gen = get_db()
            db = next(db_gen)

            try:
                media_enabled = settings_service.get_setting_value("media_processing_enabled", db)
                if media_enabled is None:
                    media_enabled = True  # Default to enabled if setting doesn't exist
                elif isinstance(media_enabled, str):
                    media_enabled = media_enabled.lower() == "true"

                if not media_enabled:
                    logger.debug("Media processing is disabled")
                    return None

                # Get instance name, message ID, and sender ID
                instance_name = instance_config.name if instance_config else "default"
                data = message.get("data", {})
                key_data = data.get("key", {})
                message_id = key_data.get("id", "unknown")
                sender_id = key_data.get("remoteJid", "unknown")  # Who sent this message in this chat

                # Extract base64 data from message
                message_obj = data.get("message", {})
                base64_data = message_obj.get("base64") or data.get("base64")

                if not base64_data:
                    # Try to find base64 in media type objects
                    for media_key in ["audioMessage", "imageMessage", "videoMessage", "documentMessage"]:
                        if media_key in message_obj and isinstance(message_obj[media_key], dict):
                            if "base64" in message_obj[media_key]:
                                base64_data = message_obj[media_key]["base64"]
                                break

                if not base64_data:
                    logger.debug("No base64 data found in message for processing")
                    return None

                # Process audio messages
                if is_audio_message:
                    audio_meta = message_obj.get("audioMessage", {})
                    mime_type = audio_meta.get("mimetype", "audio/ogg")
                    if ";" in mime_type:
                        mime_type = mime_type.split(";")[0].strip()
                    duration = audio_meta.get("seconds")

                    # Get transcription language from settings
                    language = settings_service.get_setting_value("audio_transcription_language", db) or "pt"

                    logger.info(f"Processing audio message for transcription (duration: {duration}s, lang: {language})")

                    # Decode base64 and save to temp file
                    audio_bytes = base64.b64decode(base64_data)
                    ext = ".ogg" if "ogg" in mime_type else ".mp3" if "mp3" in mime_type else ".m4a"
                    fd, temp_path = tempfile.mkstemp(suffix=ext)
                    try:
                        with os_module.fdopen(fd, "wb") as f:
                            f.write(audio_bytes)

                        # Load settings and process
                        media_processing_service._load_settings(db)

                        if not media_processing_service._audio_processor:
                            logger.warning("Audio processor not configured (missing API keys)")
                            return None

                        # Run async processing
                        from pathlib import Path

                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(
                                media_processing_service._audio_processor.process(
                                    file_path=Path(temp_path),
                                    mime_type=mime_type,
                                    language=language,
                                )
                            )
                        finally:
                            loop.close()

                        if result.success and result.content:
                            logger.info(f"Audio transcribed: {result.content[:100]}...")
                            # Store in database for future reference
                            from src.db.trace_models import MediaContent
                            from src.utils.datetime_utils import utcnow

                            media_content = MediaContent(
                                instance_name=instance_name,
                                channel_type="whatsapp",
                                original_message_id=message_id,
                                sender_id=sender_id,
                                content_type="audio_transcript",
                                source_media_type="audio",
                                content=result.content,
                                content_format=result.content_format or "text",
                                processor_name=result.processor_name,
                                processor_model=result.processor_model,
                                processing_time_ms=result.processing_time_ms,
                                confidence_score=result.confidence_score,
                                media_mime_type=mime_type,
                                media_duration_seconds=duration,
                                status="completed",
                                processed_at=utcnow(),
                            )
                            db.add(media_content)
                            db.commit()

                            return f"[Audio Transcription]: {result.content}"
                        else:
                            logger.warning(f"Audio transcription failed: {result.error_message}")
                            return None
                    finally:
                        if os_module.path.exists(temp_path):
                            os_module.unlink(temp_path)

                # Process image messages
                elif message_type in ["imageMessage", "image"]:
                    image_meta = message_obj.get("imageMessage", {})
                    mime_type = image_meta.get("mimetype", "image/jpeg")
                    if ";" in mime_type:
                        mime_type = mime_type.split(";")[0].strip()
                    caption = image_meta.get("caption", "")

                    logger.info(f"Processing image message for description (mime: {mime_type})")

                    # Decode base64 and save to temp file
                    image_bytes = base64.b64decode(base64_data)
                    ext = ".jpg" if "jpeg" in mime_type else ".png" if "png" in mime_type else ".webp"
                    fd, temp_path = tempfile.mkstemp(suffix=ext)
                    try:
                        with os_module.fdopen(fd, "wb") as f:
                            f.write(image_bytes)

                        # Load settings and process
                        media_processing_service._load_settings(db)

                        if not media_processing_service._image_processor:
                            logger.warning("Image processor not configured (missing GEMINI_API_KEY)")
                            return None

                        # Build prompt with caption context
                        custom_prompt = None
                        if caption:
                            custom_prompt = f"The user sent this image with the caption: '{caption}'\n\n{media_processing_service._image_processor.prompt}"

                        # Run async processing
                        from pathlib import Path

                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(
                                media_processing_service._image_processor.process(
                                    file_path=Path(temp_path),
                                    mime_type=mime_type,
                                    custom_prompt=custom_prompt,
                                )
                            )
                        finally:
                            loop.close()

                        if result.success and result.content:
                            logger.info(f"Image described: {result.content[:100]}...")
                            # Store in database for future reference
                            from src.db.trace_models import MediaContent
                            from src.utils.datetime_utils import utcnow

                            media_content = MediaContent(
                                instance_name=instance_name,
                                channel_type="whatsapp",
                                original_message_id=message_id,
                                sender_id=sender_id,
                                content_type="image_description",
                                source_media_type="image",
                                content=result.content,
                                content_format=result.content_format or "text",
                                processor_name=result.processor_name,
                                processor_model=result.processor_model,
                                processing_time_ms=result.processing_time_ms,
                                confidence_score=result.confidence_score,
                                media_mime_type=mime_type,
                                status="completed",
                                processed_at=utcnow(),
                            )
                            db.add(media_content)
                            db.commit()

                            return f"[Image Description]: {result.content}"
                        else:
                            logger.warning(f"Image description failed: {result.error_message}")
                            return None
                    finally:
                        if os_module.path.exists(temp_path):
                            os_module.unlink(temp_path)

                # Process document messages
                elif message_type in ["documentMessage", "document"]:
                    doc_meta = message_obj.get("documentMessage", {})
                    mime_type = doc_meta.get("mimetype", "application/pdf")
                    if ";" in mime_type:
                        mime_type = mime_type.split(";")[0].strip()
                    filename = doc_meta.get("fileName", "document")

                    # Only process PDF and Word documents
                    supported_types = [
                        "application/pdf",
                        "application/msword",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "text/plain",
                    ]
                    if mime_type not in supported_types:
                        logger.debug(f"Document type {mime_type} not supported for processing")
                        return None

                    logger.info(f"Processing document: {filename} ({mime_type})")

                    # Decode base64 and save to temp file
                    doc_bytes = base64.b64decode(base64_data)
                    ext = ".pdf" if "pdf" in mime_type else ".docx" if "word" in mime_type else ".txt"
                    fd, temp_path = tempfile.mkstemp(suffix=ext)
                    try:
                        with os_module.fdopen(fd, "wb") as f:
                            f.write(doc_bytes)

                        # Load settings and process
                        media_processing_service._load_settings(db)

                        if not media_processing_service._document_processor:
                            logger.warning("Document processor not initialized")
                            return None

                        # Run async processing
                        from pathlib import Path

                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(
                                media_processing_service._document_processor.process(
                                    file_path=Path(temp_path),
                                    mime_type=mime_type,
                                )
                            )
                        finally:
                            loop.close()

                        if result.success and result.content:
                            logger.info(f"Document extracted: {result.content[:100]}...")
                            # Store in database for future reference
                            from src.db.trace_models import MediaContent
                            from src.utils.datetime_utils import utcnow

                            media_content = MediaContent(
                                instance_name=instance_name,
                                channel_type="whatsapp",
                                original_message_id=message_id,
                                sender_id=sender_id,
                                content_type="document_content",
                                source_media_type="document",
                                content=result.content,
                                content_format=result.content_format or "text",
                                processor_name=result.processor_name,
                                processor_model=result.processor_model,
                                processing_time_ms=result.processing_time_ms,
                                confidence_score=result.confidence_score,
                                media_mime_type=mime_type,
                                status="completed",
                                processed_at=utcnow(),
                            )
                            db.add(media_content)
                            db.commit()

                            # Truncate content for agent if too long
                            content_preview = result.content
                            if len(content_preview) > 4000:
                                content_preview = (
                                    content_preview[:4000] + f"\n\n[... truncated, {len(result.content)} total chars]"
                                )

                            return f"[Document Content - {filename}]: {content_preview}"
                        else:
                            logger.warning(f"Document extraction failed: {result.error_message}")
                            return None
                    finally:
                        if os_module.path.exists(temp_path):
                            os_module.unlink(temp_path)

                return None

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error processing media content: {e}", exc_info=True)
            return None

    def _save_to_omni_messages(
        self,
        message: Dict[str, Any],
        instance_config,
        trace_context,
        message_type: str,
    ) -> Optional[str]:
        """
        Save incoming webhook message to omni_messages table for unified message store.

        This enables:
        - Media processing on ALL messages (including historical sync)
        - Reduced dependency on Evolution API for message queries
        - Local message serving without Evolution API calls

        Args:
            message: The WhatsApp webhook message data
            instance_config: Instance configuration
            trace_context: TraceContext for message lifecycle tracking
            message_type: Detected message type (text, audio, image, etc.)

        Returns:
            The omni_message record ID if saved, None on error
        """
        try:
            from src.db.database import SessionLocal
            from src.db.trace_models import OmniMessageRecord
            from src.services.chat_id_resolver import ChatIdResolver

            # Extract message data
            data = message.get("data", {})
            key_data = data.get("key", {})
            message_obj = data.get("message", {})
            context_info = data.get("contextInfo", {})

            # Get platform message ID
            platform_message_id = key_data.get("id")
            if not platform_message_id:
                logger.debug("No message ID in webhook, skipping omni_messages save")
                return None

            # Get instance name
            instance_name = instance_config.name if instance_config else "default"

            # Determine chat ID and sender
            chat_id = key_data.get("remoteJid", "")
            is_from_me = key_data.get("fromMe", False)
            sender_id = key_data.get("participant") or (None if is_from_me else key_data.get("remoteJid"))
            sender_name = data.get("pushName", "")

            # Map message type to omni format
            type_map = {
                "text": "text",
                "conversation": "text",
                "extendedTextMessage": "text",
                "audioMessage": "audio",
                "audio": "audio",
                "voice": "audio",
                "ptt": "audio",
                "imageMessage": "image",
                "image": "image",
                "videoMessage": "video",
                "video": "video",
                "documentMessage": "document",
                "document": "document",
                "stickerMessage": "sticker",
                "contactMessage": "contact",
                "locationMessage": "location",
                "reactionMessage": "reaction",
            }
            omni_type = type_map.get(message_type, "unknown")

            # Extract text content
            text_content = None
            if message_type in ["text", "conversation"]:
                text_content = message_obj.get("conversation")
            elif message_type == "extendedTextMessage":
                text_content = message_obj.get("extendedTextMessage", {}).get("text")
            else:
                # For media messages, get caption
                for media_key in ["audioMessage", "imageMessage", "videoMessage", "documentMessage"]:
                    if media_key in message_obj:
                        text_content = message_obj[media_key].get("caption")
                        break

            # Determine if has media
            has_media = omni_type in ["audio", "image", "video", "document", "sticker"]

            # Extract media info
            media_url = None
            media_key = None
            media_mime_type = None
            media_size = None
            media_duration = None
            media_sha256 = None

            if has_media:
                # Check for mediaUrl at message level first (Evolution processed)
                media_url = message_obj.get("mediaUrl")

                for media_key_name in [
                    "audioMessage",
                    "imageMessage",
                    "videoMessage",
                    "documentMessage",
                    "stickerMessage",
                ]:
                    if media_key_name in message_obj:
                        media_data = message_obj[media_key_name]
                        if not media_url:
                            media_url = media_data.get("url")
                        media_key = media_data.get("mediaKey")
                        media_mime_type = media_data.get("mimetype")
                        # Handle fileLength which can be int or {low, high, unsigned}
                        file_length = media_data.get("fileLength")
                        if isinstance(file_length, dict):
                            media_size = file_length.get("low")
                        elif isinstance(file_length, int):
                            media_size = file_length
                        # Duration for audio/video
                        seconds = media_data.get("seconds")
                        if seconds:
                            if isinstance(seconds, dict):
                                media_duration = seconds.get("low")
                            else:
                                media_duration = seconds
                        # SHA256 for deduplication
                        media_sha256 = media_data.get("fileSha256")
                        if media_sha256 and len(media_sha256) > 64:
                            media_sha256 = media_sha256[:64]
                        break

            # Extract quoted message ID
            quoted_message_id = context_info.get("stanzaId") if context_info else None

            # Get message timestamp
            msg_timestamp = data.get("messageTimestamp")
            if msg_timestamp:
                if isinstance(msg_timestamp, (int, float)):
                    msg_timestamp = datetime.utcfromtimestamp(msg_timestamp)
                else:
                    msg_timestamp = datetime_utcnow()
            else:
                msg_timestamp = datetime_utcnow()

            # Create record ID
            record_id = OmniMessageRecord.generate_id(instance_name, platform_message_id)

            # Save to database
            db_session = SessionLocal()
            try:
                # Resolve canonical chat ID for unified conversations
                resolver = ChatIdResolver(db_session)
                canonical_chat_id = resolver.get_canonical_id(instance_name, chat_id)

                # Check if exists (upsert logic)
                existing = db_session.query(OmniMessageRecord).filter(OmniMessageRecord.id == record_id).first()

                if existing:
                    # Update only specific fields (don't overwrite content_raw)
                    if not existing.trace_id and trace_context:
                        existing.trace_id = trace_context.trace_id
                    # Update canonical_chat_id if not set
                    if not existing.canonical_chat_id:
                        existing.canonical_chat_id = canonical_chat_id
                    existing.updated_at = datetime_utcnow()
                    db_session.commit()
                    logger.debug(f"Updated existing omni_message: {record_id}")
                    return record_id

                # Create new record
                record = OmniMessageRecord(
                    id=record_id,
                    instance_name=instance_name,
                    channel_type="whatsapp",
                    chat_id=chat_id,
                    canonical_chat_id=canonical_chat_id,
                    platform_message_id=platform_message_id,
                    direction="outbound" if is_from_me else "inbound",
                    sender_id=sender_id,
                    sender_name=sender_name,
                    is_from_me=is_from_me,
                    message_type=omni_type,
                    content_text=text_content,
                    has_media=has_media,
                    media_url=media_url,
                    media_key=media_key,
                    media_mime_type=media_mime_type,
                    media_size_bytes=media_size,
                    media_duration_seconds=media_duration,
                    media_sha256=media_sha256,
                    media_status="pending" if has_media else "pending",
                    quoted_message_id=quoted_message_id,
                    source="webhook",
                    trace_id=trace_context.trace_id if trace_context else None,
                    message_timestamp=msg_timestamp,
                    created_at=datetime_utcnow(),
                    updated_at=datetime_utcnow(),
                )

                # Set JSON fields
                record.set_platform_key(key_data)
                record.set_content_raw(message_obj)
                if context_info:
                    record.set_context_info(context_info)

                db_session.add(record)
                db_session.commit()

                logger.info(
                    f"Saved webhook message to omni_messages: {record_id} (type={omni_type}, has_media={has_media})"
                )
                return record_id

            except Exception as e:
                logger.error(f"Error saving to omni_messages: {e}")
                db_session.rollback()
                return None
            finally:
                db_session.close()

        except Exception as e:
            logger.error(f"Error in _save_to_omni_messages: {e}", exc_info=True)
            return None

    def _process_message(self, message: Dict[str, Any], instance_config=None, trace_context=None):
        """
        Process a WhatsApp message.

        Args:
            message: WhatsApp message data
            instance_config: Instance configuration for multi-tenant support
            trace_context: TraceContext for message lifecycle tracking
        """
        try:
            # The message from Evolution API has a different structure from our previous code
            # Message data is usually in the 'data' field
            data = message.get("data", {})

            # Extract sender information from the proper location
            if "key" in data and "remoteJid" in data["key"]:
                sender_id = data["key"]["remoteJid"]
            else:
                logger.warning("Message does not contain remoteJid in the expected location")
                # Try to get it from the sender field directly
                sender_id = message.get("sender")

            if not sender_id:
                logger.error("No sender ID found in message, unable to process")
                return

            # Extract user name from pushName field if available
            user_name = data.get("pushName", "")
            if user_name:
                logger.info(f"User name extracted: {user_name}")
            else:
                logger.info("No pushName found in message data")

            # Save webhook debug data if enabled
            message_id = data.get("key", {}).get("id", f"msg_{int(time.time())}")
            self._save_webhook_debug(message, message_id)

            # Extract message type
            message_type = self._extract_message_type(message)
            if not message_type:
                logger.warning("Unable to determine message type")
                return

            # Only process text, audio and media messages, ignore other types
            is_text_message = message_type in [
                "text",
                "conversation",
                "extendedTextMessage",
            ]
            is_audio_message = message_type in ["audioMessage", "audio", "voice", "ptt"]
            is_media_message = message_type in [
                "imageMessage",
                "image",
                "videoMessage",
                "video",
                "documentMessage",
                "document",
                "audioMessage",
                "audio",
                "voice",
                "ptt",
            ]

            if not (is_text_message or is_audio_message or is_media_message):
                logger.info(f"Ignoring message of type {message_type} - only handling text, media and audio messages")
                return

            # ================= Save to Unified Message Store =================
            # Save to omni_messages for unified storage and media processing
            try:
                omni_message_id = self._save_to_omni_messages(
                    message=message,
                    instance_config=instance_config,
                    trace_context=trace_context,
                    message_type=message_type,
                )
                if omni_message_id:
                    logger.debug(f"Message saved to unified store: {omni_message_id}")
            except Exception as e:
                # Don't fail message processing if omni save fails
                logger.warning(f"Failed to save to omni_messages (non-fatal): {e}")

            # Start showing typing indicator immediately
            # Use evolution_api_sender for presence updates (RabbitMQ disabled)
            from src.channels.whatsapp.evolution_api_sender import evolution_api_sender

            presence_updater = evolution_api_sender.get_presence_updater(sender_id)
            presence_updater.start()
            processing_start_time = time.time()  # Record when processing started

            try:
                # Extract and normalize phone number
                phone_number = self._extract_phone_number(sender_id)
                formatted_phone = f"+{phone_number}"  # Ensure + prefix for international format

                # Create user dict for the agent API (let the agent handle user management)
                user_dict = {
                    "phone_number": formatted_phone,
                    "email": None,  # WhatsApp doesn't provide email
                    "user_data": {
                        "name": user_name or "WhatsApp User",  # Use pushName or fallback
                        "whatsapp_id": sender_id,
                        "source": "whatsapp",
                    },
                }

                logger.info(
                    f"Created user dict for agent API: phone={formatted_phone}, name={user_dict['user_data']['name']}"
                )

                # The agent API will be the source of truth for user_id
                # We'll get the actual user_id from the agent response after processing

                # Extract message content first
                message_content = self._extract_message_content(message)

                # ================= Media Processing (Transcription/Description) =================
                # Process audio and image messages to extract text content
                processed_media_text = self._process_media_content(
                    message=message,
                    instance_config=instance_config,
                    is_audio_message=is_audio_message,
                    is_media_message=is_media_message,
                    message_type=message_type,
                )
                if processed_media_text:
                    # Prepend the processed media content to the message
                    if message_content:
                        message_content = f"{processed_media_text}\n\n{message_content}"
                    else:
                        message_content = processed_media_text
                    logger.info(f"Added processed media content to message ({len(processed_media_text)} chars)")

                # Add quoted message context if present
                quoted_context = self._extract_quoted_context(message)
                if quoted_context:
                    message_content = f"{quoted_context}\n\n{message_content}"
                    logger.info("Added quoted message context to message content")

                # Prepend user name to message content if available (unless disabled)
                disable_prefix = (
                    getattr(instance_config, "disable_username_prefix", False) if instance_config else False
                )

                if not disable_prefix:
                    if user_name and message_content:
                        message_content = f"[{user_name}]: {message_content}"
                        logger.info("Appended user name to message content")
                    elif user_name and not message_content:
                        # For media messages without text content
                        message_content = f"[{user_name}]: "
                        logger.info("Added user name prefix for media message")
                else:
                    logger.debug("Username prefix disabled for this instance")

                # ================= Media Handling (Images, Videos, Documents) =================
                media_contents_to_send: Optional[List[Dict[str, Any]]] = None

                if is_media_message:
                    # Extract media URL for any media type
                    media_url_to_send = self._extract_media_url_from_payload(data)
                    if media_url_to_send:
                        logger.info(f"Media URL found in message: {self._truncate_url_for_logging(media_url_to_send)}")

                        # Media URL processing (Minio conversion removed)

                        # Extract metadata based on media type
                        message_obj = data.get("message", {})
                        media_meta = {}

                        if "imageMessage" in message_obj:
                            media_meta = message_obj.get("imageMessage", {})
                        elif "videoMessage" in message_obj:
                            media_meta = message_obj.get("videoMessage", {})
                        elif "documentMessage" in message_obj:
                            media_meta = message_obj.get("documentMessage", {})
                        elif "audioMessage" in message_obj:
                            media_meta = message_obj.get("audioMessage", {})

                        # Build media_contents payload as expected by Agent API
                        # PRIORITY 1: Use base64 data if available (preferred by agent API)
                        # Check for base64 in the correct location: data.message.base64
                        base64_data = None
                        message_obj = data.get("message", {})

                        # First check if base64 is directly in message object (correct location from logs)
                        if "base64" in message_obj:
                            base64_data = message_obj["base64"]
                            logger.debug("DEBUG: Found base64 in message object")

                        # Fallback: check if base64 is directly in data
                        elif "base64" in data:
                            base64_data = data["base64"]
                            logger.debug("DEBUG: Found base64 in data object")

                        # Fallback: check if base64 is nested in media type objects
                        else:
                            for media_type_key in [
                                "imageMessage",
                                "videoMessage",
                                "documentMessage",
                                "audioMessage",
                            ]:
                                if media_type_key in message_obj:
                                    media_obj = message_obj[media_type_key]
                                    logger.debug(
                                        f"DEBUG: Checking {media_type_key}, keys: {list(media_obj.keys()) if isinstance(media_obj, dict) else 'not dict'}"
                                    )
                                    if isinstance(media_obj, dict) and "base64" in media_obj:
                                        base64_data = media_obj["base64"]
                                        logger.debug(f"DEBUG: Found base64 in {media_type_key}")
                                        break

                        logger.debug(f"DEBUG: Looking for base64 in data. Keys in data: {list(data.keys())}")
                        logger.debug(f"DEBUG: Message keys: {list(data.get('message', {}).keys())}")
                        logger.debug(f"DEBUG: Root message keys: {list(message.keys())}")
                        if base64_data:
                            logger.debug(f"DEBUG: base64_data found (length: {len(base64_data)} chars)")
                        else:
                            logger.debug("DEBUG: No base64_data found anywhere")
                        media_item = {
                            "alt_text": message_content or message_type,
                            "mime_type": media_meta.get("mimetype", f"{message_type}/"),
                        }

                        # Default behavior: use base64 data if available
                        if base64_data:
                            # Use base64 data in the data field
                            media_item["data"] = base64_data
                            logger.info(f"Using base64 data for agent API (size: {len(base64_data)} chars)")
                        else:
                            # Use standard media URL as fallback
                            media_item["media_url"] = media_url_to_send
                            logger.warning(
                                f"No base64 data available, using media URL: {self._truncate_url_for_logging(media_url_to_send)}"
                            )

                        # Add type-specific metadata
                        if "imageMessage" in message_obj or "videoMessage" in message_obj:
                            media_item["width"] = media_meta.get("width", 0)
                            media_item["height"] = media_meta.get("height", 0)
                        elif "documentMessage" in message_obj:
                            media_item["name"] = media_meta.get("fileName", "document")
                            media_item["size_bytes"] = media_meta.get("fileLength", 0)
                        elif "audioMessage" in message_obj:
                            media_item["duration"] = media_meta.get("seconds", 0)
                            media_item["size_bytes"] = media_meta.get("fileLength", 0)
                            media_item["mimetype"] = media_meta.get("mimetype", "audio/ogg")

                        media_contents_to_send = [media_item]

                # ================= End Media Handling =============

                # Process all message types including audio (transcription no longer required)

                # Create agent config using instance-specific or global configuration
                if instance_config:
                    # Use per-instance Agno configuration
                    agent_config = {
                        "name": instance_config.agent_id or "default",
                        "agent_id": instance_config.agent_id or "default",
                        "type": "whatsapp",
                        "api_url": instance_config.agent_api_url,
                        "api_key": instance_config.agent_api_key,
                        "timeout": instance_config.agent_timeout,
                        "agent_type": getattr(instance_config, "agent_type", "agent"),
                        "stream_mode": getattr(instance_config, "agent_stream_mode", False),
                        "instance_config": instance_config,  # Pass the full config for routing decisions
                    }
                    logger.info(
                        f"Using Agno configuration: {instance_config.name} -> {instance_config.agent_id} (type: {instance_config.agent_type})"
                    )
                else:
                    # No instance configuration available - use defaults
                    agent_config = {"name": "", "type": "whatsapp"}
                    logger.warning("No instance configuration available - agent calls will likely fail")

                # Generate a session ID based on the sender's WhatsApp ID
                # Create a deterministic hash from the sender's WhatsApp ID
                hashlib.md5(sender_id.encode())

                # Create a readable session name based on instance and phone
                instance_prefix = instance_config.name if instance_config else "default"
                session_name = f"{instance_prefix}_{phone_number}"

                logger.info(f"Using session name: {session_name}")

                # Create or update user in our local database for stable identity
                local_user = None  # Initialize outside try block so it's accessible later
                try:
                    from src.db.database import SessionLocal

                    db_session = SessionLocal()
                    try:
                        # Get instance name for user creation
                        instance_name = instance_config.name if instance_config else "default"

                        # Create/update user with current session info
                        local_user = user_service.get_or_create_user_by_phone(
                            phone_number=formatted_phone,
                            instance_name=instance_name,
                            display_name=user_name,
                            session_name=session_name,
                            db=db_session,
                        )

                        logger.info(f"Local user created/updated: {local_user.id} for phone {formatted_phone}")
                    finally:
                        db_session.close()
                except Exception as e:
                    logger.error(f"Failed to create/update local user: {e}")
                    # Continue processing even if user creation fails

                # Determine message_type parameter for Agent API
                if is_media_message:
                    # For all media types (images, videos, documents), use the specific type
                    if message_type in ["imageMessage", "image"]:
                        message_type_param = "image"
                    elif message_type in ["videoMessage", "video"]:
                        message_type_param = "video"
                    elif message_type in ["documentMessage", "document"]:
                        message_type_param = "document"
                    else:
                        message_type_param = "media"  # fallback
                elif is_audio_message:
                    # Audio messages should be treated as audio, not text
                    message_type_param = "audio"
                else:
                    message_type_param = "text"

                # Use stored agent user_id if available from previous interactions
                # IMPORTANT: Check if the stored agent_user_id is from the same instance/agent
                agent_user_id = None

                if local_user and local_user.last_agent_user_id:
                    # Check if this is the same instance/agent combination
                    # For now, we'll clear the user_id if switching between instances
                    # TODO: In the future, store per-instance user_ids
                    stored_session_prefix = (
                        local_user.last_session_name_interaction.split("_")[0]
                        if local_user.last_session_name_interaction
                        else None
                    )
                    current_session_prefix = session_name.split("_")[0] if session_name else None

                    if stored_session_prefix == current_session_prefix:
                        agent_user_id = local_user.last_agent_user_id
                        logger.info(
                            f"Using stored agent user_id: {agent_user_id} for phone {formatted_phone} (same instance: {current_session_prefix})"
                        )
                    else:
                        logger.info(
                            f"Instance switch detected for {formatted_phone}: {stored_session_prefix} -> {current_session_prefix}, will create new session"
                        )
                else:
                    logger.info(
                        f"No stored agent user_id for phone {formatted_phone}, will create new user via agent API"
                    )

                logger.info(
                    f"Routing message to API for user {user_dict['phone_number']}, session {session_name}: {message_content}"
                )
                try:
                    # Fixed logic: Either use stored user_id OR user creation dict, never both as None
                    if agent_user_id:
                        # Use stored agent user_id, don't pass user dict
                        agent_response = message_router.route_message(
                            user_id=agent_user_id,
                            user=None,  # Don't pass user dict when we have user_id
                            session_name=session_name,
                            message_text=message_content,
                            message_type=message_type_param,
                            whatsapp_raw_payload=message,
                            session_origin="whatsapp",
                            agent_config=agent_config,
                            media_contents=media_contents_to_send,
                            trace_context=trace_context,
                        )
                        logger.info(f"Used existing user_id: {agent_user_id}")
                    else:
                        # No stored user_id, trigger user creation via user dict
                        agent_response = message_router.route_message(
                            user_id=None,  # Don't pass user_id when creating new user
                            user=user_dict,  # Pass user dict for creation
                            session_name=session_name,
                            message_text=message_content,
                            message_type=message_type_param,
                            whatsapp_raw_payload=message,
                            session_origin="whatsapp",
                            agent_config=agent_config,
                            media_contents=media_contents_to_send,
                            trace_context=trace_context,
                        )
                        logger.info(f"Triggered user creation for phone: {formatted_phone}")
                except TypeError as te:
                    # Fallback for older versions of MessageRouter without media parameters
                    logger.warning(f"Route_message did not accept media_contents parameter, retrying without it: {te}")
                    agent_response = message_router.route_message(
                        user_id=None,  # Let the agent API manage user creation and ID assignment
                        user=user_dict,
                        session_name=session_name,
                        message_text=message_content,
                        message_type=message_type_param,
                        whatsapp_raw_payload=message,
                        session_origin="whatsapp",
                        agent_config=agent_config,
                    )

                # Calculate elapsed time since processing started
                elapsed_time = time.time() - processing_start_time

                # Note: We're not using sleep anymore, just log the time
                logger.info(f"Processing completed in {elapsed_time:.2f}s")

                # Extract the current user_id from agent response (source of truth)
                current_user_id = None
                if isinstance(agent_response, dict) and "user_id" in agent_response:
                    current_user_id = agent_response["user_id"]
                    logger.info(f"Agent API returned current user_id: {current_user_id} for session {session_name}")

                    # Update our local user with the agent's user_id for future lookups
                    if local_user:
                        try:
                            from src.db.database import SessionLocal

                            db_session = SessionLocal()
                            try:
                                user_service.update_user_agent_id(local_user.id, current_user_id, db_session)
                                logger.info(f"Updated local user {local_user.id} with agent user_id: {current_user_id}")
                            finally:
                                db_session.close()
                        except Exception as e:
                            logger.error(f"Failed to update local user with agent user_id: {e}")
                    else:
                        logger.warning(
                            f"Cannot update agent user_id - local user not created for session {session_name}"
                        )

                # Extract message text and log additional information from agent response
                if isinstance(agent_response, dict):
                    # Full agent response structure
                    message_text = agent_response.get("message", "")
                    session_id = agent_response.get("session_id", "unknown")
                    success = agent_response.get("success", True)
                    tool_calls = agent_response.get("tool_calls", [])
                    usage = agent_response.get("usage", {})

                    # Update trace with session information
                    if trace_context:
                        trace_context.update_session_info(session_name, session_id)

                    # Log detailed agent response information
                    logger.info(
                        f"Agent response - Session: {session_id}, Success: {success}, Tools used: {len(tool_calls)}"
                    )
                    if current_user_id:
                        logger.info(f"Session {session_name} is now linked to user_id: {current_user_id}")
                    if usage:
                        logger.debug(f"Agent usage stats: {usage}")
                    if tool_calls:
                        logger.debug(
                            f"Tool calls made: {[tool.get('function', {}).get('name', 'unknown') for tool in tool_calls]}"
                        )

                    # Use the extracted message text
                    response_to_send = message_text
                elif isinstance(agent_response, str):
                    # Backward compatibility - direct string response
                    response_to_send = agent_response
                    logger.debug("Received legacy string response from agent")
                else:
                    # Fallback for unexpected response format
                    response_to_send = str(agent_response)
                    logger.warning(f"Unexpected agent response format: {type(agent_response)}")

                # Check if the response should be ignored
                if isinstance(response_to_send, str) and response_to_send.startswith("AUTOMAGIK:"):
                    logger.warning(
                        f"Ignoring AUTOMAGIK message for user {user_dict['phone_number']}, session {session_name}: {response_to_send}"
                    )
                else:
                    # Check if we have streaming chunks to send progressively
                    if isinstance(agent_response, dict) and "streaming_chunks" in agent_response:
                        streaming_chunks = agent_response.get("streaming_chunks", [])
                        if streaming_chunks:
                            logger.info(f"Sending {len(streaming_chunks)} streaming chunks progressively")
                            for i, chunk in enumerate(streaming_chunks):
                                # Send each chunk as a separate message
                                # First chunk gets the quoted message, rest don't
                                self._send_whatsapp_response(
                                    recipient=sender_id,
                                    text=chunk,
                                    quoted_message=message if i == 0 else None,
                                    trace_context=trace_context,
                                )
                                # Small delay between chunks for natural flow
                                if i < len(streaming_chunks) - 1:
                                    time.sleep(0.5)  # 500ms between chunks
                        else:
                            # No chunks, send the full response
                            self._send_whatsapp_response(
                                recipient=sender_id,
                                text=response_to_send,
                                quoted_message=message,
                                trace_context=trace_context,
                            )
                    else:
                        # Send the response immediately while the typing indicator is still active
                        # Include the original message for quoting (reply)
                        self._send_whatsapp_response(
                            recipient=sender_id,
                            text=response_to_send,
                            quoted_message=message,
                            trace_context=trace_context,
                        )

                    # Mark message as sent but let the typing indicator continue for a short time
                    # This creates a more natural transition
                    presence_updater.mark_message_sent()

                    # Log with the actual user_id from agent if available
                    if current_user_id:
                        logger.info(f"Sent agent response to user_id={current_user_id}, session_id={session_name}")
                    else:
                        logger.info(
                            f"Sent agent response to phone={user_dict['phone_number']}, session_id={session_name}"
                        )

            finally:
                # Make sure typing indicator is stopped even if processing fails
                presence_updater.stop()

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    def _send_whatsapp_response(
        self,
        recipient: str,
        text: str,
        quoted_message: Optional[Dict[str, Any]] = None,
        trace_context=None,
    ):
        """Send a response back via WhatsApp with optional message quoting."""
        response_payload = None
        success = False

        # Prepare payload for tracing
        send_payload = {
            "recipient": recipient,
            "text": text,
            "has_quoted_message": quoted_message is not None,
        }

        if self.send_response_callback:
            try:
                # The Evolution API sender now supports quoting
                success = self.send_response_callback(recipient, text, quoted_message)
                response_code = 201 if success else 400  # Simulate HTTP status codes

                if success:
                    # Extract just the phone number without the suffix for logging
                    clean_recipient = recipient.split("@")[0] if "@" in recipient else recipient
                    logger.info(f"➤ Sent response to {clean_recipient}")
                else:
                    logger.error(f"❌ Failed to send response to {recipient}")

            except Exception as e:
                logger.error(f"❌ Error sending response: {e}", exc_info=True)
                response_code = 500
                success = False
        else:
            logger.warning("⚠️ No send response callback set, message not sent")
            response_code = 500
            success = False

        # Log evolution send attempt to trace
        if trace_context:
            trace_context.log_evolution_send(send_payload, response_code, success)

        return response_payload

    def _extract_media_url_from_payload(self, data: dict) -> Optional[str]:
        """Extract media URL from WhatsApp message payload with retry logic for file availability."""
        try:
            # Log data structure summary without base64 content
            data_keys = list(data.keys())
            message_keys = list(data.get("message", {}).keys()) if isinstance(data.get("message"), dict) else []
            has_base64 = "base64" in str(data)
            logger.info(
                f"🔍 DEBUG: Data structure - keys: {data_keys}, message_keys: {message_keys}, has_base64: {has_base64}"
            )

            # PRIORITY 1: Check for Evolution API processed mediaUrl in message data
            message_data = data.get("message", {})
            if isinstance(message_data, dict) and "mediaUrl" in message_data:
                evolution_media_url = message_data["mediaUrl"]
                logger.info(
                    f"✅ Found Evolution API processed mediaUrl: {self._truncate_url_for_logging(str(evolution_media_url))}"
                )
                if evolution_media_url:
                    return self._check_and_wait_for_file_availability(evolution_media_url)
                else:
                    logger.warning("⚠️ Evolution mediaUrl exists but value is empty/None")

            # PRIORITY 2: Check for mediaUrl at top level (legacy)
            logger.info(f"🔍 DEBUG: Checking for top-level 'mediaUrl' key: {'mediaUrl' in data}")
            if "mediaUrl" in data:
                media_url = data["mediaUrl"]
                logger.info(f"✅ Found top-level mediaUrl with value: {self._truncate_url_for_logging(str(media_url))}")
                if media_url:
                    return self._check_and_wait_for_file_availability(media_url)
                else:
                    logger.warning("⚠️ Top-level mediaUrl key exists but value is empty/None")
            else:
                logger.warning("❌ No top-level 'mediaUrl' key found in data")

            # PRIORITY 3: Fallback to audioMessage URL (encrypted, needs decryption)
            if isinstance(message_data, dict):
                logger.info(f"🔍 DEBUG: Message data keys: {list(message_data.keys())}")

                # Check various message types for media URL
                media_types = [
                    "audioMessage",
                    "videoMessage",
                    "imageMessage",
                    "documentMessage",
                    "stickerMessage",
                ]

                for media_type in media_types:
                    if media_type in message_data:
                        media_info = message_data[media_type]
                        logger.info(
                            f"🔍 DEBUG: Found {media_type}, keys: {list(media_info.keys()) if isinstance(media_info, dict) else 'Not a dict'}"
                        )
                        if isinstance(media_info, dict) and "url" in media_info:
                            url = media_info["url"]
                            logger.info(
                                f"✓ Found {media_type} URL in message structure: {self._truncate_url_for_logging(url)}"
                            )
                            return self._check_and_wait_for_file_availability(url)

            logger.warning("⚠️ No media URL found in any location")
            return None

        except Exception as e:
            logger.error(f"Error extracting media URL: {e}")
            return None

    def _extract_media_key_from_payload(self, data: dict) -> Optional[str]:
        """Extract media key from WhatsApp message payload for encrypted files."""
        try:
            # Check in message structure for media key
            message_data = data.get("message", {})
            if isinstance(message_data, dict):
                # Check various message types for media key
                media_types = [
                    "audioMessage",
                    "videoMessage",
                    "imageMessage",
                    "documentMessage",
                ]

                for media_type in media_types:
                    if media_type in message_data:
                        media_info = message_data[media_type]
                        if isinstance(media_info, dict) and "mediaKey" in media_info:
                            media_key = media_info["mediaKey"]
                            logger.info(f"🔑 Found {media_type} mediaKey: {media_key[:20]}...")
                            return media_key

            logger.warning("⚠️ No media key found in message")
            return None

        except Exception as e:
            logger.error(f"Error extracting media key: {e}")
            return None

    def _check_and_wait_for_file_availability(self, url: str) -> str:
        """Check file availability with retry logic for Minio URLs."""
        if not url:
            return url

        # Add retry mechanism for file availability only for Minio URLs
        if url and "minio:9000" in url:
            logger.info(
                f"🔄 Found Minio URL, checking file availability with retries: {self._truncate_url_for_logging(url)}"
            )

            # Wait and retry to ensure file upload is complete
            max_retries = 3
            retry_delay = 2  # seconds

            for attempt in range(max_retries):
                if attempt > 0:
                    logger.info(
                        f"⏳ Waiting {retry_delay}s for file upload completion (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(retry_delay)

                # Quick head request to check file availability
                try:
                    response = requests.head(url, timeout=5)
                    if response.status_code == 200:
                        logger.info(f"✅ File confirmed available after {attempt + 1} attempts")
                        return url
                    elif response.status_code == 404:
                        logger.warning(f"⏳ File not yet available (404), attempt {attempt + 1}/{max_retries}")
                    else:
                        logger.warning(
                            f"⚠️ Unexpected response {response.status_code}, attempt {attempt + 1}/{max_retries}"
                        )
                except Exception as e:
                    logger.warning(f"⚠️ File availability check failed: {e}, attempt {attempt + 1}/{max_retries}")

            logger.warning(f"⚠️ File still not available after {max_retries} attempts, proceeding anyway")

        return url

    def _truncate_url_for_logging(self, url: str, max_length: int = 60) -> str:
        """Truncate a URL for logging to reduce verbosity.

        Args:
            url: The URL to truncate
            max_length: Maximum length to display

        Returns:
            Truncated URL suitable for logging
        """
        if not url or len(url) <= max_length:
            return url

        # Parse the URL
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)

            # Get the host and path
            host = parsed.netloc
            path = parsed.path

            # Truncate the path if it's too long
            if len(path) > 30:
                path_parts = path.split("/")
                if len(path_parts) > 4:
                    # Keep first 2 and last part
                    short_path = "/".join(path_parts[:2]) + "/.../" + path_parts[-1]
                else:
                    short_path = path[:15] + "..." + path[-15:]
            else:
                short_path = path

            # Format with just a hint of the query string
            query = parsed.query
            query_hint = "?" + query[:10] + "..." if query else ""

            return f"{parsed.scheme}://{host}{short_path}{query_hint}"

        except Exception:
            # If parsing fails, do a simple truncation
            return url[:30] + "..." + url[-30:]

    def _truncate_base64_for_logging(self, base64_data: str, prefix_length: int = 20, suffix_length: int = 10) -> str:
        """Truncate base64 data for logging to show start...end format.

        Args:
            base64_data: The base64 string to truncate
            prefix_length: Number of characters to show at the start
            suffix_length: Number of characters to show at the end

        Returns:
            Truncated base64 string in format "prefix...suffix"
        """
        if not base64_data:
            return base64_data
        if len(base64_data) <= prefix_length + suffix_length + 10:
            return base64_data
        return f"{base64_data[:prefix_length]}...{base64_data[-suffix_length:]}"

    def _extract_message_content(self, message: Dict[str, Any]) -> str:
        """
        Extract the text content from a WhatsApp message.

        Args:
            message: The WhatsApp message payload

        Returns:
            Extracted text content or empty string if not found
        """
        try:
            data = message.get("data", {})

            # Transcription disabled - process audio messages as raw audio

            # Check if we have a conversation message
            message_obj = data.get("message", {})

            # Try to find the message content in common places
            if isinstance(message_obj, dict):
                # Check for text message
                if "conversation" in message_obj:
                    return message_obj["conversation"]

                # Check for extended text message
                elif "extendedTextMessage" in message_obj:
                    return message_obj["extendedTextMessage"].get("text", "")

                # Check for button response
                elif "buttonsResponseMessage" in message_obj:
                    return message_obj["buttonsResponseMessage"].get("selectedDisplayText", "")

                # Check for list response
                elif "listResponseMessage" in message_obj:
                    return message_obj["listResponseMessage"].get("title", "")

                # Check for media captions (images, videos, documents)
                elif "imageMessage" in message_obj:
                    return message_obj["imageMessage"].get("caption", "")

                elif "videoMessage" in message_obj:
                    return message_obj["videoMessage"].get("caption", "")

                elif "documentMessage" in message_obj:
                    return message_obj["documentMessage"].get("caption", "")

            # If we have raw text content directly in the data
            if "body" in data:
                return data["body"]

            # For audio messages, return meaningful content to ensure proper session creation
            # Empty content can cause session management issues
            message_type = data.get("messageType", "")
            if message_type in ["audioMessage", "audio", "voice", "ptt"]:
                return "[Audio message - transcription will be handled by agent]"

            # For other message types, return empty string
            logger.warning(f"Could not extract message content from payload: {message}")
            return ""

        except Exception as e:
            logger.error(f"Error extracting message content: {e}", exc_info=True)
            return ""

    def _extract_quoted_context(self, message: Dict[str, Any]) -> str:
        """
        Extract quoted message context from WhatsApp message payload.

        Args:
            message: The WhatsApp message payload

        Returns:
            str: Formatted quoted message context or empty string if no quote
        """
        try:
            data = message.get("data", {})

            # Check for quoted message in contextInfo
            context_info = data.get("contextInfo", {})
            quoted_message = context_info.get("quotedMessage", {})

            if not quoted_message:
                # Also check in message.contextInfo structure
                message_obj = data.get("message", {})
                context_info = message_obj.get("contextInfo", {})
                quoted_message = context_info.get("quotedMessage", {})

            if quoted_message:
                # Extract quoted text content
                quoted_text = ""

                # Check different message types in quoted message
                if "conversation" in quoted_message:
                    quoted_text = quoted_message["conversation"]
                elif "extendedTextMessage" in quoted_message:
                    quoted_text = quoted_message["extendedTextMessage"].get("text", "")
                elif "imageMessage" in quoted_message:
                    quoted_text = quoted_message["imageMessage"].get("caption", "[Image]")
                elif "videoMessage" in quoted_message:
                    quoted_text = quoted_message["videoMessage"].get("caption", "[Video]")
                elif "documentMessage" in quoted_message:
                    quoted_text = quoted_message["documentMessage"].get("caption", "[Document]")
                elif "audioMessage" in quoted_message:
                    quoted_text = "[Audio Message]"

                if quoted_text:
                    # Format the quoted message context nicely
                    # Truncate long messages for better readability
                    if len(quoted_text) > 200:
                        quoted_text = quoted_text[:200] + "..."

                    return f"📝 **Replying to:** {quoted_text}"

            return ""

        except Exception as e:
            logger.error(f"Error extracting quoted context: {e}", exc_info=True)
            return ""

    def _extract_message_type(self, message: Dict[str, Any]) -> str:
        """
        Determine the message type from a WhatsApp message.

        Args:
            message: The WhatsApp message payload

        Returns:
            Message type (text, audio, image, etc.) or empty string if not determined
        """
        try:
            data = message.get("data", {})

            # First check if the messageType is already provided by Evolution API
            if "messageType" in data:
                msg_type = data["messageType"]
                # Normalize message types
                if msg_type == "pttMessage":
                    return "ptt"
                elif msg_type == "voiceMessage":
                    return "voice"
                elif msg_type == "audioMessage":
                    return "audio"
                return msg_type

            # Otherwise try to determine from the message object
            message_obj = data.get("message", {})

            if not message_obj or not isinstance(message_obj, dict):
                return ""

            # Check for common message types
            if "conversation" in message_obj:
                return "text"

            elif "extendedTextMessage" in message_obj:
                return "text"

            elif "audioMessage" in message_obj:
                return "audio"

            elif "pttMessage" in message_obj:
                return "ptt"

            elif "voiceMessage" in message_obj:
                return "voice"

            elif "imageMessage" in message_obj:
                return "image"

            elif "videoMessage" in message_obj:
                return "video"

            elif "documentMessage" in message_obj:
                return "document"

            elif "stickerMessage" in message_obj:
                return "sticker"

            elif "contactMessage" in message_obj:
                return "contact"

            elif "locationMessage" in message_obj:
                return "location"

            # Fallback to the event type if available
            if "event" in message:
                return message["event"]

            # Could not determine message type
            logger.warning(f"Could not determine message type from payload: {message}")
            return "unknown"

        except Exception as e:
            logger.error(f"Error determining message type: {e}", exc_info=True)
            return "unknown"

    def _extract_phone_number(self, sender_id: str) -> str:
        """Extract and normalize a phone number from WhatsApp ID.

        Args:
            sender_id: The WhatsApp ID (e.g., 123456789@s.whatsapp.net)

        Returns:
            Normalized phone number without prefixes or suffixes
        """
        # Remove @s.whatsapp.net suffix if present
        phone = sender_id.split("@")[0] if "@" in sender_id else sender_id

        # Remove any + at the beginning
        if phone.startswith("+"):
            phone = phone[1:]

        # Remove any spaces, dashes, or other non-numeric characters
        phone = "".join(filter(str.isdigit, phone))

        # For Brazilian numbers, ensure it includes the country code (55)
        if len(phone) <= 11 and not phone.startswith("55"):
            phone = f"55{phone}"

        logger.info(f"Extracted and normalized phone number from {sender_id}: {phone}")
        return phone


# Singleton instance - initialized without a callback
# The callback will be set later by the client
message_handler = WhatsAppMessageHandler()

# Set up the send response callback to use evolution_api_sender for webhook-based messaging
from src.channels.whatsapp.evolution_api_sender import evolution_api_sender

message_handler.send_response_callback = evolution_api_sender.send_text_message

# Start the message processing thread immediately
message_handler.start()
