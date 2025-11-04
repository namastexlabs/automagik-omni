"""
Discord Bot Manager - Bot lifecycle management and integration with automagik-omni.

This module provides comprehensive Discord bot management including connection handling,
event management, message routing, and health monitoring.
"""

import asyncio
import logging
import random
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import json
import os
from aiohttp import web

from sqlalchemy.exc import DatabaseError

import discord
from discord.ext import commands

from src.services.message_router import MessageRouter
from ...core.exceptions import AutomagikError
from src.db.models import InstanceConfig
from src.channels.message_utils import extract_response_text, split_message_for_discord
from .voice_manager import DiscordVoiceManager
from ...utils.rate_limiter import RateLimiter
from ...utils.health_monitor import HealthMonitor
from src import __version__

logger = logging.getLogger(__name__)


@dataclass
class BotStatus:
    """Bot status information."""

    instance_name: str
    status: str  # 'starting', 'connected', 'disconnected', 'error'
    guild_count: int
    user_count: int
    latency: float
    last_heartbeat: datetime
    uptime: Optional[datetime]
    error_message: Optional[str] = None


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for bot connection failures."""

    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    is_open: bool = False
    next_retry_time: Optional[datetime] = None
    consecutive_failures: int = 0

    # Circuit breaker thresholds
    failure_threshold: int = 3  # Open circuit after 3 consecutive failures
    recovery_timeout: int = 300  # 5 minutes before attempting recovery
    half_open_max_attempts: int = 2  # Max attempts in half-open state


class AutomagikBot(commands.Bot):
    """Custom Discord bot class with automagik integration."""

    def __init__(self, instance_name: str, manager: "DiscordBotManager", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance_name = instance_name
        self.manager = manager
        self.start_time = None
        self.last_heartbeat = datetime.now(timezone.utc)
        self._heartbeat_task = None

    async def on_ready(self):
        """Called when bot is ready."""
        self.start_time = datetime.now(timezone.utc)
        self.last_heartbeat = datetime.now(timezone.utc)

        logger.info(f"Discord bot '{self.instance_name}' is ready!")
        logger.info(f"Bot user: {self.user}")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Update health monitor heartbeat
        health_monitor = self.manager.health_monitors.get(self.instance_name)
        if health_monitor:
            health_monitor.heartbeat()

        await self.manager._handle_bot_ready(self)

    async def on_message(self, message):
        """Handle incoming messages."""
        self.last_heartbeat = datetime.now(timezone.utc)

        # Update health monitor heartbeat
        health_monitor = self.manager.health_monitors.get(self.instance_name)
        if health_monitor:
            health_monitor.heartbeat()

        # Ignore messages from bots (including self)
        if message.author.bot:
            return

        await self.manager._handle_incoming_message(self.instance_name, message)

        # Process commands
        await self.process_commands(message)

    async def on_disconnect(self):
        """Handle disconnection."""
        logger.warning(f"Discord bot '{self.instance_name}' disconnected")
        await self.manager._handle_bot_disconnect(self.instance_name)

    async def on_guild_join(self, guild):
        """Handle joining a new guild."""
        logger.info(f"Bot '{self.instance_name}' joined guild: {guild.name} (ID: {guild.id})")
        await self.manager._handle_guild_join(self.instance_name, guild)

    async def on_guild_remove(self, guild):
        """Handle leaving a guild."""
        logger.info(f"Bot '{self.instance_name}' left guild: {guild.name} (ID: {guild.id})")
        await self.manager._handle_guild_remove(self.instance_name, guild)

    async def on_interaction(self, interaction):
        """Handle slash command interactions."""
        await self.manager._handle_interaction(self.instance_name, interaction)

    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates."""
        await self.manager.voice_manager.on_voice_state_update(member, before, after)

    async def on_error(self, event, *args, **kwargs):
        """Handle errors."""
        logger.error(
            f"Discord error in bot '{self.instance_name}' for event '{event}'",
            exc_info=True,
        )
        await self.manager._handle_bot_error(self.instance_name, event, args, kwargs)

    async def _periodic_heartbeat(self):
        """Send periodic heartbeats to health monitor to prevent false degradation."""
        try:
            while not self.is_closed():
                await asyncio.sleep(30)  # Heartbeat every 30 seconds

                health_monitor = self.manager.health_monitors.get(self.instance_name)
                if health_monitor:
                    health_monitor.heartbeat()

        except asyncio.CancelledError:
            logger.info(f"Periodic heartbeat stopped for {self.instance_name}")
        except Exception as e:
            logger.error(f"Error in periodic heartbeat for {self.instance_name}: {e}")

    async def setup_hook(self):
        """Setup hook to register commands after bot is ready."""
        # Start periodic heartbeat task
        asyncio.create_task(self._periodic_heartbeat())

        # Add help command
        @self.command(name="help")
        async def help_command(ctx):
            """Display all available bot commands with beautiful formatting."""
            await self.manager._handle_help_command(self.instance_name, ctx)

        # Add voice commands
        @self.command(name="join")
        async def join_voice(ctx):
            """Join the user's voice channel."""
            await self.manager._handle_voice_join(self.instance_name, ctx)

        @self.command(name="leave")
        async def leave_voice(ctx):
            """Leave the current voice channel."""
            await self.manager._handle_voice_leave(self.instance_name, ctx)

    async def send_channel_message(self, channel_id: int, content: str) -> bool:
        """
        Send a message to a specific channel.

        Args:
            channel_id: Discord channel ID
            content: Message content to send

        Returns:
            bool: True if message sent successfully
        """
        try:
            channel = self.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found")
                return False

            await channel.send(content)
            logger.info(f"Sent message to channel {channel_id}")
            return True

        except discord.errors.Forbidden:
            logger.error(f"No permission to send message to channel {channel_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to send message to channel {channel_id}: {e}")
            return False


