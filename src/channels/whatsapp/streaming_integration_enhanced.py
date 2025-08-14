"""
Enhanced WhatsApp Streaming Integration with Proper Trace Context

This module extends the base streaming integration to provide comprehensive
trace context support for streaming responses, capturing first token timing,
incremental content, and complete final output for accurate analytics.
"""
import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional, List, AsyncIterator
from contextlib import asynccontextmanager

from src.services.automagik_hive_client import AutomagikHiveClient, AutomagikHiveError
from src.services.automagik_hive_models import HiveEvent, HiveEventType, RunResponseContentEvent
from src.services.streaming_trace_context import StreamingTraceContext
from src.channels.whatsapp.evolution_api_sender import EvolutionApiSender, PresenceUpdater
from src.channels.whatsapp.streaming_integration import (
    WhatsAppMessageChunker,
    TypingIndicatorManager,
    MessageQueueHandler
)
from src.db.models import InstanceConfig

logger = logging.getLogger(__name__)


class EnhancedAutomagikHiveStreamer:
    """
    Enhanced streaming integration class with comprehensive trace context support.
    
    This class extends the base streaming functionality to:
    - Capture first token timing
    - Log incremental streaming events
    - Accumulate complete response content
    - Provide detailed streaming analytics
    """
    
    def __init__(self, instance_config: InstanceConfig):
        """
        Initialize the enhanced AutomagikHive streamer.
        
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
        logger.info(f"Enhanced AutomagikHive streamer initialized for instance: {instance_config.name}")
    
    async def stream_agent_to_whatsapp_with_traces(
        self,
        recipient: str,
        agent_id: str,
        message: str,
        trace_context: Optional[StreamingTraceContext] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Stream AutomagikHive agent responses to WhatsApp with comprehensive trace context.
        
        Args:
            recipient: WhatsApp recipient ID
            agent_id: AutomagikHive agent ID
            message: User message to send to agent
            trace_context: Streaming trace context for detailed logging
            user_id: Optional user ID for context
            
        Returns:
            True if streaming completed successfully, False otherwise
        """
        stream_id = f"{recipient}_{agent_id}_{time.time()}"
        
        # Prepare hive request payload for tracing
        hive_request = {
            "message": message,
            "user_id": user_id,
            "session_id": f"whatsapp_{recipient.split('@')[0]}",
            "agent_id": agent_id,
            "streaming": True,
            "recipient": recipient
        }
        
        # Log the request if trace context is available
        if trace_context:
            trace_context.log_agent_request(hive_request)
            trace_context.log_streaming_start({
                "agent_id": agent_id,
                "recipient": recipient,
                "message_preview": message[:100]
            })
        
        try:
            # Start typing indicator
            typing_manager = TypingIndicatorManager(self.evolution_sender, recipient)
            
            with typing_manager:
                # Track this stream
                self.current_streams[stream_id] = {
                    'recipient': recipient,
                    'agent_id': agent_id,
                    'start_time': time.time(),
                    'trace_context': trace_context
                }
                
                accumulated_content = ""
                complete_response_content = ""
                message_count = 0
                chunk_index = 0
                first_token_logged = False
                
                logger.info(f"Starting enhanced agent streaming for {recipient}, agent: {agent_id}")
                
                # Stream from AutomagikHive
                async with self.hive_client.stream_agent_conversation(agent_id, message) as stream:
                    async for event in stream:
                        try:
                            if event.event == HiveEventType.RUN_RESPONSE_CONTENT:
                                chunk_content = getattr(event, 'content', '')
                                
                                # Log first token if not already logged
                                if not first_token_logged and chunk_content.strip():
                                    if trace_context:
                                        trace_context.log_first_token(
                                            chunk_content,
                                            {"event_type": event.event, "chunk_size": len(chunk_content)}
                                        )
                                    first_token_logged = True
                                
                                # Accumulate complete content for final trace
                                complete_response_content += chunk_content
                                
                                # Log streaming chunk
                                if trace_context:
                                    trace_context.log_streaming_chunk(
                                        chunk_content, 
                                        chunk_index,
                                        {"event_type": event.event, "timestamp": time.time()}
                                    )
                                
                                chunk_index += 1
                                
                                # Process content chunk for WhatsApp delivery
                                accumulated_content, ready_chunks = self.message_chunker.process_stream_content(
                                    accumulated_content, chunk_content
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
                                
                                # Log streaming completion with full content
                                if trace_context:
                                    completion_data = {
                                        "event_type": event.event,
                                        "messages_sent": message_count,
                                        "whatsapp_chunks": message_count,
                                        "streaming_chunks": chunk_index
                                    }
                                    trace_context.log_streaming_complete(complete_response_content, completion_data)
                                
                                logger.info(f"Enhanced streaming completed for {recipient}: {message_count} messages, {chunk_index} chunks")
                                break
                            
                            elif event.event == HiveEventType.ERROR:
                                error_msg = getattr(event, 'error_message', str(event))
                                logger.error(f"Stream error for {recipient}: {error_msg}")
                                
                                # Log error in trace context
                                if trace_context:
                                    trace_context.log_streaming_error(
                                        Exception(error_msg), 
                                        "stream_event_error"
                                    )
                                
                                # Send error message to user
                                await self.message_queue_handler.send_message_with_delay(
                                    recipient, "Sorry, I encountered an error processing your request. Please try again."
                                )
                                return False
                            
                            else:
                                # Log other event types for debugging
                                logger.debug(f"Received event type: {event.event} for {recipient}")
                                
                        except Exception as event_error:
                            logger.error(f"Error processing streaming event for {recipient}: {event_error}")
                            if trace_context:
                                trace_context.log_streaming_error(event_error, "event_processing")
                            continue
            
            return True
            
        except Exception as e:
            logger.error(f"Error in enhanced stream_agent_to_whatsapp for {recipient}: {e}")
            
            # Log error in trace context
            if trace_context:
                trace_context.log_streaming_error(e, "streaming_general")
            
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
    
    async def stream_team_to_whatsapp_with_traces(
        self,
        recipient: str,
        team_id: str,
        message: str,
        trace_context: Optional[StreamingTraceContext] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Stream AutomagikHive team responses to WhatsApp with comprehensive trace context.
        
        Args:
            recipient: WhatsApp recipient ID
            team_id: AutomagikHive team ID
            message: User message to send to team
            trace_context: Streaming trace context for detailed logging
            user_id: Optional user ID for context
            
        Returns:
            True if streaming completed successfully, False otherwise
        """
        stream_id = f"{recipient}_{team_id}_{time.time()}"
        
        # Prepare hive request payload for tracing
        hive_request = {
            "message": message,
            "user_id": user_id,
            "session_id": f"whatsapp_{recipient.split('@')[0]}",
            "team_id": team_id,
            "streaming": True,
            "recipient": recipient
        }
        
        # Log the request if trace context is available
        if trace_context:
            trace_context.log_agent_request(hive_request)
            trace_context.log_streaming_start({
                "team_id": team_id,
                "recipient": recipient,
                "message_preview": message[:100]
            })
        
        try:
            # Start typing indicator
            typing_manager = TypingIndicatorManager(self.evolution_sender, recipient)
            
            with typing_manager:
                # Track this stream
                self.current_streams[stream_id] = {
                    'recipient': recipient,
                    'team_id': team_id,
                    'start_time': time.time(),
                    'trace_context': trace_context
                }
                
                accumulated_content = ""
                complete_response_content = ""
                message_count = 0
                chunk_index = 0
                first_token_logged = False
                
                logger.info(f"Starting enhanced team streaming for {recipient}, team: {team_id}")
                
                # Stream from AutomagikHive
                async with self.hive_client.stream_team_conversation(team_id, message) as stream:
                    async for event in stream:
                        try:
                            if event.event == HiveEventType.RUN_RESPONSE_CONTENT:
                                chunk_content = getattr(event, 'content', '')
                                
                                # Log first token if not already logged
                                if not first_token_logged and chunk_content.strip():
                                    if trace_context:
                                        trace_context.log_first_token(
                                            chunk_content,
                                            {"event_type": event.event, "chunk_size": len(chunk_content)}
                                        )
                                    first_token_logged = True
                                
                                # Accumulate complete content for final trace
                                complete_response_content += chunk_content
                                
                                # Log streaming chunk
                                if trace_context:
                                    trace_context.log_streaming_chunk(
                                        chunk_content, 
                                        chunk_index,
                                        {"event_type": event.event, "timestamp": time.time()}
                                    )
                                
                                chunk_index += 1
                                
                                # Process content chunk for WhatsApp delivery
                                accumulated_content, ready_chunks = self.message_chunker.process_stream_content(
                                    accumulated_content, chunk_content
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
                                
                                # Log streaming completion with full content
                                if trace_context:
                                    completion_data = {
                                        "event_type": event.event,
                                        "messages_sent": message_count,
                                        "whatsapp_chunks": message_count,
                                        "streaming_chunks": chunk_index
                                    }
                                    trace_context.log_streaming_complete(complete_response_content, completion_data)
                                
                                logger.info(f"Enhanced team streaming completed for {recipient}: {message_count} messages, {chunk_index} chunks")
                                break
                            
                            elif event.event == HiveEventType.ERROR:
                                error_msg = getattr(event, 'error_message', str(event))
                                logger.error(f"Team stream error for {recipient}: {error_msg}")
                                
                                # Log error in trace context
                                if trace_context:
                                    trace_context.log_streaming_error(
                                        Exception(error_msg), 
                                        "stream_event_error"
                                    )
                                
                                # Send error message to user
                                await self.message_queue_handler.send_message_with_delay(
                                    recipient, "Sorry, I encountered an error processing your request. Please try again."
                                )
                                return False
                            
                            else:
                                # Log other event types for debugging
                                logger.debug(f"Received event type: {event.event} for {recipient}")
                                
                        except Exception as event_error:
                            logger.error(f"Error processing team streaming event for {recipient}: {event_error}")
                            if trace_context:
                                trace_context.log_streaming_error(event_error, "event_processing")
                            continue
            
            return True
            
        except Exception as e:
            logger.error(f"Error in enhanced stream_team_to_whatsapp for {recipient}: {e}")
            
            # Log error in trace context
            if trace_context:
                trace_context.log_streaming_error(e, "streaming_general")
            
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
    
    def get_streaming_analytics(self) -> Dict[str, Any]:
        """
        Get analytics for completed streaming sessions.
        
        Returns:
            Analytics data for streaming performance analysis
        """
        analytics = {
            "active_streams": len(self.current_streams),
            "instance_name": self.instance_config.name,
            "streaming_enabled": True
        }
        
        # Add trace context summaries if available
        stream_summaries = []
        for stream_id, stream_data in self.current_streams.items():
            trace_context = stream_data.get('trace_context')
            if isinstance(trace_context, StreamingTraceContext):
                summary = trace_context.get_streaming_summary()
                summary['stream_id'] = stream_id
                summary['recipient'] = stream_data.get('recipient', 'unknown')
                stream_summaries.append(summary)
        
        analytics['stream_summaries'] = stream_summaries
        return analytics
    
    def stop_all_streams(self):
        """
        Emergency stop for all active streaming sessions.
        Used for cleanup during shutdown or error recovery.
        """
        logger.warning("Stopping all enhanced streaming sessions")
        
        # Log cleanup in trace contexts if available
        for stream_data in self.current_streams.values():
            trace_context = stream_data.get('trace_context')
            if isinstance(trace_context, StreamingTraceContext):
                trace_context.log_streaming_error(
                    Exception("Stream forcibly stopped"), 
                    "forced_cleanup"
                )
        
        self.current_streams.clear()


# Global instance for easy access (will be initialized when needed)
_enhanced_streaming_instances: Dict[str, EnhancedAutomagikHiveStreamer] = {}


def get_enhanced_streaming_instance(instance_config: InstanceConfig) -> EnhancedAutomagikHiveStreamer:
    """
    Get or create an enhanced AutomagikHive streaming instance for the given configuration.
    
    Args:
        instance_config: Instance configuration
        
    Returns:
        EnhancedAutomagikHiveStreamer instance
    """
    instance_key = f"{instance_config.name}_{instance_config.id}"
    
    if instance_key not in _enhanced_streaming_instances:
        _enhanced_streaming_instances[instance_key] = EnhancedAutomagikHiveStreamer(instance_config)
    
    return _enhanced_streaming_instances[instance_key]


def cleanup_enhanced_streaming_instances():
    """
    Clean up all enhanced streaming instances.
    Should be called during application shutdown.
    """
    global _enhanced_streaming_instances
    
    for instance in _enhanced_streaming_instances.values():
        try:
            instance.stop_all_streams()
        except Exception as e:
            logger.error(f"Error stopping enhanced streaming instance: {e}")
    
    _enhanced_streaming_instances.clear()
    logger.info("All enhanced streaming instances cleaned up")