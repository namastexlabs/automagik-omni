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
import queue
import requests
import json
import os
import base64
import tempfile

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from src.services.message_router import message_router
from src.services.user_service import user_service
from src.channels.whatsapp.audio_transcriber import AudioTranscriptionService
from src.utils.datetime_utils import now

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

    def start(self):
        """Start the message processing thread."""
        if self.processing_thread is None or not self.processing_thread.is_alive():
            self.is_running = True
            self.processing_thread = threading.Thread(
                target=self._process_messages_loop
            )
            self.processing_thread.daemon = True
            self.processing_thread.start()

    def stop(self):
        """Stop the message processing thread."""
        self.is_running = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)

    def handle_message(
        self, message: Dict[str, Any], instance_config=None, trace_context=None
    ):
        """Queue a message for processing."""
        # Add instance config and trace context to the message for processing
        message_with_config = {
            "message": message,
            "instance_config": instance_config,
            "trace_context": trace_context,
        }
        self.message_queue.put(message_with_config)
        logger.debug(f"Message queued for processing: {message.get('event')}")
        if instance_config:
            logger.debug(
                f"Using instance config: {instance_config.name} -> Agent: {instance_config.default_agent}"
            )
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
                filename = (
                    media_meta.get("fileName")
                    or f"{timestamp}_{message_id}_{media_type}"
                )
                if not filename.endswith(file_extension):
                    filename += file_extension

                # Save media file
                media_path = os.path.join(debug_dir, filename)
                try:
                    decoded_data = base64.b64decode(base64_data)
                    with open(media_path, "wb") as f:
                        f.write(decoded_data)
                    logger.info(
                        f"Downloaded media file: {media_path} ({len(decoded_data)} bytes)"
                    )
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

    def _process_message(
        self, message: Dict[str, Any], instance_config=None, trace_context=None
    ):
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
                logger.warning(
                    "Message does not contain remoteJid in the expected location"
                )
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
                logger.info(
                    f"Ignoring message of type {message_type} - only handling text, media and audio messages"
                )
                return

            # Start showing typing indicator immediately
            # Use evolution_api_sender for presence updates (RabbitMQ disabled)
            from src.channels.whatsapp.evolution_api_sender import evolution_api_sender

            presence_updater = evolution_api_sender.get_presence_updater(sender_id)
            presence_updater.start()
            processing_start_time = time.time()  # Record when processing started

            try:
                # Extract and normalize phone number
                phone_number = self._extract_phone_number(sender_id)
                formatted_phone = (
                    f"+{phone_number}"  # Ensure + prefix for international format
                )

                # Create user dict for the agent API (let the agent handle user management)
                user_dict = {
                    "phone_number": formatted_phone,
                    "email": None,  # WhatsApp doesn't provide email
                    "user_data": {
                        "name": user_name
                        or "WhatsApp User",  # Use pushName or fallback
                        "whatsapp_id": sender_id,
                        "source": "whatsapp",
                    },
                }

                logger.info(
                    f"Created user dict for agent API: phone={formatted_phone}, name={user_dict['user_data']['name']}"
                )

                # The agent API will be the source of truth for user_id
                # We'll get the actual user_id from the agent response after processing

                # ================= Media Handling (Images, Videos, Documents) =================
                media_contents_to_send: Optional[List[Dict[str, Any]]] = None

                # Initialize transcription variable
                transcribed_text = None
                
                # Extract message content (will be replaced with transcription if available)
                message_content = self._extract_message_content(message)

                # Add quoted message context if present
                quoted_context = self._extract_quoted_context(message)
                if quoted_context:
                    message_content = f"{quoted_context}\n\n{message_content}"
                    logger.info("Added quoted message context to message content")

                # Prepend user name to message content if available
                if user_name and message_content:
                    message_content = f"[{user_name}]: {message_content}"
                    logger.info("Appended user name to message content")
                elif user_name and not message_content:
                    # For media messages without text content
                    message_content = f"[{user_name}]: "
                    logger.info("Added user name prefix for media message")

                if is_media_message:
                    # Extract media URL for any media type
                    media_url_to_send = self._extract_media_url_from_payload(data)
                    if media_url_to_send:
                        logger.info(
                            f"Media URL found in message: {self._truncate_url_for_logging(media_url_to_send)}"
                        )

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
                                    if (
                                        isinstance(media_obj, dict)
                                        and "base64" in media_obj
                                    ):
                                        base64_data = media_obj["base64"]
                                        logger.debug(
                                            f"DEBUG: Found base64 in {media_type_key}"
                                        )
                                        break

                        logger.debug(
                            f"DEBUG: Looking for base64 in data. Keys in data: {list(data.keys())}"
                        )
                        logger.debug(
                            f"DEBUG: Message keys: {list(data.get('message', {}).keys())}"
                        )
                        logger.debug(
                            f"DEBUG: Root message keys: {list(message.keys())}"
                        )
                        if base64_data:
                            logger.debug(
                                f"DEBUG: base64_data found (length: {len(base64_data)} chars)"
                            )
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
                            logger.info(
                                f"Using base64 data for agent API (size: {len(base64_data)} chars)"
                            )
                        else:
                            # Download and convert media to base64 for Hive API
                            logger.info("🔄 No base64 data found, downloading and converting media to base64")
                            downloaded_base64 = self._download_and_encode_media(media_url_to_send)
                            
                            if downloaded_base64:
                                media_item["data"] = downloaded_base64
                                logger.info(
                                    f"✅ Successfully downloaded and converted media to base64 (size: {len(downloaded_base64)} chars)"
                                )
                            else:
                                # Fallback to media URL if download fails
                                media_item["media_url"] = media_url_to_send
                                logger.warning(
                                    f"❌ Failed to download media, using media URL as fallback: {self._truncate_url_for_logging(media_url_to_send)}"
                                )

                        # Add type-specific metadata
                        if (
                            "imageMessage" in message_obj
                            or "videoMessage" in message_obj
                        ):
                            media_item["width"] = media_meta.get("width", 0)
                            media_item["height"] = media_meta.get("height", 0)
                        elif "documentMessage" in message_obj:
                            media_item["name"] = media_meta.get("fileName", "document")
                            media_item["size_bytes"] = media_meta.get("fileLength", 0)
                        elif "audioMessage" in message_obj:
                            media_item["duration"] = media_meta.get("seconds", 0)
                            media_item["size_bytes"] = media_meta.get("fileLength", 0)
                            media_item["mimetype"] = media_meta.get(
                                "mimetype", "audio/ogg"
                            )

                        media_contents_to_send = [media_item]
                        
                        # Log audio base64 data if available
                        if is_audio_message and media_item and 'data' in media_item:
                            logger.info("🎵 Audio base64 data available for transcription")
                            # Log the base64 data size for debugging
                            base64_size = len(media_item['data'])
                            logger.info(f"🎵 Audio base64 size: {base64_size} characters")
                            logger.info(f"🎵 Audio base64 preview: {media_item['data'][:50]}...")
                        
                        # Log audio information but let the agent handle transcription
                        if is_audio_message and media_item and 'data' in media_item:
                            logger.info("🎵 Audio message received - base64 data available")
                            audio_base64 = media_item['data']
                            audio_mime_type = media_item.get('mime_type', 'audio/ogg')
                            
                            logger.info(f"🎵 Audio details: MIME={audio_mime_type}, Size={len(audio_base64)} chars")
                            logger.info("🎵 Audio will be sent as base64 to agent for transcription and processing")
                            
                            # Optional: Try local transcription if OpenAI key is available
                            openai_api_key = os.getenv('OPENAI_API_KEY')
                            if openai_api_key and OPENAI_AVAILABLE:
                                logger.info("🎵 OpenAI available - attempting local transcription as preview")
                                try:
                                    transcribed_text = self._transcribe_audio_from_base64(audio_base64, audio_mime_type)
                                    if transcribed_text:
                                        logger.info(f"🎵 LOCAL TRANSCRIPTION PREVIEW: {transcribed_text}")
                                        # Update message content with transcription
                                        if "[Audio message - transcription will be handled by agent]" in message_content:
                                            message_content = message_content.replace("[Audio message - transcription will be handled by agent]", transcribed_text)
                                        else:
                                            message_content = f"[{user_name}]: {transcribed_text}" if user_name else transcribed_text
                                        logger.info(f"🎵 Updated message content with local transcription")
                                    else:
                                        logger.info("🎵 Local transcription failed, agent will handle it")
                                except Exception as transcribe_error:
                                    logger.warning(f"🎵 Local transcription failed: {transcribe_error}")
                                    logger.info("🎵 Agent will handle transcription using its tools")
                            else:
                                logger.info("🎵 No OpenAI key - agent will handle transcription using its tools")
                        elif is_audio_message:
                            logger.warning("🎵 Audio message detected but no base64 data available")

                # ================= End Media Handling =============

                # Process all message types including audio (transcription no longer required)

                # Create agent config using instance-specific or global configuration
                if instance_config:
                    # Use per-instance configuration with unified fields
                    # Check if this is a Hive instance
                    if (
                        hasattr(instance_config, "agent_instance_type")
                        and instance_config.agent_instance_type == "hive"
                    ):
                        # Use unified fields for Hive configuration
                        agent_config = {
                            "name": instance_config.agent_id
                            or instance_config.default_agent,
                            "type": "whatsapp",
                            "api_url": instance_config.agent_api_url,
                            "api_key": instance_config.agent_api_key,
                            "timeout": instance_config.agent_timeout,
                            "instance_type": instance_config.agent_instance_type,
                            "agent_type": getattr(
                                instance_config, "agent_type", "agent"
                            ),
                            "stream_mode": getattr(
                                instance_config, "agent_stream_mode", False
                            ),
                            "instance_config": instance_config,  # Pass the full config for routing decisions
                        }
                        logger.info(
                            f"Using Hive configuration: {instance_config.name} -> {instance_config.agent_instance_type}:{instance_config.agent_id} (type: {instance_config.agent_type})"
                        )
                    else:
                        # Use legacy fields for Automagik
                        agent_config = {
                            "name": instance_config.agent_id
                            or instance_config.default_agent,
                            "type": "whatsapp",
                            "api_url": instance_config.agent_api_url,
                            "api_key": instance_config.agent_api_key,
                            "timeout": instance_config.agent_timeout,
                            "instance_type": getattr(
                                instance_config, "agent_instance_type", "automagik"
                            ),
                            "instance_config": instance_config,  # Pass the full config for routing decisions
                        }
                        logger.info(
                            f"Using Automagik configuration: {instance_config.name} -> {instance_config.agent_id or instance_config.default_agent}"
                        )
                else:
                    # No instance configuration available - use defaults
                    agent_config = {"name": "", "type": "whatsapp"}
                    logger.warning(
                        "No instance configuration available - agent calls will likely fail"
                    )

                # Generate a session ID based on the sender's WhatsApp ID
                # Create a deterministic hash from the sender's WhatsApp ID
                hashlib.md5(sender_id.encode())

                # Create a readable session name based on instance and phone
                instance_prefix = instance_config.name if instance_config else "default"
                session_name = f"{instance_prefix}_{phone_number}"

                logger.info(f"Using session name: {session_name}")

                # Create or update user in our local database for stable identity
                local_user = (
                    None  # Initialize outside try block so it's accessible later
                )
                try:
                    from src.db.database import get_db

                    db_session = next(get_db())
                    try:
                        # Get instance name for user creation
                        instance_name = (
                            instance_config.name if instance_config else "default"
                        )

                        # Create/update user with current session info
                        local_user = user_service.get_or_create_user_by_phone(
                            phone_number=formatted_phone,
                            instance_name=instance_name,
                            display_name=user_name,
                            session_name=session_name,
                            db=db_session,
                        )

                        logger.info(
                            f"Local user created/updated: {local_user.id} for phone {formatted_phone}"
                        )
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
                    current_session_prefix = (
                        session_name.split("_")[0] if session_name else None
                    )

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

                # Log detailed payload information for Hive
                logger.info("=" * 80)
                logger.info("🚀 HIVE API PAYLOAD DEBUG")
                logger.info("=" * 80)
                logger.info(f"📱 User: {user_dict['phone_number']}")
                logger.info(f"📝 Session: {session_name}")
                logger.info(f"💬 Message Content: {message_content}")
                logger.info(f"🏷️ Message Type: {message_type_param}")
                logger.info(f"🤖 Agent Config: {agent_config}")
                
                if media_contents_to_send:
                    logger.info("📎 Media Contents:")
                    for i, media_item in enumerate(media_contents_to_send):
                        logger.info(f"  📎 Media {i+1}:")
                        logger.info(f"    - Alt Text: {media_item.get('alt_text', 'N/A')}")
                        logger.info(f"    - MIME Type: {media_item.get('mime_type', 'N/A')}")
                        if 'data' in media_item:
                            data_size = len(media_item['data'])
                            logger.info(f"    - Base64 Data: {data_size} chars")
                            logger.info(f"    - Base64 Preview: {media_item['data'][:100]}...")
                        if 'media_url' in media_item:
                            logger.info(f"    - Media URL: {self._truncate_url_for_logging(media_item['media_url'])}")
                        if 'duration' in media_item:
                            logger.info(f"    - Duration: {media_item['duration']} seconds")
                        if 'size_bytes' in media_item:
                            logger.info(f"    - Size: {media_item['size_bytes']} bytes")
                else:
                    logger.info("📎 No media contents")
                
                logger.info("=" * 80)

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
                        logger.info(
                            f"Triggered user creation for phone: {formatted_phone}"
                        )
                except TypeError as te:
                    # Fallback for older versions of MessageRouter without media parameters
                    logger.warning(
                        f"Route_message did not accept media_contents parameter, retrying without it: {te}"
                    )
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

                # Log Hive response details
                logger.info("=" * 80)
                logger.info("🤖 HIVE API RESPONSE DEBUG")
                logger.info("=" * 80)
                logger.info(f"⏱️ Processing time: {elapsed_time:.2f}s")
                logger.info(f"📊 Response type: {type(agent_response)}")
                
                if isinstance(agent_response, dict):
                    logger.info("📋 Response structure:")
                    for key, value in agent_response.items():
                        if key == 'messages' and isinstance(value, list):
                            logger.info(f"  📝 {key}: {len(value)} messages")
                            for i, msg in enumerate(value):
                                if isinstance(msg, dict) and 'content' in msg:
                                    content_preview = str(msg['content'])[:100] + "..." if len(str(msg['content'])) > 100 else str(msg['content'])
                                    logger.info(f"    Message {i+1}: {content_preview}")
                        elif key == 'content':
                            content_preview = str(value)[:200] + "..." if len(str(value)) > 200 else str(value)
                            logger.info(f"  📝 {key}: {content_preview}")
                        else:
                            logger.info(f"  🔑 {key}: {value}")
                else:
                    logger.info(f"📝 Response content: {str(agent_response)[:200]}...")
                
                logger.info("=" * 80)

                # Note: We're not using sleep anymore, just log the time
                logger.info(f"Processing completed in {elapsed_time:.2f}s")

                # Extract the current user_id from agent response (source of truth)
                current_user_id = None
                if isinstance(agent_response, dict) and "user_id" in agent_response:
                    current_user_id = agent_response["user_id"]
                    logger.info(
                        f"Agent API returned current user_id: {current_user_id} for session {session_name}"
                    )

                    # Update our local user with the agent's user_id for future lookups
                    if local_user:
                        try:
                            from src.db.database import get_db

                            db_session = next(get_db())
                            try:
                                user_service.update_user_agent_id(
                                    local_user.id, current_user_id, db_session
                                )
                                logger.info(
                                    f"Updated local user {local_user.id} with agent user_id: {current_user_id}"
                                )
                            finally:
                                db_session.close()
                        except Exception as e:
                            logger.error(
                                f"Failed to update local user with agent user_id: {e}"
                            )
                    else:
                        logger.warning(
                            f"Cannot update agent user_id - local user not created for session {session_name}"
                        )

                # Initialize audio_response_url for all cases
                audio_response_url = None
                
                # Extract message text and log additional information from agent response
                if isinstance(agent_response, dict):
                    # Full agent response structure
                    message_text = agent_response.get("message", "")
                    session_id = agent_response.get("session_id", "unknown")
                    success = agent_response.get("success", True)
                    tool_calls = agent_response.get("tool_calls", [])
                    usage = agent_response.get("usage", {})
                    
                    # Check for audio response in tool calls
                    for tool_call in tool_calls:
                        if tool_call.get("function", {}).get("name") == "generate_audio_response":
                            # Extract audio URL from tool call result
                            tool_result = tool_call.get("result", {})
                            if isinstance(tool_result, dict) and "audio_url" in tool_result:
                                audio_response_url = tool_result["audio_url"]
                                logger.info(f"🎵 Audio response detected: {audio_response_url}")
                            break

                    # Update trace with session information
                    if trace_context:
                        trace_context.update_session_info(session_name, session_id)

                    # Log detailed agent response information
                    logger.info(
                        f"Agent response - Session: {session_id}, Success: {success}, Tools used: {len(tool_calls)}"
                    )
                    if current_user_id:
                        logger.info(
                            f"Session {session_name} is now linked to user_id: {current_user_id}"
                        )
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
                    logger.warning(
                        f"Unexpected agent response format: {type(agent_response)}"
                    )

                # Check if the response should be ignored
                if isinstance(response_to_send, str) and response_to_send.startswith(
                    "AUTOMAGIK:"
                ):
                    logger.warning(
                        f"Ignoring AUTOMAGIK message for user {user_dict['phone_number']}, session {session_name}: {response_to_send}"
                    )
                else:
                    # Check if we have an audio response to send
                    if audio_response_url:
                        logger.info(f"🎵 Sending audio response: {audio_response_url}")
                        self._send_whatsapp_audio_response(
                            recipient=sender_id,
                            audio_url=audio_response_url,
                            quoted_message=message,
                            trace_context=trace_context,
                        )
                    # Check if we have streaming chunks to send progressively
                    elif (
                        isinstance(agent_response, dict)
                        and "streaming_chunks" in agent_response
                    ):
                        streaming_chunks = agent_response.get("streaming_chunks", [])
                        if streaming_chunks:
                            logger.info(
                                f"Sending {len(streaming_chunks)} streaming chunks progressively"
                            )
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
                        # Check if original message was audio to respond with audio
                        if is_audio_message:
                            # Generate audio response from text
                            try:
                                audio_base64 = self._generate_audio_from_text(response_to_send)
                                if audio_base64:
                                    # Try to send audio response
                                    try:
                                        self._send_whatsapp_audio_base64_response(
                                            recipient=sender_id,
                                            audio_base64=audio_base64,
                                            quoted_message=message,
                                            trace_context=trace_context,
                                        )
                                        logger.info(f"🎵 Sent audio response to {sender_id}")
                                    except Exception as audio_send_error:
                                        logger.warning(f"🎵 Audio send failed: {audio_send_error}")
                                        # Fallback: send text with audio indicator
                                        audio_response_text = f"🎵 [Audio Response]\n\n{response_to_send}"
                                        self._send_whatsapp_response(
                                            recipient=sender_id,
                                            text=audio_response_text,
                                            quoted_message=message,
                                            trace_context=trace_context,
                                        )
                                        logger.info(f"🎵 Sent text response with audio indicator to {sender_id}")
                                else:
                                    # Fallback to text if audio generation fails
                                    logger.warning("🎵 Audio generation failed, sending text response")
                                    audio_response_text = f"🎵 [Audio Response]\n\n{response_to_send}"
                                    self._send_whatsapp_response(
                                        recipient=sender_id,
                                        text=audio_response_text,
                                        quoted_message=message,
                                        trace_context=trace_context,
                                    )
                            except Exception as e:
                                logger.error(f"🎵 Error generating audio response: {e}")
                                # Fallback to text response
                                audio_response_text = f"🎵 [Audio Response]\n\n{response_to_send}"
                                self._send_whatsapp_response(
                                    recipient=sender_id,
                                    text=audio_response_text,
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
                        logger.info(
                            f"Sent agent response to user_id={current_user_id}, session_id={session_name}"
                        )
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
                    clean_recipient = (
                        recipient.split("@")[0] if "@" in recipient else recipient
                    )
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

    def _send_whatsapp_audio_response(
        self,
        recipient: str,
        audio_url: str,
        quoted_message: Optional[Dict[str, Any]] = None,
        trace_context=None,
    ):
        """Send an audio response back via WhatsApp with optional message quoting."""
        response_payload = None
        success = False

        # Prepare payload for tracing
        send_payload = {
            "recipient": recipient,
            "audio_url": audio_url,
            "has_quoted_message": quoted_message is not None,
        }

        if self.send_response_callback:
            try:
                # Import the Evolution API sender
                from src.channels.whatsapp.evolution_api_sender import evolution_api_sender
                
                # Send audio message via Evolution API
                success = evolution_api_sender.send_audio_message(recipient, audio_url)
                response_code = 201 if success else 400  # Simulate HTTP status codes

                if success:
                    # Extract just the phone number without the suffix for logging
                    clean_recipient = (
                        recipient.split("@")[0] if "@" in recipient else recipient
                    )
                    logger.info(f"🎵 Sent audio response to {clean_recipient}")
                else:
                    logger.error(f"❌ Failed to send audio response to {recipient}")

            except Exception as e:
                logger.error(f"❌ Error sending audio response: {e}", exc_info=True)
                response_code = 500
                success = False
        else:
            logger.warning("⚠️ No send response callback set, audio message not sent")
            response_code = 500
            success = False

        # Log evolution send attempt to trace
        if trace_context:
            trace_context.log_evolution_send(send_payload, response_code, success)

        return response_payload

    def _transcribe_audio_from_base64(self, base64_data: str, mime_type: str = "audio/ogg") -> Optional[str]:
        """Transcribe audio from base64 data using OpenAI Whisper API.
        
        Args:
            base64_data: Base64 encoded audio data
            mime_type: MIME type of the audio
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            logger.info(f"🎵 Starting audio transcription from base64 data ({len(base64_data)} chars)")
            
            # Try to use OpenAI Whisper API if available
            if not OPENAI_AVAILABLE:
                logger.warning("🎵 OpenAI library not available, skipping transcription")
                return None
            
            # Check if OpenAI API key is available
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                logger.warning("🎵 No OpenAI API key found, skipping transcription")
                logger.info("🎵 To enable audio transcription, set OPENAI_API_KEY environment variable")
                logger.info("🎵 Audio will be sent as base64 to agent for processing instead")
                return None
            
            # Decode base64 to binary
            try:
                audio_content = base64.b64decode(base64_data)
                logger.info(f"🎵 Decoded base64 to {len(audio_content)} bytes")
            except Exception as decode_error:
                logger.error(f"🎵 Failed to decode base64 audio: {decode_error}")
                return None
            
            # Check file signature to determine actual format
            signature = audio_content[:16] if len(audio_content) >= 16 else audio_content
            logger.info(f"🎵 Raw audio signature (hex): {signature.hex()}")
            logger.info(f"🎵 Raw audio signature (ascii): {repr(signature)}")
            
            # Check if this is a valid audio file
            is_valid_ogg = signature.startswith(b'OggS')
            is_valid_wav = signature.startswith(b'RIFF') and b'WAVE' in signature
            is_valid_mp3 = signature.startswith(b'ID3') or (len(signature) > 2 and signature[1:3] == b'\xff\xfb')
            
            if is_valid_ogg:
                suffix = '.ogg'
                logger.info("🎵 Detected valid OGG format")
            elif is_valid_wav:
                suffix = '.wav'
                logger.info("🎵 Detected valid WAV format")
            elif is_valid_mp3:
                suffix = '.mp3'
                logger.info("🎵 Detected valid MP3 format")
            else:
                # Invalid or unknown format - create a simple WAV file
                logger.warning("🎵 Invalid audio format detected, creating simple WAV")
                return self._transcribe_as_simple_wav(audio_content)
            
            # Save to temporary file with detected extension
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
                temp_file.write(audio_content)
                temp_path = temp_file.name
            
            try:
                client = openai.OpenAI(api_key=openai_api_key)
                
                # Log file info before transcription
                file_size = os.path.getsize(temp_path)
                logger.info(f"🎵 Transcribing audio file: {temp_path} ({file_size} bytes, format: {suffix})")
                
                # Transcribe using Whisper
                with open(temp_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="pt"  # Portuguese
                    )
                
                transcribed_text = transcript.text
                logger.info(f"🎵 OpenAI Whisper transcription successful: {transcribed_text}")
                return transcribed_text
                    
            except Exception as openai_error:
                logger.error(f"🎵 OpenAI Whisper transcription failed: {openai_error}")
                # Try FFmpeg conversion as fallback
                logger.info("🎵 Attempting FFmpeg conversion as fallback")
                return self._transcribe_with_ffmpeg_conversion(audio_content)
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"🎵 Audio transcription failed: {e}")
            return None

    def _transcribe_with_ffmpeg_conversion(self, audio_content: bytes) -> Optional[str]:
        """Convert audio using FFmpeg and transcribe.
        
        Args:
            audio_content: Raw audio bytes
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            import subprocess
            
            # Check if FFmpeg is available
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("🎵 FFmpeg not available, cannot convert audio")
                return None
            
            logger.info("🎵 Using FFmpeg to convert audio to supported format")
            
            # Save raw audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.raw', delete=False) as raw_file:
                raw_file.write(audio_content)
                raw_path = raw_file.name
            
            # Convert to WAV using FFmpeg
            wav_path = raw_path.replace('.raw', '.wav')
            
            try:
                # Use FFmpeg to convert to WAV
                cmd = [
                    'ffmpeg', '-y',  # Overwrite output
                    '-i', raw_path,  # Input file
                    '-ar', '16000',  # Sample rate
                    '-ac', '1',      # Mono
                    '-f', 'wav',     # Output format
                    wav_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    logger.info(f"🎵 FFmpeg conversion successful: {wav_path}")
                    
                    # Now transcribe the converted file
                    if not OPENAI_AVAILABLE:
                        return None
                        
                    openai_api_key = os.getenv('OPENAI_API_KEY')
                    if not openai_api_key:
                        return None
                    
                    client = openai.OpenAI(api_key=openai_api_key)
                    
                    with open(wav_path, "rb") as audio_file:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="pt"
                        )
                    
                    transcribed_text = transcript.text
                    logger.info(f"🎵 FFmpeg + Whisper transcription successful: {transcribed_text}")
                    return transcribed_text
                else:
                    logger.error(f"🎵 FFmpeg conversion failed: {result.stderr}")
                    return None
                    
            finally:
                # Clean up files
                for path in [raw_path, wav_path]:
                    try:
                        os.unlink(path)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"🎵 FFmpeg conversion failed: {e}")
            return None

    def _transcribe_as_simple_wav(self, audio_content: bytes) -> Optional[str]:
        """Create a simple WAV file and transcribe it.
        
        Args:
            audio_content: Raw audio bytes
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            logger.info("🎵 Creating simple WAV file for transcription")
            
            # Check if OpenAI is available
            if not OPENAI_AVAILABLE:
                logger.warning("🎵 OpenAI library not available")
                return None
            
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                logger.warning("🎵 No OpenAI API key found")
                return None
            
            # Create a minimal WAV file with proper header
            # Assume 16kHz, 16-bit, mono for WhatsApp audio
            sample_rate = 16000
            bits_per_sample = 16
            channels = 1
            
            # Calculate data size (assume raw PCM data)
            data_size = len(audio_content)
            file_size = 36 + data_size
            
            # Create WAV header
            wav_header = bytearray()
            wav_header.extend(b'RIFF')                              # ChunkID
            wav_header.extend(file_size.to_bytes(4, 'little'))      # ChunkSize
            wav_header.extend(b'WAVE')                              # Format
            wav_header.extend(b'fmt ')                              # Subchunk1ID
            wav_header.extend((16).to_bytes(4, 'little'))           # Subchunk1Size
            wav_header.extend((1).to_bytes(2, 'little'))            # AudioFormat (PCM)
            wav_header.extend(channels.to_bytes(2, 'little'))       # NumChannels
            wav_header.extend(sample_rate.to_bytes(4, 'little'))    # SampleRate
            wav_header.extend((sample_rate * channels * bits_per_sample // 8).to_bytes(4, 'little'))  # ByteRate
            wav_header.extend((channels * bits_per_sample // 8).to_bytes(2, 'little'))  # BlockAlign
            wav_header.extend(bits_per_sample.to_bytes(2, 'little')) # BitsPerSample
            wav_header.extend(b'data')                              # Subchunk2ID
            wav_header.extend(data_size.to_bytes(4, 'little'))      # Subchunk2Size
            
            # Create complete WAV file
            wav_content = wav_header + audio_content
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(wav_content)
                temp_path = temp_file.name
            
            try:
                client = openai.OpenAI(api_key=openai_api_key)
                
                logger.info(f"🎵 Transcribing simple WAV file: {temp_path} ({len(wav_content)} bytes)")
                
                # Transcribe using Whisper
                with open(temp_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="pt"  # Portuguese
                    )
                
                transcribed_text = transcript.text
                logger.info(f"🎵 Simple WAV transcription successful: {transcribed_text}")
                return transcribed_text
                    
            except Exception as openai_error:
                logger.error(f"🎵 Simple WAV transcription failed: {openai_error}")
                return None
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"🎵 Simple WAV creation failed: {e}")
            return None

    def _create_wav_from_raw_audio(self, audio_data: bytes, output_path: str):
        """Create a basic WAV file from raw audio data.
        
        Args:
            audio_data: Raw audio bytes
            output_path: Path to save the WAV file
        """
        try:
            # Basic WAV header for 16kHz, 16-bit, mono
            # This is a simple approach - may not work for all audio formats
            sample_rate = 16000
            bits_per_sample = 16
            channels = 1
            
            # Calculate sizes
            data_size = len(audio_data)
            file_size = 36 + data_size
            
            # Create WAV header
            wav_header = bytearray()
            wav_header.extend(b'RIFF')                              # ChunkID
            wav_header.extend(file_size.to_bytes(4, 'little'))      # ChunkSize
            wav_header.extend(b'WAVE')                              # Format
            wav_header.extend(b'fmt ')                              # Subchunk1ID
            wav_header.extend((16).to_bytes(4, 'little'))           # Subchunk1Size
            wav_header.extend((1).to_bytes(2, 'little'))            # AudioFormat (PCM)
            wav_header.extend(channels.to_bytes(2, 'little'))       # NumChannels
            wav_header.extend(sample_rate.to_bytes(4, 'little'))    # SampleRate
            wav_header.extend((sample_rate * channels * bits_per_sample // 8).to_bytes(4, 'little'))  # ByteRate
            wav_header.extend((channels * bits_per_sample // 8).to_bytes(2, 'little'))  # BlockAlign
            wav_header.extend(bits_per_sample.to_bytes(2, 'little')) # BitsPerSample
            wav_header.extend(b'data')                              # Subchunk2ID
            wav_header.extend(data_size.to_bytes(4, 'little'))      # Subchunk2Size
            
            # Write WAV file
            with open(output_path, 'wb') as f:
                f.write(wav_header)
                f.write(audio_data)
                
            logger.info(f"🎵 Created WAV file: {output_path} ({len(wav_header) + data_size} bytes)")
            
        except Exception as e:
            logger.error(f"🎵 Failed to create WAV file: {e}")
            raise

    def _transcribe_audio_simple(self, audio_url: str, media_key: str = None) -> Optional[str]:
        """Simple audio transcription using OpenAI Whisper API.
        
        Args:
            audio_url: URL to the audio file
            media_key: Media key for WhatsApp encrypted files
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            logger.info(f"🎵 Starting simple audio transcription from: {self._truncate_url_for_logging(audio_url)}")
            logger.warning("🎵 URL-based transcription disabled due to encryption issues")
            logger.info("🎵 Use _transcribe_audio_from_base64 instead with already downloaded content")
            return None
                    
        except Exception as e:
            logger.error(f"🎵 Audio transcription failed: {e}")
            return None

    def _download_and_encode_media(self, media_url: str, save_to_disk: bool = True) -> Optional[str]:
        """Download media from URL and convert to base64.
        
        Args:
            media_url: URL to download media from
            save_to_disk: Whether to save the media file to disk for validation
            
        Returns:
            Base64 encoded media content or None if failed
        """
        try:
            logger.info(f"📥 Downloading media from: {self._truncate_url_for_logging(media_url)}")
            
            # Download the media file
            response = requests.get(media_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Read the content
            content = response.content
            logger.info(f"📥 Downloaded {len(content)} bytes of media")
            
            # Save to disk if requested (for validation)
            if save_to_disk and content:
                try:
                    # Generate filename with timestamp
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Determine file extension from Content-Type or URL
                    content_type = response.headers.get('Content-Type', '')
                    logger.info(f"🎵 Content-Type: {content_type}")
                    
                    # Check file signature (magic bytes) to determine actual format
                    file_signature = content[:12] if len(content) >= 12 else content
                    logger.info(f"🎵 File signature (hex): {file_signature.hex()}")
                    
                    # Determine extension based on file signature first, then Content-Type
                    if file_signature.startswith(b'OggS'):
                        extension = '.ogg'
                        logger.info("🎵 Detected OGG format from file signature")
                    elif file_signature.startswith(b'RIFF') and b'WAVE' in file_signature:
                        extension = '.wav'
                        logger.info("🎵 Detected WAV format from file signature")
                    elif file_signature.startswith(b'ID3') or file_signature[1:3] == b'\xff\xfb':
                        extension = '.mp3'
                        logger.info("🎵 Detected MP3 format from file signature")
                    elif file_signature.startswith(b'\x00\x00\x00') and b'ftyp' in file_signature:
                        extension = '.m4a'
                        logger.info("🎵 Detected M4A format from file signature")
                    elif 'audio/ogg' in content_type or 'application/ogg' in content_type:
                        extension = '.ogg'
                        logger.info("🎵 Detected OGG format from Content-Type")
                    elif 'audio/mpeg' in content_type:
                        extension = '.mp3'
                        logger.info("🎵 Detected MP3 format from Content-Type")
                    elif 'audio/wav' in content_type:
                        extension = '.wav'
                        logger.info("🎵 Detected WAV format from Content-Type")
                    elif 'audio/mp4' in content_type or 'audio/m4a' in content_type:
                        extension = '.m4a'
                        logger.info("🎵 Detected M4A format from Content-Type")
                    else:
                        # For WhatsApp encrypted files, default to .ogg as it's most common
                        if '.enc' in media_url or 'whatsapp.net' in media_url:
                            extension = '.ogg'
                            logger.info("🎵 WhatsApp encrypted file detected, defaulting to .ogg")
                        else:
                            extension = '.audio'  # fallback
                            logger.info("🎵 Unknown format, using .audio extension")
                    
                    filename = f"audio_download_{timestamp}{extension}"
                    filepath = os.path.join(".", filename)  # Save in project root
                    
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    
                    logger.info(f"🎵 Audio saved to disk for validation: {filepath}")
                    logger.info(f"🎵 File size: {len(content)} bytes, Content-Type: {content_type}")
                    logger.info(f"🎵 You can now listen to the audio file at: {os.path.abspath(filepath)}")
                    
                    # Try to verify the file is playable and provide playback instructions
                    absolute_path = os.path.abspath(filepath)
                    logger.info(f"🎵 To play this file, try:")
                    logger.info(f"🎵   VLC: open -a VLC '{absolute_path}'")
                    logger.info(f"🎵   Browser: open '{absolute_path}'")
                    logger.info(f"🎵   FFplay: ffplay '{absolute_path}'")
                    
                    # Check if it's an encrypted WhatsApp file
                    if '.enc' in media_url:
                        logger.warning(f"⚠️ This appears to be an encrypted WhatsApp file (.enc)")
                        logger.warning(f"⚠️ The file may need to be decrypted before playback")
                        logger.warning(f"⚠️ Try renaming to .ogg and playing with VLC: mv '{filepath}' '{filepath.replace('.audio', '.ogg')}'")
                    
                    # For debugging: show first few bytes in different formats
                    if len(content) >= 16:
                        logger.info(f"🎵 First 16 bytes (hex): {content[:16].hex()}")
                        logger.info(f"🎵 First 16 bytes (ascii): {repr(content[:16])}")
                    
                except Exception as save_error:
                    logger.warning(f"⚠️ Failed to save audio to disk: {save_error}")
            
            # Encode to base64
            base64_data = base64.b64encode(content).decode('utf-8')
            logger.info(f"✅ Successfully encoded media to base64 ({len(base64_data)} chars)")
            
            return base64_data
            
        except Exception as e:
            logger.error(f"❌ Failed to download and encode media: {e}")
            return None

    def _extract_media_url_from_payload(self, data: dict) -> Optional[str]:
        """Extract media URL from WhatsApp message payload with retry logic for file availability."""
        try:
            # Log data structure summary without base64 content
            data_keys = list(data.keys())
            message_keys = (
                list(data.get("message", {}).keys())
                if isinstance(data.get("message"), dict)
                else []
            )
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
                    return self._check_and_wait_for_file_availability(
                        evolution_media_url
                    )
                else:
                    logger.warning(
                        "⚠️ Evolution mediaUrl exists but value is empty/None"
                    )

            # PRIORITY 2: Check for mediaUrl at top level (legacy)
            logger.info(
                f"🔍 DEBUG: Checking for top-level 'mediaUrl' key: {'mediaUrl' in data}"
            )
            if "mediaUrl" in data:
                media_url = data["mediaUrl"]
                logger.info(
                    f"✅ Found top-level mediaUrl with value: {self._truncate_url_for_logging(str(media_url))}"
                )
                if media_url:
                    return self._check_and_wait_for_file_availability(media_url)
                else:
                    logger.warning(
                        "⚠️ Top-level mediaUrl key exists but value is empty/None"
                    )
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
                            logger.info(
                                f"🔑 Found {media_type} mediaKey: {media_key[:20]}..."
                            )
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
                        logger.info(
                            f"✅ File confirmed available after {attempt + 1} attempts"
                        )
                        return url
                    elif response.status_code == 404:
                        logger.warning(
                            f"⏳ File not yet available (404), attempt {attempt + 1}/{max_retries}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Unexpected response {response.status_code}, attempt {attempt + 1}/{max_retries}"
                        )
                except Exception as e:
                    logger.warning(
                        f"⚠️ File availability check failed: {e}, attempt {attempt + 1}/{max_retries}"
                    )

            logger.warning(
                f"⚠️ File still not available after {max_retries} attempts, proceeding anyway"
            )

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

    def _truncate_base64_for_logging(
        self, base64_data: str, prefix_length: int = 20, suffix_length: int = 10
    ) -> str:
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
                    return message_obj["buttonsResponseMessage"].get(
                        "selectedDisplayText", ""
                    )

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
            context_info = data.get("contextInfo")
            quoted_message = {}
            
            if context_info and isinstance(context_info, dict):
                quoted_message = context_info.get("quotedMessage", {})

            if not quoted_message:
                # Also check in message.contextInfo structure
                message_obj = data.get("message", {})
                if isinstance(message_obj, dict):
                    context_info = message_obj.get("contextInfo")
                    if context_info and isinstance(context_info, dict):
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
                    quoted_text = quoted_message["imageMessage"].get(
                        "caption", "[Image]"
                    )
                elif "videoMessage" in quoted_message:
                    quoted_text = quoted_message["videoMessage"].get(
                        "caption", "[Video]"
                    )
                elif "documentMessage" in quoted_message:
                    quoted_text = quoted_message["documentMessage"].get(
                        "caption", "[Document]"
                    )
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

    def _generate_audio_from_text(self, text: str) -> Optional[str]:
        """
        Generate audio from text using OpenAI TTS and return base64 encoded audio.
        
        Args:
            text: The text to convert to audio
            
        Returns:
            Base64 encoded audio data or None if generation fails
        """
        if not OPENAI_AVAILABLE:
            logger.warning("🎵 OpenAI not available for audio generation")
            return None
            
        try:
            import io
            import base64
            from openai import OpenAI
            
            # Initialize OpenAI client
            client = OpenAI()
            
            # Generate audio using OpenAI TTS
            logger.info(f"🎵 Generating audio for text: {text[:100]}...")
            
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",  # You can change this to other voices: echo, fable, onyx, nova, shimmer
                input=text,
                response_format="mp3"
            )
            
            # Get audio data
            audio_data = response.content
            
            # Convert to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            logger.info(f"🎵 Audio generated successfully: {len(audio_data)} bytes, base64: {len(audio_base64)} chars")
            
            # Log the base64 for debugging (first 100 and last 50 chars)
            logger.info(f"🎵 AUDIO BASE64 DEBUG:")
            logger.info(f"🎵 First 100 chars: {audio_base64[:100]}")
            logger.info(f"🎵 Last 50 chars: {audio_base64[-50:]}")
            logger.info(f"🎵 Full base64 length: {len(audio_base64)}")
            
            # Also log the full base64 in a separate log entry for easy copying
            logger.info(f"🎵 FULL BASE64 AUDIO: {audio_base64}")
            
            return audio_base64
            
        except Exception as e:
            logger.error(f"🎵 Failed to generate audio from text: {e}")
            return None

    def _send_whatsapp_audio_base64_response(
        self,
        recipient: str,
        audio_base64: str,
        quoted_message: Optional[Dict[str, Any]] = None,
        trace_context=None,
    ):
        """Send an audio response back via WhatsApp using base64 audio data."""
        response_payload = None
        success = False

        # Prepare payload for tracing
        send_payload = {
            "recipient": recipient,
            "audio_base64_length": len(audio_base64),
            "has_quoted_message": quoted_message is not None,
        }

        try:
            # Import the Evolution API sender
            from src.channels.whatsapp.evolution_api_sender import evolution_api_sender
            
            # Send audio message via Evolution API using sendMedia endpoint with pure base64
            success = self._send_audio_via_evolution_media(recipient, audio_base64)
            response_code = 201 if success else 400

            if success:
                # Extract just the phone number without the suffix for logging
                clean_recipient = (
                    recipient.split("@")[0] if "@" in recipient else recipient
                )
                logger.info(f"🎵 Sent audio response to {clean_recipient}")
            else:
                logger.error(f"🎵 Failed to send audio response to {recipient}")

        except Exception as e:
            logger.error(f"🎵 Error sending audio response: {e}", exc_info=True)
            response_code = 500
            success = False

        # Log evolution send attempt to trace
        if trace_context:
            trace_context.log_evolution_send(send_payload, response_code, success)

        return response_payload

    def _format_audio_for_evolution(self, audio_base64: str) -> str:
        """Format base64 audio for Evolution API with proper data URL."""
        try:
            import base64
            
            # Decode to check format
            decoded = base64.b64decode(audio_base64[:50])
            
            # Detect format from magic bytes
            if decoded.startswith(b'RIFF') and b'WAVE' in decoded:
                mime_type = "audio/wav"
            elif decoded.startswith(b'ID3') or decoded[1:3] == b'\xff\xfb':
                mime_type = "audio/mp3"
            elif decoded.startswith(b'OggS'):
                mime_type = "audio/ogg"
            else:
                mime_type = "audio/mp3"  # Default to MP3
            
            data_url = f"data:{mime_type};base64,{audio_base64}"
            logger.info(f"🎵 Formatted audio as {mime_type} data URL")
            return data_url
            
        except Exception as e:
            logger.warning(f"🎵 Format detection failed: {e}, using MP3 default")
            return f"data:audio/mp3;base64,{audio_base64}"

    def _send_audio_via_evolution_media(self, recipient: str, audio_base64: str) -> bool:
        """Send audio via Evolution API sendMedia endpoint using pure base64."""
        try:
            from src.channels.whatsapp.evolution_api_sender import evolution_api_sender
            
            # Get instance configuration
            server_url = evolution_api_sender.server_url
            api_key = evolution_api_sender.api_key
            instance_name = evolution_api_sender.instance_name
            
            if not all([server_url, api_key, instance_name]):
                logger.error("🎵 Missing Evolution API configuration")
                return False
            
            # Prepare recipient
            formatted_recipient = recipient.split("@")[0] if "@" in recipient else recipient
            
            url = f"{server_url}/message/sendMedia/{instance_name}"
            headers = {"apikey": api_key, "Content-Type": "application/json"}
            
            # Use pure base64 without data URL prefix (as per Evolution API docs)
            payload = {
                "number": formatted_recipient,
                "media": audio_base64,  # Pure base64, no data URL prefix
                "mediatype": "audio"
            }
            
            logger.info(f"🎵 Sending audio via sendMedia to {formatted_recipient}")
            logger.info(f"🎵 Base64 length: {len(audio_base64)} chars")
            logger.info(f"🎵 Payload preview: {audio_base64[:50]}...")
            
            # Log complete payload for debugging
            logger.info(f"🎵 EVOLUTION API PAYLOAD DEBUG:")
            logger.info(f"🎵 URL: {url}")
            logger.info(f"🎵 Headers: {headers}")
            logger.info(f"🎵 Payload structure:")
            logger.info(f"🎵   number: {payload['number']}")
            logger.info(f"🎵   mediatype: {payload['mediatype']}")
            logger.info(f"🎵   media length: {len(payload['media'])}")
            logger.info(f"🎵   media preview: {payload['media'][:100]}...")
            
            # Log full payload (truncated for readability)
            payload_copy = payload.copy()
            payload_copy['media'] = f"{payload['media'][:100]}...[TRUNCATED {len(payload['media'])} chars total]"
            logger.info(f"🎵 FULL PAYLOAD: {payload_copy}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 201:
                logger.info(f"🎵 Audio sent successfully via sendMedia")
                return True
            else:
                logger.error(f"🎵 Evolution sendMedia failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"🎵 Error in _send_audio_via_evolution_media: {e}")
            return False


# Singleton instance - initialized without a callback
# The callback will be set later by the client
message_handler = WhatsAppMessageHandler()

# Set up the send response callback to use evolution_api_sender for webhook-based messaging
from src.channels.whatsapp.evolution_api_sender import evolution_api_sender

message_handler.send_response_callback = evolution_api_sender.send_text_message

# Start the message processing thread immediately
message_handler.start()
