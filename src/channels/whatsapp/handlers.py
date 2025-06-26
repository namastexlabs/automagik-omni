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
from datetime import datetime

from src.config import config
from src.services.message_router import message_router
from src.channels.whatsapp.audio_transcriber import AudioTranscriptionService

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
        logger.info("WhatsApp message handler initialized with audio transcription service")
    
    def start(self):
        """Start the message processing thread."""
        if self.processing_thread is None or not self.processing_thread.is_alive():
            self.is_running = True
            self.processing_thread = threading.Thread(target=self._process_messages_loop)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            logger.info("WhatsApp message handler started")
    
    def stop(self):
        """Stop the message processing thread."""
        self.is_running = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
            logger.info("WhatsApp message handler stopped")
    
    def handle_message(self, message: Dict[str, Any], instance_config=None):
        """Queue a message for processing."""
        # Add instance config to the message for processing
        message_with_config = {
            'message': message,
            'instance_config': instance_config
        }
        self.message_queue.put(message_with_config)
        logger.debug(f"Message queued for processing: {message.get('event')}")
        if instance_config:
            logger.debug(f"Using instance config: {instance_config.name} -> Agent: {instance_config.default_agent}")
    
    def _process_messages_loop(self):
        """Process messages from the queue in a loop."""
        while self.is_running:
            try:
                # Get message with timeout to allow for clean shutdown
                message_data = self.message_queue.get(timeout=1.0)
                
                # Extract message and instance config
                if isinstance(message_data, dict) and 'message' in message_data:
                    message = message_data['message']
                    instance_config = message_data.get('instance_config')
                else:
                    # Backward compatibility for direct message data
                    message = message_data
                    instance_config = None
                
                self._process_message(message, instance_config)
                self.message_queue.task_done()
            except queue.Empty:
                # No messages, continue waiting
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
    
    def _save_webhook_debug(self, message: Dict[str, Any], message_id: str):
        """Save webhook JSON and download media files when debug mode is enabled."""
        if not config.whatsapp.save_webhook_debug:
            return
            
        try:
            # Create debug directory
            debug_dir = "./webhook_debug"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Save webhook JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"{timestamp}_{message_id}_webhook.json"
            json_path = os.path.join(debug_dir, json_filename)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(message, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved webhook JSON: {json_path}")
            
            # Download and save media files if base64 is present
            data = message.get('data', {})
            message_obj = data.get('message', {})
            
            # Check for base64 data in message
            base64_data = None
            if 'base64' in message_obj:
                base64_data = message_obj['base64']
            
            if base64_data:
                # Get media metadata for filename and type
                media_meta = {}
                media_type = "unknown"
                
                for media_type_key in ['imageMessage', 'videoMessage', 'documentMessage', 'audioMessage']:
                    if media_type_key in message_obj:
                        media_meta = message_obj[media_type_key]
                        media_type = media_type_key.replace('Message', '')
                        break
                
                # Determine file extension from mimetype
                mime_type = media_meta.get('mimetype', 'application/octet-stream')
                file_extension = self._get_file_extension_from_mime(mime_type)
                
                # Create filename
                filename = media_meta.get('fileName') or f"{timestamp}_{message_id}_{media_type}"
                if not filename.endswith(file_extension):
                    filename += file_extension
                
                # Save media file
                media_path = os.path.join(debug_dir, filename)
                try:
                    decoded_data = base64.b64decode(base64_data)
                    with open(media_path, 'wb') as f:
                        f.write(decoded_data)
                    logger.info(f"Downloaded media file: {media_path} ({len(decoded_data)} bytes)")
                except Exception as e:
                    logger.error(f"Failed to save media file {media_path}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to save webhook debug data: {e}")

    def _get_file_extension_from_mime(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg', 
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'video/webm': '.webm',
            'audio/ogg': '.ogg',
            'audio/mpeg': '.mp3',
            'audio/mp4': '.m4a',
            'audio/wav': '.wav',
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'text/plain': '.txt'
        }
        return mime_to_ext.get(mime_type, '.bin')

    def _process_message(self, message: Dict[str, Any], instance_config=None):
        """
        Process a WhatsApp message.
        """
        try:
            # The message from Evolution API has a different structure from our previous code
            # Message data is usually in the 'data' field
            data = message.get('data', {})
            
            # Extract sender information from the proper location
            if 'key' in data and 'remoteJid' in data['key']:
                sender_id = data['key']['remoteJid']
            else:
                logger.warning("Message does not contain remoteJid in the expected location")
                # Try to get it from the sender field directly
                sender_id = message.get('sender')
                
            if not sender_id:
                logger.error("No sender ID found in message, unable to process")
                return
                
            # Extract user name from pushName field if available
            user_name = data.get('pushName', '')
            if user_name:
                logger.info(f"User name extracted: {user_name}")
            else:
                logger.info("No pushName found in message data")
                
            # Save webhook debug data if enabled
            message_id = data.get('key', {}).get('id', f"msg_{int(time.time())}")
            self._save_webhook_debug(message, message_id)
            
            # Extract message type
            message_type = self._extract_message_type(message)
            if not message_type:
                logger.warning("Unable to determine message type")
                return
            
            # Only process text, audio and media messages, ignore other types
            is_text_message = message_type in ['text', 'conversation', 'extendedTextMessage']
            is_audio_message = message_type in ['audioMessage', 'audio', 'voice', 'ptt']
            is_media_message = message_type in ['imageMessage', 'image', 'videoMessage', 'video', 'documentMessage', 'document']
            
            if not (is_text_message or is_audio_message or is_media_message):
                logger.info(f"Ignoring message of type {message_type} - only handling text, media and audio messages")
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
                
                # Create user dict for automatic user creation (skip user lookup)
                user_dict = {
                    "phone_number": f"+{phone_number}",  # Ensure + prefix for international format
                    "email": "",  # WhatsApp doesn't provide email, leave empty
                    "user_data": {
                        "name": user_name or "WhatsApp User",  # Use pushName or fallback
                        "whatsapp_id": sender_id,
                        "source": "whatsapp"
                    }
                }
                
                logger.info(f"Created user dict for automatic creation: phone={user_dict['phone_number']}, name={user_dict['user_data']['name']}")
                
                # Skip the user lookup entirely - let the API handle user creation
                
                # Handle audio messages - attempt transcription first
                transcription_successful = False
                if is_audio_message:
                    # Extract media URL and media key from the message
                    media_url = self._extract_media_url_from_payload(data)
                    media_key = self._extract_media_key_from_payload(data)
                    
                    if media_url:
                        # Log which URL is being used for debugging
                        if "api.bucket.namastex.ai" in media_url:
                            logger.info(f"✅ Using Evolution API processed URL: {self._truncate_url_for_logging(media_url)}")
                        elif "mmg.whatsapp.net" in media_url:
                            logger.warning(f"⚠️ Using WhatsApp encrypted URL (may not work): {self._truncate_url_for_logging(media_url)}")
                        else:
                            logger.info(f"Audio URL found in message: {self._truncate_url_for_logging(media_url)}")
                        
                        # PRIORITY 1: Use Evolution API processed mediaUrl (contains decrypted .oga file)
                        # Check if this is a processed minio URL from Evolution API
                        if "minio:9000" in media_url and ".oga" in media_url:
                            logger.info(f"✅ Found Evolution API processed audio file: {self._truncate_url_for_logging(media_url)}")
                            
                            # Convert minio URL to external accessible URL
                            external_media_url = self._convert_minio_url(media_url)
                            logger.info(f"🔄 Converted to external URL: {self._truncate_url_for_logging(external_media_url)}")
                            
                            # Try to transcribe using the processed URL directly
                            if not self.audio_transcriber.is_configured():
                                logger.warning("Audio transcription service is not properly configured. Skipping transcription.")
                            else:
                                logger.info("🎯 Attempting to transcribe Evolution API processed audio")
                                transcription = self.audio_transcriber.transcribe_with_fallback(external_media_url)
                                
                                if transcription:
                                    logger.info(f"✅ Successfully transcribed processed audio: {transcription}")
                                    data['transcription'] = transcription
                                    transcription_successful = True
                                else:
                                    logger.warning("❌ Failed to transcribe processed audio message")
                        
                        # FALLBACK: If no processed mediaUrl, try the encrypted decryption approach
                        elif media_key and not transcription_successful:
                            logger.info("🔍 No processed audio file, trying encrypted decryption approach")
                            # If media URL is from minio, convert to accessible URL
                            if "minio:" in media_url:
                                media_url = self._convert_minio_url(media_url)
                                logger.info(f"Converted Minio URL: {self._truncate_url_for_logging(media_url)}")
                            
                            # Check if this is an encrypted WhatsApp URL that needs decryption
                            is_encrypted_url = '.enc?' in media_url or media_url.endswith('.enc')
                            logger.info(f"🔍 DEBUG: URL contains .enc: {is_encrypted_url}")
                            logger.info(f"🔍 DEBUG: Media key present: {bool(media_key)}")
                            logger.info(f"🔍 DEBUG: Media key value: {media_key if media_key else 'None'}")
                            
                            if is_encrypted_url and media_key:
                                logger.info("🔓 Found encrypted WhatsApp audio with media key - attempting decryption")
                                transcription = self.audio_transcriber.transcribe_encrypted_audio(media_url, media_key)
                                
                                if transcription:
                                    logger.info(f"✅ Successfully transcribed encrypted audio: {transcription}")
                                    data['transcription'] = transcription
                                    transcription_successful = True
                                else:
                                    logger.warning("❌ Failed to transcribe encrypted audio message")
                        
                        else:
                            logger.warning("❌ No processed audio file or media key available for transcription")
                    else:
                        logger.warning("No media URL found for audio message")
                
                # Extract message content (will use transcription if available)
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
                
                # ================= Media Handling (Images, Videos, Documents) =================
                media_contents_to_send: Optional[List[Dict[str, Any]]] = None

                if is_media_message:
                    # Extract media URL for any media type
                    media_url_to_send = self._extract_media_url_from_payload(data)
                    if media_url_to_send:
                        logger.info(f"Media URL found in message: {self._truncate_url_for_logging(media_url_to_send)}")

                        # Convert Minio URL to external if necessary
                        if "minio:" in media_url_to_send:
                            media_url_to_send = self._convert_minio_url(media_url_to_send)
                            logger.info(f"Converted Minio URL: {self._truncate_url_for_logging(media_url_to_send)}")

                        # Extract metadata based on media type
                        message_obj = data.get('message', {})
                        media_meta = {}
                        
                        if 'imageMessage' in message_obj:
                            media_meta = message_obj.get('imageMessage', {})
                        elif 'videoMessage' in message_obj:
                            media_meta = message_obj.get('videoMessage', {})
                        elif 'documentMessage' in message_obj:
                            media_meta = message_obj.get('documentMessage', {})
                        
                        # Build media_contents payload as expected by Agent API
                        # PRIORITY 1: Use base64 data if available (preferred by agent API)
                        # Check for base64 in the correct location: data.message.base64
                        base64_data = None
                        message_obj = data.get('message', {})
                        
                        # First check if base64 is directly in message object (correct location from logs)
                        if 'base64' in message_obj:
                            base64_data = message_obj['base64']
                            logger.debug(f"DEBUG: Found base64 in message object")
                        
                        # Fallback: check if base64 is directly in data
                        elif 'base64' in data:
                            base64_data = data['base64']
                            logger.debug(f"DEBUG: Found base64 in data object")
                        
                        # Fallback: check if base64 is nested in media type objects
                        else:
                            for media_type_key in ['imageMessage', 'videoMessage', 'documentMessage', 'audioMessage']:
                                if media_type_key in message_obj:
                                    media_obj = message_obj[media_type_key]
                                    logger.debug(f"DEBUG: Checking {media_type_key}, keys: {list(media_obj.keys()) if isinstance(media_obj, dict) else 'not dict'}")
                                    if isinstance(media_obj, dict) and 'base64' in media_obj:
                                        base64_data = media_obj['base64']
                                        logger.debug(f"DEBUG: Found base64 in {media_type_key}")
                                        break
                        
                        logger.debug(f"DEBUG: Looking for base64 in data. Keys in data: {list(data.keys())}")
                        logger.debug(f"DEBUG: Message keys: {list(data.get('message', {}).keys())}")
                        logger.debug(f"DEBUG: Root message keys: {list(message.keys())}")
                        if base64_data:
                            logger.debug(f"DEBUG: base64_data found (length: {len(base64_data)} chars)")
                        else:
                            logger.debug(f"DEBUG: No base64_data found anywhere")
                        media_item = {
                            "alt_text": message_content or message_type,
                            "mime_type": media_meta.get('mimetype', f"{message_type}/")
                        }
                        
                        if config.whatsapp.use_base64_media and base64_data:
                            # Use base64 data in the data field (when enabled)
                            media_item["data"] = base64_data
                            logger.info(f"Using base64 data for agent API (size: {len(base64_data)} chars)")
                        else:
                            # Use standard media URL (default behavior)
                            media_item["media_url"] = media_url_to_send
                            if base64_data and not config.whatsapp.use_base64_media:
                                logger.info(f"Base64 data available but USE_BASE64_MEDIA=false, using media URL: {self._truncate_url_for_logging(media_url_to_send)}")
                            else:
                                logger.warning(f"No base64 data available, using media URL: {self._truncate_url_for_logging(media_url_to_send)}")
                        
                        # Add type-specific metadata
                        if 'imageMessage' in message_obj or 'videoMessage' in message_obj:
                            media_item["width"] = media_meta.get('width', 0)
                            media_item["height"] = media_meta.get('height', 0)
                        elif 'documentMessage' in message_obj:
                            media_item["name"] = media_meta.get('fileName', 'document')
                            media_item["size_bytes"] = media_meta.get('fileLength', 0)
                        
                        media_contents_to_send = [media_item]

                # ================= End Media Handling =============

                # If it's an audio message and transcription failed, don't proceed
                if is_audio_message and not transcription_successful and not message_content.strip():
                    logger.info("Skipping audio message processing as transcription failed and no content available")
                    response_result = self._send_whatsapp_response(
                        recipient=sender_id,
                        text="Recebi seu áudio, mas não consegui transcrever o conteúdo. Poderia enviar sua mensagem em texto?",
                        quoted_message=message
                    )
                    presence_updater.mark_message_sent()
                    return
                
                # Create agent config using instance-specific or global configuration
                if instance_config:
                    # Use per-instance configuration
                    agent_config = {
                        "name": instance_config.default_agent,
                        "type": "whatsapp",
                        "api_url": instance_config.agent_api_url,
                        "api_key": instance_config.agent_api_key,
                        "timeout": instance_config.agent_timeout
                    }
                    logger.info(f"Using instance-specific agent config: {instance_config.name} -> {instance_config.default_agent}")
                else:
                    # Fallback to global configuration
                    agent_config = {
                        "name": config.agent_api.default_agent_name,
                        "type": "whatsapp"
                    }
                    logger.info(f"Using global agent config: {config.agent_api.default_agent_name}")
                
                # Generate a session ID based on the sender's WhatsApp ID
                # Create a deterministic hash from the sender's WhatsApp ID
                hash_obj = hashlib.md5(sender_id.encode())
                
                # Get the session ID prefix from config
                session_id_prefix = config.whatsapp.session_id_prefix
                
                # Create a readable session name instead of UUID
                # Format: prefix + phone_number (cleaned)
                session_name = f"{session_id_prefix}{phone_number}"
                
                logger.info(f"Using session name: {session_name}")
                
                # Determine message_type parameter for Agent API
                if is_media_message:
                    # For all media types (images, videos, documents), use the specific type
                    if message_type in ['imageMessage', 'image']:
                        message_type_param = "image"
                    elif message_type in ['videoMessage', 'video']:
                        message_type_param = "video"
                    elif message_type in ['documentMessage', 'document']:
                        message_type_param = "document"
                    else:
                        message_type_param = "media"  # fallback
                elif is_audio_message:
                    # We use "text" because we've transcribed the audio
                    message_type_param = "text"
                else:
                    message_type_param = "text"

                logger.info(f"Routing message to API for user {user_dict['phone_number']}, session {session_name}: {message_content}")
                try:
                    agent_response = message_router.route_message(
                        user=user_dict,
                        session_name=session_name,
                        message_text=message_content,
                        message_type=message_type_param,
                        whatsapp_raw_payload=message,
                        session_origin="whatsapp",
                        agent_config=agent_config,
                        media_contents=media_contents_to_send
                    )
                except TypeError as te:
                    # Fallback for older versions of MessageRouter without media parameters
                    logger.warning(f"Route_message did not accept media_contents parameter, retrying without it: {te}")
                    agent_response = message_router.route_message(
                        user=user_dict,
                        session_name=session_name,
                        message_text=message_content,
                        message_type=message_type_param,
                        whatsapp_raw_payload=message,
                        session_origin="whatsapp",
                        agent_config=agent_config
                    )
                
                # Calculate elapsed time since processing started
                elapsed_time = time.time() - processing_start_time
                
                # Note: We're not using sleep anymore, just log the time
                logger.info(f"Processing completed in {elapsed_time:.2f}s")
                
                # Extract message text and log additional information from agent response
                if isinstance(agent_response, dict):
                    # Full agent response structure
                    message_text = agent_response.get('message', '')
                    session_id = agent_response.get('session_id', 'unknown')
                    success = agent_response.get('success', True)
                    tool_calls = agent_response.get('tool_calls', [])
                    usage = agent_response.get('usage', {})
                    
                    # Log detailed agent response information
                    logger.info(f"Agent response - Session: {session_id}, Success: {success}, Tools used: {len(tool_calls)}")
                    if usage:
                        logger.debug(f"Agent usage stats: {usage}")
                    if tool_calls:
                        logger.debug(f"Tool calls made: {[tool.get('function', {}).get('name', 'unknown') for tool in tool_calls]}")
                    
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
                    logger.warning(f"Ignoring AUTOMAGIK message for user {user_dict['phone_number']}, session {session_name}: {response_to_send}")
                else:
                    # Send the response immediately while the typing indicator is still active
                    # Include the original message for quoting (reply)
                    response_result = self._send_whatsapp_response(
                        recipient=sender_id,
                        text=response_to_send,
                        quoted_message=message
                    )
                    
                    # Mark message as sent but let the typing indicator continue for a short time
                    # This creates a more natural transition
                    presence_updater.mark_message_sent()
                    
                    logger.info(f"Sent agent response to user_id={user_dict['phone_number']}, session_id={session_name}")
            
            finally:
                # Make sure typing indicator is stopped even if processing fails
                presence_updater.stop()
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
    
    def _send_whatsapp_response(self, recipient: str, text: str, quoted_message: Optional[Dict[str, Any]] = None):
        """Send a response back via WhatsApp with optional message quoting."""
        response_payload = None
        if self.send_response_callback:
            try:
                # The Evolution API sender now supports quoting
                success = self.send_response_callback(recipient, text, quoted_message)
                if success:
                    # Extract just the phone number without the suffix for logging
                    clean_recipient = recipient.split('@')[0] if '@' in recipient else recipient
                    logger.info(f"➤ Sent response to {clean_recipient}")
                else:
                    logger.error(f"❌ Failed to send response to {recipient}")
            except Exception as e:
                logger.error(f"❌ Error sending response: {e}", exc_info=True)
        else:
            logger.warning("⚠️ No send response callback set, message not sent")
        
        return response_payload

    def _convert_minio_url(self, url: str) -> str:
        """Convert internal minio URLs to use the configured external Minio URL."""
        if not url or "minio:9000" not in url:
            return url
            
        # Get the external Minio URL from config
        minio_ext_url = config.whatsapp.minio_url
        if not minio_ext_url:
            return url
            
        try:
            # Extract the path and query string from the URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path_and_query = parsed.path
            if parsed.query:
                path_and_query += f"?{parsed.query}"
                
            # Create new URL with the external Minio address
            # Ensure we have a proper URL format with protocol
            if not minio_ext_url.startswith(('http://', 'https://')):
                external_url = f"http://{minio_ext_url.rstrip('/')}"
            else:
                external_url = minio_ext_url.rstrip('/')
                
            converted_url = f"{external_url}{path_and_query}"
            logger.info(f"\033[96mConverted internal minio URL to external URL: {self._truncate_url_for_logging(converted_url)}\033[0m")
            return converted_url
        except Exception as e:
            logger.warning(f"\033[93mFailed to convert minio URL: {str(e)}\033[0m")
            return url
    
    def _extract_media_url_from_payload(self, data: dict) -> Optional[str]:
        """Extract media URL from WhatsApp message payload with retry logic for file availability."""
        try:
            # Log data structure summary without base64 content
            data_keys = list(data.keys())
            message_keys = list(data.get('message', {}).keys()) if isinstance(data.get('message'), dict) else []
            has_base64 = 'base64' in str(data)
            logger.info(f"🔍 DEBUG: Data structure - keys: {data_keys}, message_keys: {message_keys}, has_base64: {has_base64}")
            
            # PRIORITY 1: Check for Evolution API processed mediaUrl in message data
            message_data = data.get("message", {})
            if isinstance(message_data, dict) and 'mediaUrl' in message_data:
                evolution_media_url = message_data['mediaUrl']
                logger.info(f"✅ Found Evolution API processed mediaUrl: {self._truncate_url_for_logging(str(evolution_media_url))}")
                if evolution_media_url:
                    return self._check_and_wait_for_file_availability(evolution_media_url)
                else:
                    logger.warning("⚠️ Evolution mediaUrl exists but value is empty/None")
            
            # PRIORITY 2: Check for mediaUrl at top level (legacy)
            logger.info(f"🔍 DEBUG: Checking for top-level 'mediaUrl' key: {'mediaUrl' in data}")
            if 'mediaUrl' in data:
                media_url = data['mediaUrl']
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
                media_types = ["audioMessage", "videoMessage", "imageMessage", "documentMessage", "stickerMessage"]
                
                for media_type in media_types:
                    if media_type in message_data:
                        media_info = message_data[media_type]
                        logger.info(f"🔍 DEBUG: Found {media_type}, keys: {list(media_info.keys()) if isinstance(media_info, dict) else 'Not a dict'}")
                        if isinstance(media_info, dict) and "url" in media_info:
                            url = media_info["url"]
                            logger.info(f"✓ Found {media_type} URL in message structure: {self._truncate_url_for_logging(url)}")
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
                media_types = ["audioMessage", "videoMessage", "imageMessage", "documentMessage"]
                
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
            logger.info(f"🔄 Found Minio URL, checking file availability with retries: {self._truncate_url_for_logging(url)}")
            
            # Wait and retry to ensure file upload is complete
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                if attempt > 0:
                    logger.info(f"⏳ Waiting {retry_delay}s for file upload completion (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                
                # Quick head request to check file availability
                try:
                    response = requests.head(url.replace("minio:9000", "localhost:9000"), timeout=5)
                    if response.status_code == 200:
                        logger.info(f"✅ File confirmed available after {attempt + 1} attempts")
                        return url
                    elif response.status_code == 404:
                        logger.warning(f"⏳ File not yet available (404), attempt {attempt + 1}/{max_retries}")
                    else:
                        logger.warning(f"⚠️ Unexpected response {response.status_code}, attempt {attempt + 1}/{max_retries}")
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
                path_parts = path.split('/')
                if len(path_parts) > 4:
                    # Keep first 2 and last part
                    short_path = '/'.join(path_parts[:2]) + '/.../' + path_parts[-1]
                else:
                    short_path = path[:15] + '...' + path[-15:]
            else:
                short_path = path
                
            # Format with just a hint of the query string
            query = parsed.query
            query_hint = '?' + query[:10] + '...' if query else ''
            
            return f"{parsed.scheme}://{host}{short_path}{query_hint}"
            
        except Exception:
            # If parsing fails, do a simple truncation
            return url[:30] + '...' + url[-30:]
    
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
            data = message.get('data', {})
            
            # Check for transcription first (for audio messages)
            if 'transcription' in data:
                return data['transcription']
            
            # Check if we have a conversation message
            message_obj = data.get('message', {})
            
            # Try to find the message content in common places
            if isinstance(message_obj, dict):
                # Check for text message
                if 'conversation' in message_obj:
                    return message_obj['conversation']
                
                # Check for extended text message
                elif 'extendedTextMessage' in message_obj:
                    return message_obj['extendedTextMessage'].get('text', '')
                
                # Check for button response
                elif 'buttonsResponseMessage' in message_obj:
                    return message_obj['buttonsResponseMessage'].get('selectedDisplayText', '')
                
                # Check for list response
                elif 'listResponseMessage' in message_obj:
                    return message_obj['listResponseMessage'].get('title', '')
                
                # Check for media captions (images, videos, documents)
                elif 'imageMessage' in message_obj:
                    return message_obj['imageMessage'].get('caption', '')
                
                elif 'videoMessage' in message_obj:
                    return message_obj['videoMessage'].get('caption', '')
                    
                elif 'documentMessage' in message_obj:
                    return message_obj['documentMessage'].get('caption', '')
            
            # If we have raw text content directly in the data
            if 'body' in data:
                return data['body']
                
            # For audio messages, return empty string instead of placeholder
            # This allows the calling code to handle audio messages properly
            message_type = data.get('messageType', '')
            if message_type in ['audioMessage', 'audio', 'voice', 'ptt']:
                return ""
                
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
            data = message.get('data', {})
            
            # Check for quoted message in contextInfo
            context_info = data.get('contextInfo', {})
            quoted_message = context_info.get('quotedMessage', {})
            
            if not quoted_message:
                # Also check in message.contextInfo structure
                message_obj = data.get('message', {})
                context_info = message_obj.get('contextInfo', {})
                quoted_message = context_info.get('quotedMessage', {})
            
            if quoted_message:
                # Extract quoted text content
                quoted_text = ""
                
                # Check different message types in quoted message
                if 'conversation' in quoted_message:
                    quoted_text = quoted_message['conversation']
                elif 'extendedTextMessage' in quoted_message:
                    quoted_text = quoted_message['extendedTextMessage'].get('text', '')
                elif 'imageMessage' in quoted_message:
                    quoted_text = quoted_message['imageMessage'].get('caption', '[Image]')
                elif 'videoMessage' in quoted_message:
                    quoted_text = quoted_message['videoMessage'].get('caption', '[Video]')
                elif 'documentMessage' in quoted_message:
                    quoted_text = quoted_message['documentMessage'].get('caption', '[Document]')
                elif 'audioMessage' in quoted_message:
                    quoted_text = '[Audio Message]'
                
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
            data = message.get('data', {})
            
            # First check if the messageType is already provided by Evolution API
            if 'messageType' in data:
                msg_type = data['messageType']
                # Normalize message types
                if msg_type == 'pttMessage':
                    return 'ptt'
                elif msg_type == 'voiceMessage':
                    return 'voice'
                elif msg_type == 'audioMessage':
                    return 'audio'
                return msg_type
            
            # Otherwise try to determine from the message object
            message_obj = data.get('message', {})
            
            if not message_obj or not isinstance(message_obj, dict):
                return ""
                
            # Check for common message types
            if 'conversation' in message_obj:
                return 'text'
                
            elif 'extendedTextMessage' in message_obj:
                return 'text'
                
            elif 'audioMessage' in message_obj:
                return 'audio'
                
            elif 'pttMessage' in message_obj:
                return 'ptt'
                
            elif 'voiceMessage' in message_obj:
                return 'voice'
                
            elif 'imageMessage' in message_obj:
                return 'image'
                
            elif 'videoMessage' in message_obj:
                return 'video'
                
            elif 'documentMessage' in message_obj:
                return 'document'
                
            elif 'stickerMessage' in message_obj:
                return 'sticker'
                
            elif 'contactMessage' in message_obj:
                return 'contact'
                
            elif 'locationMessage' in message_obj:
                return 'location'
                
            # Fallback to the event type if available
            if 'event' in message:
                return message['event']
                
            # Could not determine message type
            logger.warning(f"Could not determine message type from payload: {message}")
            return 'unknown'
            
        except Exception as e:
            logger.error(f"Error determining message type: {e}", exc_info=True)
            return 'unknown'

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
        phone = ''.join(filter(str.isdigit, phone))
        
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