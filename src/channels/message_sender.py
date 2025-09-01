"""
Channel-agnostic message sender that routes messages to the appropriate channel handler.
"""

import logging
from typing import Optional, Dict, Any
from src.db.models import InstanceConfig
from src.channels.whatsapp.evolution_api_sender import EvolutionApiSender

logger = logging.getLogger(__name__)


class OmniChannelMessageSender:
    """Routes messages to the appropriate channel handler based on instance configuration."""

    def __init__(self, instance_config: InstanceConfig):
        """
        Initialize the message sender with instance configuration.

        Args:
            instance_config: The instance configuration from database
        """
        self.instance_config = instance_config
        self.channel_type = instance_config.channel_type

    async def send_text_message(
        self,
        recipient: str,
        text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a text message through the appropriate channel.

        Args:
            recipient: Recipient identifier (phone for WhatsApp, channel_id for Discord, etc.)
            text: Message text
            **kwargs: Additional channel-specific parameters

        Returns:
            Dict with success status and message_id if available
        """
        try:
            logger.info(f"OmniChannelMessageSender: Sending text via {self.channel_type} to {recipient}")
            if self.channel_type == "whatsapp":
                return await self._send_whatsapp_text(recipient, text, **kwargs)
            elif self.channel_type == "discord":
                logger.info(f"Calling _send_discord_text for instance '{self.instance_config.name}'")
                return await self._send_discord_text(recipient, text, **kwargs)
            else:
                logger.error(f"Unsupported channel type: {self.channel_type}")
                return {"success": False, "error": f"Unsupported channel type: {self.channel_type}"}

        except Exception as e:
            logger.error(f"Failed to send message via {self.channel_type}: {e}")
            return {"success": False, "error": str(e)}

    async def _send_whatsapp_text(self, recipient: str, text: str, **kwargs) -> Dict[str, Any]:
        """Send text message via WhatsApp."""
        try:
            sender = EvolutionApiSender(config_override=self.instance_config)
            success = sender.send_text_message(
                recipient=recipient,
                text=text,
                quoted_message=kwargs.get("quoted_message"),
                mentioned=kwargs.get("mentioned"),
                mentions_everyone=kwargs.get("mentions_everyone", False),
                auto_parse_mentions=kwargs.get("auto_parse_mentions", True)
            )
            return {"success": success, "channel": "whatsapp"}
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return {"success": False, "error": str(e), "channel": "whatsapp"}

    async def _send_discord_text(self, recipient: str, text: str, **kwargs) -> Dict[str, Any]:
        """Send text message via Discord using Unix domain socket IPC."""
        logger.info(f"_send_discord_text called: recipient={recipient}, text_length={len(text)}")
        import aiohttp
        import os
        from src.ipc_config import IPCConfig

        try:
            # Parse Discord mentions in the text
            # Convert @username or @userid to <@userid> format
            text = self._parse_discord_mentions(text)
            # Parse the channel ID
            try:
                channel_id = int(recipient)
            except ValueError:
                # Try to use default channel from instance config
                default_channel = self.instance_config.discord_default_channel_id
                if default_channel:
                    channel_id = int(default_channel)
                else:
                    return {"success": False, "error": "Invalid Discord channel ID", "channel": "discord"}

            # Get socket path using centralized configuration
            socket_path = IPCConfig.get_socket_path('discord', self.instance_config.name)

            # Check if socket exists (bot is running)
            if not os.path.exists(socket_path):
                logger.error(f"Discord bot not running for instance '{self.instance_config.name}' (socket not found: {socket_path})")
                return {"success": False, "error": "Discord bot not running", "channel": "discord"}

            # Connect via Unix domain socket
            connector = aiohttp.UnixConnector(path=socket_path)
            timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                try:
                    # Send request to bot's Unix socket server
                    async with session.post(
                        'http://localhost/send',  # URL path (domain ignored for Unix sockets)
                        json={'channel_id': str(channel_id), 'text': text}
                    ) as response:
                        result = await response.json()
                        logger.info(f"Discord IPC response: status={response.status}, result={result}")

                        if response.status == 200:
                            logger.info(f"Message sent via Discord bot '{self.instance_config.name}' to channel {channel_id}")
                            return {
                                "success": result.get('success', False),
                                "channel": "discord",
                                "instance": self.instance_config.name,
                                "channel_id": channel_id
                            }
                        else:
                            error_msg = result.get('error', 'Unknown error')
                            logger.error(f"Discord IPC error: {error_msg}")
                            return {"success": False, "error": error_msg, "channel": "discord"}

                except asyncio.TimeoutError:
                    logger.error(f"Timeout connecting to Discord bot '{self.instance_config.name}' via Unix socket")
                    return {"success": False, "error": "Bot not responding (timeout)", "channel": "discord"}
                except aiohttp.ClientError as e:
                    logger.error(f"Connection error to Discord bot Unix socket: {e}")
                    return {"success": False, "error": f"Connection error: {e}", "channel": "discord"}

        except Exception as e:
            logger.error(f"Discord send failed: {e}")
            return {"success": False, "error": str(e), "channel": "discord"}

    def _parse_discord_mentions(self, text: str) -> str:
        """
        Parse Discord mentions in text.
        Keeps @userid format as-is since Discord handles it properly.

        Examples:
            @230869302276784128 -> @230869302276784128 (Discord handles this)
            @cezar -> @cezar (would need user lookup for ID)

        Args:
            text: Message text with potential mentions

        Returns:
            Text with mentions (Discord will auto-parse them)
        """
        import re

        # For now, just log if we find username mentions that might need lookup
        # Discord will handle @userid mentions automatically
        username_pattern = r'@([a-zA-Z][a-zA-Z0-9_\.]{0,31})(?!\d)'  # Discord username pattern
        usernames = re.findall(username_pattern, text)
        if usernames:
            logger.info(f"Found username mentions that would need lookup: {usernames}")
            # In the future, we could lookup these usernames to get their IDs
            # For now, they'll be sent as plain text

        # Return text as-is, Discord handles @userid mentions automatically
        return text

    async def send_media_message(
        self,
        recipient: str,
        media_url: Optional[str] = None,
        media_base64: Optional[str] = None,
        caption: Optional[str] = None,
        media_type: str = "image",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a media message through the appropriate channel.

        Args:
            recipient: Recipient identifier
            media_url: URL of the media file
            media_base64: Base64 encoded media
            caption: Optional caption
            media_type: Type of media (image, video, document, audio)
            **kwargs: Additional channel-specific parameters

        Returns:
            Dict with success status and message_id if available
        """
        try:
            if self.channel_type == "whatsapp":
                return await self._send_whatsapp_media(
                    recipient, media_url, media_base64, caption, media_type, **kwargs
                )
            elif self.channel_type == "discord":
                return await self._send_discord_media(
                    recipient, media_url, media_base64, caption, media_type, **kwargs
                )
            else:
                logger.error(f"Unsupported channel type: {self.channel_type}")
                return {"success": False, "error": f"Unsupported channel type: {self.channel_type}"}

        except Exception as e:
            logger.error(f"Failed to send media via {self.channel_type}: {e}")
            return {"success": False, "error": str(e)}

    async def _send_whatsapp_media(
        self,
        recipient: str,
        media_url: Optional[str],
        media_base64: Optional[str],
        caption: Optional[str],
        media_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Send media message via WhatsApp."""
        try:
            sender = EvolutionApiSender(config_override=self.instance_config)
            media_source = media_url if media_url else media_base64

            success = sender.send_media_message(
                recipient=recipient,
                media_url=media_source,
                caption=caption,
                media_type=media_type
            )
            return {"success": success, "channel": "whatsapp"}
        except Exception as e:
            logger.error(f"WhatsApp media send failed: {e}")
            return {"success": False, "error": str(e), "channel": "whatsapp"}

    async def _send_discord_media(
        self,
        recipient: str,
        media_url: Optional[str],
        media_base64: Optional[str],
        caption: Optional[str],
        media_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Send media message via Discord (as attachment with optional text)."""
        try:
            from src.channels.discord.bot_manager import BotManager
            import aiohttp
            import io
            import base64

            bot_manager = BotManager()

            # Ensure bot is connected
            if not await bot_manager.is_connected(self.instance_config.name):
                success = await bot_manager.start_bot(self.instance_config)
                if not success:
                    return {"success": False, "error": "Failed to start Discord bot", "channel": "discord"}

            # Parse channel ID
            try:
                channel_id = int(recipient)
            except ValueError:
                if self.instance_config.discord_default_channel_id:
                    channel_id = int(self.instance_config.discord_default_channel_id)
                else:
                    return {"success": False, "error": "Invalid Discord channel ID", "channel": "discord"}

            # Prepare attachment
            attachments = []
            if media_url:
                # Download media from URL
                async with aiohttp.ClientSession() as session:
                    async with session.get(media_url) as response:
                        if response.status == 200:
                            media_data = await response.read()
                            filename = media_url.split("/")[-1] or f"media.{media_type}"
                            attachments.append((filename, io.BytesIO(media_data)))
            elif media_base64:
                # Decode base64 media
                media_data = base64.b64decode(media_base64)
                filename = f"media.{media_type}"
                attachments.append((filename, io.BytesIO(media_data)))

            # Send message with attachment
            success = await bot_manager.send_message(
                instance_name=self.instance_config.name,
                channel_id=channel_id,
                content=caption or "",
                attachments=attachments
            )

            return {"success": success, "channel": "discord"}

        except ImportError as e:
            logger.error(f"Discord dependencies not installed: {e}")
            return {"success": False, "error": "Discord dependencies not installed", "channel": "discord"}
        except Exception as e:
            logger.error(f"Discord media send failed: {e}")
            return {"success": False, "error": str(e), "channel": "discord"}

    async def send_audio_message(
        self,
        recipient: str,
        audio: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Send an audio message through the appropriate channel."""
        try:
            logger.info(f"OmniChannelMessageSender: Sending audio via {self.channel_type} to {recipient}")
            if self.channel_type == "whatsapp":
                sender = EvolutionApiSender(config_override=self.instance_config)
                success = sender.send_audio_message(recipient=recipient, audio=audio)
                return {"success": success, "channel": "whatsapp"}
            elif self.channel_type == "discord":
                logger.warning(f"Audio messages not directly supported on Discord for instance '{self.instance_config.name}' - use media message instead")
                return {"success": False, "error": "Audio messages not supported on Discord - use media message with audio file", "channel": "discord"}
            else:
                logger.error(f"Unsupported channel type: {self.channel_type}")
                return {"success": False, "error": f"Unsupported channel type: {self.channel_type}"}
        except Exception as e:
            logger.error(f"Failed to send audio message via {self.channel_type}: {e}")
            return {"success": False, "error": str(e)}

    async def send_sticker_message(
        self,
        recipient: str,
        sticker: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a sticker message through the appropriate channel."""
        try:
            logger.info(f"OmniChannelMessageSender: Sending sticker via {self.channel_type} to {recipient}")
            if self.channel_type == "whatsapp":
                sender = EvolutionApiSender(config_override=self.instance_config)
                success = sender.send_sticker_message(recipient=recipient, sticker=sticker)
                return {"success": success, "channel": "whatsapp"}
            elif self.channel_type == "discord":
                logger.warning(f"Sticker messages not supported on Discord for instance '{self.instance_config.name}' - use emojis or media instead")
                return {"success": False, "error": "Sticker messages not supported on Discord - use emojis or media message", "channel": "discord"}
            else:
                logger.error(f"Unsupported channel type: {self.channel_type}")
                return {"success": False, "error": f"Unsupported channel type: {self.channel_type}"}
        except Exception as e:
            logger.error(f"Failed to send sticker message via {self.channel_type}: {e}")
            return {"success": False, "error": str(e)}

    async def send_contact_message(
        self,
        recipient: str,
        contacts: list,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a contact message through the appropriate channel."""
        try:
            logger.info(f"OmniChannelMessageSender: Sending contacts via {self.channel_type} to {recipient}")
            if self.channel_type == "whatsapp":
                sender = EvolutionApiSender(config_override=self.instance_config)
                success = sender.send_contact_message(recipient=recipient, contacts=contacts)
                return {"success": success, "channel": "whatsapp"}
            elif self.channel_type == "discord":
                logger.warning(f"Contact messages not supported on Discord for instance '{self.instance_config.name}' - send as text instead")
                return {"success": False, "error": "Contact messages not supported on Discord - send contact info as text message", "channel": "discord"}
            else:
                logger.error(f"Unsupported channel type: {self.channel_type}")
                return {"success": False, "error": f"Unsupported channel type: {self.channel_type}"}
        except Exception as e:
            logger.error(f"Failed to send contact message via {self.channel_type}: {e}")
            return {"success": False, "error": str(e)}

    async def send_reaction_message(
        self,
        recipient: str,
        message_id: str,
        emoji: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a reaction to a message through the appropriate channel."""
        try:
            logger.info(f"OmniChannelMessageSender: Sending reaction via {self.channel_type} to {recipient}")
            if self.channel_type == "whatsapp":
                sender = EvolutionApiSender(config_override=self.instance_config)
                success = sender.send_reaction_message(recipient=recipient, message_id=message_id, emoji=emoji)
                return {"success": success, "channel": "whatsapp"}
            elif self.channel_type == "discord":
                logger.warning(f"Direct message reactions not supported on Discord for instance '{self.instance_config.name}' - reactions work on server messages")
                return {"success": False, "error": "Direct message reactions not supported on Discord - reactions only work on server messages", "channel": "discord"}
            else:
                logger.error(f"Unsupported channel type: {self.channel_type}")
                return {"success": False, "error": f"Unsupported channel type: {self.channel_type}"}
        except Exception as e:
            logger.error(f"Failed to send reaction via {self.channel_type}: {e}")
            return {"success": False, "error": str(e)}

    def fetch_profile(self, recipient: str) -> Optional[Dict[str, Any]]:
        """Fetch user profile information through the appropriate channel."""
        try:
            logger.info(f"OmniChannelMessageSender: Fetching profile via {self.channel_type} for {recipient}")
            if self.channel_type == "whatsapp":
                sender = EvolutionApiSender(config_override=self.instance_config)
                return sender.fetch_profile(phone_number=recipient)
            elif self.channel_type == "discord":
                logger.warning(f"Profile fetching not supported on Discord for instance '{self.instance_config.name}'")
                return None
            else:
                logger.error(f"Unsupported channel type: {self.channel_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to fetch profile via {self.channel_type}: {e}")
            return None

    def update_profile_picture(self, picture_url: str) -> bool:
        """Update profile picture through the appropriate channel."""
        try:
            logger.info(f"OmniChannelMessageSender: Updating profile picture via {self.channel_type}")
            if self.channel_type == "whatsapp":
                sender = EvolutionApiSender(config_override=self.instance_config)
                return sender.update_profile_picture(picture_url=picture_url)
            elif self.channel_type == "discord":
                logger.warning(f"Profile picture updates not supported on Discord for instance '{self.instance_config.name}'")
                return False
            else:
                logger.error(f"Unsupported channel type: {self.channel_type}")
                return False
        except Exception as e:
            logger.error(f"Failed to update profile picture via {self.channel_type}: {e}")
            return False
