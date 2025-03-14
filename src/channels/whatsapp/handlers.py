"""
WhatsApp message handlers.
Processes incoming messages from the Evolution API.
"""

import logging
import json
from typing import Dict, Any, Optional, Callable, List
import threading
import queue
import time
import os
import hashlib
import uuid

from src.config import config
from src.db.engine import get_session
from src.db.repositories import (
    UserRepository,
    SessionRepository,
    ChatMessageRepository,
    AgentRepository
)
from src.services.message_router import message_router
from src.channels.whatsapp.audio_transcriber import AudioTranscriptionService

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
    
    def handle_message(self, message: Dict[str, Any]):
        """Queue a message for processing."""
        self.message_queue.put(message)
        logger.debug(f"Message queued for processing: {message.get('event')}")
    
    def _process_messages_loop(self):
        """Process messages from the queue in a loop."""
        while self.is_running:
            try:
                # Get message with timeout to allow for clean shutdown
                message = self.message_queue.get(timeout=1.0)
                self._process_message(message)
                self.message_queue.task_done()
            except queue.Empty:
                # No messages, continue waiting
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
    
    def _process_message(self, message: Dict[str, Any]):
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
                
            # Extract message type
            message_type = self._extract_message_type(message)
            if not message_type:
                logger.warning("Unable to determine message type")
                return
            
            # Get or create user
            max_retries = 3
            retry_count = 0
            user = None
            user_id = None
            
            while retry_count < max_retries:
                try:
                    with get_session() as db:
                        user_repo = UserRepository(db)
                        user = user_repo.get_or_create_by_whatsapp(
                            whatsapp_id=sender_id
                        )
                        
                        # Ensure we have a valid user ID
                        if user and user.id:
                            user_id = user.id
                            logger.info(f"Using user ID: {user_id}")
                            break  # Success, exit retry loop
                        else:
                            logger.warning("Could not get valid user ID, will retry")
                            retry_count += 1
                            time.sleep(0.5)  # Small delay before retry
                except Exception as e:
                    logger.error(f"Error creating/getting user (attempt {retry_count + 1}): {e}", exc_info=True)
                    retry_count += 1
                    time.sleep(0.5)  # Small delay before retry
            
            if not user_id:
                logger.error("Failed to get valid user ID after multiple attempts, proceeding with None")
                user_id = None
                
            # Extract message content
            message_content = self._extract_message_content(message)
            
            # Instead of getting the agent from the database, create a simple config with the default agent name
            agent_config = {
                "name": config.agent_api.default_agent_name,
                "type": "whatsapp"
            }
            
            # Extract any media URL from the message
            media_url = self._extract_media_url_from_payload(data)
            if media_url:
                logger.info(f"Media URL found in message: {self._truncate_url_for_logging(media_url)}")
                
                # If media URL is from minio, convert to accessible URL
                if "minio:" in media_url:
                    media_url = self._convert_minio_url(media_url)
                    logger.info(f"Converted Minio URL: {self._truncate_url_for_logging(media_url)}")
                
                # If this is an audio message, attempt to transcribe it
                if message_type == 'audioMessage' or message_type == 'audio' or message_type == 'voice' or message_type == 'ptt':
                    logger.info(f"Attempting to transcribe audio message from URL: {self._truncate_url_for_logging(media_url)}")
                    
                    # Check if the audio transcription service is configured
                    if not self.audio_transcriber.is_configured():
                        logger.warning("Audio transcription service is not properly configured. Skipping transcription.")
                    else:
                        transcription = self.audio_transcriber.transcribe_with_fallback(media_url)
                        if transcription:
                            logger.info(f"Successfully transcribed audio: {transcription}")
                            message_content = transcription
                            # Store transcription in data for later use
                            data['transcription'] = transcription
                        else:
                            logger.warning("Failed to transcribe audio message")
            
            # MODIFIED: Get existing session or use a fixed format session ID without creating a new record
            session_repo = SessionRepository(db)
            session = None
            
            if user_id:
                # Try to get the latest session for this user
                session = session_repo.get_latest_for_user(user_id)
            
            if not session:
                # If no session exists, create a session object with a fixed ID format
                # but don't save it to the database
                session_id_prefix = os.getenv("SESSION_ID_PREFIX", "")
                # Use WhatsApp instance name as part of the session ID
                instance_name = config.rabbitmq.instance_name
                # Create a deterministic hash from the sender's WhatsApp ID
                hash_obj = hashlib.md5(sender_id.encode())
                hash_digest = hash_obj.hexdigest()
                
                # Generate a namespace UUID based on the hash (using UUID5 with DNS namespace)
                # This ensures we get the same UUID for the same WhatsApp ID consistently
                namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
                session_id = uuid.uuid5(namespace, f"{session_id_prefix}{instance_name}-{hash_digest}")
                
                # Check if this session already exists
                session = session_repo.get(session_id)
                
                if not session:
                    # Create a session object but don't add it to the database
                    from src.db.models import Session as DbSession
                    session = DbSession(
                        id=session_id,
                        user_id=user_id,
                        platform='whatsapp'
                    )
                    logger.info(f"Using temporary session with ID: {session_id} (not saved to DB)")
            
            # Check for transcription
            transcription = data.get('transcription')
            if transcription and (message_type == 'audioMessage' or message_type == 'audio' or message_type == 'voice' or message_type == 'ptt'):
                logger.info(f"Using transcription: {transcription}")
                message_content = transcription
            
            # Generate agent response without saving the user message to DB
            logger.info(f"Routing message to API for user {user_id}, session {session.id}: {message_content}")
            agent_response = message_router.route_message(
                user_id=user_id,
                session_id=session.id,
                message_text=message_content,
                message_type=message_type,
                whatsapp_raw_payload=message,
                session_origin="whatsapp",
                agent_config=agent_config
            )
            
            # Send the response via WhatsApp
            response_result = self._send_whatsapp_response(
                recipient=sender_id,
                text=agent_response
            )
            
            logger.info(f"Sent agent response to user_id={user_id}, session_id={session.id}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
    
    def _send_whatsapp_response(self, recipient: str, text: str):
        """Send a response back via WhatsApp."""
        response_payload = None
        if self.send_response_callback:
            try:
                success, response_data = self.send_response_callback(recipient, text)
                if success:
                    logger.info(f"Sent response to {recipient}")
                    # Store the response payload for later use
                    response_payload = response_data
                else:
                    logger.error(f"Failed to send response to {recipient}")
            except Exception as e:
                logger.error(f"Error sending response: {e}", exc_info=True)
        else:
            logger.warning(f"No send response callback set, message to {recipient} not sent")
        
        return response_payload

    def _retrieve_message_from_evolution_db(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve message details from Evolution database."""
        try:
            # Only import SQLAlchemy when needed
            from sqlalchemy import create_engine, text
            
            # Get the database URI from config
            db_uri = config.evolution_database.uri
            
            if not db_uri:
                logger.error("Evolution database URI not configured")
                return None
                
            # Create database engine
            engine = create_engine(
                db_uri,
                echo=False,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True
            )
            
            # Query to get message by ID
            query = '''
                SELECT id, "messageTimestamp", "messageType", message, "pushName", key
                FROM public."Message"
                WHERE id = :message_id
                LIMIT 1
            '''
            
            # Execute query
            with engine.connect() as conn:
                result = conn.execute(text(query), {"message_id": message_id})
                message = result.fetchone()
                
            if not message:
                logger.warning(f"No message found in Evolution DB with ID: {message_id}")
                return None
                
            # Convert row to dict
            message_dict = {column: value for column, value in zip(result.keys(), message)}
            
            # Parse JSON fields
            if 'message' in message_dict and message_dict['message']:
                try:
                    message_dict['message'] = json.loads(message_dict['message'])
                except:
                    pass
                    
            if 'key' in message_dict and message_dict['key']:
                try:
                    message_dict['key'] = json.loads(message_dict['key'])
                except:
                    pass
            
            return message_dict
            
        except Exception as e:
            logger.error(f"Error retrieving message from Evolution DB: {str(e)}")
            return None
            
    def _extract_media_url_from_evolution_message(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract media URL from Evolution database message."""
        try:
            # First check for mediaUrl at the top level
            media_url = message.get('mediaUrl')
            if media_url:
                # Return as-is, no conversion needed
                return media_url
                
            # Check in the message content if it's a dict
            message_content = message.get('message')
            if isinstance(message_content, dict):
                # Check for audioMessage
                audio_message = message_content.get('audioMessage')
                if isinstance(audio_message, dict):
                    url = audio_message.get('url')
                    if url:
                        return url  # WhatsApp URL doesn't need conversion
                        
                # Check for mediaUrl in message content
                media_url = message_content.get('mediaUrl')
                if media_url:
                    # Return as-is, no conversion needed
                    return media_url
                
            return None
            
        except Exception as e:
            logger.error(f"\033[91mError extracting media URL from Evolution message: {str(e)}\033[0m")
            return None
            
    def _convert_minio_url(self, url: str) -> str:
        """Convert internal minio URLs to use the configured external Minio URL."""
        if not url or "minio:9000" not in url:
            return url
            
        # Get the external Minio URL from environment
        minio_ext_url = os.getenv("EVOLUTION_MINIO_URL", "")
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
    
    def _extract_media_url_from_payload(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract media URL from the webhook payload."""
        try:
            # First check for mediaUrl at the data root level (usually the Minio URL)
            media_url = data.get('mediaUrl')
            
            # If there's no media URL at the root level, check in the message content
            if not media_url:
                message_content = data.get('message', {})
                if 'audioMessage' in message_content:
                    whatsapp_url = message_content.get('audioMessage', {}).get('url', '')
                    if whatsapp_url:
                        media_url = whatsapp_url
                
                # Get mediaUrl directly from the 'message' object if it exists
                if isinstance(message_content, dict) and 'mediaUrl' in message_content:
                    minio_url = message_content.get('mediaUrl')
                    if minio_url:
                        media_url = minio_url
            
            # Do NOT convert internal minio URLs - the transcription service expects this format
            return media_url
            
        except Exception as e:
            logger.error(f"\033[91mError extracting media URL from payload: {str(e)}\033[0m")
            return None

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
            
            # If no text content found but it's an audio message
            message_type = data.get('messageType', '')
            if message_type == 'audioMessage':
                return "[Audio Message]"
            
            # If no text content found but it's an image message
            if message_type == 'imageMessage':
                return "[Image Message]"
                
            # If we have raw text content directly in the data
            if 'body' in data:
                return data['body']
                
            # Could not find any text content
            logger.warning(f"Could not extract message content from payload: {message}")
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting message content: {e}", exc_info=True)
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

# Singleton instance
message_handler = WhatsAppMessageHandler() 