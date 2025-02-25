"""
Main entry point for Stan application.
"""

import os
import sys
import signal
import logging
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading environment variables
from src.service import stan_service
from src.db.engine import init_db, create_tables
from src.config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, str(config.logging.level).upper()),
    format=config.logging.format,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("src.main")

def handle_shutdown(signal_number, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signal_number}, shutting down...")
    
    # Stop the Stan service
    stan_service.stop()
    
    logger.info("Shutdown complete")
    sys.exit(0)

def run():
    """Run the Stan application."""
    try:
        logger.info("Starting Stan application...")
        
        # Check if configuration is valid
        if not config.is_valid:
            logger.error("Invalid configuration. Please check your .env file.")
            sys.exit(1)
        
        # Initialize the database
        init_db()
        
        # Create database tables if they don't exist
        create_tables()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
        
        # Start the Stan service
        if not stan_service.start():
            logger.error("Failed to start Stan service")
            sys.exit(1)
        
        logger.info("Stan application started successfully")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Error running Stan application: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run() 