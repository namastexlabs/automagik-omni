"""
WhatsApp Streaming Integration for AutomagikHive

This module provides real-time streaming integration between AutomagikHive and WhatsApp.
It handles real-time message chunking, typing simulation, and seamless delivery of
streaming responses from AutomagikHive to WhatsApp users.

Key Features:
- Real-time message chunking on natural boundaries (newlines)
- Coordinated typing indicator management during streaming
- Rate-limited message delivery with proper ordering
- Error recovery and stream interruption handling
- Integration with existing WhatsApp message processing flow
"""
import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional, List, AsyncIterator
from contextlib import asynccontextmanager

from src.services.automagik_hive_client import AutomagikHiveClient, AutomagikHiveError
from src.services.automagik_hive_models import HiveEvent, HiveEventType, RunResponseContentEvent
from src.channels.whatsapp.evolution_api_sender import EvolutionApiSender, PresenceUpdater
from src.db.models import InstanceConfig

logger = logging.getLogger(__name__)


class WhatsAppMessageChunker:
    """
    Handles intelligent message chunking for WhatsApp delivery.
    Splits content on natural boundaries (newlines) to create readable messages.
    """
    
    def __init__(self, max_chunk_size: int = 4000):
        """
        Initialize the message chunker.
        
        Args:
            max_chunk_size: Maximum size for each message chunk (WhatsApp limit is 4096)
        """
        self.max_chunk_size = max_chunk_size
    
    def split_on_newlines(self, content: str) -> List[str]:
        """
        Split content into chunks based on newline boundaries.
        
        Args:
            content: Content string to split
            
        Returns:
            List of message chunks, each suitable for WhatsApp delivery
        """
        if not content or not content.strip():
            return []
        
        # Split on double newlines first (paragraph breaks), then single newlines
        paragraphs = content.split('\n\n')
        chunks = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
                
            # If paragraph is small enough, add it as a chunk
            if len(paragraph) <= self.max_chunk_size:
                chunks.append(paragraph.strip())
            else:
                # Split long paragraphs on single newlines
                lines = paragraph.split('\n')
                current_chunk = ""
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Check if adding this line would exceed the limit
                    if current_chunk and len(current_chunk + '\n' + line) > self.max_chunk_size:
                        # Save current chunk and start new one
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = line
                    else:
                        # Add line to current chunk
                        if current_chunk:
                            current_chunk += '\n' + line
                        else:
                            current_chunk = line
                
                # Add final chunk if exists
                if current_chunk:
                    chunks.append(current_chunk)
        
        return chunks
    
    def process_stream_content(self, accumulated_content: str, new_content: str) -> tuple[str, List[str]]:
        """
        Process new streaming content and return ready chunks for delivery.
        Only sends messages when a double newline (\\n\\n) is encountered.
        
        Args:
            accumulated_content: Previously accumulated content
            new_content: New content from stream
            
        Returns:
            Tuple of (updated_accumulated_content, ready_chunks_to_send)
        """
        combined_content = accumulated_content + new_content
        
        # Check for double newline (paragraph break)
        if '\n\n' in combined_content:
            # Split at double newlines
            parts = combined_content.split('\n\n')
            
            # All parts except the last are complete paragraphs
            complete_chunks = parts[:-1]
            
            # The last part is the remaining incomplete content
            remaining = parts[-1]
            
            # Filter out empty chunks and return
            ready_chunks = [chunk.strip() for chunk in complete_chunks if chunk.strip()]
            return remaining, ready_chunks
        
        # No double newline yet, keep accumulating
        return combined_content, []


