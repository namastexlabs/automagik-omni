"""
Main entry point for Agent application.
"""

import os
import sys
import signal
import logging
import time

# Import configuration first to ensure environment variables are loaded
from src.config import config

# Import and set up logging
from src.logger import setup_logging

# Set up logging with defaults from config
setup_logging()

# Import other modules after logging is configured
from src.services.agent_service import agent_service
from src.services.agent_api_client import agent_api_client
from src.services.automagik_api_client import automagik_api_client

# Import WhatsApp components initialization to set up HTTP webhook processing
from src.channels.whatsapp import init as whatsapp_init

# Removed: Import WhatsApp components initialization
# from src.channels.whatsapp import init as whatsapp_init

# Get a logger for this module
logger = logging.getLogger("src.cli.main")

def handle_shutdown(signal_number, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signal_number}, shutting down...")
    
    # Stop the Agent service
    agent_service.stop()
    
    logger.info("Shutdown complete")
    sys.exit(0)

def check_api_availability() -> bool:
    """Check if required APIs are available."""
    api_healthy = agent_api_client.health_check()
    
    if api_healthy:
        logger.info("Agent API is available")
    else:
        logger.error("Agent API is not available. Service may not function correctly.")
    
    return api_healthy

def run():
    """Run the Agent application."""
    try:
        logger.info("Starting Agent application...")
        
        # Check if configuration is valid
        if not config.is_valid:
            logger.error("Invalid configuration. Please check your .env file.")
            sys.exit(1)
        
        # Check API availability (warn but continue if not available)
        check_api_availability()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
        
        # Start the Agent service
        if not agent_service.start():
            logger.error("Failed to start Agent service")
            sys.exit(1)
        
        logger.info("Agent application started successfully")
        
        # Start the FastAPI server instead of keeping the main thread alive with a sleep loop
        from src.api.app import start_api
        start_api()
        
    except Exception as e:
        logger.error(f"Error running Agent application: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run() 