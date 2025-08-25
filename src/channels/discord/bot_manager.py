"""
Discord Bot Manager - Bot lifecycle management and integration with automagik-omni.

This module provides comprehensive Discord bot management including connection handling,
event management, message routing, and health monitoring.
"""

import asyncio
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from aiohttp import web

import discord
from discord.ext import commands

from src.services.message_router import MessageRouter
from ...core.exceptions import AutomagikError
from src.db.models import InstanceConfig
from src.channels.message_utils import extract_response_text
from ...utils.rate_limiter import RateLimiter
from ...utils.health_monitor import HealthMonitor

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


class AutomagikBot(commands.Bot):
    """Custom Discord bot class with automagik integration."""
    
    def __init__(self, instance_name: str, manager: 'DiscordBotManager', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance_name = instance_name
        self.manager = manager
        self.start_time = None
        self.last_heartbeat = datetime.now(timezone.utc)
        
    async def on_ready(self):
        """Called when bot is ready."""
        self.start_time = datetime.now(timezone.utc)
        self.last_heartbeat = datetime.now(timezone.utc)
        
        logger.info(f"Discord bot '{self.instance_name}' is ready!")
        logger.info(f"Bot user: {self.user}")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        await self.manager._handle_bot_ready(self)
    
    async def on_message(self, message):
        """Handle incoming messages."""
        self.last_heartbeat = datetime.now(timezone.utc)
        
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
    
    async def on_error(self, event, *args, **kwargs):
        """Handle errors."""
        logger.error(f"Discord error in bot '{self.instance_name}' for event '{event}'", 
                    exc_info=True)
        await self.manager._handle_bot_error(self.instance_name, event, args, kwargs)
    
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
        self._shutdown_event = asyncio.Event()
        
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
                command_prefix='!',
                intents=intents,
                help_command=None  # We'll implement our own
            )
            
            # Setup rate limiting
            self.rate_limiters[instance_name] = RateLimiter(
                max_requests=5,
                time_window=60
            )
            
            # Setup health monitoring
            self.health_monitors[instance_name] = HealthMonitor(
                instance_name=instance_name,
                check_interval=30
            )
            
            # Store bot
            self.bots[instance_name] = bot
            
            # Start Unix socket server for IPC
            asyncio.create_task(self._start_unix_socket_server(instance_name))
            
            # Start bot in background task
            self.bot_tasks[instance_name] = asyncio.create_task(
                self._run_bot(bot, instance_config.discord_bot_token)
            )
            
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
    
    async def send_message(self, instance_name: str, channel_id: int, 
                          content: str, embed: Optional[discord.Embed] = None,
                          attachments: Optional[List] = None) -> bool:
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
                kwargs['content'] = content[:2000]  # Discord message limit
            if embed:
                kwargs['embed'] = embed
            if attachments:
                kwargs['files'] = attachments
            
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
            status = 'starting' if instance_name in self.bot_tasks else 'disconnected'
        else:
            status = 'connected'
        
        # Count users across all guilds
        user_count = sum(guild.member_count or 0 for guild in bot.guilds)
        
        return BotStatus(
            instance_name=instance_name,
            status=status,
            guild_count=len(bot.guilds),
            user_count=user_count,
            latency=bot.latency * 1000,  # Convert to milliseconds
            last_heartbeat=bot.last_heartbeat,
            uptime=bot.start_time
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
            socket_path = IPCConfig.get_socket_path('discord', instance_name)
            
            # Clean up old socket if it exists
            IPCConfig.cleanup_stale_socket(socket_path)
            
            # Create HTTP application for IPC
            app = web.Application()
            
            # Add routes for IPC communication
            app.router.add_post('/send', self._handle_ipc_send_message)
            app.router.add_get('/health', self._handle_ipc_health_check)
            app.router.add_get('/status', self._handle_ipc_status)
            
            # Store instance name in app for handler access
            app['instance_name'] = instance_name
            app['manager'] = self
            
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
            instance_name = request.app['instance_name']
            manager = request.app['manager']
            
            # Parse JSON request
            data = await request.json()
            channel_id = data.get('channel_id')
            text = data.get('text')
            
            if not channel_id or not text:
                return web.json_response(
                    {'success': False, 'error': 'Missing channel_id or text'},
                    status=400
                )
            
            # Convert channel_id to int if it's a string
            try:
                channel_id = int(channel_id)
            except (ValueError, TypeError):
                return web.json_response(
                    {'success': False, 'error': 'Invalid channel_id'},
                    status=400
                )
            
            # Send message through the bot
            success = await manager.send_message(
                instance_name=instance_name,
                channel_id=channel_id,
                content=text
            )
            
            return web.json_response({
                'success': success,
                'instance': instance_name,
                'channel_id': channel_id
            })
            
        except json.JSONDecodeError:
            return web.json_response(
                {'success': False, 'error': 'Invalid JSON'},
                status=400
            )
        except Exception as e:
            logger.error(f"IPC send message error: {e}")
            return web.json_response(
                {'success': False, 'error': str(e)},
                status=500
            )
    
    async def _handle_ipc_health_check(self, request: web.Request) -> web.Response:
        """Handle IPC health check request."""
        instance_name = request.app['instance_name']
        manager = request.app['manager']
        
        bot = manager.bots.get(instance_name)
        if not bot:
            return web.json_response(
                {'status': 'error', 'message': 'Bot not found'},
                status=404
            )
        
        return web.json_response({
            'status': 'ok',
            'instance': instance_name,
            'bot_connected': bot.is_ready(),
            'latency_ms': round(bot.latency * 1000, 2) if bot.is_ready() else None
        })
    
    async def _handle_ipc_status(self, request: web.Request) -> web.Response:
        """Handle IPC status request."""
        instance_name = request.app['instance_name']
        manager = request.app['manager']
        
        status = manager.get_bot_status(instance_name)
        if not status:
            return web.json_response(
                {'error': 'Bot not found'},
                status=404
            )
        
        return web.json_response({
            'instance_name': status.instance_name,
            'status': status.status,
            'guild_count': status.guild_count,
            'user_count': status.user_count,
            'latency_ms': status.latency,
            'uptime': status.uptime.isoformat() if status.uptime else None
        })
    
    async def _run_bot(self, bot: AutomagikBot, token: str):
        """Run a Discord bot with auto-reconnection."""
        instance_name = bot.instance_name
        max_retries = 5
        retry_count = 0
        
        while not self._shutdown_event.is_set() and retry_count < max_retries:
            try:
                await bot.start(token)
            except discord.LoginFailure:
                logger.error(f"Invalid token for bot '{instance_name}'")
                break
            except discord.ConnectionClosed:
                logger.warning(f"Bot '{instance_name}' connection closed")
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = min(2 ** retry_count, 60)  # Exponential backoff
                    logger.info(f"Retrying connection for bot '{instance_name}' in {wait_time}s")
                    await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error in bot '{instance_name}': {e}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(5)
        
        if retry_count >= max_retries:
            logger.error(f"Max retries exceeded for bot '{instance_name}'")
    
    async def _handle_bot_ready(self, bot: AutomagikBot):
        """Handle bot ready event."""
        # Start health monitoring
        health_monitor = self.health_monitors.get(bot.instance_name)
        if health_monitor:
            await health_monitor.start()
        
        # Notify message router (if method exists)
        if hasattr(self.message_router, 'handle_bot_connected'):
            await self.message_router.handle_bot_connected(bot.instance_name, 'discord')
    
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
                'email': f"{message.author.id}@discord.user",  # Synthetic email for Discord users
                'phone_number': None,  # Discord doesn't have phone numbers
                'user_data': {
                    'discord_id': str(message.author.id),
                    'username': message.author.name,
                    'display_name': message.author.display_name,
                    'discriminator': message.author.discriminator,
                    'guild_id': str(message.guild.id) if message.guild else None,
                    'guild_name': message.guild.name if message.guild else None,
                    'channel_id': str(message.channel.id),
                    'channel_name': getattr(message.channel, 'name', 'DM'),
                    'is_dm': is_dm
                }
            }
            
            # Generate session name similar to WhatsApp format
            session_name = f"discord_{message.guild.id}_{message.author.id}" if message.guild else f"discord_dm_{message.author.id}"
            
            # Extract message content and remove bot mention if present
            content = message.content.strip()
            # Remove bot mention from the message
            if bot_mentioned:
                content = content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
            
            logger.info(f"Processing Discord message: '{content}' from user: {message.author.name} in session: {session_name}")
            
            # Get instance configuration for this bot
            instance_config = self.instance_configs.get(instance_name)
            
            # Create agent config from instance config
            agent_config = None
            if instance_config:
                agent_config = {
                    "name": instance_config.default_agent or "master-genie",
                    "api_url": instance_config.agent_api_url,
                    "api_key": instance_config.agent_api_key,
                    "timeout": instance_config.agent_timeout or 60
                }
            
            # Route message to MessageRouter (synchronous call, no await)
            try:
                agent_response = self.message_router.route_message(
                    user_id=None,  # Let the agent API manage user creation and ID assignment
                    user=user_dict,  # Pass user dict for creation/lookup
                    session_name=session_name,
                    message_text=content,
                    message_type="text",
                    session_origin="discord",
                    whatsapp_raw_payload=None,  # Discord doesn't use WhatsApp payload
                    media_contents=None,  # TODO: Handle Discord attachments if needed
                    agent_config=agent_config  # Pass agent configuration
                )
                
                # Send response back to Discord if we got one
                if agent_response:
                    # Use unified response extraction
                    response_text = extract_response_text(agent_response)
                    await message.channel.send(response_text)
                else:
                    await message.channel.send("I'm sorry, I couldn't process your message right now. Please try again later.")
                    
            except TypeError as te:
                # Fallback for older versions of MessageRouter without some parameters
                logger.warning(f"Route_message did not accept some parameters, retrying with basic ones: {te}")
                agent_response = self.message_router.route_message(
                    user_id=None,
                    user=user_dict,
                    session_name=session_name,
                    message_text=content,
                    message_type="text",
                    session_origin="discord",
                    whatsapp_raw_payload=None,
                    agent_config=agent_config
                )
                
                if agent_response:
                    # Use unified response extraction
                    response_text = extract_response_text(agent_response)
                    await message.channel.send(response_text)
                else:
                    await message.channel.send("I'm sorry, I couldn't process your message right now. Please try again later.")
            
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
            await health_monitor.stop()
        
        # Notify message router if method exists
        if hasattr(self.message_router, 'handle_bot_disconnected'):
            await self.message_router.handle_bot_disconnected(instance_name, 'discord')
    
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
                'platform': 'discord',
                'instance_name': instance_name,
                'type': 'interaction',
                'interaction_id': str(interaction.id),
                'command_name': interaction.data.get('name') if interaction.data else None,
                'options': interaction.data.get('options', []) if interaction.data else [],
                'user_id': str(interaction.user.id),
                'username': interaction.user.display_name,
                'channel_id': str(interaction.channel_id) if interaction.channel_id else None,
                'guild_id': str(interaction.guild_id) if interaction.guild_id else None,
                'timestamp': interaction.created_at.isoformat()
            }
            
            # Route interaction through automagik system
            await self.message_router.route_interaction(automagik_interaction)
            
        except Exception as e:
            logger.error(f"Error handling interaction from '{instance_name}': {e}")
            # Send error response to user
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Sorry, an error occurred while processing your command.",
                    ephemeral=True
                )
    
    async def _handle_bot_error(self, instance_name: str, event: str, args: tuple, kwargs: dict):
        """Handle bot errors."""
        logger.error(f"Discord error in bot '{instance_name}' for event '{event}': {args}, {kwargs}")
        
        # Could implement error recovery logic here
        # e.g., restart bot on certain errors, notify admins, etc.
    
    async def _cleanup_bot(self, instance_name: str):
        """Cleanup bot resources."""
        # Remove bot from tracking
        self.bots.pop(instance_name, None)
        self.bot_tasks.pop(instance_name, None)
        
        # Cleanup rate limiter
        rate_limiter = self.rate_limiters.pop(instance_name, None)
        if rate_limiter:
            # RateLimiter doesn't have cleanup method, just remove reference
            pass
        
        # Cleanup health monitor
        health_monitor = self.health_monitors.pop(instance_name, None)
        if health_monitor:
            await health_monitor.stop()


# Utility functions for Discord message formatting
def create_embed(title: str, description: str = None, color: int = 0x00ff00,
                fields: List[Dict[str, Any]] = None) -> discord.Embed:
    """Create a Discord embed with common formatting."""
    embed = discord.Embed(title=title, description=description, color=color)
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field['name'],
                value=field['value'],
                inline=field.get('inline', False)
            )
    
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def format_automagik_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Format automagik response for Discord."""
    formatted = {
        'content': response.get('content', ''),
        'embed': None,
        'attachments': []
    }
    
    # Handle different response types
    if response.get('type') == 'embed':
        embed_data = response.get('embed', {})
        formatted['embed'] = create_embed(
            title=embed_data.get('title', ''),
            description=embed_data.get('description'),
            color=embed_data.get('color', 0x00ff00),
            fields=embed_data.get('fields', [])
        )
    
    return formatted