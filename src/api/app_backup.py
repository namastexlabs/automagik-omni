"""
FastAPI application for receiving Evolution API webhooks.
"""

# Import telemetry
# Import configuration first to ensure environment variables are loaded
# Import and set up logging
from src.logger import setup_logging

# Set up logging with defaults from config
setup_logging()