class DiscordBotManager:
    """Discord bot lifecycle manager with automagik integration."""

    def __init__(self, message_router: MessageRouter):
        self.message_router = message_router
        self.bots: Dict[str, AutomagikBot] = {}
        self.bot_tasks: Dict[str, asyncio.Task] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.health_monitors: Dict[str, HealthMonitor] = {}
        self.instance_configs: Dict[str, InstanceConfig] = {}  # Store instance configs
        self.voice_manager = DiscordVoiceManager()  # Voice management
        self._shutdown_event = asyncio.Event()
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}  # Circuit breaker tracking

        logger.info("Discord Bot Manager initialized")

    async def start_bot(self, instance_config: InstanceConfig) -> bool:
        """
        Start a Discord bot with the given configuration.

        Args:
            instance_config: Bot configuration including token and settings

        Returns:
            bool: True if bot started successfully
        """
        instance_name = instance_config.name

        if instance_name in self.bots:
            logger.warning(f"Bot '{instance_name}' is already running")
            return False

        try:
            # Store instance configuration for later use
            self.instance_configs[instance_name] = instance_config

            # Validate configuration
            if not instance_config.discord_bot_token:
                raise AutomagikError(f"No Discord token provided for instance '{instance_name}'")

            # Set up intents
            intents = discord.Intents.default()
            intents.message_content = True
            intents.guilds = True
            intents.guild_messages = True
            intents.dm_messages = True

            # Create bot instance
            bot = AutomagikBot(
                instance_name=instance_name,
                manager=self,
                command_prefix="!",
                intents=intents,
                help_command=None,  # We'll implement our own
            )

            # Setup rate limiting
            self.rate_limiters[instance_name] = RateLimiter(max_requests=5, time_window=60)

            # Setup health monitoring
            self.health_monitors[instance_name] = HealthMonitor(instance_name=instance_name, check_interval=30)

            # Store bot
            self.bots[instance_name] = bot

            # Start Unix socket server for IPC
            asyncio.create_task(self._start_unix_socket_server(instance_name))

            # Start bot in background task
            self.bot_tasks[instance_name] = asyncio.create_task(self._run_bot(bot, instance_config.discord_bot_token))

            logger.info(f"Started Discord bot '{instance_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to start Discord bot '{instance_name}': {e}")
            # Cleanup on failure
            await self._cleanup_bot(instance_name)
            return False

    async def stop_bot(self, instance_name: str) -> bool:
        """
        Gracefully stop a Discord bot.

        Args:
            instance_name: Name of the bot instance to stop

        Returns:
            bool: True if bot stopped successfully
        """
        if instance_name not in self.bots:
            logger.warning(f"Bot '{instance_name}' is not running")
            return False

        try:
            bot = self.bots[instance_name]

            # Close bot connection
            await bot.close()

            # Cancel background task
            if instance_name in self.bot_tasks:
                task = self.bot_tasks[instance_name]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Cleanup resources
            await self._cleanup_bot(instance_name)

            logger.info(f"Stopped Discord bot '{instance_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to stop Discord bot '{instance_name}': {e}")
            return False

    async def send_message(
        self,
        instance_name: str,
        channel_id: int,
        content: str,
        embed: Optional[discord.Embed] = None,
        attachments: Optional[List] = None,
    ) -> bool:
        """
        Send a message through a Discord bot.

        Args:
            instance_name: Name of the bot instance
            channel_id: Discord channel ID
            content: Message content
            embed: Optional Discord embed
            attachments: Optional file attachments

        Returns:
            bool: True if message sent successfully
        """
        if instance_name not in self.bots:
            logger.error(f"Bot '{instance_name}' is not running")
            return False

        bot = self.bots[instance_name]

        # Check rate limiting
        rate_limiter = self.rate_limiters.get(instance_name)
        if rate_limiter and not await rate_limiter.check_rate_limit():
            logger.warning(f"Rate limit exceeded for bot '{instance_name}'")
            return False

        try:
            channel = bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found for bot '{instance_name}'")
                return False

            # Prepare message parameters
            kwargs = {}
            if content:
                kwargs["content"] = content[:2000]  # Discord message limit
            if embed:
                kwargs["embed"] = embed
            if attachments:
                kwargs["files"] = attachments

            # Send message
            await channel.send(**kwargs)
            logger.debug(f"Message sent to channel {channel_id} by bot '{instance_name}'")
            return True

        except discord.errors.Forbidden:
            logger.error(f"No permission to send message to channel {channel_id}")
            return False
        except discord.errors.HTTPException as e:
            logger.error(f"HTTP error sending message: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def get_bot_status(self, instance_name: str) -> Optional[BotStatus]:
        """
        Get detailed status information for a bot.

        Args:
            instance_name: Name of the bot instance

        Returns:
            BotStatus: Status information or None if bot not found
        """
        if instance_name not in self.bots:
            return None

        bot = self.bots[instance_name]

        # Determine status
        if not bot.is_ready():
            status = "starting" if instance_name in self.bot_tasks else "disconnected"
        else:
            status = "connected"

        # Count users across all guilds
        user_count = sum(guild.member_count or 0 for guild in bot.guilds)

        return BotStatus(
            instance_name=instance_name,
            status=status,
            guild_count=len(bot.guilds),
            user_count=user_count,
            latency=bot.latency * 1000,  # Convert to milliseconds
            last_heartbeat=bot.last_heartbeat,
            uptime=bot.start_time,
        )

    def get_all_bot_statuses(self) -> Dict[str, BotStatus]:
        """Get status information for all running bots."""
        statuses = {}
        for instance_name in self.bots:
            status = self.get_bot_status(instance_name)
            if status:
                statuses[instance_name] = status
        return statuses

    async def shutdown(self):
        """Shutdown all bots gracefully."""
        logger.info("Shutting down Discord Bot Manager...")

        self._shutdown_event.set()

        # Stop all bots
        stop_tasks = []
        for instance_name in list(self.bots.keys()):
            stop_tasks.append(self.stop_bot(instance_name))

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        logger.info("Discord Bot Manager shutdown complete")

    async def _run_bot(self, bot: AutomagikBot, token: str):
        """Run a Discord bot with resilient auto-reconnection, jittered backoff, and circuit breaker."""
        instance_name = bot.instance_name
        max_retries = 5
        retry_count = 0

        # Initialize circuit breaker if not exists
        if instance_name not in self.circuit_breakers:
            self.circuit_breakers[instance_name] = CircuitBreakerState()

        circuit_breaker = self.circuit_breakers[instance_name]

        while not self._shutdown_event.is_set() and retry_count < max_retries:
            # Check circuit breaker state
            if await self._should_skip_connection_attempt(instance_name, circuit_breaker):
                logger.warning(
                    f"Circuit breaker OPEN for bot '{instance_name}' - skipping connection attempt. "
                    f"Next retry at: {circuit_breaker.next_retry_time}"
                )
                await asyncio.sleep(30)  # Check again in 30 seconds
                continue

            try:
                logger.info(
                    f"Attempting bot connection for '{instance_name}' (attempt {retry_count + 1}/{max_retries}, "
                    f"circuit breaker failures: {circuit_breaker.consecutive_failures})"
                )

                await bot.start(token)

                # Connection successful - reset circuit breaker
                await self._reset_circuit_breaker(instance_name, circuit_breaker)
                logger.info(f"Bot '{instance_name}' connected successfully - circuit breaker reset")
                break

            except discord.LoginFailure as e:
                logger.error(
                    f"AUTHENTICATION FAILURE for bot '{instance_name}': Invalid Discord token provided. "
                    f"Error details: {e}"
                )
                # LoginFailure is permanent - cleanup resources and exit
                await self._handle_permanent_failure(instance_name, "Invalid Discord token", circuit_breaker)
                break

            except discord.ConnectionClosed as e:
                retry_count += 1
                await self._handle_connection_failure(
                    instance_name,
                    f"Connection closed: {e}",
                    retry_count,
                    max_retries,
                    circuit_breaker,
                )

                if retry_count < max_retries:
                    wait_time = await self._calculate_jittered_backoff(retry_count)
                    logger.info(
                        f"Retrying connection for bot '{instance_name}' in {wait_time:.2f}s "
                        f"(attempt {retry_count + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)

            except discord.HTTPException as e:
                retry_count += 1
                await self._handle_connection_failure(
                    instance_name,
                    f"HTTP error: {e} (status: {getattr(e, 'status', 'unknown')})",
                    retry_count,
                    max_retries,
                    circuit_breaker,
                )

                if retry_count < max_retries:
                    wait_time = await self._calculate_jittered_backoff(retry_count)
                    logger.warning(f"HTTP error for bot '{instance_name}': {e} - retrying in {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                retry_count += 1
                await self._handle_connection_failure(
                    instance_name,
                    f"Unexpected error: {e}",
                    retry_count,
                    max_retries,
                    circuit_breaker,
                )

                if retry_count < max_retries:
                    wait_time = 5  # Fixed delay for unexpected errors
                    logger.error(
                        f"Unexpected error in bot '{instance_name}': {e} - retrying in {wait_time}s",
                        exc_info=True,
                    )
                    await asyncio.sleep(wait_time)

        if retry_count >= max_retries:
            await self._handle_max_retries_exceeded(instance_name, circuit_breaker)

    async def _should_skip_connection_attempt(self, instance_name: str, circuit_breaker: CircuitBreakerState) -> bool:
        """Check if connection attempt should be skipped due to circuit breaker state."""
        if not circuit_breaker.is_open:
            return False

        current_time = datetime.now(timezone.utc)

        # Check if recovery timeout has passed
        if circuit_breaker.next_retry_time and current_time >= circuit_breaker.next_retry_time:
            # Move to half-open state
            circuit_breaker.is_open = False
            logger.info(f"Circuit breaker for '{instance_name}' moved to HALF-OPEN state")
            return False

        return True

    async def _calculate_jittered_backoff(self, retry_count: int) -> float:
        """Calculate jittered exponential backoff delay."""
        base_delay = min(2**retry_count, 60)  # Cap at 60 seconds
        # Add jitter (up to 10% of base delay) to prevent thundering herd
        jitter = random.uniform(0, 0.1 * base_delay)
        return base_delay + jitter

    async def _handle_permanent_failure(self, instance_name: str, reason: str, circuit_breaker: CircuitBreakerState):
        """Handle permanent failures like LoginFailure with proper resource cleanup."""
        logger.error(f"PERMANENT FAILURE for bot '{instance_name}': {reason} - cleaning up resources")

        # Mark circuit breaker as permanently failed
        circuit_breaker.is_open = True
        circuit_breaker.consecutive_failures += 1
        circuit_breaker.last_failure_time = datetime.now(timezone.utc)

        # Cleanup resources immediately for permanent failures
        await self._cleanup_bot(instance_name)

        logger.info(f"Resource cleanup completed for bot '{instance_name}' after permanent failure")

    async def _handle_connection_failure(
        self,
        instance_name: str,
        error_message: str,
        retry_count: int,
        max_retries: int,
        circuit_breaker: CircuitBreakerState,
    ):
        """Handle connection failures with circuit breaker logic."""
        circuit_breaker.failure_count += 1
        circuit_breaker.consecutive_failures += 1
        circuit_breaker.last_failure_time = datetime.now(timezone.utc)

        # Check if circuit breaker should open
        if circuit_breaker.consecutive_failures >= circuit_breaker.failure_threshold and not circuit_breaker.is_open:
            circuit_breaker.is_open = True
            circuit_breaker.next_retry_time = datetime.now(timezone.utc) + timedelta(
                seconds=circuit_breaker.recovery_timeout
            )
            logger.warning(
                f"Circuit breaker OPENED for bot '{instance_name}' after {circuit_breaker.consecutive_failures} "
                f"consecutive failures. Recovery timeout: {circuit_breaker.recovery_timeout}s"
            )

        logger.warning(
            f"Connection failure for bot '{instance_name}' ({retry_count}/{max_retries}): {error_message} "
            f"(consecutive failures: {circuit_breaker.consecutive_failures})"
        )

    async def _reset_circuit_breaker(self, instance_name: str, circuit_breaker: CircuitBreakerState):
        """Reset circuit breaker after successful connection."""
        if circuit_breaker.consecutive_failures > 0 or circuit_breaker.is_open:
            logger.info(
                f"Resetting circuit breaker for bot '{instance_name}' after successful connection "
                f"(was: {circuit_breaker.consecutive_failures} consecutive failures)"
            )

        circuit_breaker.consecutive_failures = 0
        circuit_breaker.is_open = False
        circuit_breaker.next_retry_time = None

    async def _handle_max_retries_exceeded(self, instance_name: str, circuit_breaker: CircuitBreakerState):
        """Handle the case when max retries are exceeded."""
        logger.error(
            f"MAX RETRIES EXCEEDED for bot '{instance_name}' - permanent failure. "
            f"Total failures: {circuit_breaker.failure_count}, "
            f"Consecutive failures: {circuit_breaker.consecutive_failures}"
        )

        # Open circuit breaker permanently for this session
        circuit_breaker.is_open = True
        circuit_breaker.next_retry_time = None  # No automatic recovery

        # Cleanup resources
        await self._cleanup_bot(instance_name)

    async def _handle_bot_ready(self, bot: AutomagikBot):
        """Handle bot ready event."""
        # Start health monitoring
        health_monitor = self.health_monitors.get(bot.instance_name)
        if health_monitor:
            await health_monitor.start_monitoring()

        # Notify message router (if method exists)
        if hasattr(self.message_router, "handle_bot_connected"):
            await self.message_router.handle_bot_connected(bot.instance_name, "discord")

    async def _handle_incoming_message(self, instance_name: str, message: discord.Message):
        """Handle incoming Discord message and route to MessageRouter."""
        try:
            # Get the bot instance
            bot = self.bots.get(instance_name)
            if not bot:
                logger.error(f"Bot '{instance_name}' not found")
                return

            # Check if bot was mentioned or if it's a DM
            is_dm = isinstance(message.channel, discord.DMChannel)
            bot_mentioned = bot.user in message.mentions if bot.user else False

            # Only process if bot was mentioned or it's a DM
            if not is_dm and not bot_mentioned:
                return

            # Extract user information for routing
            user_dict = {
                "email": f"{message.author.id}@discord.user",  # Synthetic email for Discord users
                "phone_number": None,  # Discord doesn't have phone numbers
                "user_data": {
                    "discord_id": str(message.author.id),
                    "username": message.author.name,
                    "display_name": message.author.display_name,
                    "discriminator": message.author.discriminator,
                    "guild_id": str(message.guild.id) if message.guild else None,
                    "guild_name": message.guild.name if message.guild else None,
                    "channel_id": str(message.channel.id),
                    "channel_name": getattr(message.channel, "name", "DM"),
                    "is_dm": is_dm,
                },
            }

            # Generate session name similar to WhatsApp format
            session_name = (
                f"discord_{message.guild.id}_{message.author.id}"
                if message.guild
                else f"discord_dm_{message.author.id}"
            )

            # Extract message content and remove bot mention if present
            content = message.content.strip()
            # Remove bot mention from the message
            if bot_mentioned:
                content = content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

            logger.info(
                f"Processing Discord message: '{content}' from user: {message.author.name} in session: {session_name}"
            )

            # Get instance configuration for this bot
            instance_config = self.instance_configs.get(instance_name)

            # Create agent config from instance config
            agent_config = None
            if instance_config:
                # Get agent_id properly from instance config
                agent_id = (
                    instance_config.agent_id
                    if instance_config.agent_id and instance_config.agent_id != "default"
                    else instance_config.default_agent
                )
                if not agent_id:
                    agent_id = "default"

                agent_config = {
                    "name": agent_id,
                    "agent_id": agent_id,
                    "api_url": instance_config.agent_api_url,
                    "api_key": instance_config.agent_api_key,
                    "timeout": instance_config.agent_timeout or 60,
                    "instance_type": instance_config.agent_instance_type,  # Add instance type for proper routing
                    "agent_type": instance_config.agent_type,  # Add agent type (agent or team)
                    "instance_config": instance_config,  # Pass the full config for hive client
                }

            # Attempt to resolve existing local user via shared identity linking
            resolved_user_id = None
            try:
                from src.db.database import SessionLocal
                from src.services.user_service import user_service

                db_session = SessionLocal()
                try:
                    resolved = user_service.resolve_user_by_external(
                        provider="discord", external_id=str(message.author.id), db=db_session
                    )
                    if resolved:
                        resolved_user_id = resolved.id
                        logger.info(
                            f"Resolved Discord user {message.author.id} to local user {resolved_user_id} via external link"
                        )
                except DatabaseError as db_err:
                    logger.error(f"Failed to resolve Discord user {message.author.id}: {db_err}")
                except Exception as e:
                    logger.error(f"Failed during Discord identity resolution: {e}", exc_info=True)
                finally:
                    db_session.close()
            except Exception as e:
                logger.error(f"Failed to initialise Discord identity resolution session: {e}", exc_info=True)

            # Route message to MessageRouter (synchronous call from async context)
            # Since we're in an async context and route_message is sync, use executor
            import asyncio
            from functools import partial

            try:
                loop = asyncio.get_event_loop()
                # Use partial to ensure correct parameter mapping
                route_func = partial(
                    self.message_router.route_message,
                    message_text=content,  # CRITICAL: message_text comes first in the signature
                    user_id=resolved_user_id,  # If resolved, prefer stable local user_id
                    user=None if resolved_user_id else user_dict,  # Fallback to user dict if not resolved
                    session_name=session_name,
                    message_type="text",
                    whatsapp_raw_payload=None,  # Discord doesn't use WhatsApp payload
                    session_origin="discord",
                    agent_config=agent_config,  # Pass agent configuration
                    media_contents=None,  # TODO: Handle Discord attachments if needed
                    trace_context=None,
                )
                agent_response = await loop.run_in_executor(None, route_func)

                # Send response back to Discord if we got one
                if agent_response:
                    # Use unified response extraction
                    response_text = extract_response_text(agent_response)

                    # Split message if it exceeds Discord's 2000 char limit
                    message_chunks = split_message_for_discord(response_text)

                    # Send all chunks
                    for chunk in message_chunks:
                        await message.channel.send(chunk)
                else:
                    await message.channel.send(
                        "I'm sorry, I couldn't process your message right now. Please try again later."
                    )

            except TypeError as te:
                # Fallback for older versions of MessageRouter without some parameters
                logger.warning(f"Route_message did not accept some parameters, retrying with basic ones: {te}")
                route_func_fallback = partial(
                    self.message_router.route_message,
                    message_text=content,
                    user_id=resolved_user_id,
                    user=None if resolved_user_id else user_dict,
                    session_name=session_name,
                    message_type="text",
                    whatsapp_raw_payload=None,
                    session_origin="discord",
                    agent_config=agent_config,
                )
                agent_response = await loop.run_in_executor(None, route_func_fallback)

                if agent_response:
                    # Use unified response extraction
                    response_text = extract_response_text(agent_response)

                    # Split message if it exceeds Discord's 2000 char limit
                    message_chunks = split_message_for_discord(response_text)

                    # Send all chunks
                    for chunk in message_chunks:
                        await message.channel.send(chunk)
                else:
                    await message.channel.send(
                        "I'm sorry, I couldn't process your message right now. Please try again later."
                    )

        except Exception as e:
            logger.error(f"Error handling incoming message from '{instance_name}': {e}")
            try:
                await message.channel.send("I encountered an error processing your message. Please try again later.")
            except Exception as send_error:
                logger.error(f"Failed to send error message to Discord: {send_error}")

    async def _handle_bot_disconnect(self, instance_name: str):
        """Handle bot disconnection."""
        # Stop health monitoring
        health_monitor = self.health_monitors.get(instance_name)
        if health_monitor:
            await health_monitor.stop_monitoring()

        # Notify message router if method exists
        if hasattr(self.message_router, "handle_bot_disconnected"):
            await self.message_router.handle_bot_disconnected(instance_name, "discord")

    async def _handle_guild_join(self, instance_name: str, guild: discord.Guild):
        """Handle bot joining a guild."""
        logger.info(f"Bot '{instance_name}' joined guild: {guild.name} (ID: {guild.id})")

        # Could implement guild-specific setup here
        # e.g., register slash commands, send welcome message, etc.

    async def _handle_guild_remove(self, instance_name: str, guild: discord.Guild):
        """Handle bot leaving a guild."""
        logger.info(f"Bot '{instance_name}' left guild: {guild.name} (ID: {guild.id})")

        # Could implement cleanup here

    async def _handle_interaction(self, instance_name: str, interaction: discord.Interaction):
        """Handle slash command interactions."""
        try:
            # Convert interaction to automagik format
            automagik_interaction = {
                "platform": "discord",
                "instance_name": instance_name,
                "type": "interaction",
                "interaction_id": str(interaction.id),
                "command_name": (interaction.data.get("name") if interaction.data else None),
                "options": (interaction.data.get("options", []) if interaction.data else []),
                "user_id": str(interaction.user.id),
                "username": interaction.user.display_name,
                "channel_id": (str(interaction.channel_id) if interaction.channel_id else None),
                "guild_id": str(interaction.guild_id) if interaction.guild_id else None,
                "timestamp": interaction.created_at.isoformat(),
            }

            # Route interaction through automagik system
            await self.message_router.route_interaction(automagik_interaction)

        except Exception as e:
            logger.error(f"Error handling interaction from '{instance_name}': {e}")
            # Send error response to user
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Sorry, an error occurred while processing your command.",
                    ephemeral=True,
                )

    async def _handle_bot_error(self, instance_name: str, event: str, args: tuple, kwargs: dict):
        """Handle bot errors."""
        logger.error(f"Discord error in bot '{instance_name}' for event '{event}': {args}, {kwargs}")

        # Could implement error recovery logic here
        # e.g., restart bot on certain errors, notify admins, etc.

    async def _handle_voice_join(self, instance_name: str, ctx):
        """Handle !join command - join user's voice channel."""
        try:
            # Check if user is in a voice channel
            if not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.send("❌ You need to be in a voice channel first!")
                return

            voice_channel = ctx.author.voice.channel
            bot = self.bots.get(instance_name)
            if not bot:
                await ctx.send("❌ Bot not found!")
                return

            # Connect to voice channel
            success = await self.voice_manager.connect_voice(instance_name, voice_channel.id, bot)

            if success:
                await ctx.send(f"🎤 Joined voice channel: **{voice_channel.name}**")
                logger.info(f"Bot {instance_name} joined voice channel {voice_channel.name}")
            else:
                await ctx.send("❌ Failed to join voice channel!")

        except Exception as e:
            logger.error(f"Voice join error for {instance_name}: {e}")
            await ctx.send("❌ Error joining voice channel!")

    async def _handle_voice_leave(self, instance_name: str, ctx):
        """Handle !leave command - leave current voice channel."""
        try:
            success = await self.voice_manager.disconnect_voice(instance_name, ctx.guild.id)

            if success:
                await ctx.send("👋 Left voice channel!")
                logger.info(f"Bot {instance_name} left voice channel")
            else:
                await ctx.send("❌ Not connected to any voice channel!")

        except Exception as e:
            logger.error(f"Voice leave error for {instance_name}: {e}")
            await ctx.send("❌ Error leaving voice channel!")

    async def _handle_help_command(self, instance_name: str, ctx):
        """Handle !help command - display all available commands with beautiful formatting."""
        try:
            # Create a beautiful embed for the help message
            embed = discord.Embed(
                title="🤖 Automagik Omni Discord Bot Commands",
                description="Welcome to Automagik Omni! Here are all available commands:",
                color=0x7289DA,  # Discord blurple color
            )

            # Add bot info
            bot = self.bots.get(instance_name)
            if bot:
                embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)

            # Command categories
            embed.add_field(
                name="🎤 Voice Commands",
                value=("`!join` - Join your current voice channel\n`!leave` - Leave the current voice channel"),
                inline=False,
            )

            embed.add_field(
                name="ℹ️ Information Commands",
                value="`!help` - Show this help message",
                inline=False,
            )

            embed.add_field(
                name="💬 Chat Features",
                value=(
                    "• **Mention me** (@bot) to start a conversation\n"
                    "• **Direct Messages** are always processed\n"
                    "• Powered by Automagik AI agents"
                ),
                inline=False,
            )

            # Add usage tips
            embed.add_field(
                name="💡 Tips",
                value=(
                    "• Use `!join` to bring me into voice chat\n"
                    "• Use `!leave` when done with voice\n"
                    "• Mention me in channels to chat\n"
                    "• DM me anytime for private conversations"
                ),
                inline=False,
            )

            # Add footer with instance info
            embed.set_footer(
                text=f"Instance: {instance_name} | Automagik Omni v{__version__}",
                icon_url="https://cdn.discordapp.com/emojis/1234567890123456789.png",  # Would use actual emoji if available
            )

            # Add timestamp
            embed.timestamp = datetime.now(timezone.utc)

            await ctx.send(embed=embed)
            logger.info(f"Help command executed for {instance_name}")

        except Exception as e:
            logger.error(f"Help command error for {instance_name}: {e}")
            # Fallback to simple text message if embed fails
            help_text = (
                "🤖 **Automagik Omni Discord Bot Commands**\n\n"
                "🎤 **Voice Commands:**\n"
                "`!join` - Join your voice channel\n"
                "`!leave` - Leave voice channel\n\n"
                "ℹ️ **Other Commands:**\n"
                "`!help` - Show this help message\n\n"
                "💬 **Chat:** Mention me or DM me to chat!\n"
                f"Instance: {instance_name}"
            )
            await ctx.send(help_text)

    async def _cleanup_bot(self, instance_name: str):
        """Cleanup bot resources."""
        # Remove bot from tracking
        self.bots.pop(instance_name, None)
        self.bot_tasks.pop(instance_name, None)

        # Cleanup circuit breaker state
        self.circuit_breakers.pop(instance_name, None)

        # Cleanup rate limiter
        rate_limiter = self.rate_limiters.pop(instance_name, None)
        if rate_limiter:
            # RateLimiter doesn't have cleanup method, just remove reference
            pass

        # Cleanup voice sessions
        await self.voice_manager.disconnect_voice(instance_name)

        # Cleanup health monitor
        health_monitor = self.health_monitors.pop(instance_name, None)
        if health_monitor:
            await health_monitor.stop_monitoring()

    async def _start_unix_socket_server(self, instance_name: str):
        """
        Start Unix domain socket server for IPC communication.

        This allows the API to send messages through the Discord bot
        without needing network ports.
        """
        try:
            # Import IPC configuration
            from src.ipc_config import IPCConfig

            # Get socket path using centralized configuration
            socket_path = IPCConfig.get_socket_path("discord", instance_name)

            # Clean up old socket if it exists
            IPCConfig.cleanup_stale_socket(socket_path)

            # Create HTTP application for IPC
            app = web.Application()

            # Add routes for IPC communication
            app.router.add_post("/send", self._handle_ipc_send_message)
            app.router.add_get("/health", self._handle_ipc_health_check)
            app.router.add_get("/status", self._handle_ipc_status)

            # Store instance name in app for handler access
            app["instance_name"] = instance_name
            app["manager"] = self

            # Create and start Unix socket server
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.UnixSite(runner, socket_path)
            await site.start()

            # Set socket permissions (owner read/write only for security)
            os.chmod(socket_path, 0o600)

            logger.info(f"Unix socket server started for '{instance_name}' at {socket_path}")

        except Exception as e:
            logger.error(f"Failed to start Unix socket server for '{instance_name}': {e}")

    async def _handle_ipc_send_message(self, request: web.Request) -> web.Response:
        """Handle IPC message send request via Unix socket."""
        try:
            instance_name = request.app["instance_name"]
            manager = request.app["manager"]

            # Parse JSON request
            data = await request.json()
            channel_id = data.get("channel_id")
            text = data.get("text")

            if not channel_id or not text:
                return web.json_response(
                    {"success": False, "error": "Missing channel_id or text"},
                    status=400,
                )

            # Convert channel_id to int if it's a string
            try:
                channel_id = int(channel_id)
            except (ValueError, TypeError):
                return web.json_response({"success": False, "error": "Invalid channel_id"}, status=400)

            # Send message through the bot
            success = await manager.send_message(instance_name=instance_name, channel_id=channel_id, content=text)

            return web.json_response(
                {
                    "success": success,
                    "instance": instance_name,
                    "channel_id": channel_id,
                }
            )

        except json.JSONDecodeError:
            return web.json_response({"success": False, "error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f"IPC send message error: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _handle_ipc_health_check(self, request: web.Request) -> web.Response:
        """Handle IPC health check request."""
        instance_name = request.app["instance_name"]
        manager = request.app["manager"]

        bot = manager.bots.get(instance_name)
        if not bot:
            return web.json_response({"status": "error", "message": "Bot not found"}, status=404)

        return web.json_response(
            {
                "status": "ok",
                "instance": instance_name,
                "bot_connected": bot.is_ready(),
                "latency_ms": round(bot.latency * 1000, 2) if bot.is_ready() else None,
            }
        )

    async def _handle_ipc_status(self, request: web.Request) -> web.Response:
        """Handle IPC status request."""
        instance_name = request.app["instance_name"]
        manager = request.app["manager"]

        status = manager.get_bot_status(instance_name)
        if not status:
            return web.json_response({"status": "error", "message": "Bot not found"}, status=404)

        return web.json_response(
            {
                "status": status.status,
                "instance": status.instance_name,
                "guild_count": status.guild_count,
                "user_count": status.user_count,
                "latency_ms": status.latency,
                "uptime": status.uptime.isoformat() if status.uptime else None,
            }
        )


# Utility functions for Discord message formatting
def create_embed(
    title: str,
    description: str = None,
    color: int = 0x00FF00,
    fields: List[Dict[str, Any]] = None,
) -> discord.Embed:
    """Create a Discord embed with common formatting."""
    embed = discord.Embed(title=title, description=description, color=color)

    if fields:
        for field in fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", False),
            )

    embed.timestamp = datetime.now(timezone.utc)
    return embed


def format_automagik_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Format automagik response for Discord."""
    formatted = {
        "content": response.get("content", ""),
        "embed": None,
        "attachments": [],
    }

    # Handle different response types
    if response.get("type") == "embed":
        embed_data = response.get("embed", {})
        formatted["embed"] = create_embed(
            title=embed_data.get("title", ""),
            description=embed_data.get("description"),
            color=embed_data.get("color", 0x00FF00),
            fields=embed_data.get("fields", []),
        )

    return formatted
