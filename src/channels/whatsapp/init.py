"""
Initialization module for WhatsApp components.
Connects the message handler to the Evolution API sender.
"""

import logging
from src.channels.whatsapp.handlers import message_handler
from src.channels.whatsapp.evolution_api_sender import evolution_api_sender

# Configure logging
logger = logging.getLogger("src.channels.whatsapp.init")


def initialize_whatsapp_components():
    """
    Initialize WhatsApp components and connect them together.
    Sets up the message handler's send_response_callback to use the Evolution API sender.

    Note: RabbitMQ processing is DISABLED. Only HTTP webhook processing is active.
    """
    # Set the send_response_callback on the message handler to use the Evolution API sender
    message_handler.send_response_callback = evolution_api_sender.send_text_message

    logger.info(
        "WhatsApp message handler connected to Evolution API sender (HTTP webhooks only)"
    )

    # Make sure the message handler is started
    if not message_handler.is_running:
        message_handler.start()
        logger.info("WhatsApp message handler started")

    logger.info("🚫 RabbitMQ processing DISABLED - using HTTP webhooks only")


# Initialize components when this module is imported
initialize_whatsapp_components()
