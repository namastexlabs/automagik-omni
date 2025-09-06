"""
Discord service for managing Discord bot lifecycle.
This handles the coordination between Discord bots and the message routing system.
"""

import asyncio
import logging
import threading
from typing import Dict, Any, Optional, List

from src.db.database import SessionLocal
from src.db.models import InstanceConfig
from src.channels.discord.bot_manager import DiscordBotManager
from src.services.message_router import MessageRouter
from src.core.telemetry import track_command
from src.utils.health_check import wait_for_api_health
from src.utils.datetime_utils import utcnow
import os

logger = logging.getLogger("src.services.discord_service")


class DiscordService:
    """Service layer for Discord bot management."""

    def __init__(self):
        """Initialize the Discord service."""
        self.lock = threading.Lock()
        self.message_router = MessageRouter()
        self.bot_manager = DiscordBotManager(self.message_router)
        self._running_instances: Dict[str, Dict[str, Any]] = {}
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Start the Discord service."""
        logger.info("Starting Discord service")
        try:
            with self.lock:
                if self._loop_thread is None:
                    # Start event loop in separate thread
                    self._loop_thread = threading.Thread(
                        target=self._run_event_loop, daemon=True
                    )
                    self._loop_thread.start()

                    # Wait a moment for loop to initialize
                    import time

                    time.sleep(0.1)

            logger.info("Discord service started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting Discord service: {e}", exc_info=True)
            return False

    def stop(self) -> None:
        """Stop the Discord service."""
        logger.info("Stopping Discord service")
        try:
            with self.lock:
                if self._event_loop:
                    # Stop all running bots
                    for instance_name in list(self._running_instances.keys()):
                        asyncio.run_coroutine_threadsafe(
                            self._stop_bot_internal(instance_name), self._event_loop
                        ).result(timeout=5.0)

                    # Stop event loop
                    self._event_loop.call_soon_threadsafe(self._event_loop.stop)

                if self._loop_thread:
                    self._loop_thread.join(timeout=5.0)
                    self._loop_thread = None

                self._event_loop = None
                self._running_instances.clear()

        except Exception as e:
            logger.error(f"Error stopping Discord service: {e}", exc_info=True)

    def _run_event_loop(self):
        """Run the event loop in a separate thread."""
        try:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            self._event_loop.run_forever()
        except Exception as e:
            logger.error(f"Error in Discord service event loop: {e}", exc_info=True)
        finally:
            if self._event_loop:
                self._event_loop.close()
                self._event_loop = None

    def start_bot(self, instance_name: str) -> bool:
        """Start a Discord bot for the given instance."""
        logger.info(f"Starting Discord bot for instance: {instance_name}")

        # Wait for API to be healthy before proceeding
        api_host = os.getenv("AUTOMAGIK_OMNI_API_HOST", "localhost")
        api_port = int(os.getenv("AUTOMAGIK_OMNI_API_PORT", "8882"))
        health_timeout = int(os.getenv("DISCORD_HEALTH_CHECK_TIMEOUT", "60"))

        logger.info("🏥 Checking API health before starting Discord bot...")

        api_url = f"http://{api_host}:{api_port}"

        # Run health check in async context
        try:
            is_healthy = asyncio.run(wait_for_api_health(api_url, health_timeout))
            if not is_healthy:
                logger.error("❌ API is not healthy - cannot start Discord bot")
                logger.error("🚨 Make sure the API server is running and healthy")
                return False
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False

        logger.info("✅ API is healthy - proceeding with Discord bot startup")

        try:
            # Get instance configuration from database
            db = SessionLocal()
            try:
                instance = (
                    db.query(InstanceConfig)
                    .filter_by(name=instance_name, channel_type="discord")
                    .first()
                )

                if not instance:
                    logger.error(
                        f"Discord instance '{instance_name}' not found in database"
                    )
                    return False

                if not instance.discord_bot_token:
                    logger.error(
                        f"Discord instance '{instance_name}' has no bot token configured"
                    )
                    return False

                # Check if already running
                with self.lock:
                    if instance_name in self._running_instances:
                        logger.warning(
                            f"Discord bot '{instance_name}' is already running"
                        )
                        return False

                    # Start bot in event loop
                    if not self._event_loop:
                        logger.error(
                            "Discord service not started - no event loop available"
                        )
                        return False

                    future = asyncio.run_coroutine_threadsafe(
                        self._start_bot_internal(instance), self._event_loop
                    )

                    success = future.result(timeout=10.0)

                    if success:
                        self._running_instances[instance_name] = {
                            "instance_config": instance,
                            "started_at": utcnow(),  # ✅ FIXED: Using timezone-aware utility
                            "status": "running",
                        }
                        track_command(
                            "discord_start", success=True, instance_name=instance_name
                        )
                        logger.info(
                            f"✅ Discord bot '{instance_name}' started successfully"
                        )
                    else:
                        track_command(
                            "discord_start", success=False, instance_name=instance_name
                        )
                        logger.error(
                            f"❌ Failed to start Discord bot '{instance_name}'"
                        )

                    return success

            finally:
                db.close()

        except Exception as e:
            logger.error(
                f"Error starting Discord bot '{instance_name}': {e}", exc_info=True
            )
            track_command(
                "discord_start",
                success=False,
                instance_name=instance_name,
                error=str(e),
            )
            return False

    async def _start_bot_internal(self, instance_config: InstanceConfig) -> bool:
        """Internal method to start bot in event loop."""
        return await self.bot_manager.start_bot(instance_config)

    def stop_bot(self, instance_name: str) -> bool:
        """Stop a Discord bot for the given instance."""
        logger.info(f"Stopping Discord bot for instance: {instance_name}")

        try:
            with self.lock:
                if instance_name not in self._running_instances:
                    logger.warning(f"Discord bot '{instance_name}' is not running")
                    return False

                if not self._event_loop:
                    logger.error(
                        "Discord service not started - no event loop available"
                    )
                    return False

                future = asyncio.run_coroutine_threadsafe(
                    self._stop_bot_internal(instance_name), self._event_loop
                )

                success = future.result(timeout=10.0)

                if success:
                    del self._running_instances[instance_name]
                    track_command(
                        "discord_stop", success=True, instance_name=instance_name
                    )
                    logger.info(
                        f"✅ Discord bot '{instance_name}' stopped successfully"
                    )
                else:
                    track_command(
                        "discord_stop", success=False, instance_name=instance_name
                    )
                    logger.error(f"❌ Failed to stop Discord bot '{instance_name}'")

                return success

        except Exception as e:
            logger.error(
                f"Error stopping Discord bot '{instance_name}': {e}", exc_info=True
            )
            track_command(
                "discord_stop", success=False, instance_name=instance_name, error=str(e)
            )
            return False

    async def _stop_bot_internal(self, instance_name: str) -> bool:
        """Internal method to stop bot in event loop."""
        return await self.bot_manager.stop_bot(instance_name)

    def restart_bot(self, instance_name: str) -> bool:
        """Restart a Discord bot for the given instance."""
        logger.info(f"Restarting Discord bot for instance: {instance_name}")

        # Stop the bot first
        if instance_name in self._running_instances:
            if not self.stop_bot(instance_name):
                logger.error(
                    f"Failed to stop Discord bot '{instance_name}' for restart"
                )
                return False

        # Start the bot again
        return self.start_bot(instance_name)

    def get_bot_status(self, instance_name: str) -> Optional[Dict[str, Any]]:
        """Get status information for a Discord bot."""
        try:
            with self.lock:
                if instance_name not in self._running_instances:
                    return None

                if not self._event_loop:
                    return None

                future = asyncio.run_coroutine_threadsafe(
                    self._get_bot_status_internal(instance_name), self._event_loop
                )

                return future.result(timeout=5.0)

        except Exception as e:
            logger.error(
                f"Error getting status for Discord bot '{instance_name}': {e}",
                exc_info=True,
            )
            return None

    async def _get_bot_status_internal(
        self, instance_name: str
    ) -> Optional[Dict[str, Any]]:
        """Internal method to get bot status in event loop."""
        try:
            bot_status = self.bot_manager.get_bot_status(instance_name)
            if not bot_status:
                return None

            instance_info = self._running_instances.get(instance_name, {})

            return {
                "instance_name": bot_status.instance_name,
                "status": bot_status.status,
                "guild_count": bot_status.guild_count,
                "user_count": bot_status.user_count,
                "latency": bot_status.latency,
                "last_heartbeat": bot_status.last_heartbeat,
                "uptime": bot_status.uptime,
                "error_message": bot_status.error_message,
                "started_at": instance_info.get(
                    "started_at"
                ),  # ✅ Uses timezone-aware timestamp
                "service_status": instance_info.get("status", "unknown"),
            }
        except Exception as e:
            logger.error(f"Error getting bot status: {e}", exc_info=True)
            return None

    def list_running_bots(self) -> List[str]:
        """List all currently running Discord bot instances."""
        with self.lock:
            return list(self._running_instances.keys())

    def list_available_instances(self) -> List[Dict[str, Any]]:
        """List all available Discord instances from the database."""
        try:
            db = SessionLocal()
            try:
                instances = (
                    db.query(InstanceConfig).filter_by(channel_type="discord").all()
                )

                result = []
                for instance in instances:
                    result.append(
                        {
                            "name": instance.name,
                            "discord_client_id": instance.discord_client_id,
                            "has_token": bool(instance.discord_bot_token),
                            "is_running": instance.name in self._running_instances,
                            "agent_api_url": instance.agent_api_url,
                            "default_agent": instance.default_agent,
                        }
                    )

                return result

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error listing Discord instances: {e}", exc_info=True)
            return []

    def get_service_status(self) -> Dict[str, Any]:
        """Get overall Discord service status."""
        with self.lock:
            return {
                "service_running": self._event_loop is not None,
                "loop_thread_alive": self._loop_thread is not None
                and self._loop_thread.is_alive(),
                "running_bots": len(self._running_instances),
                "bot_instances": list(self._running_instances.keys()),
            }


# Global Discord service instance
discord_service = DiscordService()
