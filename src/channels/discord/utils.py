"""
Discord Utilities

Collection of utility functions for Discord bot operations including
permission calculations, invite URL generation, ID validation, embed builders,
and format converters.
"""
import re
import json
import logging
from typing import List, Dict, Optional, Union, Any
from urllib.parse import urlencode
from datetime import datetime
from enum import IntFlag

logger = logging.getLogger(__name__)


# Discord Permission Constants (from Discord API)
class DiscordPermissions(IntFlag):
    """Discord permission flags as defined in the Discord API."""
    CREATE_INSTANT_INVITE = 1 << 0
    KICK_MEMBERS = 1 << 1
    BAN_MEMBERS = 1 << 2
    ADMINISTRATOR = 1 << 3
    MANAGE_CHANNELS = 1 << 4
    MANAGE_GUILD = 1 << 5
    ADD_REACTIONS = 1 << 6
    VIEW_AUDIT_LOG = 1 << 7
    PRIORITY_SPEAKER = 1 << 8
    STREAM = 1 << 9
    VIEW_CHANNEL = 1 << 10
    SEND_MESSAGES = 1 << 11
    SEND_TTS_MESSAGES = 1 << 12
    MANAGE_MESSAGES = 1 << 13
    EMBED_LINKS = 1 << 14
    ATTACH_FILES = 1 << 15
    READ_MESSAGE_HISTORY = 1 << 16
    MENTION_EVERYONE = 1 << 17
    USE_EXTERNAL_EMOJIS = 1 << 18
    VIEW_GUILD_INSIGHTS = 1 << 19
    CONNECT = 1 << 20
    SPEAK = 1 << 21
    MUTE_MEMBERS = 1 << 22
    DEAFEN_MEMBERS = 1 << 23
    MOVE_MEMBERS = 1 << 24
    USE_VAD = 1 << 25
    CHANGE_NICKNAME = 1 << 26
    MANAGE_NICKNAMES = 1 << 27
    MANAGE_ROLES = 1 << 28
    MANAGE_WEBHOOKS = 1 << 29
    MANAGE_EMOJIS_AND_STICKERS = 1 << 30
    USE_SLASH_COMMANDS = 1 << 31
    REQUEST_TO_SPEAK = 1 << 32
    MANAGE_EVENTS = 1 << 33
    MANAGE_THREADS = 1 << 34
    CREATE_PUBLIC_THREADS = 1 << 35
    CREATE_PRIVATE_THREADS = 1 << 36
    USE_EXTERNAL_STICKERS = 1 << 37
    SEND_MESSAGES_IN_THREADS = 1 << 38
    USE_EMBEDDED_ACTIVITIES = 1 << 39
    MODERATE_MEMBERS = 1 << 40


# Predefined permission sets
PERMISSION_PRESETS = {
    "minimal": [
        DiscordPermissions.VIEW_CHANNEL,
        DiscordPermissions.SEND_MESSAGES,
        DiscordPermissions.EMBED_LINKS
    ],
    "basic_bot": [
        DiscordPermissions.VIEW_CHANNEL,
        DiscordPermissions.SEND_MESSAGES,
        DiscordPermissions.READ_MESSAGE_HISTORY,
        DiscordPermissions.EMBED_LINKS,
        DiscordPermissions.ATTACH_FILES,
        DiscordPermissions.USE_SLASH_COMMANDS
    ],
    "advanced_bot": [
        DiscordPermissions.VIEW_CHANNEL,
        DiscordPermissions.SEND_MESSAGES,
        DiscordPermissions.READ_MESSAGE_HISTORY,
        DiscordPermissions.EMBED_LINKS,
        DiscordPermissions.ATTACH_FILES,
        DiscordPermissions.USE_SLASH_COMMANDS,
        DiscordPermissions.MANAGE_MESSAGES,
        DiscordPermissions.CONNECT,
        DiscordPermissions.SPEAK
    ],
    "moderation_bot": [
        DiscordPermissions.VIEW_CHANNEL,
        DiscordPermissions.SEND_MESSAGES,
        DiscordPermissions.READ_MESSAGE_HISTORY,
        DiscordPermissions.EMBED_LINKS,
        DiscordPermissions.ATTACH_FILES,
        DiscordPermissions.USE_SLASH_COMMANDS,
        DiscordPermissions.MANAGE_MESSAGES,
        DiscordPermissions.KICK_MEMBERS,
        DiscordPermissions.BAN_MEMBERS,
        DiscordPermissions.MANAGE_ROLES
    ],
    "administrator": [
        DiscordPermissions.ADMINISTRATOR
    ]
}


