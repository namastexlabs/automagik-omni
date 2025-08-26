#!/usr/bin/env python3
"""
Wait script for PM2 to ensure API is healthy before starting Discord bot.
This script will be used in PM2 configuration to enforce startup order.
"""
import sys
import os
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from src.utils.health_check import wait_for_api_health
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for PM2 wait script."""
    logger.info("🚀 PM2 Wait Script: Ensuring API is healthy before Discord startup")
    
    # Get configuration from environment
    api_host = os.getenv("AUTOMAGIK_OMNI_API_HOST", "localhost")
    api_port = int(os.getenv("AUTOMAGIK_OMNI_API_PORT", "8882"))
    timeout = int(os.getenv("DISCORD_HEALTH_CHECK_TIMEOUT", "120"))
    
    logger.info(f"📡 Waiting for API at {api_host}:{api_port}")
    logger.info(f"⏰ Timeout: {timeout} seconds")
    
    # Wait for API to become healthy
    if wait_for_api_health(api_host, api_port, timeout):
        logger.info("✅ API is healthy - Discord bot can now start!")
        sys.exit(0)
    else:
        logger.error("❌ API health check failed - Discord bot cannot start")
        logger.error("🚨 Check API logs: pm2 logs automagik-omni")
        sys.exit(1)

if __name__ == "__main__":
    main()