class TypingIndicatorManager:
    """
    Manages typing indicators during streaming to provide natural conversation flow.
    Coordinates with EvolutionAPI PresenceUpdater for continuous typing simulation.
    """
    
    def __init__(self, evolution_sender: EvolutionApiSender, recipient: str):
        """
        Initialize the typing indicator manager.
        
        Args:
            evolution_sender: EvolutionApiSender instance for sending presence
            recipient: WhatsApp ID to send typing indicators to
        """
        self.evolution_sender = evolution_sender
        self.recipient = recipient
        self.presence_updater: Optional[PresenceUpdater] = None
        self.is_active = False
        self.lock = threading.Lock()
    
    def start_typing(self):
        """Start continuous typing indicator."""
        with self.lock:
            if self.is_active:
                return  # Already started
                
            try:
                self.presence_updater = self.evolution_sender.get_presence_updater(
                    self.recipient, "composing"
                )
                self.presence_updater.start()
                self.is_active = True
                logger.debug(f"Started typing indicators for {self.recipient}")
            except Exception as e:
                logger.error(f"Failed to start typing indicators: {e}")
    
    def stop_typing(self):
        """Stop typing indicator and clear it."""
        with self.lock:
            if not self.is_active or not self.presence_updater:
                return
                
            try:
                self.presence_updater.stop()
                self.is_active = False
                logger.debug(f"Stopped typing indicators for {self.recipient}")
            except Exception as e:
                logger.error(f"Failed to stop typing indicators: {e}")
    
    def __enter__(self):
        """Context manager entry - start typing."""
        self.start_typing()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop typing."""
        self.stop_typing()


class MessageQueueHandler:
    """
    Handles queued message delivery with proper ordering and rate limiting.
    Ensures messages are delivered in the correct sequence while respecting WhatsApp limits.
    """
    
    def __init__(self, evolution_sender: EvolutionApiSender, min_delay: float = 0.5):
        """
        Initialize the message queue handler.
        
        Args:
            evolution_sender: EvolutionApiSender for message delivery
            min_delay: Minimum delay between messages (seconds)
        """
        self.evolution_sender = evolution_sender
        self.min_delay = min_delay
        self.last_send_time = 0
        self.lock = threading.Lock()
    
    async def send_message_with_delay(self, recipient: str, message: str) -> bool:
        """
        Send a message with appropriate rate limiting delay.
        
        Args:
            recipient: WhatsApp recipient ID
            message: Message text to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        with self.lock:
            # Calculate required delay
            elapsed = time.time() - self.last_send_time
            if elapsed < self.min_delay:
                delay_needed = self.min_delay - elapsed
                time.sleep(delay_needed)
        
        try:
            # Send the message
            success = self.evolution_sender.send_text_message(recipient, message)
            
            with self.lock:
                self.last_send_time = time.time()
            
            if success:
                logger.debug(f"Sent message chunk to {recipient}: {message[:50]}...")
                return True
            else:
                logger.error(f"Failed to send message chunk to {recipient}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to {recipient}: {e}")
            return False