class PermissionCalculator:
    """Calculate Discord permissions and generate permission integers."""

    @staticmethod
    def calculate_permissions(permissions: List[Union[str, DiscordPermissions]]) -> int:
        """
        Calculate the permission integer from a list of permissions.

        Args:
            permissions: List of permission names or DiscordPermissions flags

        Returns:
            Integer representing the combined permissions
        """
        total = 0

        for perm in permissions:
            if isinstance(perm, str):
                # Convert string to DiscordPermissions enum
                perm_name = perm.upper()
                if hasattr(DiscordPermissions, perm_name):
                    perm_value = getattr(DiscordPermissions, perm_name)
                    total |= perm_value
                else:
                    logger.warning(f"Unknown permission: {perm}")
            elif isinstance(perm, DiscordPermissions):
                total |= perm
            elif isinstance(perm, int):
                total |= perm

        return total

    @staticmethod
    def get_preset_permissions(preset_name: str) -> int:
        """
        Get permissions integer for a predefined preset.

        Args:
            preset_name: Name of the permission preset

        Returns:
            Integer representing the preset permissions
        """
        if preset_name in PERMISSION_PRESETS:
            return PermissionCalculator.calculate_permissions(PERMISSION_PRESETS[preset_name])
        else:
            logger.error(f"Unknown permission preset: {preset_name}")
            return 0

    @staticmethod
    def permissions_to_list(permission_int: int) -> List[str]:
        """
        Convert a permission integer to a list of permission names.

        Args:
            permission_int: Integer representing permissions

        Returns:
            List of permission names
        """
        permissions = []

        for perm in DiscordPermissions:
            if permission_int & perm:
                permissions.append(perm.name)

        return permissions

    @staticmethod
    def has_permission(permission_int: int, check_permission: Union[str, DiscordPermissions]) -> bool:
        """
        Check if a permission integer includes a specific permission.

        Args:
            permission_int: Integer representing permissions
            check_permission: Permission to check for

        Returns:
            True if permission is included
        """
        if isinstance(check_permission, str):
            check_permission = getattr(DiscordPermissions, check_permission.upper(), 0)

        return bool(permission_int & check_permission)


class InviteURLGenerator:
    """Generate Discord bot invite URLs with proper permissions and scopes."""

    @staticmethod
    def generate_invite_url(client_id: str, permissions: Union[int, List[str], str] = 0,
                          scopes: List[str] = None, guild_id: Optional[str] = None) -> str:
        """
        Generate a Discord bot invite URL.

        Args:
            client_id: Discord application client ID
            permissions: Permissions as integer, list of names, or preset name
            scopes: OAuth2 scopes (default: ["bot", "applications.commands"])
            guild_id: Optional guild ID to pre-select server

        Returns:
            Complete Discord invite URL
        """
        if scopes is None:
            scopes = ["bot", "applications.commands"]

        # Handle different permission formats
        if isinstance(permissions, str):
            # Preset name
            perm_int = PermissionCalculator.get_preset_permissions(permissions)
        elif isinstance(permissions, list):
            # List of permission names
            perm_int = PermissionCalculator.calculate_permissions(permissions)
        else:
            # Already an integer
            perm_int = permissions

        # Build URL parameters
        params = {
            "client_id": client_id,
            "permissions": str(perm_int),
            "scope": "%20".join(scopes)
        }

        if guild_id:
            params["guild_id"] = guild_id

        base_url = "https://discord.com/api/oauth2/authorize"
        query_string = urlencode(params, safe="%20")

        return f"{base_url}?{query_string}"

    @staticmethod
    def generate_preset_urls(client_id: str, guild_id: Optional[str] = None) -> Dict[str, str]:
        """
        Generate invite URLs for all permission presets.

        Args:
            client_id: Discord application client ID
            guild_id: Optional guild ID

        Returns:
            Dictionary mapping preset names to invite URLs
        """
        urls = {}

        for preset_name in PERMISSION_PRESETS.keys():
            urls[preset_name] = InviteURLGenerator.generate_invite_url(
                client_id, preset_name, guild_id=guild_id
            )

        return urls


