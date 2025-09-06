"""
Discord Webhook Notifier

Simple webhook-only notifications for Discord channels.
No bot needed, just webhook URLs for sending messages.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EmbedColor(Enum):
    """Standard embed colors for different notification types."""

    SUCCESS = 0x00FF00  # Green
    INFO = 0x0099FF  # Blue
    WARNING = 0xFFCC00  # Orange
    ERROR = 0xFF0000  # Red
    SYSTEM = 0x9932CC  # Purple


class EmbedField(BaseModel):
    """Represents an embed field."""

    name: str
    value: str
    inline: bool = False


class DiscordEmbed(BaseModel):
    """Represents a Discord embed."""

    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[int] = None
    url: Optional[str] = None
    timestamp: Optional[str] = None
    footer: Optional[Dict[str, str]] = None
    author: Optional[Dict[str, str]] = None
    thumbnail: Optional[Dict[str, str]] = None
    image: Optional[Dict[str, str]] = None
    fields: List[EmbedField] = Field(default_factory=list)

    def add_field(self, name: str, value: str, inline: bool = False) -> "DiscordEmbed":
        """Add a field to the embed."""
        self.fields.append(EmbedField(name=name, value=value, inline=inline))
        return self

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> "DiscordEmbed":
        """Set the footer of the embed."""
        self.footer = {"text": text}
        if icon_url:
            self.footer["icon_url"] = icon_url
        return self

    def set_author(
        self, name: str, url: Optional[str] = None, icon_url: Optional[str] = None
    ) -> "DiscordEmbed":
        """Set the author of the embed."""
        self.author = {"name": name}
        if url:
            self.author["url"] = url
        if icon_url:
            self.author["icon_url"] = icon_url
        return self

    def set_thumbnail(self, url: str) -> "DiscordEmbed":
        """Set the thumbnail of the embed."""
        self.thumbnail = {"url": url}
        return self

    def set_image(self, url: str) -> "DiscordEmbed":
        """Set the image of the embed."""
        self.image = {"url": url}
        return self

    def set_timestamp(self, timestamp: Optional[datetime] = None) -> "DiscordEmbed":
        """Set the timestamp of the embed."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        self.timestamp = timestamp.isoformat()
        return self


class WebhookMessage(BaseModel):
    """Represents a webhook message payload."""

    content: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    tts: bool = False
    embeds: List[DiscordEmbed] = Field(default_factory=list)
    allowed_mentions: Optional[Dict[str, Any]] = None

    def add_embed(self, embed: DiscordEmbed) -> "WebhookMessage":
        """Add an embed to the message."""
        self.embeds.append(embed)
        return self