class AutomagikHiveStreamer:
    """
    Main streaming integration class that bridges AutomagikHive SSE streams 
    to WhatsApp real-time message delivery.
    
    This class orchestrates:
    - Real-time streaming from AutomagikHive
    - Message chunking on natural boundaries
    - Typing indicator management
    - Rate-limited message delivery
    - Error recovery and connection management
    """
    
    def __init__(self, instance_config: InstanceConfig):
        """
        Initialize the AutomagikHive streamer.
        
        Args:
            instance_config: Instance configuration with AutomagikHive and WhatsApp settings
        """
        self.instance_config = instance_config
        self.hive_client = AutomagikHiveClient(instance_config)
        self.evolution_sender = EvolutionApiSender(instance_config)
        self.message_chunker = WhatsAppMessageChunker()
        self.message_queue_handler = MessageQueueHandler(self.evolution_sender)
        self.is_streaming = False
        self.current_streams = {}  # Track active streams by recipient
        logger.info(f"AutomagikHive streamer initialized for instance: {instance_config.name}")
    
    async def stream_agent_to_whatsapp(
        self,
        recipient: str,
        agent_id: str,
        message: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Stream AutomagikHive agent responses to WhatsApp in real-time.
        
        Args:
            recipient: WhatsApp recipient ID
            agent_id: AutomagikHive agent ID
            message: User message to send to agent
            user_id: Optional user ID for context
            
        Returns:
            True if streaming completed successfully, False otherwise
        """
        stream_id = f"{recipient}_{agent_id}_{time.time()}"
        
        try:
            # Start typing indicator
            typing_manager = TypingIndicatorManager(self.evolution_sender, recipient)
            
            with typing_manager:
                # Track this stream
                self.current_streams[stream_id] = {
                    'recipient': recipient,
                    'agent_id': agent_id,
                    'start_time': time.time()
                }
                
                accumulated_content = ""
                message_count = 0
                
                logger.info(f"Starting agent streaming for {recipient}, agent: {agent_id}")
                
                # Stream from AutomagikHive using context manager
                async with self.hive_client.stream_agent_conversation(agent_id, message) as stream:
                    async for event in stream:
                        if event.event == HiveEventType.RUN_RESPONSE_CONTENT:
                            # Process content chunk
                            accumulated_content, ready_chunks = self.message_chunker.process_stream_content(
                                accumulated_content, event.content
                            )
                            
                            # Send ready chunks to WhatsApp
                            for chunk in ready_chunks:
                                if chunk.strip():  # Only send non-empty chunks
                                    success = await self.message_queue_handler.send_message_with_delay(
                                        recipient, chunk
                                    )
                                    if success:
                                        message_count += 1
                                    else:
                                        logger.warning(f"Failed to send chunk to {recipient}")
                        
                        elif event.event == HiveEventType.RUN_COMPLETED:
                            # Send any remaining accumulated content
                            if accumulated_content.strip():
                                final_chunks = self.message_chunker.split_on_newlines(accumulated_content)
                                for chunk in final_chunks:
                                    if chunk.strip():
                                        await self.message_queue_handler.send_message_with_delay(
                                            recipient, chunk
                                        )
                                        message_count += 1
                            
                            logger.info(f"Streaming completed for {recipient}, sent {message_count} messages")
                            break
                        
                        elif event.event == HiveEventType.ERROR:
                            logger.error(f"Stream error for {recipient}: {event.error_message}")
                            # Send error message to user
                            await self.message_queue_handler.send_message_with_delay(
                                recipient, "Sorry, I encountered an error processing your request. Please try again."
                            )
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in stream_agent_to_whatsapp for {recipient}: {e}")
            # Try to send error message to user
            try:
                await self.message_queue_handler.send_message_with_delay(
                    recipient, "Sorry, I encountered a technical error. Please try again."
                )
            except:
                pass
            return False
            
        finally:
            # Clean up stream tracking
            self.current_streams.pop(stream_id, None)
    
    async def stream_team_to_whatsapp(
        self,
        recipient: str,
        team_id: str,
        message: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Stream AutomagikHive team responses to WhatsApp in real-time.
        
        Args:
            recipient: WhatsApp recipient ID
            team_id: AutomagikHive team ID
            message: User message to send to team
            user_id: Optional user ID for context
            
        Returns:
            True if streaming completed successfully, False otherwise
        """
        stream_id = f"{recipient}_{team_id}_{time.time()}"
        
        try:
            # Start typing indicator
            typing_manager = TypingIndicatorManager(self.evolution_sender, recipient)
            
            with typing_manager:
                # Track this stream
                self.current_streams[stream_id] = {
                    'recipient': recipient,
                    'team_id': team_id,
                    'start_time': time.time()
                }
                
                accumulated_content = ""
                message_count = 0
                
                logger.info(f"Starting team streaming for {recipient}, team: {team_id}")
                
                # Stream from AutomagikHive using context manager
                async with self.hive_client.stream_team_conversation(team_id, message) as stream:
                    async for event in stream:
                        if event.event == HiveEventType.RUN_RESPONSE_CONTENT:
                            # Process content chunk
                            accumulated_content, ready_chunks = self.message_chunker.process_stream_content(
                                accumulated_content, event.content
                            )
                            
                            # Send ready chunks to WhatsApp
                            for chunk in ready_chunks:
                                if chunk.strip():  # Only send non-empty chunks
                                    success = await self.message_queue_handler.send_message_with_delay(
                                        recipient, chunk
                                    )
                                    if success:
                                        message_count += 1
                                    else:
                                        logger.warning(f"Failed to send chunk to {recipient}")
                        
                        elif event.event == HiveEventType.RUN_COMPLETED:
                            # Send any remaining accumulated content
                            if accumulated_content.strip():
                                final_chunks = self.message_chunker.split_on_newlines(accumulated_content)
                                for chunk in final_chunks:
                                    if chunk.strip():
                                        await self.message_queue_handler.send_message_with_delay(
                                            recipient, chunk
                                        )
                                        message_count += 1
                            
                            logger.info(f"Team streaming completed for {recipient}, sent {message_count} messages")
                            break
                        
                        elif event.event == HiveEventType.ERROR:
                            logger.error(f"Team stream error for {recipient}: {event.error_message}")
                            # Send error message to user
                            await self.message_queue_handler.send_message_with_delay(
                                recipient, "Sorry, I encountered an error processing your request. Please try again."
                            )
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in stream_team_to_whatsapp for {recipient}: {e}")
            # Try to send error message to user
            try:
                await self.message_queue_handler.send_message_with_delay(
                    recipient, "Sorry, I encountered a technical error. Please try again."
                )
            except:
                pass
            return False
            
        finally:
            # Clean up stream tracking
            self.current_streams.pop(stream_id, None)
    
    def get_active_streams(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about currently active streaming sessions.
        
        Returns:
            Dictionary of active streams with their metadata
        """
        return self.current_streams.copy()
    
    def stop_all_streams(self):
        """
        Emergency stop for all active streaming sessions.
        Used for cleanup during shutdown or error recovery.
        """
        logger.warning("Stopping all active streaming sessions")
        self.current_streams.clear()


# Global instance for easy access (will be initialized when needed)
_streaming_instances: Dict[str, AutomagikHiveStreamer] = {}


def get_streaming_instance(instance_config: InstanceConfig) -> AutomagikHiveStreamer:
    """
    Get or create an AutomagikHive streaming instance for the given configuration.
    
    Args:
        instance_config: Instance configuration
        
    Returns:
        AutomagikHiveStreamer instance
    """
    instance_key = f"{instance_config.name}_{instance_config.id}"
    
    if instance_key not in _streaming_instances:
        _streaming_instances[instance_key] = AutomagikHiveStreamer(instance_config)
    
    return _streaming_instances[instance_key]


def cleanup_streaming_instances():
    """
    Clean up all streaming instances.
    Should be called during application shutdown.
    """
    global _streaming_instances
    
    for instance in _streaming_instances.values():
        try:
            instance.stop_all_streams()
        except Exception as e:
            logger.error(f"Error stopping streaming instance: {e}")
    
    _streaming_instances.clear()
    logger.info("All streaming instances cleaned up")