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

from src.config import config
from src.db.engine import get_session
from src.db.repositories import (
    UserRepository,
    SessionRepository,
    ChatMessageRepository,
    AgentRepository
)
from src.agent.agent import AgentImplementation
from src.channels.whatsapp.audio_transcriber import AudioTranscriptionService

# Configure logging
logger = logging.getLogger("src.channels.whatsapp.handlers")

class WhatsAppMessageHandler:
    """Handler for WhatsApp messages."""
    
    def __init__(self):
        self.message_queue = queue.Queue()
        self.processing_thread = None
        self.is_running = False
        self.agent = AgentImplementation()
        self.send_response_callback = None
        self.audio_transcriber = AudioTranscriptionService()
    
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
    
    def set_send_response_callback(self, callback: Callable[[str, str], bool]):
        """Set the callback function for sending responses."""
        self.send_response_callback = callback
    
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
        """Process a single message."""
        try:
            # Only process messages_upsert events
            if message.get('event') != 'messages.upsert':
                logger.debug(f"Ignoring non-message event: {message.get('event')}")
                return
            
            # Extract the sender's WhatsApp ID
            data = message.get('data', {})
            key = data.get('key', {})
            sender_id = key.get('remoteJid')
            
            # Skip messages sent by us
            if key.get('fromMe', False):
                logger.debug(f"Ignoring message sent by us to {sender_id}")
                return
            
            # Skip messages without a sender
            if not sender_id:
                logger.warning("Message has no sender ID, skipping")
                return
            
            # Check if this is an audio message and try to transcribe
            message_type = message.get('messageType', '')
            message_content = data.get('message', {})
            is_audio_message = message_type == 'audioMessage' or 'audioMessage' in message_content
            
            if is_audio_message and self.audio_transcriber.is_configured():
                logger.info("Audio message detected, attempting transcription")
                
                # First, get the message ID
                message_id = key.get('id')
                if not message_id:
                    logger.warning("Audio message has no ID, cannot process for transcription")
                else:
                    # Add delay before retrieving from Evolution DB
                    # to ensure message has been fully persisted
                    delay_seconds = 0
                    logger.info(f"Waiting {delay_seconds} seconds before retrieving message from Evolution DB...")
                    time.sleep(delay_seconds)
                    
                    # Retrieve the full message from Evolution database
                    logger.info(f"Retrieving message details from Evolution DB for ID: {message_id}")
                    evolution_message = self._retrieve_message_from_evolution_db(message_id)
                    
                    if not evolution_message:
                        logger.warning(f"Could not retrieve message {message_id} from Evolution DB")
                        # Fallback to processing with payload data
                        media_url = self._extract_media_url_from_payload(data)
                    else:
                        logger.info(f"Successfully retrieved message from Evolution DB: {message_id}")
                        # Extract media URL from the retrieved message
                        media_url = self._extract_media_url_from_evolution_message(evolution_message)
                        
                    if media_url:
                        # Log the URL we're using for transcription (without any modifications)
                        logger.info(f"Using URL for transcription: {self._truncate_url_for_logging(media_url)}")
                        
                        # Try to transcribe the audio with fallback methods
                        transcription = self.audio_transcriber.transcribe_with_fallback(media_url)
                        
                        if transcription:
                            logger.info(f"\033[92mSuccessfully transcribed audio: {transcription[:100]}...\033[0m")
                            
                            # Save the transcription in the data dict to be stored with the message
                            data['transcription'] = transcription
                        else:
                            logger.warning("\033[93mFailed to transcribe audio message\033[0m")
                    else:
                        logger.warning("\033[93mAudio message detected but no media URL found\033[0m")
            
            # Process the message in the database
            with get_session() as db:
                try:
                    # Get or create user
                    user_repo = UserRepository(db)
                    user = user_repo.get_or_create_by_whatsapp(sender_id)
                    
                    # Ensure user has an ID
                    if not user.id:
                        logger.warning(f"\033[93mUser has no ID after creation/retrieval: {user}\033[0m")
                        db.refresh(user)  # Try to refresh from DB
                        if not user.id:
                            logger.error("\033[91mFailed to get valid user ID, cannot process message\033[0m")
                            return
                    
                    # Log user details for debugging
                    logger.info(f"\033[96mProcessing message for user: id={user.id}, phone={user.phone_number}\033[0m")
                    
                    # Get or create session
                    session_repo = SessionRepository(db)
                    session = session_repo.get_or_create_for_user(user.id, 'whatsapp')
                    
                    # Save the message
                    msg_repo = ChatMessageRepository(db)
                    
                    # For audio messages with transcription, set the transcription as text content
                    if is_audio_message and 'transcription' in data:
                        logger.info("\033[92mStoring audio message with transcription\033[0m")
                        chat_message = msg_repo.create_from_whatsapp(
                            session.id, 
                            user.id, 
                            message, 
                            override_text=data['transcription']
                        )
                        # Note that we're storing the transcription directly in the text_content field
                        # This allows the audio message to have the actual transcribed text instead of "[Audio]"
                        # The message type remains "audio" to indicate it's an audio file
                        logger.info(f"\033[92mStored audio transcription in message text_content\033[0m")
                    else:
                        chat_message = msg_repo.create_from_whatsapp(session.id, user.id, message)
                        
                    logger.info(f"\033[92mCreated chat message: id={chat_message.id}, user_id={chat_message.user_id}\033[0m")
                    
                    # Get active agent
                    agent_repo = AgentRepository(db)
                    agent = agent_repo.get_active_agent(agent_type='whatsapp')
                    
                    if not agent:
                        logger.warning("No active WhatsApp agent found")
                        return
                    
                    # Ensure agent has an ID
                    if not agent.id:
                        logger.warning("Agent has no ID, cannot process message")
                        return
                    
                    # Get conversation history
                    conversation_messages = msg_repo.get_by_session(session.id, limit=20)
                    
                    # Generate agent response
                    agent_response = self.agent.generate_response(
                        user_id=user.id,
                        session_id=session.id,
                        message_text=chat_message.text_content or "",
                        message_type=chat_message.message_type,
                        conversation_history=conversation_messages,
                        agent=agent
                    )
                    
                    # First send the response via WhatsApp to get the message ID
                    response_result = self._send_whatsapp_response(
                        recipient=sender_id,
                        text=agent_response
                    )
                    
                    # Get the message ID from the response payload or generate one if not available
                    wpp_message_id = None
                    if response_result and isinstance(response_result, dict):
                        # Try to extract message ID from the response payload
                        if 'raw_response' in response_result and response_result['raw_response']:
                            raw_response = response_result['raw_response']
                            if isinstance(raw_response, dict) and 'key' in raw_response:
                                wpp_message_id = raw_response['key'].get('id')
                            elif isinstance(raw_response, dict) and 'id' in raw_response:
                                wpp_message_id = raw_response['id']
                    
                    # If we couldn't extract a message ID, use a timestamp-based ID
                    if not wpp_message_id:
                        import uuid
                        # Create a deterministic ID similar to WhatsApp format
                        wpp_message_id = f"AGENT{int(time.time())}{str(uuid.uuid4())[:8]}"
                    
                    # Now create the agent message with the WhatsApp message ID
                    agent_message = agent_repo.create_agent_response(
                        session_id=session.id,
                        user_id=user.id,  # Ensure user ID is set
                        agent_id=agent.id,  # Ensure agent ID is set
                        text_content=agent_response,
                        id=wpp_message_id  # Use WhatsApp message ID
                    )
                    
                    logger.info(f"Created agent response with ID={wpp_message_id} for user_id={user.id}, session_id={session.id}")
                    
                    # Update the agent message with the response payload if available
                    if response_result:
                        msg_repo = ChatMessageRepository(db)
                        msg_repo.update(agent_message.id, raw_payload=response_result)
                        logger.info(f"Updated agent message with response payload: {agent_message.id}")
                    
                except Exception as e:
                    logger.error(f"Database error processing message: {e}", exc_info=True)
                    db.rollback()
                
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

# Singleton instance
message_handler = WhatsAppMessageHandler() 