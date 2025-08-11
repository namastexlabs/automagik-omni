"""
WhatsApp Streaming Handler Integration

This module provides streaming support for WhatsApp message handlers.
It integrates with the existing handler architecture to add AutomagikHive 
streaming capabilities while maintaining backward compatibility.
"""
import asyncio
import logging
import threading
from typing import Dict, Any, Optional
from src.services.message_router import message_router
from src.db.models import InstanceConfig

logger = logging.getLogger(__name__)


class WhatsAppStreamingHandler:
    """
    Enhanced WhatsApp handler with streaming integration.
    
    This handler extends the existing message processing to support 
    AutomagikHive streaming for real-time message delivery.
    """
    
    def __init__(self):
        """Initialize the streaming handler."""
        self.loop = None
        self.loop_thread = None
        self.is_running = False
        logger.info("WhatsApp streaming handler initialized")
    
    def start_event_loop(self):
        """Start the async event loop in a separate thread."""
        if self.loop_thread and self.loop_thread.is_alive():
            return  # Already running
        
        self.is_running = True
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()
        
        # Wait for loop to be ready
        while self.loop is None:
            threading.Event().wait(0.01)
        
        logger.info("Async event loop started for streaming")
    
    def _run_event_loop(self):
        """Run the async event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def stop_event_loop(self):
        """Stop the async event loop."""
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.is_running = False
        if self.loop_thread:
            self.loop_thread.join(timeout=1.0)
        logger.info("Async event loop stopped")
    
    def handle_message_with_streaming(
        self,
        message: Dict[str, Any],
        instance_config: Optional[InstanceConfig] = None,
        trace_context=None,
        original_handler=None
    ):
        """
        Handle a WhatsApp message with streaming support.
        
        Args:
            message: WhatsApp message data
            instance_config: Instance configuration for routing decisions
            trace_context: Trace context for logging
            original_handler: Fallback to original handler if needed
        """
        if not instance_config:
            logger.warning("No instance config provided, falling back to original handler")
            if original_handler:
                return original_handler(message, instance_config, trace_context)
            return
        
        # Extract recipient information
        recipient = self._extract_recipient(message)
        if not recipient:
            logger.error("Could not extract recipient from message")
            return
        
        # Check if streaming should be used
        logger.debug(f"Checking streaming for recipient {recipient}")
        logger.debug(f"Instance config type: {type(instance_config)}")
        logger.debug(f"Instance config name: {getattr(instance_config, 'name', 'N/A')}")
        logger.debug(f"Instance agent_instance_type: {getattr(instance_config, 'agent_instance_type', 'N/A')}")
        logger.debug(f"Instance agent_stream_mode: {getattr(instance_config, 'agent_stream_mode', 'N/A')}")
        logger.debug(f"Instance agent_id: {getattr(instance_config, 'agent_id', 'N/A')}")
        
        should_stream = message_router.should_use_streaming(instance_config)
        logger.debug(f"should_use_streaming returned: {should_stream}")
        
        if should_stream:
            logger.info(f"Using AutomagikHive streaming for {recipient}")
            self._handle_streaming_message(message, recipient, instance_config, trace_context)
        else:
            logger.info(f"Using traditional handler for {recipient}")
            if original_handler:
                original_handler(message, instance_config, trace_context)
    
    def _extract_recipient(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Extract the recipient (sender) ID from a WhatsApp message.
        
        Args:
            message: WhatsApp message data
            
        Returns:
            Recipient ID or None if not found
        """
        try:
            # Try different possible structures for recipient/sender
            if 'data' in message and 'key' in message['data']:
                key_data = message['data']['key']
                if 'remoteJid' in key_data:
                    return key_data['remoteJid']
            
            # Alternative structure
            if 'key' in message and 'remoteJid' in message['key']:
                return message['key']['remoteJid']
            
            # Another common structure
            if 'from' in message:
                return message['from']
            
            logger.warning(f"Could not extract recipient from message structure: {list(message.keys())}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting recipient: {e}")
            return None
    
    def _handle_streaming_message(
        self,
        message: Dict[str, Any],
        recipient: str,
        instance_config: InstanceConfig,
        trace_context=None
    ):
        """
        Handle a message using AutomagikHive streaming.
        
        Args:
            message: WhatsApp message data
            recipient: WhatsApp recipient ID
            instance_config: Instance configuration
            trace_context: Trace context for logging
        """
        # Ensure event loop is running
        if not self.loop or not self.is_running:
            self.start_event_loop()
        
        # Schedule the async streaming in the event loop
        future = asyncio.run_coroutine_threadsafe(
            self._async_stream_message(message, recipient, instance_config, trace_context),
            self.loop
        )
        
        # Don't block on the result - streaming happens asynchronously
        logger.debug(f"Scheduled streaming message processing for {recipient}")
    
    async def _async_stream_message(
        self,
        message: Dict[str, Any],
        recipient: str,
        instance_config: InstanceConfig,
        trace_context=None
    ):
        """
        Async method to handle streaming message processing.
        
        Args:
            message: WhatsApp message data
            recipient: WhatsApp recipient ID
            instance_config: Instance configuration
            trace_context: Trace context for logging
        """
        try:
            # Extract message content and metadata
            message_text = self._extract_message_text(message)
            if not message_text:
                logger.warning(f"No text content found in message from {recipient}")
                return
            
            # Extract user information for routing
            user_id = self._extract_user_id(message, instance_config)
            session_name = self._generate_session_name(message, recipient)
            
            logger.info(f"Processing streaming message from {recipient}: {message_text[:50]}...")
            
            # Route to streaming with smart routing
            success = await message_router.route_message_smart(
                message_text=message_text,
                recipient=recipient,
                instance_config=instance_config,
                user_id=user_id,
                session_name=session_name,
                message_type="text",
                whatsapp_raw_payload=message,
                session_origin="whatsapp",
                trace_context=trace_context
            )
            
            if success is True:
                logger.info(f"AutomagikHive streaming completed successfully for {recipient}")
            elif success is False:
                logger.warning(f"AutomagikHive streaming failed for {recipient}")
            else:
                # Traditional API response - this shouldn't happen in streaming path
                logger.warning(f"Unexpected response type from smart routing: {type(success)}")
                
        except Exception as e:
            logger.error(f"Error in async streaming message processing for {recipient}: {e}", exc_info=True)
    
    def _extract_message_text(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Extract text content from WhatsApp message.
        
        Args:
            message: WhatsApp message data
            
        Returns:
            Message text or None if not found
        """
        try:
            # Try different message structures
            if 'data' in message and 'message' in message['data']:
                msg_data = message['data']['message']
                
                # Text message
                if 'conversation' in msg_data:
                    return msg_data['conversation']
                
                # Extended text message
                if 'extendedTextMessage' in msg_data and 'text' in msg_data['extendedTextMessage']:
                    return msg_data['extendedTextMessage']['text']
            
            # Alternative structure
            if 'message' in message:
                msg_data = message['message']
                if 'conversation' in msg_data:
                    return msg_data['conversation']
                if 'extendedTextMessage' in msg_data and 'text' in msg_data['extendedTextMessage']:
                    return msg_data['extendedTextMessage']['text']
            
            logger.debug(f"No text content found in message structure")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting message text: {e}")
            return None
    
    def _extract_user_id(self, message: Dict[str, Any], instance_config: InstanceConfig) -> Optional[str]:
        """
        Extract or generate user ID for routing.
        
        Args:
            message: WhatsApp message data
            instance_config: Instance configuration
            
        Returns:
            User ID or None if not available
        """
        # For now, return None to let the routing system handle user creation
        # This can be enhanced later based on specific user identification needs
        return None
    
    def _generate_session_name(self, message: Dict[str, Any], recipient: str) -> str:
        """
        Generate a session name for the conversation.
        
        Args:
            message: WhatsApp message data
            recipient: Recipient ID
            
        Returns:
            Session name
        """
        # Clean up recipient for display
        clean_recipient = recipient.split("@")[0] if "@" in recipient else recipient
        return f"whatsapp_{clean_recipient}"


# Global streaming handler instance
streaming_handler = WhatsAppStreamingHandler()


def integrate_streaming_with_handler(original_process_message_func):
    """
    Decorator to integrate streaming capabilities with existing message handler.
    
    Args:
        original_process_message_func: Original _process_message function
        
    Returns:
        Enhanced function with streaming support
    """
    def enhanced_process_message(self, message: Dict[str, Any], instance_config=None, trace_context=None):
        """Enhanced process message with streaming support."""
        
        # Check if we should use streaming
        logger.debug(f"[DECORATOR] Checking streaming, instance_config type: {type(instance_config)}")
        logger.debug(f"[DECORATOR] Instance name: {getattr(instance_config, 'name', 'N/A') if instance_config else 'None'}")
        
        if instance_config and message_router.should_use_streaming(instance_config):
            logger.debug(f"[DECORATOR] Streaming check PASSED, calling streaming handler")
            # Use streaming handler
            streaming_handler.handle_message_with_streaming(
                message=message,
                instance_config=instance_config,
                trace_context=trace_context,
                original_handler=lambda m, ic, tc: original_process_message_func(self, m, ic, tc)
            )
        else:
            logger.debug(f"[DECORATOR] Streaming check FAILED, using original handler")
            # Use original handler
            original_process_message_func(self, message, instance_config, trace_context)
    
    return enhanced_process_message


def setup_streaming_integration():
    """
    Set up streaming integration with WhatsApp handlers.
    This function should be called during application startup.
    """
    # Start the async event loop for streaming
    streaming_handler.start_event_loop()
    logger.info("WhatsApp streaming integration setup completed")


def cleanup_streaming_integration():
    """
    Clean up streaming integration resources.
    This function should be called during application shutdown.
    """
    streaming_handler.stop_event_loop()
    
    # Clean up streaming instances
    try:
        from src.channels.whatsapp.streaming_integration import cleanup_streaming_instances
        cleanup_streaming_instances()
    except ImportError:
        pass
    
    logger.info("WhatsApp streaming integration cleanup completed")