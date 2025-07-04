"""
Main entry point for Agent application.
"""

import sys
import signal
import logging

# Import configuration first to ensure environment variables are loaded
from src.config import config

# Import and set up logging
from src.logger import setup_logging

# Set up logging with defaults from config
setup_logging()

# Import other modules after logging is configured
from src.services.agent_service import agent_service
from src.services.agent_api_client import agent_api_client

# Import WhatsApp components initialization to set up HTTP webhook processing

# Import database initialization
from src.db.database import create_tables

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

        # Initialize database
        logger.info("Initializing database...")
        create_tables()

        logger.info("Database initialization complete")

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

        # Telemetry status logging
        from src.core.telemetry import telemetry_client
        if telemetry_client.is_enabled():
            logger.info("📊 Telemetry enabled - Anonymous usage analytics help improve Automagik Omni")
            logger.info("   • Collected: CLI usage, API performance, system info (no personal data)")
            logger.info("   • Disable: 'automagik-omni telemetry disable' or AUTOMAGIK_OMNI_DISABLE_TELEMETRY=true")
        else:
            logger.info("📊 Telemetry disabled")

        logger.info("Agent application started successfully")

        # Start the FastAPI server instead of keeping the main thread alive with a sleep loop
        from src.api.app import start_api

        start_api()

    except Exception as e:
        logger.error(f"Error running Agent application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
