#!/usr/bin/env python3
"""
Discord Service Manager - Manages ALL Discord bot instances in a single process.

This service automatically discovers and starts all Discord bot instances from the database.
It runs as a single PM2 process that handles multiple Discord bots efficiently.

Supports Discord feature toggles via environment variables:
- DISCORD_ENABLED=true/false (default: true)
- DISCORD_VOICE_ENABLED=true/false (default: true)
- DISCORD_MAX_INSTANCES=10 (default: 10)
"""

import os
import sys
import logging
import signal
import time
import threading
from pathlib import Path
from typing import Set

# Add src to path
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

from src.db.database import SessionLocal
from src.db.models import InstanceConfig
from src.services.discord_service import discord_service

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DiscordFeatureConfig:
    """Discord feature toggle configuration."""

    def __init__(self):
        self.enabled = os.getenv("DISCORD_ENABLED", "true").lower() == "true"
        self.voice_enabled = os.getenv("DISCORD_VOICE_ENABLED", "true").lower() == "true"
        self.max_instances = int(os.getenv("DISCORD_MAX_INSTANCES", "10"))

    def log_config(self):
        """Log the current configuration."""
        logger.info("Discord Feature Configuration:")
        logger.info(f"  - Discord Enabled: {self.enabled}")
        logger.info(f"  - Voice Enabled: {self.voice_enabled}")
        logger.info(f"  - Max Instances: {self.max_instances}")


class DiscordServiceManager:
    """Manages all Discord bot instances in a single service."""

    def __init__(self):
        self.running = False
        self.active_bots: Set[str] = set()
        self.check_interval = 30  # Check for new bots every 30 seconds
        self.feature_config = DiscordFeatureConfig()
        self.shutdown_event = threading.Event()

    def get_discord_instances(self):
        """Get all active Discord instances from database."""
        if not self.feature_config.enabled:
            logger.info("Discord functionality is disabled via DISCORD_ENABLED=false")
            return []

        db = SessionLocal()
        try:
            instances = (
                db.query(InstanceConfig)
                .filter(
                    InstanceConfig.channel_type == "discord",
                    InstanceConfig.is_active,
                    InstanceConfig.discord_bot_token.isnot(None),
                )
                .limit(self.feature_config.max_instances)
                .all()
            )

            result = [(inst.name, inst.discord_bot_token, inst.discord_voice_enabled) for inst in instances]

            # Apply voice filtering if voice is globally disabled
            if not self.feature_config.voice_enabled:
                logger.info("Discord voice functionality is disabled via DISCORD_VOICE_ENABLED=false")

            return result
        finally:
            db.close()

    def start_missing_bots(self):
        """Start any Discord bots that aren't currently running."""
        if not self.feature_config.enabled:
            if self.active_bots:
                logger.info("Discord is disabled, stopping all active bots")
                for bot_name in list(self.active_bots):
                    discord_service.stop_bot(bot_name)
                    self.active_bots.remove(bot_name)
            return

        try:
            discord_instances = self.get_discord_instances()

            if len(discord_instances) > self.feature_config.max_instances:
                logger.warning(
                    f"Found {len(discord_instances)} Discord instances, but max allowed is {self.feature_config.max_instances}"
                )
                discord_instances = discord_instances[: self.feature_config.max_instances]

            for instance_name, token, voice_enabled in discord_instances:
                if instance_name not in self.active_bots:
                    # Check voice configuration
                    if voice_enabled and not self.feature_config.voice_enabled:
                        logger.warning(f"Discord bot {instance_name} has voice enabled but global voice is disabled")

                    logger.info(f"Starting Discord bot: {instance_name}")
                    if discord_service.start_bot(instance_name):
                        self.active_bots.add(instance_name)
                        logger.info(f"✅ Started Discord bot: {instance_name}")
                    else:
                        logger.error(f"❌ Failed to start Discord bot: {instance_name}")

            # Check for removed bots
            current_names = {name for name, _, _ in discord_instances}
            removed_bots = self.active_bots - current_names

            for bot_name in removed_bots:
                logger.info(f"Stopping removed Discord bot: {bot_name}")
                discord_service.stop_bot(bot_name)
                self.active_bots.remove(bot_name)

        except Exception as e:
            logger.error(f"Error managing Discord bots: {e}", exc_info=True)

    def run(self):
        """Main run loop for the Discord service manager."""
        logger.info("Discord Service Manager starting...")

        # Log feature configuration
        self.feature_config.log_config()

        # Check if Discord is disabled
        if not self.feature_config.enabled:
            logger.info("Discord functionality is disabled. Service manager will not start Discord bots.")
            logger.info("Set DISCORD_ENABLED=true to enable Discord functionality.")
            # Still run the loop to monitor for configuration changes
            try:
                while not self.shutdown_event.is_set():
                    # Use wait with timeout for better signal handling
                    if self.shutdown_event.wait(timeout=60):  # Check every minute for config changes
                        break
                    # Reload config to check for changes
                    new_config = DiscordFeatureConfig()
                    if new_config.enabled != self.feature_config.enabled:
                        logger.info("Discord configuration changed, restarting service manager...")
                        break
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
            return True

        # Wait for API to be ready
        logger.info("Waiting for API to be ready...")
        # Simple API health check
        import requests

        api_healthy = False
        api_port = int(os.getenv("AUTOMAGIK_OMNI_API_PORT", "8882"))
        api_url = f"http://localhost:{api_port}/health"
        logger.info(f"Checking API health at {api_url}")

        for _ in range(60):  # Try for 60 seconds
            if self.shutdown_event.is_set():
                logger.info("Shutdown requested during API health check")
                return False
            try:
                response = requests.get(api_url, timeout=2)
                if response.status_code == 200:
                    api_healthy = True
                    logger.info("API is healthy")
                    break
            except Exception:
                pass
            # Use wait instead of sleep for better signal handling
            if self.shutdown_event.wait(timeout=1):
                logger.info("Shutdown requested during API health check")
                return False

        if not api_healthy:
            logger.error("API health check failed after 60 seconds")
            return False

        # Start Discord service
        if not discord_service.start():
            logger.error("Failed to start Discord service")
            return False

        self.running = True
        logger.info("Discord Service Manager started successfully")

        try:
            while self.running:
                # Start any new bots
                self.start_missing_bots()

                # Use wait with timeout instead of sleep for better signal handling
                if self.shutdown_event.wait(timeout=self.check_interval):
                    break

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.shutdown()

    def shutdown(self):
        """Shutdown the service manager."""
        logger.info("Discord Service Manager shutting down...")
        self.running = False
        self.shutdown_event.set()  # Signal shutdown to break wait

        # Stop all bots
        for bot_name in list(self.active_bots):
            discord_service.stop_bot(bot_name)

        # Stop Discord service
        discord_service.stop()

        logger.info("Discord Service Manager stopped")


def main():
    """Main entry point."""
    manager = DiscordServiceManager()

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        manager.running = False
        manager.shutdown_event.set()  # Trigger immediate shutdown

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the manager
    manager.run()


if __name__ == "__main__":
    main()
