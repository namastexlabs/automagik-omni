"""Discord Channel Handler Implementation.
This module implements the Discord channel handler for the automagik-omni system.
Provides multi-tenant Discord bot management with proper lifecycle control.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
from src.channels.base import ChannelHandler, QRCodeResponse, ConnectionStatus
from src.db.models import InstanceConfig
from src.config import config
from src.utils.dependency_guard import requires_feature, LazyImport, DependencyError
from src.services.message_router import message_router
# Lazy imports with dependency guards
discord = LazyImport('discord', 'discord')
logger = logging.getLogger(__name__)
from src.channels.message_utils import extract_response_text
@dataclass
class DiscordBotInstance:
    """Container for Discord bot instance data."""
    client: Any  # discord.Client
    task: Optional[asyncio.Task] = None
    status: str = "disconnected"
    invite_url: Optional[str] = None
    error_message: Optional[str] = None
class ValidationError(Exception):
    """Discord configuration validation error."""
    pass
class DiscordChannelHandler(ChannelHandler):
    """Discord channel handler implementation."""
    def __init__(self):
        """Initialize Discord channel handler."""
        self._bot_instances: Dict[str, DiscordBotInstance] = {}
    
    def _chunk_message(self, message: str, max_length: int = 2000) -> list[str]:
        """Split message into chunks that respect Discord's character limit."""
        if len(message) <= max_length:
            return [message]
        
        chunks = []
        remaining = message
        
        while remaining:
            if len(remaining) <= max_length:
                chunks.append(remaining)
                break
            
            # Try to split at a reasonable point
            chunk = remaining[:max_length]
            
            # Find the last newline, sentence end, or word boundary
            split_points = ['\n\n', '\n', '. ', '! ', '? ', ' ']
            split_at = -1
            
            for split_point in split_points:
                last_occurrence = chunk.rfind(split_point)
                if last_occurrence > max_length * 0.5:  # Don't split too early
                    split_at = last_occurrence + len(split_point)
                    break
            
            if split_at == -1:
                # No good split point found, just cut at max length
                split_at = max_length
            
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:]
        
        return chunks
    
    async def _send_response_to_discord(self, channel, response: str) -> None:
        """Send response to Discord channel, handling message chunking."""
        try:
            if not response:
                return
            
            # Split response into chunks if needed
            chunks = self._chunk_message(response)
            
            # Send each chunk
            for chunk in chunks:
                await channel.send(chunk)
                # Small delay between chunks to avoid rate limits
                if len(chunks) > 1:
                    await asyncio.sleep(0.5)
                    
        except Exception as e:
            logger.error(f"Failed to send Discord response: {e}")
            try:
                await channel.send("Sorry, I encountered an error while processing your message.")
            except:
                pass  # If we can't even send an error message, just log and continue
    
    async def _handle_message(self, message, instance: InstanceConfig, client) -> None:
        """Handle incoming Discord message with @mention detection."""
        try:
            # Ignore messages from the bot itself
            if message.author == client.user:
                return
            
            # Check if the bot is mentioned
            if not client.user.mentioned_in(message):
                return
            
            logger.info(f"Discord bot '{instance.name}' received mention from {message.author} in #{message.channel.name}")
            
            # Extract message content after removing the mention
            content = message.content
            for mention in message.mentions:
                if mention == client.user:
                    # Remove the mention from the message
                    mention_pattern = f"<@{mention.id}>"
                    alt_mention_pattern = f"<@!{mention.id}>"
                    content = content.replace(mention_pattern, "").replace(alt_mention_pattern, "")
            
            # Clean up the message (strip whitespace)
            content = content.strip()
            
            if not content:
                await message.channel.send("Hi! How can I help you? Please include your message after mentioning me.")
                return
            
            # Create user dictionary similar to WhatsApp handler
            user_dict = {
                "discord_user_id": str(message.author.id),
                "username": message.author.name,
                "email": None,  # Discord doesn't provide email unless OAuth
                "user_data": {
                    "name": message.author.display_name or message.author.name,
                    "discord_discriminator": message.author.discriminator if hasattr(message.author, 'discriminator') else None,
                    "guild_id": str(message.guild.id) if message.guild else None,
                    "guild_name": message.guild.name if message.guild else None,
                    "channel_id": str(message.channel.id),
                    "channel_name": message.channel.name if hasattr(message.channel, 'name') else None
                }
            }
            
            # Generate session name similar to WhatsApp format
            session_name = f"discord_{message.guild.id}_{message.author.id}" if message.guild else f"discord_dm_{message.author.id}"
            
            logger.info(f"Processing Discord message: '{content}' from user: {message.author.name} in session: {session_name}")
            
            # Send typing indicator
            async with message.channel.typing():
                # Route message to MessageRouter (same as WhatsApp)
                try:
                    agent_response = message_router.route_message(
                        user_id=None,  # Let the agent API manage user creation and ID assignment
                        user=user_dict,  # Pass user dict for creation/lookup
                        session_name=session_name,
                        message_text=content,
                        message_type="text",
                        session_origin="discord",
                        whatsapp_raw_payload=None,  # Discord doesn't use WhatsApp payload
                        media_contents=None  # TODO: Handle Discord attachments if needed
                    )
                    
                    logger.info(f"Got agent response for Discord user {message.author.name}: {len(str(agent_response))} characters")
                    
                    # Send response back to Discord
                    if agent_response:
                        response_text = extract_response_text(agent_response)
                        await self._send_response_to_discord(message.channel, response_text)
                    else:
                        await message.channel.send("I'm sorry, I couldn't process your message right now. Please try again later.")
                        
                except TypeError as te:
                    # Fallback for older versions of MessageRouter without media parameters
                    logger.warning(f"Route_message did not accept media_contents parameter, retrying without it: {te}")
                    agent_response = message_router.route_message(
                        user_id=None,
                        user=user_dict,
                        session_name=session_name,
                        message_text=content,
                        message_type="text",
                        session_origin="discord",
                        whatsapp_raw_payload=None
                    )
                    
                    if agent_response:
                        response_text = extract_response_text(agent_response)
                        await self._send_response_to_discord(message.channel, response_text)
                    else:
                        await message.channel.send("I'm sorry, I couldn't process your message right now. Please try again later.")
                
                except Exception as e:
                    logger.error(f"Error processing Discord message: {e}", exc_info=True)
                    await message.channel.send("I encountered an error while processing your message. Please try again later.")
        
        except Exception as e:
            logger.error(f"Error in Discord message handler: {e}", exc_info=True)

    def _validate_bot_config(self, instance: InstanceConfig) -> Dict[str, str]:
        """Validate and extract Discord bot configuration."""
        # Extract token from instance or environment
        bot_token = getattr(instance, 'discord_bot_token', None) or config.get_env("DISCORD_BOT_TOKEN", "")
        client_id = getattr(instance, 'discord_client_id', None) or config.get_env("DISCORD_CLIENT_ID", "")
        
        # Validate configuration values
        if not bot_token or bot_token.lower() in ["string", "null", "undefined", ""]:
            logger.error(f"Invalid Discord bot token for instance '{instance.name}'. Please provide a valid bot token.")
            raise ValidationError(f"Invalid Discord bot token for instance '{instance.name}'. Please provide a valid bot token from Discord Developer Portal.")
        
        if not client_id or client_id.lower() in ["string", "null", "undefined", ""]:
            logger.error(f"Invalid Discord client ID for instance '{instance.name}'. Please provide a valid client ID.")
            raise ValidationError(f"Invalid Discord client ID for instance '{instance.name}'. Please provide a valid client ID from Discord Developer Portal.")
        logger.debug(f"Discord config validated for instance '{instance.name}' - Token: {'*' * len(bot_token)}, Client ID: {client_id}")
        
        return {
            "token": bot_token,
            "client_id": client_id
        }
    def _generate_invite_url(self, client_id: str, permissions: int = 8) -> str:
        """Generate Discord bot invite URL."""
        # Default permissions: Administrator (8) - can be customized based on needs
        # Common permissions combinations:
        # - Send Messages (2048) + Read Messages (1024) = 3072
        # - Administrator (8)
        # - Manage Messages (8192) + Send Messages (2048) + Read Messages (1024) = 11264
        base_url = "https://discord.com/api/oauth2/authorize"
        params = f"client_id={client_id}&permissions={permissions}&scope=bot%20applications.commands"
        return f"{base_url}?{params}"
    @requires_feature('discord')
    async def create_instance(self, instance: InstanceConfig, **kwargs) -> Dict[str, Any]:
        """Create a new Discord bot instance."""
        try:
            logger.info(f"Creating Discord bot instance '{instance.name}'...")
            # Check if instance already exists
            if instance.name in self._bot_instances:
                existing_bot = self._bot_instances[instance.name]
                logger.info(f"Discord bot instance '{instance.name}' already exists with status: {existing_bot.status}")
                
                if existing_bot.status == "connected":
                    logger.info(f"Instance '{instance.name}' is already connected and running")
                    return {
                        "instance_name": instance.name,
                        "status": "already_exists",
                        "connection_status": existing_bot.status,
                        "message": f"Discord bot instance '{instance.name}' already exists and is connected",
                        "invite_url": existing_bot.invite_url
                    }
                else:
                    logger.info(f"Existing instance '{instance.name}' found but not connected, will restart")
                    await self._cleanup_bot_instance(instance.name)
            # Validate configuration
            bot_config = self._validate_bot_config(instance)
            
            # Create Discord client
            intents = discord.Intents.default()
            intents.message_content = True  # Required for message content access
            intents.guilds = True
            intents.guild_messages = True
            
            client = discord.Client(intents=intents)
            # Generate invite URL
            invite_url = self._generate_invite_url(bot_config["client_id"])
            # Create bot instance container
            bot_instance = DiscordBotInstance(
                client=client,
                status="connecting",
                invite_url=invite_url
            )
            
            # Store the instance
            self._bot_instances[instance.name] = bot_instance
            # Set up event handlers
            @client.event
            async def on_ready():
                logger.info(f"Discord bot '{instance.name}' logged in as {client.user}")
                bot_instance.status = "connected"
            
            @client.event
            async def on_disconnect():
                logger.warning(f"Discord bot '{instance.name}' disconnected")
                bot_instance.status = "disconnected"
            
            @client.event
            async def on_error(event, *args, **kwargs):
                logger.error(f"Discord bot '{instance.name}' error in {event}: {args}, {kwargs}")
                bot_instance.status = "error"
            
            @client.event
            async def on_message(message):
                """Handle incoming Discord messages with @mention detection."""
                await self._handle_message(message, instance, client)
            
            # Start the bot in a background task
            async def run_bot():
                try:
                    await client.start(bot_config["token"])
                except Exception as e:
                    logger.error(f"Failed to start Discord bot '{instance.name}': {e}")
                    bot_instance.status = "error"
                    bot_instance.error_message = str(e)
                    raise
            # Create and store the bot task
            bot_task = asyncio.create_task(run_bot())
            bot_instance.task = bot_task
            # Wait a moment for the bot to start connecting
            await asyncio.sleep(2)
            logger.info(f"Discord bot instance '{instance.name}' created successfully")
            logger.info(f"Invite URL: {invite_url}")
            return {
                "instance_name": instance.name,
                "status": "created",
                "connection_status": bot_instance.status,
                "message": f"Discord bot instance '{instance.name}' created successfully. Use the invite URL to add the bot to Discord servers.",
                "invite_url": invite_url,
                "client_id": bot_config["client_id"]
            }
        except ValidationError as e:
            logger.error(f"Validation error creating Discord instance: {e}")
            # Clean up any partial state
            if instance.name in self._bot_instances:
                await self._cleanup_bot_instance(instance.name)
            return {"error": str(e), "status": "validation_failed"}
        except DependencyError as e:
            logger.error(f"Missing Discord dependencies: {e}")
            return {"error": str(e), "status": "dependency_missing"}
        except Exception as e:
            logger.error(f"Failed to create Discord bot instance: {e}")
            # Clean up any partial state
            if instance.name in self._bot_instances:
                await self._cleanup_bot_instance(instance.name)
            return {"error": str(e), "status": "failed"}
    async def get_qr_code(self, instance: InstanceConfig) -> QRCodeResponse:
        """Get Discord bot invite URL (Discord doesn't use QR codes like WhatsApp)."""
        try:
            logger.debug(f"=== INVITE URL REQUEST START for {instance.name} ===")
            
            # Check if instance exists
            if instance.name not in self._bot_instances:
                logger.warning(f"Discord bot instance '{instance.name}' not found")
                return QRCodeResponse(
                    instance_name=instance.name,
                    channel_type="discord",
                    status="not_found",
                    message=f"Discord bot instance '{instance.name}' not found. Create the instance first."
                )
            bot_instance = self._bot_instances[instance.name]
            
            # If we don't have an invite URL, generate it
            if not bot_instance.invite_url:
                try:
                    bot_config = self._validate_bot_config(instance)
                    bot_instance.invite_url = self._generate_invite_url(bot_config["client_id"])
                except ValidationError as e:
                    return QRCodeResponse(
                        instance_name=instance.name,
                        channel_type="discord",
                        status="configuration_error",
                        message=str(e)
                    )
            logger.debug(f"Discord invite URL for '{instance.name}': {bot_instance.invite_url}")
            
            return QRCodeResponse(
                instance_name=instance.name,
                channel_type="discord",
                invite_url=bot_instance.invite_url,
                status="success",
                message=f"Discord bot invite URL ready. Use this URL to add the bot to Discord servers."
            )
        except Exception as e:
            logger.error(f"Failed to get Discord invite URL: {e}")
            return QRCodeResponse(
                instance_name=instance.name,
                channel_type="discord",
                status="error",
                message=f"Failed to get Discord invite URL: {str(e)}"
            )
    async def get_status(self, instance: InstanceConfig) -> ConnectionStatus:
        """Get Discord bot connection status."""
        try:
            if instance.name not in self._bot_instances:
                return ConnectionStatus(
                    instance_name=instance.name,
                    channel_type="discord",
                    status="not_found"
                )
            bot_instance = self._bot_instances[instance.name]
            
            # Get additional connection info
            channel_data = {
                "invite_url": bot_instance.invite_url,
                "error_message": bot_instance.error_message
            }
            
            # Add bot-specific data if connected
            if bot_instance.status == "connected" and bot_instance.client.user:
                channel_data.update({
                    "bot_username": str(bot_instance.client.user),
                    "bot_id": bot_instance.client.user.id,
                    "guild_count": len(bot_instance.client.guilds),
                    "guilds": [{"id": guild.id, "name": guild.name} for guild in bot_instance.client.guilds]
                })
            return ConnectionStatus(
                instance_name=instance.name,
                channel_type="discord",
                status=bot_instance.status,
                channel_data=channel_data
            )
        except Exception as e:
            logger.error(f"Failed to get Discord bot status: {e}")
            return ConnectionStatus(
                instance_name=instance.name,
                channel_type="discord",
                status="error",
                channel_data={"error": str(e)}
            )
    async def restart_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Restart Discord bot connection."""
        try:
            logger.info(f"Restarting Discord bot instance '{instance.name}'...")
            
            # Clean up existing instance
            if instance.name in self._bot_instances:
                await self._cleanup_bot_instance(instance.name)
            
            # Create new instance
            result = await self.create_instance(instance)
            
            if "error" not in result:
                logger.info(f"Discord bot instance '{instance.name}' restarted successfully")
                result["status"] = "restarted"
                result["message"] = f"Discord bot instance '{instance.name}' restarted successfully"
            
            return result
        except Exception as e:
            logger.error(f"Failed to restart Discord bot instance: {e}")
            return {"error": str(e), "status": "restart_failed"}
    async def logout_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Logout/disconnect Discord bot."""
        try:
            logger.info(f"Logging out Discord bot instance '{instance.name}'...")
            
            if instance.name not in self._bot_instances:
                return {
                    "instance_name": instance.name,
                    "status": "not_found",
                    "message": f"Discord bot instance '{instance.name}' not found"
                }
            await self._cleanup_bot_instance(instance.name)
            
            logger.info(f"Discord bot instance '{instance.name}' logged out successfully")
            return {
                "instance_name": instance.name,
                "status": "logged_out",
                "message": f"Discord bot instance '{instance.name}' logged out successfully"
            }
        except Exception as e:
            logger.error(f"Failed to logout Discord bot instance: {e}")
            return {"error": str(e), "status": "logout_failed"}
    async def delete_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Delete Discord bot instance."""
        try:
            logger.info(f"Deleting Discord bot instance '{instance.name}'...")
            
            if instance.name not in self._bot_instances:
                return {
                    "instance_name": instance.name,
                    "status": "not_found",
                    "message": f"Discord bot instance '{instance.name}' not found"
                }
            await self._cleanup_bot_instance(instance.name)
            
            logger.info(f"Discord bot instance '{instance.name}' deleted successfully")
            return {
                "instance_name": instance.name,
                "status": "deleted", 
                "message": f"Discord bot instance '{instance.name}' deleted successfully"
            }
        except Exception as e:
            logger.error(f"Failed to delete Discord bot instance: {e}")
            return {"error": str(e), "status": "delete_failed"}
    async def _cleanup_bot_instance(self, instance_name: str) -> None:
        """Clean up Discord bot instance resources."""
        if instance_name not in self._bot_instances:
            return
            
        bot_instance = self._bot_instances[instance_name]
        
        try:
            # Cancel the bot task if it exists
            if bot_instance.task and not bot_instance.task.done():
                bot_instance.task.cancel()
                try:
                    await bot_instance.task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f"Error cancelling bot task for '{instance_name}': {e}")
            
            # Close the Discord client
            if bot_instance.client and not bot_instance.client.is_closed():
                await bot_instance.client.close()
                
        except Exception as e:
            logger.warning(f"Error during cleanup of Discord bot '{instance_name}': {e}")
        finally:
            # Remove from instances dict
            del self._bot_instances[instance_name]
            logger.debug(f"Discord bot instance '{instance_name}' cleaned up")