class DiscordWebhookNotifier:
    """
    Discord Webhook Notifier for sending messages to Discord channels.

    Features:
    - Send text messages and rich embeds
    - Error notifications with stack traces
    - System status updates
    - Custom formatting and colors
    """

    def __init__(
        self,
        webhook_url: str,
        default_username: Optional[str] = None,
        default_avatar_url: Optional[str] = None,
    ):
        """
        Initialize the webhook notifier.

        Args:
            webhook_url: The Discord webhook URL
            default_username: Default username for messages
            default_avatar_url: Default avatar URL for messages
        """
        self.webhook_url = webhook_url
        self.default_username = default_username or "Automagik Omni"
        self.default_avatar_url = default_avatar_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def send_message(self, message: WebhookMessage) -> bool:
        """
        Send a message via webhook.

        Args:
            message: The message to send

        Returns:
            True if successful, False otherwise
        """
        try:
            # Set defaults if not provided
            if message.username is None:
                message.username = self.default_username
            if message.avatar_url is None:
                message.avatar_url = self.default_avatar_url

            # Prepare payload
            payload = message.model_dump(exclude_none=True)

            # Convert embeds to dict format
            if payload.get("embeds"):
                payload["embeds"] = [
                    embed.model_dump(exclude_none=True) for embed in message.embeds
                ]

            # Send the message
            response = await self.client.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in [200, 204]:
                logger.info("Successfully sent Discord webhook message")
                return True
            else:
                logger.error(
                    f"Failed to send Discord webhook: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending Discord webhook: {e}")
            return False

    async def send_text(self, content: str, username: Optional[str] = None) -> bool:
        """
        Send a simple text message.

        Args:
            content: The message content
            username: Optional custom username

        Returns:
            True if successful, False otherwise
        """
        message = WebhookMessage(content=content, username=username)
        return await self.send_message(message)

    async def send_embed(
        self, embed: DiscordEmbed, content: Optional[str] = None
    ) -> bool:
        """
        Send an embed message.

        Args:
            embed: The embed to send
            content: Optional text content

        Returns:
            True if successful, False otherwise
        """
        message = WebhookMessage(content=content)
        message.add_embed(embed)
        return await self.send_message(message)

    async def send_error_notification(
        self,
        error_title: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        instance_id: Optional[str] = None,
    ) -> bool:
        """
        Send an error notification with formatted embed.

        Args:
            error_title: Title of the error
            error_message: Error message description
            stack_trace: Optional stack trace
            instance_id: Optional instance identifier

        Returns:
            True if successful, False otherwise
        """
        embed = DiscordEmbed(
            title="🚨 Error Alert",
            description=error_title,
            color=EmbedColor.ERROR.value,
        )

        embed.add_field("Error Message", error_message, inline=False)

        if instance_id:
            embed.add_field("Instance ID", instance_id, inline=True)

        if stack_trace:
            # Truncate long stack traces
            truncated_trace = (
                stack_trace[:1000] + "..." if len(stack_trace) > 1000 else stack_trace
            )
            embed.add_field("Stack Trace", f"```\n{truncated_trace}\n```", inline=False)

        embed.set_timestamp()
        embed.set_footer("Automagik Omni Error System")

        return await self.send_embed(embed)

    async def send_system_status(
        self, status: str, details: Dict[str, Any], status_type: str = "info"
    ) -> bool:
        """
        Send a system status update.

        Args:
            status: Status message
            details: Dictionary of status details
            status_type: Type of status (info, warning, error, success)

        Returns:
            True if successful, False otherwise
        """
        color_map = {
            "info": EmbedColor.INFO.value,
            "warning": EmbedColor.WARNING.value,
            "error": EmbedColor.ERROR.value,
            "success": EmbedColor.SUCCESS.value,
            "system": EmbedColor.SYSTEM.value,
        }

        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🚨",
            "success": "✅",
            "system": "🔧",
        }

        embed = DiscordEmbed(
            title=f"{icon_map.get(status_type, '📊')} System Status",
            description=status,
            color=color_map.get(status_type, EmbedColor.INFO.value),
        )

        # Add detail fields
        for key, value in details.items():
            embed.add_field(
                key.replace("_", " ").title(), str(value), inline=len(str(value)) < 50
            )

        embed.set_timestamp()
        embed.set_footer("Automagik Omni System Monitor")

        return await self.send_embed(embed)

    async def send_user_activity(
        self, user_id: str, action: str, details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send user activity notification.

        Args:
            user_id: User identifier
            action: Action performed
            details: Optional additional details

        Returns:
            True if successful, False otherwise
        """
        embed = DiscordEmbed(
            title="👤 User Activity",
            description=f"User `{user_id}` performed action: **{action}**",
            color=EmbedColor.INFO.value,
        )

        if details:
            for key, value in details.items():
                embed.add_field(key.replace("_", " ").title(), str(value), inline=True)

        embed.set_timestamp()
        embed.set_footer("Automagik Omni Activity Monitor")

        return await self.send_embed(embed)

    async def send_custom_notification(
        self,
        title: str,
        message: str,
        color: Optional[int] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Send a custom notification with flexible formatting.

        Args:
            title: Notification title
            message: Notification message
            color: Optional embed color
            fields: Optional list of fields to add

        Returns:
            True if successful, False otherwise
        """
        embed = DiscordEmbed(
            title=title, description=message, color=color or EmbedColor.INFO.value
        )

        if fields:
            for field in fields:
                embed.add_field(
                    field.get("name", "Field"),
                    field.get("value", "Value"),
                    field.get("inline", False),
                )

        embed.set_timestamp()

        return await self.send_embed(embed)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Utility functions for quick webhook usage
async def send_quick_notification(
    webhook_url: str,
    message: str,
    title: Optional[str] = None,
    color: Optional[int] = None,
) -> bool:
    """
    Quick utility function to send a notification.

    Args:
        webhook_url: Discord webhook URL
        message: Message content
        title: Optional embed title
        color: Optional embed color

    Returns:
        True if successful, False otherwise
    """
    async with DiscordWebhookNotifier(webhook_url) as notifier:
        if title:
            embed = DiscordEmbed(
                title=title, description=message, color=color or EmbedColor.INFO.value
            )
            embed.set_timestamp()
            return await notifier.send_embed(embed)
        else:
            return await notifier.send_text(message)


async def send_error_alert(
    webhook_url: str,
    error_title: str,
    error_message: str,
    instance_id: Optional[str] = None,
) -> bool:
    """
    Quick utility function to send an error alert.

    Args:
        webhook_url: Discord webhook URL
        error_title: Error title
        error_message: Error description
        instance_id: Optional instance identifier

    Returns:
        True if successful, False otherwise
    """
    async with DiscordWebhookNotifier(webhook_url) as notifier:
        return await notifier.send_error_notification(
            error_title, error_message, instance_id=instance_id
        )
