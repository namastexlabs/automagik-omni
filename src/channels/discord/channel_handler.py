"""Discord Channel Handler Implementation.
This module implements the Discord channel handler for the automagik-omni system.
Provides multi-tenant Discord bot management with proper lifecycle control.
"""

import logging
import asyncio
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from src.channels.base import ChannelHandler, QRCodeResponse, ConnectionStatus
from src.db.models import InstanceConfig
from src.utils.dependency_guard import requires_feature, LazyImport, DependencyError
from src.services.message_router import message_router
from src.services.trace_service import TraceService
from src.services.media_processing import media_processing_service
from src.services.settings_service import settings_service
from src.db.database import SessionLocal
from src.utils.datetime_utils import utcnow, datetime_utcnow

# Lazy imports with dependency guards
discord = LazyImport("discord", "discord")
logger = logging.getLogger(__name__)
from src.channels.message_utils import extract_response_text


@dataclass
class DiscordBotInstance:
    """Container for Discord bot instance data."""

    client: Any  # discord.Client
    task: Optional[asyncio.Task] = None
    status: str = "disconnected"
    invite_url: Optional[str] = None
    error_message: Optional[str] = None


class ValidationError(Exception):
    """Discord configuration validation error."""

    pass


class DiscordChannelHandler(ChannelHandler):
    """Discord channel handler implementation."""

    def __init__(self):
        """Initialize Discord channel handler."""
        self._bot_instances: Dict[str, DiscordBotInstance] = {}
        # Cache agent user_id returned by downstream routers keyed by instance+discord user
        self._agent_user_cache: Dict[str, Dict[str, str]] = {}

    def _chunk_message(self, message: str, max_length: int = 2000, prefer_double_newline: bool = True) -> list[str]:
        """
        Split message into chunks that respect Discord's character limit.

        Smart splitting strategy:
        1. First, try to split at major section boundaries (double newline + header)
        2. Then at double newlines (\n\n) for natural paragraphs
        3. Then at single newlines
        4. Finally at sentence/word boundaries

        Args:
            message: Message text to split
            max_length: Maximum length per chunk (Discord hard limit: 2000)
            prefer_double_newline: Whether to prefer \\n\\n as split point (controlled by enable_auto_split)

        Returns:
            List of message chunks
        """
        if len(message) <= max_length:
            return [message]

        chunks = []
        remaining = message

        while remaining:
            if len(remaining) <= max_length:
                chunks.append(remaining)
                break

            # Try to split at a reasonable point
            chunk = remaining[:max_length]

            # Smart split point detection with priority order
            split_at = -1

            # Priority 1: Split before markdown headers (### or ##) with double newline
            if prefer_double_newline:
                # Look for pattern: \n\n### or \n\n##
                for header_pattern in ["\n\n### ", "\n\n## "]:
                    header_pos = chunk.rfind(header_pattern)
                    if header_pos > max_length * 0.3:  # At least 30% into the chunk
                        split_at = header_pos + 2  # Keep the \n\n at end of previous chunk
                        break

            # Priority 2: Split at double newlines (paragraph boundaries)
            if split_at == -1 and prefer_double_newline:
                double_nl = chunk.rfind("\n\n")
                if double_nl > max_length * 0.4:  # At least 40% into the chunk
                    split_at = double_nl + 2  # Include both newlines

            # Priority 3: Split at single newlines
            if split_at == -1:
                single_nl = chunk.rfind("\n")
                if single_nl > max_length * 0.5:  # At least 50% into the chunk
                    split_at = single_nl + 1

            # Priority 4: Split at sentence boundaries
            if split_at == -1:
                for sentence_end in [". ", "! ", "? "]:
                    last_occurrence = chunk.rfind(sentence_end)
                    if last_occurrence > max_length * 0.6:  # At least 60% into the chunk
                        split_at = last_occurrence + len(sentence_end)
                        break

            # Priority 5: Split at word boundary
            if split_at == -1:
                last_space = chunk.rfind(" ")
                if last_space > max_length * 0.7:  # At least 70% into the chunk
                    split_at = last_space + 1

            # Last resort: hard cut at max length
            if split_at == -1:
                split_at = max_length

            chunks.append(remaining[:split_at].rstrip())
            remaining = remaining[split_at:].lstrip()

        return chunks

    def _get_cached_agent_user_id(self, instance_name: str, discord_user_id: str) -> Optional[str]:
        """Return cached agent user id for an instance/user combination."""
        return self._agent_user_cache.get(instance_name, {}).get(discord_user_id)

    def _store_agent_user_id(self, instance_name: str, discord_user_id: str, agent_user_id: str) -> None:
        """Persist agent user id for reuse on subsequent messages."""
        if not agent_user_id:
            return
        cache = self._agent_user_cache.setdefault(instance_name, {})
        cache[discord_user_id] = agent_user_id

    def _serialize_message_for_trace(self, message) -> Dict[str, Any]:
        """Normalize discord.Message attributes into a trace-friendly payload."""

        author = getattr(message, "author", None)
        guild = getattr(message, "guild", None)
        channel = getattr(message, "channel", None)

        attachments = []
        for attachment in getattr(message, "attachments", []) or []:
            try:
                attachments.append(
                    {
                        "id": str(getattr(attachment, "id", "")),
                        "filename": getattr(attachment, "filename", None),
                        "content_type": getattr(attachment, "content_type", None),
                        "size": getattr(attachment, "size", None),
                        "url": getattr(attachment, "url", None),
                    }
                )
            except Exception:
                # Capture best-effort metadata without breaking tracing
                attachments.append({"error": "failed_to_serialize_attachment"})

        serialized = {
            "id": getattr(message, "id", None),
            "content": getattr(message, "content", None),
            "author": {
                "id": getattr(author, "id", None),
                "username": getattr(author, "name", None),
                "display_name": getattr(author, "display_name", None),
                "discriminator": getattr(author, "discriminator", None),
                "bot": getattr(author, "bot", None),
            }
            if author
            else None,
            "guild": {
                "id": getattr(guild, "id", None),
                "name": getattr(guild, "name", None),
            }
            if guild
            else None,
            "channel": {
                "id": getattr(channel, "id", None),
                "name": getattr(channel, "name", None),
            }
            if channel
            else None,
            "mentions": [getattr(m, "id", None) for m in getattr(message, "mentions", []) or []],
            "attachments": attachments,
        }

        return serialized

    async def _send_response_to_discord(
        self,
        channel,
        response: str,
        *,
        trace_context=None,
        instance: Optional[InstanceConfig] = None,
        session_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_response: Optional[Dict[str, Any]] = None,
        split_message: Optional[bool] = None,
    ) -> None:
        """Send response to Discord channel, handling message chunking + trace logging.

        Args:
            channel: Discord channel to send to
            response: Message text to send
            trace_context: Optional trace context for logging
            instance: Optional InstanceConfig for accessing enable_auto_split
            session_name: Optional session name for tracing
            metadata: Optional metadata dict
            agent_response: Optional agent response data
            split_message: Optional per-message override for splitting behavior
        """

        if not response:
            return

        metadata = metadata or {}
        channel_id = metadata.get("channel_id") or getattr(channel, "id", None)
        channel_name = metadata.get("channel_name") or getattr(channel, "name", None)

        # Determine whether to prefer \n\n for splitting
        # Priority: per-message override > instance config > default (True)
        if split_message is not None:
            prefer_double_newline = split_message
            logger.info(f"Discord: Using per-message split override: {prefer_double_newline}")
        elif instance and hasattr(instance, "enable_auto_split"):
            prefer_double_newline = instance.enable_auto_split
            logger.info(f"Discord: Using instance config enable_auto_split: {prefer_double_newline}")
        else:
            prefer_double_newline = True
            logger.info("Discord: Using default split behavior: True")

        chunks = self._chunk_message(response, prefer_double_newline=prefer_double_newline)
        send_payload = {
            "recipient": str(channel_id) if channel_id is not None else None,
            "channel_name": channel_name,
            "message_text": response,
            "chunk_count": len(chunks),
            "metadata": metadata,
        }

        success = True
        error_details = None

        try:
            for chunk in chunks:
                await channel.send(chunk)
                if len(chunks) > 1:
                    await asyncio.sleep(0.5)

        except Exception as e:
            success = False
            error_details = str(e)
            logger.error(f"Failed to send Discord response: {e}")
            try:
                await channel.send("Sorry, I encountered an error while processing your message.")
            except Exception:
                logger.warning("Discord fallback error message could not be delivered", exc_info=True)

        finally:
            trace_instance_name = instance.name if instance else metadata.get("instance_name")
            response_payload: Optional[Dict[str, Any]]
            if agent_response is None:
                response_payload = {"success": success}
            elif isinstance(agent_response, dict):
                response_payload = agent_response
            else:
                response_payload = {"agent_response": agent_response}

            try:
                TraceService.record_outbound_message(
                    instance_name=trace_instance_name,
                    channel_type="discord",
                    payload=send_payload,
                    response=response_payload,
                    success=success,
                    trace_context=trace_context,
                    session_name=session_name,
                    message_id=metadata.get("message_id"),
                    error=error_details,
                )
            except Exception:
                logger.warning("Failed to persist Discord outbound trace", exc_info=True)

    async def _process_discord_attachments(
        self,
        message,
        instance: InstanceConfig,
    ) -> Optional[str]:
        """
        Process Discord attachments (audio/images) and return text description.

        Args:
            message: Discord message object
            instance: Instance configuration

        Returns:
            Processed text content or None
        """
        import tempfile
        import os as os_module
        import httpx
        from pathlib import Path

        if not message.attachments:
            return None

        try:
            # Check if media processing is enabled
            db = SessionLocal()
            try:
                media_enabled = settings_service.get_setting_value("media_processing_enabled", db)
                if media_enabled is None:
                    media_enabled = True
                elif isinstance(media_enabled, str):
                    media_enabled = media_enabled.lower() == "true"

                if not media_enabled:
                    logger.debug("Media processing is disabled")
                    return None

                processed_texts = []

                for attachment in message.attachments:
                    content_type = attachment.content_type or ""
                    filename = attachment.filename.lower()

                    # Determine media type
                    is_audio = content_type.startswith("audio/") or any(
                        filename.endswith(ext) for ext in [".mp3", ".ogg", ".wav", ".m4a", ".opus", ".flac"]
                    )
                    is_image = content_type.startswith("image/") or any(
                        filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]
                    )
                    is_document = content_type in [
                        "application/pdf",
                        "application/msword",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "text/plain",
                    ] or any(filename.endswith(ext) for ext in [".pdf", ".doc", ".docx", ".txt"])

                    if not (is_audio or is_image or is_document):
                        continue

                    logger.info(f"Processing Discord attachment: {attachment.filename} ({content_type})")

                    # Download attachment
                    try:
                        async with httpx.AsyncClient(timeout=60.0) as client:
                            response = await client.get(attachment.url)
                            response.raise_for_status()
                            file_data = response.content
                    except Exception as e:
                        logger.error(f"Failed to download Discord attachment: {e}")
                        continue

                    # Determine extension and mime type
                    if is_audio:
                        ext = ".ogg" if "ogg" in content_type else ".mp3" if "mp3" in content_type else ".m4a"
                        mime_type = content_type if content_type else "audio/mpeg"
                    elif is_image:
                        ext = ".jpg" if "jpeg" in content_type else ".png" if "png" in content_type else ".webp"
                        mime_type = content_type if content_type else "image/jpeg"
                    else:  # is_document
                        ext = (
                            ".pdf"
                            if "pdf" in content_type or filename.endswith(".pdf")
                            else ".docx"
                            if "word" in content_type or filename.endswith((".doc", ".docx"))
                            else ".txt"
                        )
                        mime_type = content_type if content_type else "application/pdf"

                    # Save to temp file
                    fd, temp_path = tempfile.mkstemp(suffix=ext)
                    try:
                        with os_module.fdopen(fd, "wb") as f:
                            f.write(file_data)

                        # Load settings and process
                        media_processing_service._load_settings(db)

                        if is_audio:
                            if not media_processing_service._audio_processor:
                                logger.warning("Audio processor not configured")
                                continue

                            language = settings_service.get_setting_value("audio_transcription_language", db) or "pt"

                            result = await media_processing_service._audio_processor.process(
                                file_path=Path(temp_path),
                                mime_type=mime_type,
                                language=language,
                            )

                            if result.success and result.content:
                                logger.info(f"Discord audio transcribed: {result.content[:100]}...")
                                processed_texts.append(
                                    f"[Audio Transcription - {attachment.filename}]: {result.content}"
                                )

                                # Store in database
                                from src.db.trace_models import MediaContent

                                media_content = MediaContent(
                                    instance_name=instance.name,
                                    channel_type="discord",
                                    original_message_id=str(message.id),
                                    sender_id=str(message.author.id),
                                    content_type="audio_transcript",
                                    source_media_type="audio",
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

                        elif is_image:
                            if not media_processing_service._image_processor:
                                logger.warning("Image processor not configured")
                                continue

                            result = await media_processing_service._image_processor.process(
                                file_path=Path(temp_path),
                                mime_type=mime_type,
                            )

                            if result.success and result.content:
                                logger.info(f"Discord image described: {result.content[:100]}...")
                                processed_texts.append(f"[Image Description - {attachment.filename}]: {result.content}")

                                # Store in database
                                from src.db.trace_models import MediaContent

                                media_content = MediaContent(
                                    instance_name=instance.name,
                                    channel_type="discord",
                                    original_message_id=str(message.id),
                                    sender_id=str(message.author.id),
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

                        else:  # is_document
                            if not media_processing_service._document_processor:
                                logger.warning("Document processor not configured")
                                continue

                            result = await media_processing_service._document_processor.process(
                                file_path=Path(temp_path),
                                mime_type=mime_type,
                            )

                            if result.success and result.content:
                                logger.info(f"Discord document extracted: {result.content[:100]}...")
                                # Truncate content if too long
                                content_preview = result.content
                                if len(content_preview) > 4000:
                                    content_preview = (
                                        content_preview[:4000]
                                        + f"\n\n[... truncated, {len(result.content)} total chars]"
                                    )
                                processed_texts.append(f"[Document Content - {attachment.filename}]: {content_preview}")

                                # Store in database
                                from src.db.trace_models import MediaContent

                                media_content = MediaContent(
                                    instance_name=instance.name,
                                    channel_type="discord",
                                    original_message_id=str(message.id),
                                    sender_id=str(message.author.id),
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

                    finally:
                        if os_module.path.exists(temp_path):
                            os_module.unlink(temp_path)

                return "\n\n".join(processed_texts) if processed_texts else None

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error processing Discord attachments: {e}", exc_info=True)
            return None

    def _save_to_omni_messages(
        self,
        message,
        instance: InstanceConfig,
        trace_context,
    ) -> Optional[str]:
        """
        Save Discord message to omni_messages table for unified message store.

        This enables:
        - Unified message storage across all channels
        - Media processing consistency
        - Local message queries without external API calls

        Args:
            message: Discord message object
            instance: Instance configuration
            trace_context: Optional trace context

        Returns:
            The omni_message record ID if saved, None on error
        """
        try:
            from src.db.trace_models import OmniMessageRecord

            # Get platform message ID
            platform_message_id = str(message.id)

            # Determine message type and media info
            has_media = bool(message.attachments)
            message_type = "text"
            media_url = None
            media_mime_type = None
            media_size = None

            if message.attachments:
                attachment = message.attachments[0]  # Primary attachment
                content_type = attachment.content_type or ""
                filename = attachment.filename.lower()

                # Determine media type
                if content_type.startswith("audio/") or any(
                    filename.endswith(ext) for ext in [".mp3", ".ogg", ".wav", ".m4a"]
                ):
                    message_type = "audio"
                elif content_type.startswith("image/") or any(
                    filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]
                ):
                    message_type = "image"
                elif content_type.startswith("video/") or any(
                    filename.endswith(ext) for ext in [".mp4", ".mov", ".webm"]
                ):
                    message_type = "video"
                elif content_type in ["application/pdf", "application/msword"] or any(
                    filename.endswith(ext) for ext in [".pdf", ".doc", ".docx", ".txt"]
                ):
                    message_type = "document"

                media_url = attachment.url
                media_mime_type = content_type
                media_size = attachment.size

            # Determine chat ID
            chat_id = str(message.channel.id)

            # Create record ID
            record_id = OmniMessageRecord.generate_id(instance.name, platform_message_id)

            # Save to database
            db_session = SessionLocal()
            try:
                # Check if exists
                existing = db_session.query(OmniMessageRecord).filter(OmniMessageRecord.id == record_id).first()

                if existing:
                    # Update trace_id if not set
                    if not existing.trace_id and trace_context:
                        existing.trace_id = trace_context.trace_id
                    existing.updated_at = datetime_utcnow()
                    db_session.commit()
                    logger.debug(f"Updated existing Discord omni_message: {record_id}")
                    return record_id

                # Create platform key for Discord
                platform_key = {
                    "id": platform_message_id,
                    "channel_id": str(message.channel.id),
                    "guild_id": str(message.guild.id) if message.guild else None,
                    "author_id": str(message.author.id),
                }

                # Create raw content
                content_raw = {
                    "content": message.content,
                    "attachments": [
                        {
                            "id": str(a.id),
                            "filename": a.filename,
                            "content_type": a.content_type,
                            "size": a.size,
                            "url": a.url,
                        }
                        for a in message.attachments
                    ],
                    "author": {
                        "id": str(message.author.id),
                        "name": message.author.name,
                        "display_name": message.author.display_name,
                    },
                }

                # Create record
                record = OmniMessageRecord(
                    id=record_id,
                    instance_name=instance.name,
                    channel_type="discord",
                    chat_id=chat_id,
                    platform_message_id=platform_message_id,
                    direction="inbound",
                    sender_id=str(message.author.id),
                    sender_name=message.author.display_name or message.author.name,
                    is_from_me=False,
                    message_type=message_type,
                    content_text=message.content,
                    has_media=has_media,
                    media_url=media_url,
                    media_mime_type=media_mime_type,
                    media_size_bytes=media_size,
                    media_status="pending" if has_media else "pending",
                    source="webhook",
                    trace_id=trace_context.trace_id if trace_context else None,
                    message_timestamp=message.created_at.replace(tzinfo=None),
                    created_at=datetime_utcnow(),
                    updated_at=datetime_utcnow(),
                )

                # Set JSON fields
                record.set_platform_key(platform_key)
                record.set_content_raw(content_raw)

                db_session.add(record)
                db_session.commit()

                logger.info(
                    f"Saved Discord message to omni_messages: {record_id} (type={message_type}, has_media={has_media})"
                )
                return record_id

            except Exception as e:
                logger.error(f"Error saving Discord message to omni_messages: {e}")
                db_session.rollback()
                return None
            finally:
                db_session.close()

        except Exception as e:
            logger.error(f"Error in Discord _save_to_omni_messages: {e}", exc_info=True)
            return None

    async def _handle_message(self, message, instance: InstanceConfig, client) -> None:
        """Handle incoming Discord message with @mention detection."""
        try:
            # Ignore messages from the bot itself
            if message.author == client.user:
                return

            # Check if the bot is mentioned
            if not client.user.mentioned_in(message):
                return

            logger.info(
                f"Discord bot '{instance.name}' received mention from {message.author} in #{message.channel.name}"
            )

            # Extract message content after removing the mention
            content = message.content
            for mention in message.mentions:
                if mention == client.user:
                    # Remove the mention from the message
                    mention_pattern = f"<@{mention.id}>"
                    alt_mention_pattern = f"<@!{mention.id}>"
                    content = content.replace(mention_pattern, "").replace(alt_mention_pattern, "")

            # Clean up the message (strip whitespace)
            content = content.strip()

            # Process any attachments (audio/images)
            attachment_text = await self._process_discord_attachments(message, instance)
            if attachment_text:
                if content:
                    content = f"{attachment_text}\n\n{content}"
                else:
                    content = attachment_text
                logger.info(f"Added processed attachment content ({len(attachment_text)} chars)")

            if not content:
                await message.channel.send("Hi! How can I help you? Please include your message after mentioning me.")
                return

            # Create user dictionary similar to WhatsApp handler
            user_dict = {
                "discord_user_id": str(message.author.id),
                "username": message.author.name,
                "email": None,  # Discord doesn't provide email unless OAuth
                "user_data": {
                    "name": message.author.display_name or message.author.name,
                    "discord_discriminator": (
                        message.author.discriminator if hasattr(message.author, "discriminator") else None
                    ),
                    "guild_id": str(message.guild.id) if message.guild else None,
                    "guild_name": message.guild.name if message.guild else None,
                    "channel_id": str(message.channel.id),
                    "channel_name": (message.channel.name if hasattr(message.channel, "name") else None),
                },
            }

            # Generate session name similar to WhatsApp format
            session_name = (
                f"discord_{message.guild.id}_{message.author.id}"
                if message.guild
                else f"discord_dm_{message.author.id}"
            )

            logger.info(
                f"Processing Discord message: '{content}' from user: {message.author.name} in session: {session_name}"
            )

            db_session = None
            trace_context = None
            serialized_event = self._serialize_message_for_trace(message)

            try:
                db_session = SessionLocal()
                trace_payload = {
                    "channel_type": "discord",
                    "direction": "inbound",
                    "session_name": session_name,
                    "event": serialized_event,
                    "metadata": {
                        "instance_name": instance.name,
                        "guild_id": getattr(message.guild, "id", None),
                        "guild_name": getattr(message.guild, "name", None),
                        "channel_id": getattr(message.channel, "id", None),
                        "channel_name": getattr(message.channel, "name", None),
                        "author_name": user_dict["user_data"].get("name"),
                    },
                }

                trace_context = TraceService.create_trace(trace_payload, instance.name, db_session)
                if trace_context:
                    initial_logged = getattr(trace_context, "initial_stage_logged", False)
                    if not isinstance(initial_logged, bool) or not initial_logged:
                        trace_context.log_stage("webhook_received", trace_payload, "webhook")
                        trace_context.initial_stage_logged = True
                    trace_context.update_trace_status("processing", processing_started_at=utcnow())
                    logger.info(
                        "Discord trace started trace_id=%s message_id=%s instance=%s",
                        trace_context.trace_id,
                        serialized_event.get("id"),
                        instance.name,
                    )
            except Exception:
                logger.warning("Unable to initialize Discord trace context", exc_info=True)
                if db_session:
                    db_session.close()
                    db_session = None

            # ================= Save to Unified Message Store =================
            # Now that we have trace_context, save to omni_messages
            try:
                omni_message_id = self._save_to_omni_messages(
                    message=message,
                    instance=instance,
                    trace_context=trace_context,
                )
                if omni_message_id:
                    logger.debug(f"Discord message saved to unified store: {omni_message_id}")
            except Exception as e:
                logger.warning(f"Failed to save Discord message to omni_messages (non-fatal): {e}")

            cached_agent_user_id = self._get_cached_agent_user_id(instance.name, str(message.author.id))

            # Send typing indicator
            async with message.channel.typing():
                # Route message to MessageRouter (same as WhatsApp)
                try:
                    agent_response = message_router.route_message(
                        user_id=cached_agent_user_id,
                        user=user_dict if not cached_agent_user_id else None,
                        session_name=session_name,
                        message_text=content,
                        message_type="text",
                        session_origin="discord",
                        whatsapp_raw_payload=None,  # Discord doesn't use WhatsApp payload
                        media_contents=None,  # TODO: Handle Discord attachments if needed
                        trace_context=trace_context,
                    )

                    logger.info(
                        f"Got agent response for Discord user {message.author.name}: {len(str(agent_response))} characters"
                    )

                except TypeError as te:
                    # Fallback for older versions of MessageRouter without media parameters
                    logger.warning(f"Route_message did not accept media_contents parameter, retrying without it: {te}")
                    agent_response = message_router.route_message(
                        user_id=cached_agent_user_id,
                        user=user_dict if not cached_agent_user_id else None,
                        session_name=session_name,
                        message_text=content,
                        message_type="text",
                        session_origin="discord",
                        whatsapp_raw_payload=None,
                        trace_context=trace_context,
                    )

                    if agent_response:
                        response_text = extract_response_text(agent_response)
                        await self._send_response_to_discord(
                            message.channel,
                            response_text,
                            trace_context=trace_context,
                            instance=instance,
                            session_name=session_name,
                            metadata={
                                "instance_name": instance.name,
                                "channel_id": getattr(message.channel, "id", None),
                                "channel_name": getattr(message.channel, "name", None),
                                "guild_id": getattr(message.guild, "id", None),
                                "guild_name": getattr(message.guild, "name", None),
                            },
                            agent_response=agent_response,
                        )
                    else:
                        await message.channel.send(
                            "I'm sorry, I couldn't process your message right now. Please try again later."
                        )

                    if isinstance(agent_response, dict) and agent_response.get("user_id"):
                        self._store_agent_user_id(
                            instance.name,
                            str(message.author.id),
                            agent_response.get("user_id"),
                        )

                except Exception as e:
                    logger.error(f"Error processing Discord message: {e}", exc_info=True)
                    await message.channel.send(
                        "I encountered an error while processing your message. Please try again later."
                    )

                else:
                    if agent_response:
                        response_text = extract_response_text(agent_response)
                        await self._send_response_to_discord(
                            message.channel,
                            response_text,
                            trace_context=trace_context,
                            instance=instance,
                            session_name=session_name,
                            metadata={
                                "instance_name": instance.name,
                                "channel_id": getattr(message.channel, "id", None),
                                "channel_name": getattr(message.channel, "name", None),
                                "guild_id": getattr(message.guild, "id", None),
                                "guild_name": getattr(message.guild, "name", None),
                            },
                            agent_response=agent_response,
                        )
                    else:
                        await message.channel.send(
                            "I'm sorry, I couldn't process your message right now. Please try again later."
                        )

                    # Cache agent user id when provided
                    if isinstance(agent_response, dict) and agent_response.get("user_id"):
                        agent_user_id = agent_response.get("user_id")
                        self._store_agent_user_id(
                            instance.name,
                            str(message.author.id),
                            agent_user_id,
                        )

        except Exception as e:
            logger.error(f"Error in Discord message handler: {e}", exc_info=True)
        finally:
            if trace_context:
                try:
                    trace_context.db_session.close()
                except Exception:
                    logger.debug("Trace context session already closed", exc_info=True)
            elif db_session:
                try:
                    db_session.close()
                except Exception:
                    logger.debug("Discord handler session close failed", exc_info=True)

    def _validate_bot_config(self, instance: InstanceConfig) -> Dict[str, str]:
        """Validate and extract Discord bot configuration."""
        # Extract token from instance configuration only
        bot_token = getattr(instance, "discord_bot_token", None) or ""
        client_id = getattr(instance, "discord_client_id", None) or ""

        # Validate configuration values
        if not bot_token or bot_token.lower() in ["string", "null", "undefined", ""]:
            logger.error(f"Invalid Discord bot token for instance '{instance.name}'. Please provide a valid bot token.")
            raise ValidationError(
                f"Invalid Discord bot token for instance '{instance.name}'. Please provide a valid bot token from Discord Developer Portal."
            )

        if not client_id or client_id.lower() in ["string", "null", "undefined", ""]:
            logger.error(f"Invalid Discord client ID for instance '{instance.name}'. Please provide a valid client ID.")
            raise ValidationError(
                f"Invalid Discord client ID for instance '{instance.name}'. Please provide a valid client ID from Discord Developer Portal."
            )
        logger.debug(
            f"Discord config validated for instance '{instance.name}' - Token: {'*' * len(bot_token)}, Client ID: {client_id}"
        )

        return {"token": bot_token, "client_id": client_id}

    def _generate_invite_url(self, client_id: str, permissions: int = 8) -> str:
        """Generate Discord bot invite URL."""
        # Default permissions: Administrator (8) - can be customized based on needs
        # Common permissions combinations:
        # - Send Messages (2048) + Read Messages (1024) = 3072
        # - Administrator (8)
        # - Manage Messages (8192) + Send Messages (2048) + Read Messages (1024) = 11264
        base_url = "https://discord.com/api/oauth2/authorize"
        params = f"client_id={client_id}&permissions={permissions}&scope=bot%20applications.commands"
        return f"{base_url}?{params}"

    @requires_feature("discord")
    async def create_instance(self, instance: InstanceConfig, **kwargs) -> Dict[str, Any]:
        """Create a new Discord bot instance."""
        try:
            logger.info(f"Creating Discord bot instance '{instance.name}'...")
            # Check if instance already exists
            if instance.name in self._bot_instances:
                existing_bot = self._bot_instances[instance.name]
                logger.info(f"Discord bot instance '{instance.name}' already exists with status: {existing_bot.status}")

                if existing_bot.status == "connected":
                    logger.info(f"Instance '{instance.name}' is already connected and running")
                    return {
                        "instance_name": instance.name,
                        "status": "already_exists",
                        "connection_status": existing_bot.status,
                        "message": f"Discord bot instance '{instance.name}' already exists and is connected",
                        "invite_url": existing_bot.invite_url,
                    }
                else:
                    logger.info(f"Existing instance '{instance.name}' found but not connected, will restart")
                    await self._cleanup_bot_instance(instance.name)
            # Validate configuration
            bot_config = self._validate_bot_config(instance)

            # Create Discord client
            intents = discord.Intents.default()
            intents.message_content = True  # Required for message content access
            intents.guilds = True
            intents.guild_messages = True

            client = discord.Client(intents=intents)
            # Generate invite URL
            invite_url = self._generate_invite_url(bot_config["client_id"])
            # Create bot instance container
            bot_instance = DiscordBotInstance(client=client, status="connecting", invite_url=invite_url)

            # Store the instance
            self._bot_instances[instance.name] = bot_instance

            # Set up event handlers
            @client.event
            async def on_ready():
                logger.info(f"Discord bot '{instance.name}' logged in as {client.user}")
                bot_instance.status = "connected"

            @client.event
            async def on_disconnect():
                logger.warning(f"Discord bot '{instance.name}' disconnected")
                bot_instance.status = "disconnected"

            @client.event
            async def on_error(event, *args, **kwargs):
                logger.error(f"Discord bot '{instance.name}' error in {event}: {args}, {kwargs}")
                bot_instance.status = "error"

            @client.event
            async def on_message(message):
                """Handle incoming Discord messages with @mention detection."""
                await self._handle_message(message, instance, client)

            @client.event
            async def on_guild_join(guild):
                """Handle bot joining a new guild - optionally import history."""
                logger.info(f"Discord bot '{instance.name}' joined guild: {guild.name} ({guild.id})")

                # Check if auto-import is enabled (can be configured per instance)
                auto_import = getattr(instance, "discord_auto_import_history", False)
                if auto_import:
                    logger.info(f"Auto-importing Discord history for guild {guild.name}")
                    try:
                        from src.services.discord_import import import_discord_guild_on_connect

                        stats = await import_discord_guild_on_connect(
                            client=client,
                            guild=guild,
                            instance_name=instance.name,
                            days_back=7,  # Default: last 7 days
                            max_messages_per_channel=500,
                        )
                        logger.info(f"Discord history import complete: {stats}")
                    except Exception as e:
                        logger.error(f"Failed to auto-import Discord history: {e}", exc_info=True)

            # Start the bot in a background task
            async def run_bot():
                try:
                    await client.start(bot_config["token"])
                except Exception as e:
                    logger.error(f"Failed to start Discord bot '{instance.name}': {e}")
                    bot_instance.status = "error"
                    bot_instance.error_message = str(e)
                    raise

            # Create and store the bot task
            bot_task = asyncio.create_task(run_bot())
            bot_instance.task = bot_task
            # Wait a moment for the bot to start connecting
            await asyncio.sleep(2)
            logger.info(f"Discord bot instance '{instance.name}' created successfully")
            logger.info(f"Invite URL: {invite_url}")
            return {
                "instance_name": instance.name,
                "status": "created",
                "connection_status": bot_instance.status,
                "message": f"Discord bot instance '{instance.name}' created successfully. Use the invite URL to add the bot to Discord servers.",
                "invite_url": invite_url,
                "client_id": bot_config["client_id"],
            }
        except ValidationError as e:
            logger.error(f"Validation error creating Discord instance: {e}")
            # Clean up any partial state
            if instance.name in self._bot_instances:
                await self._cleanup_bot_instance(instance.name)
            return {"error": str(e), "status": "validation_failed"}
        except DependencyError as e:
            logger.error(f"Missing Discord dependencies: {e}")
            return {"error": str(e), "status": "dependency_missing"}
        except Exception as e:
            logger.error(f"Failed to create Discord bot instance: {e}")
            # Clean up any partial state
            if instance.name in self._bot_instances:
                await self._cleanup_bot_instance(instance.name)
            return {"error": str(e), "status": "failed"}

    async def get_qr_code(self, instance: InstanceConfig) -> QRCodeResponse:
        """Get Discord bot invite URL (Discord doesn't use QR codes like WhatsApp)."""
        try:
            logger.debug(f"=== INVITE URL REQUEST START for {instance.name} ===")

            # Check if instance exists
            if instance.name not in self._bot_instances:
                logger.warning(f"Discord bot instance '{instance.name}' not found")
                return QRCodeResponse(
                    instance_name=instance.name,
                    channel_type="discord",
                    status="not_found",
                    message=f"Discord bot instance '{instance.name}' not found. Create the instance first.",
                )
            bot_instance = self._bot_instances[instance.name]

            # If we don't have an invite URL, generate it
            if not bot_instance.invite_url:
                try:
                    bot_config = self._validate_bot_config(instance)
                    bot_instance.invite_url = self._generate_invite_url(bot_config["client_id"])
                except ValidationError as e:
                    return QRCodeResponse(
                        instance_name=instance.name,
                        channel_type="discord",
                        status="configuration_error",
                        message=str(e),
                    )
            logger.debug(f"Discord invite URL for '{instance.name}': {bot_instance.invite_url}")

            return QRCodeResponse(
                instance_name=instance.name,
                channel_type="discord",
                invite_url=bot_instance.invite_url,
                status="success",
                message="Discord bot invite URL ready. Use this URL to add the bot to Discord servers.",
            )
        except Exception as e:
            logger.error(f"Failed to get Discord invite URL: {e}")
            return QRCodeResponse(
                instance_name=instance.name,
                channel_type="discord",
                status="error",
                message=f"Failed to get Discord invite URL: {str(e)}",
            )

    async def get_status(self, instance: InstanceConfig) -> ConnectionStatus:
        """Get Discord bot connection status via IPC socket."""
        try:
            # Query the Discord service manager via Unix socket
            from src.ipc_config import IPCConfig
            import aiohttp

            socket_path = IPCConfig.get_socket_path("discord", instance.name)

            # Check if socket exists
            if not os.path.exists(socket_path):
                logger.debug(f"Discord socket not found for '{instance.name}' at {socket_path}")
                return ConnectionStatus(
                    instance_name=instance.name,
                    channel_type="discord",
                    status="disconnected",
                    channel_data={"message": "Discord service not running for this instance"},
                )

            # Query status via Unix socket
            connector = aiohttp.UnixConnector(path=socket_path)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get("http://localhost/status", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        status = data.get("status", "unknown")
                        # Map status to standard values
                        if status == "connected":
                            status = "connected"
                        elif status in ("starting", "connecting"):
                            status = "connecting"
                        elif status in ("disconnected", "error"):
                            status = "disconnected"

                        # Build channel_data with all available info
                        channel_data = {
                            "guild_count": data.get("guild_count", 0),
                            "user_count": data.get("user_count", 0),
                            "latency_ms": data.get("latency_ms", 0),
                            "uptime": data.get("uptime"),
                        }

                        # Add bot profile info if available
                        if "bot" in data:
                            channel_data["bot"] = data["bot"]

                        # Add guild details if available
                        if "guilds" in data:
                            channel_data["guilds"] = data["guilds"]

                        return ConnectionStatus(
                            instance_name=instance.name,
                            channel_type="discord",
                            status=status,
                            channel_data=channel_data,
                        )
                    else:
                        return ConnectionStatus(
                            instance_name=instance.name,
                            channel_type="discord",
                            status="error",
                            channel_data={"message": f"IPC status returned {resp.status}"},
                        )

        except aiohttp.ClientError as e:
            logger.debug(f"Cannot connect to Discord IPC socket for '{instance.name}': {e}")
            return ConnectionStatus(
                instance_name=instance.name,
                channel_type="discord",
                status="disconnected",
                channel_data={"message": "Cannot connect to Discord service"},
            )
        except Exception as e:
            logger.error(f"Failed to get Discord bot status: {e}")
            return ConnectionStatus(
                instance_name=instance.name,
                channel_type="discord",
                status="error",
                channel_data={"error": str(e)},
            )

    async def connect_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Connect Discord bot (same as create)."""
        try:
            logger.info(f"Connecting Discord bot instance '{instance.name}'...")
            result = await self.create_instance(instance)

            if "error" not in result:
                result["status"] = "connected"
                result["message"] = f"Discord bot instance '{instance.name}' connected successfully"

            return result
        except Exception as e:
            logger.error(f"Failed to connect Discord bot instance: {e}")
            return {"error": str(e), "status": "connect_failed"}

    async def restart_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Restart Discord bot connection."""
        try:
            logger.info(f"Restarting Discord bot instance '{instance.name}'...")

            # Clean up existing instance
            if instance.name in self._bot_instances:
                await self._cleanup_bot_instance(instance.name)

            # Create new instance
            result = await self.create_instance(instance)

            if "error" not in result:
                logger.info(f"Discord bot instance '{instance.name}' restarted successfully")
                result["status"] = "restarted"
                result["message"] = f"Discord bot instance '{instance.name}' restarted successfully"

            return result
        except Exception as e:
            logger.error(f"Failed to restart Discord bot instance: {e}")
            return {"error": str(e), "status": "restart_failed"}

    async def disconnect_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Disconnect Discord bot (same as logout)."""
        try:
            logger.info(f"Disconnecting Discord bot instance '{instance.name}'...")

            if instance.name not in self._bot_instances:
                return {
                    "instance_name": instance.name,
                    "status": "not_found",
                    "message": f"Discord bot instance '{instance.name}' not found",
                }
            await self._cleanup_bot_instance(instance.name)

            logger.info(f"Discord bot instance '{instance.name}' disconnected successfully")
            return {
                "instance_name": instance.name,
                "status": "disconnected",
                "message": f"Discord bot instance '{instance.name}' disconnected successfully",
            }
        except Exception as e:
            logger.error(f"Failed to disconnect Discord bot instance: {e}")
            return {"error": str(e), "status": "disconnect_failed"}

    async def logout_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Logout/disconnect Discord bot."""
        try:
            logger.info(f"Logging out Discord bot instance '{instance.name}'...")

            if instance.name not in self._bot_instances:
                return {
                    "instance_name": instance.name,
                    "status": "not_found",
                    "message": f"Discord bot instance '{instance.name}' not found",
                }
            await self._cleanup_bot_instance(instance.name)

            logger.info(f"Discord bot instance '{instance.name}' logged out successfully")
            return {
                "instance_name": instance.name,
                "status": "logged_out",
                "message": f"Discord bot instance '{instance.name}' logged out successfully",
            }
        except Exception as e:
            logger.error(f"Failed to logout Discord bot instance: {e}")
            return {"error": str(e), "status": "logout_failed"}

    async def delete_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Delete Discord bot instance."""
        try:
            logger.info(f"Deleting Discord bot instance '{instance.name}'...")

            if instance.name not in self._bot_instances:
                return {
                    "instance_name": instance.name,
                    "status": "not_found",
                    "message": f"Discord bot instance '{instance.name}' not found",
                }
            await self._cleanup_bot_instance(instance.name)

            logger.info(f"Discord bot instance '{instance.name}' deleted successfully")
            return {
                "instance_name": instance.name,
                "status": "deleted",
                "message": f"Discord bot instance '{instance.name}' deleted successfully",
            }
        except Exception as e:
            logger.error(f"Failed to delete Discord bot instance: {e}")
            return {"error": str(e), "status": "delete_failed"}

    async def _cleanup_bot_instance(self, instance_name: str) -> None:
        """Clean up Discord bot instance resources."""
        if instance_name not in self._bot_instances:
            return

        bot_instance = self._bot_instances[instance_name]

        try:
            # Cancel the bot task if it exists
            if bot_instance.task and not bot_instance.task.done():
                bot_instance.task.cancel()
                try:
                    await bot_instance.task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f"Error cancelling bot task for '{instance_name}': {e}")

            # Close the Discord client
            if bot_instance.client and not bot_instance.client.is_closed():
                await bot_instance.client.close()

        except Exception as e:
            logger.warning(f"Error during cleanup of Discord bot '{instance_name}': {e}")
        finally:
            # Remove from instances dict
            del self._bot_instances[instance_name]
            logger.debug(f"Discord bot instance '{instance_name}' cleaned up")
