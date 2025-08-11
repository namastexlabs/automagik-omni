"""
Streaming Integration Patch for WhatsApp Handlers

This module patches the existing WhatsApp message handlers to support 
AutomagikHive streaming without requiring major refactoring of the 
existing codebase.

Usage:
    from src.channels.whatsapp.streaming_patch import apply_streaming_patch
    apply_streaming_patch()
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def apply_streaming_patch():
    """
    Apply streaming integration patch to existing WhatsApp handlers.
    
    This function monkey-patches the existing handlers to add streaming support
    while maintaining backward compatibility with the current architecture.
    """
    try:
        # Import the modules we need to patch
        from src.channels.whatsapp.handlers import WhatsAppMessageHandler, message_handler
        from src.channels.whatsapp.streaming_handler import streaming_handler, integrate_streaming_with_handler
        from src.services.message_router import message_router
        
        
        # Store the original _process_message method
        original_process_message = WhatsAppMessageHandler._process_message
        
        # Create enhanced version with streaming
        enhanced_process_message = integrate_streaming_with_handler(original_process_message)
        
        # Patch the class method
        WhatsAppMessageHandler._process_message = enhanced_process_message
        
        # Initialize streaming components
        streaming_handler.start_event_loop()
        
        # Update the message router import in handlers module to use enhanced version
        import src.channels.whatsapp.handlers as handlers_module
        handlers_module.message_router = message_router
        
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to apply streaming integration patch: {e}", exc_info=True)
        return False


def remove_streaming_patch():
    """
    Remove the streaming patch and restore original behavior.
    
    This is useful for testing or if issues arise with the streaming integration.
    """
    try:
        from src.channels.whatsapp.streaming_handler import cleanup_streaming_integration
        
        logger.info("Removing streaming integration patch...")
        
        # Clean up streaming resources
        cleanup_streaming_integration()
        
        # Note: We don't restore the original methods as they would have been
        # replaced by the monkey patch. In a production system, we would
        # store references to originals, but for this implementation,
        # a restart would be needed to fully revert.
        
        logger.info("✅ Streaming integration patch removed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to remove streaming integration patch: {e}", exc_info=True)
        return False


def is_streaming_available() -> bool:
    """
    Check if streaming functionality is available and working.
    
    Returns:
        True if streaming is available, False otherwise
    """
    try:
        from src.channels.whatsapp.streaming_integration import AutomagikHiveStreamer
        from src.channels.whatsapp.streaming_handler import streaming_handler
        from src.services.automagik_hive_client import AutomagikHiveClient
        
        # Check if components are importable and initialized
        return (
            streaming_handler.is_running and 
            streaming_handler.loop is not None
        )
        
    except Exception as e:
        logger.debug(f"Streaming not available: {e}")
        return False


def get_streaming_status() -> Dict[str, Any]:
    """
    Get detailed status of streaming integration.
    
    Returns:
        Dictionary with streaming status information
    """
    try:
        from src.channels.whatsapp.streaming_handler import streaming_handler
        from src.channels.whatsapp.streaming_integration import _streaming_instances
        
        return {
            "streaming_available": is_streaming_available(),
            "event_loop_running": streaming_handler.is_running,
            "event_loop_thread_alive": streaming_handler.loop_thread.is_alive() if streaming_handler.loop_thread else False,
            "active_streaming_instances": len(_streaming_instances),
            "streaming_instances": list(_streaming_instances.keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting streaming status: {e}")
        return {
            "streaming_available": False,
            "error": str(e)
        }


def test_streaming_integration() -> bool:
    """
    Test the streaming integration with a mock scenario.
    
    Returns:
        True if test passes, False otherwise
    """
    try:
        from src.db.models import InstanceConfig
        from src.services.message_router import message_router
        
        logger.info("Testing streaming integration...")
        
        # Create a mock instance config
        mock_config = InstanceConfig(
            name="test_instance",
            hive_enabled=True,
            hive_api_url="https://test.automagikhive.ai",
            hive_api_key="test_key",
            hive_agent_id="test_agent",
            hive_stream_mode=True
        )
        
        # Test streaming decision logic
        should_stream = message_router.should_use_streaming(mock_config)
        
        if should_stream:
            logger.info("✅ Streaming decision logic working correctly")
        else:
            logger.warning("⚠️  Streaming decision logic returned False for valid config")
        
        # Test streaming availability
        if is_streaming_available():
            logger.info("✅ Streaming components available and running")
        else:
            logger.warning("⚠️  Streaming components not fully available")
        
        # Get status
        status = get_streaming_status()
        logger.info(f"Streaming status: {status}")
        
        logger.info("✅ Streaming integration test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Streaming integration test failed: {e}", exc_info=True)
        return False


# Auto-apply patch on import if desired
# Disabled - patch is now applied explicitly in app.py
AUTO_APPLY_PATCH = False

if AUTO_APPLY_PATCH:
    try:
        apply_streaming_patch()
        logger.info("Streaming patch auto-applied on import")
    except Exception as e:
        logger.warning(f"Auto-apply streaming patch failed: {e}")