class DiscordIDValidator:
    """Validate Discord IDs (snowflakes) and related identifiers."""

    SNOWFLAKE_PATTERN = re.compile(r'^[0-9]{15,21}$')
    WEBHOOK_URL_PATTERN = re.compile(
        r'^https://discord\.com/api/webhooks/([0-9]+)/([A-Za-z0-9\-_]+)/?$'
    )

    @staticmethod
    def is_valid_snowflake(snowflake: str) -> bool:
        """
        Validate a Discord snowflake ID.

        Args:
            snowflake: String to validate

        Returns:
            True if valid snowflake
        """
        return bool(DiscordIDValidator.SNOWFLAKE_PATTERN.match(str(snowflake)))

    @staticmethod
    def is_valid_webhook_url(webhook_url: str) -> bool:
        """
        Validate a Discord webhook URL.

        Args:
            webhook_url: URL to validate

        Returns:
            True if valid webhook URL
        """
        return bool(DiscordIDValidator.WEBHOOK_URL_PATTERN.match(webhook_url))

    @staticmethod
    def extract_webhook_info(webhook_url: str) -> Optional[Dict[str, str]]:
        """
        Extract webhook ID and token from a webhook URL.

        Args:
            webhook_url: Discord webhook URL

        Returns:
            Dictionary with webhook_id and webhook_token, or None if invalid
        """
        match = DiscordIDValidator.WEBHOOK_URL_PATTERN.match(webhook_url)
        if match:
            return {
                "webhook_id": match.group(1),
                "webhook_token": match.group(2)
            }
        return None

    @staticmethod
    def validate_ids(config: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate all Discord IDs in a configuration dictionary.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Dictionary with 'valid' and 'invalid' lists
        """
        results = {"valid": [], "invalid": []}

        id_fields = ["client_id", "guild_id", "channel_id", "user_id", "role_id"]

        for field in id_fields:
            if field in config:
                value = str(config[field])
                if DiscordIDValidator.is_valid_snowflake(value):
                    results["valid"].append(f"{field}: {value}")
                else:
                    results["invalid"].append(f"{field}: {value}")

        # Check webhook URLs
        webhook_fields = ["webhook_url", "notification_webhook", "error_webhook"]
        for field in webhook_fields:
            if field in config:
                url = config[field]
                if DiscordIDValidator.is_valid_webhook_url(url):
                    results["valid"].append(f"{field}: {url}")
                else:
                    results["invalid"].append(f"{field}: {url}")

        return results


class EmbedBuilder:
    """Build Discord embeds with fluent interface."""

    def __init__(self):
        """Initialize embed builder."""
        self.embed_data = {
            "type": "rich"
        }

    def title(self, title: str) -> 'EmbedBuilder':
        """Set embed title."""
        self.embed_data["title"] = title
        return self

    def description(self, description: str) -> 'EmbedBuilder':
        """Set embed description."""
        self.embed_data["description"] = description
        return self

    def color(self, color: Union[int, str]) -> 'EmbedBuilder':
        """Set embed color."""
        if isinstance(color, str):
            # Convert hex string to int
            if color.startswith("#"):
                color = color[1:]
            color = int(color, 16)
        self.embed_data["color"] = color
        return self

    def url(self, url: str) -> 'EmbedBuilder':
        """Set embed URL."""
        self.embed_data["url"] = url
        return self

    def timestamp(self, timestamp: Optional[datetime] = None) -> 'EmbedBuilder':
        """Set embed timestamp."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        self.embed_data["timestamp"] = timestamp.isoformat()
        return self

    def footer(self, text: str, icon_url: Optional[str] = None) -> 'EmbedBuilder':
        """Set embed footer."""
        self.embed_data["footer"] = {"text": text}
        if icon_url:
            self.embed_data["footer"]["icon_url"] = icon_url
        return self

    def author(self, name: str, url: Optional[str] = None, icon_url: Optional[str] = None) -> 'EmbedBuilder':
        """Set embed author."""
        self.embed_data["author"] = {"name": name}
        if url:
            self.embed_data["author"]["url"] = url
        if icon_url:
            self.embed_data["author"]["icon_url"] = icon_url
        return self

    def thumbnail(self, url: str) -> 'EmbedBuilder':
        """Set embed thumbnail."""
        self.embed_data["thumbnail"] = {"url": url}
        return self

    def image(self, url: str) -> 'EmbedBuilder':
        """Set embed image."""
        self.embed_data["image"] = {"url": url}
        return self

    def add_field(self, name: str, value: str, inline: bool = False) -> 'EmbedBuilder':
        """Add a field to the embed."""
        if "fields" not in self.embed_data:
            self.embed_data["fields"] = []

        self.embed_data["fields"].append({
            "name": name,
            "value": value,
            "inline": inline
        })
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the embed dictionary."""
        return self.embed_data.copy()

    def to_json(self) -> str:
        """Return embed as JSON string."""
        return json.dumps(self.embed_data, indent=2)


class FormatConverter:
    """Convert between different Discord message formats."""

    @staticmethod
    def markdown_to_discord(markdown_text: str) -> str:
        """
        Convert basic markdown to Discord formatting.

        Args:
            markdown_text: Text with markdown formatting

        Returns:
            Text with Discord formatting
        """
        # Discord uses similar markdown, but with some differences
        conversions = [
            (r'\*\*(.*?)\*\*', r'**\1**'),  # Bold (same)
            (r'\*(.*?)\*', r'*\1*'),        # Italic (same)
            (r'`(.*?)`', r'`\1`'),          # Code (same)
            (r'~~(.*?)~~', r'~~\1~~'),      # Strikethrough (same)
            (r'__(.*?)__', r'__\1__'),      # Underline (same)
        ]

        result = markdown_text
        for pattern, replacement in conversions:
            result = re.sub(pattern, replacement, result)

        return result

    @staticmethod
    def escape_discord_formatting(text: str) -> str:
        """
        Escape Discord formatting characters.

        Args:
            text: Text to escape

        Returns:
            Text with escaped formatting
        """
        escape_chars = ['*', '_', '~', '`', '|', '\\']

        for char in escape_chars:
            text = text.replace(char, f'\\{char}')

        return text

    @staticmethod
    def format_code_block(code: str, language: str = "") -> str:
        """
        Format text as Discord code block.

        Args:
            code: Code content
            language: Programming language for syntax highlighting

        Returns:
            Formatted code block
        """
        return f"```{language}\n{code}\n```"

    @staticmethod
    def format_mention(mention_type: str, id_value: str) -> str:
        """
        Format Discord mentions.

        Args:
            mention_type: Type of mention (user, channel, role)
            id_value: ID to mention

        Returns:
            Formatted mention string
        """
        mention_formats = {
            "user": f"<@{id_value}>",
            "channel": f"<#{id_value}>",
            "role": f"<@&{id_value}>"
        }

        return mention_formats.get(mention_type, f"@{id_value}")

    @staticmethod
    def format_timestamp(timestamp: datetime, style: str = "f") -> str:
        """
        Format timestamp for Discord display.

        Args:
            timestamp: Datetime to format
            style: Discord timestamp style (t, T, d, D, f, F, R)

        Returns:
            Formatted timestamp string
        """
        unix_timestamp = int(timestamp.timestamp())
        return f"<t:{unix_timestamp}:{style}>"


# Utility functions for common operations
def create_error_embed(title: str, description: str, error_details: Optional[str] = None) -> Dict[str, Any]:
    """Create a standardized error embed."""
    builder = EmbedBuilder()
    builder.title(f"🚨 {title}")
    builder.description(description)
    builder.color(0xFF0000)  # Red
    builder.timestamp()

    if error_details:
        builder.add_field("Details", error_details, inline=False)

    return builder.build()


def create_success_embed(title: str, description: str) -> Dict[str, Any]:
    """Create a standardized success embed."""
    builder = EmbedBuilder()
    builder.title(f"✅ {title}")
    builder.description(description)
    builder.color(0x00FF00)  # Green
    builder.timestamp()

    return builder.build()


def create_info_embed(title: str, description: str, fields: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Create a standardized info embed."""
    builder = EmbedBuilder()
    builder.title(f"ℹ️ {title}")
    builder.description(description)
    builder.color(0x0099FF)  # Blue
    builder.timestamp()

    if fields:
        for field in fields:
            builder.add_field(
                field.get("name", "Field"),
                field.get("value", "Value"),
                field.get("inline", False)
            )

    return builder.build()


def validate_discord_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a complete Discord configuration.

    Args:
        config: Discord configuration dictionary

    Returns:
        Validation results with status and details
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "details": {}
    }

    # Validate IDs
    id_validation = DiscordIDValidator.validate_ids(config)
    results["details"]["id_validation"] = id_validation

    if id_validation["invalid"]:
        results["valid"] = False
        results["errors"].extend([f"Invalid ID: {item}" for item in id_validation["invalid"]])

    # Check required fields
    required_fields = ["bot_token", "client_id"]
    for field in required_fields:
        if field not in config or not config[field]:
            results["valid"] = False
            results["errors"].append(f"Missing required field: {field}")

    # Check for placeholder values
    placeholder_patterns = ["YOUR_", "PLACEHOLDER", "EXAMPLE", "TEST"]
    for key, value in config.items():
        if isinstance(value, str):
            for pattern in placeholder_patterns:
                if pattern in value.upper():
                    results["warnings"].append(f"Placeholder value detected in {key}: {value}")

    return results
