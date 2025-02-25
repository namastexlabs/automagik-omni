"""
WhatsApp message handlers.
Processes incoming messages from the Evolution API.
"""

import logging
import json
from typing import Dict, Any, Optional, Callable
import threading
import queue

from src.config import config
from src.db.engine import get_session
from src.db.repositories import (
    UserRepository,
    SessionRepository,
    ChatMessageRepository,
    AgentRepository
)
from src.agent.agent import AgentImplementation

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
            
            # Process the message in the database
            with get_session() as db:
                try:
                    # Get or create user
                    user_repo = UserRepository(db)
                    user = user_repo.get_or_create_by_whatsapp(sender_id)
                    
                    # Ensure user has an ID
                    if not user.id:
                        logger.warning(f"User has no ID after creation/retrieval: {user}")
                        db.refresh(user)  # Try to refresh from DB
                        if not user.id:
                            logger.error("Failed to get valid user ID, cannot process message")
                            return
                    
                    # Log user details for debugging
                    logger.info(f"Processing message for user: id={user.id}, phone={user.phone_number}")
                    
                    # Get or create session
                    session_repo = SessionRepository(db)
                    session = session_repo.get_or_create_for_user(user.id, 'whatsapp')
                    
                    # Save the message
                    msg_repo = ChatMessageRepository(db)
                    chat_message = msg_repo.create_from_whatsapp(session.id, user.id, message)
                    logger.info(f"Created chat message: id={chat_message.id}, user_id={chat_message.user_id}")
                    
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
                        import time
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

# Singleton instance
message_handler = WhatsAppMessageHandler() 