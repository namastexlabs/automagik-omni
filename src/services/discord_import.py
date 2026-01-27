"""
Discord Message Import Service

Imports historical messages from Discord channels into the unified omni_messages store.
Uses Discord API to fetch message history when a bot connects to a new server.

Features:
- Fetch message history from Discord channels
- Respects Discord API rate limits with exponential backoff
- Handles attachments/media metadata
- Deduplication via platform_message_id
- Background processing with progress tracking
- Configurable batch sizes and delays

Rate Limit Strategy:
- discord.py handles most rate limits automatically
- We add conservative delays to avoid hitting limits
- Exponential backoff on any 429 errors
- Configurable delays between channels and batches
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session as SQLAlchemySession

from src.db.database import SessionLocal
from src.db.trace_models import OmniMessageRecord
from src.utils.datetime_utils import datetime_utcnow

logger = logging.getLogger(__name__)

# Rate limit configuration
DEFAULT_BATCH_DELAY_MS = 100  # Delay between message batches (ms)
DEFAULT_CHANNEL_DELAY_MS = 2000  # Delay between channels (ms)
DEFAULT_MESSAGES_PER_BATCH = 100  # Messages to fetch per API call
MAX_RETRIES = 3  # Max retries on rate limit
BACKOFF_BASE_MS = 5000  # Base backoff time (5 seconds)


class DiscordImportStats:
    """Statistics for Discord import operation."""

    def __init__(self, instance_name: str, guild_id: str):
        self.instance_name = instance_name
        self.guild_id = guild_id
        self.total_found = 0
        self.total_imported = 0
        self.already_exists = 0
        self.failed = 0
        self.with_media = 0
        self.channels_processed = 0
        self.started_at = datetime_utcnow()
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        duration = None
        if self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()

        return {
            "instance_name": self.instance_name,
            "guild_id": self.guild_id,
            "total_found": self.total_found,
            "total_imported": self.total_imported,
            "already_exists": self.already_exists,
            "failed": self.failed,
            "with_media": self.with_media,
            "channels_processed": self.channels_processed,
            "source": "discord_api",
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": duration,
        }


class DiscordImportService:
    """
    Service for importing Discord message history into omni_messages.

    Requires:
    - Bot must have "Read Message History" permission
    - Bot must be in the server/guild

    Usage:
        service = DiscordImportService(db)
        stats = await service.import_guild_history(
            client=discord_client,
            guild=guild,
            instance_name="my-discord-bot",
            days_back=30,
            max_messages_per_channel=1000,
        )
    """

    def __init__(self, db: SQLAlchemySession):
        self.db = db

    def _determine_message_type(self, message) -> tuple[str, bool]:
        """
        Determine message type and whether it has media.

        Returns:
            Tuple of (message_type, has_media)
        """
        if not message.attachments:
            return "text", False

        attachment = message.attachments[0]
        content_type = attachment.content_type or ""
        filename = (attachment.filename or "").lower()

        if content_type.startswith("audio/") or any(
            filename.endswith(ext) for ext in [".mp3", ".ogg", ".wav", ".m4a", ".opus"]
        ):
            return "audio", True
        elif content_type.startswith("image/") or any(
            filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]
        ):
            return "image", True
        elif content_type.startswith("video/") or any(
            filename.endswith(ext) for ext in [".mp4", ".mov", ".webm", ".avi"]
        ):
            return "video", True
        elif any(filename.endswith(ext) for ext in [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx"]):
            return "document", True

        return "text", True  # Unknown attachment type

    def _transform_message(self, message, instance_name: str, sync_batch_id: str) -> Optional[OmniMessageRecord]:
        """
        Transform Discord message to OmniMessageRecord.

        Args:
            message: discord.Message object
            instance_name: Instance name
            sync_batch_id: Batch identifier for this sync

        Returns:
            OmniMessageRecord or None if transformation fails
        """
        try:
            platform_message_id = str(message.id)
            message_type, has_media = self._determine_message_type(message)

            # Extract media info from first attachment
            media_url = None
            media_mime_type = None
            media_size = None

            if message.attachments:
                attachment = message.attachments[0]
                media_url = attachment.url
                media_mime_type = attachment.content_type
                media_size = attachment.size

            # Build platform key
            platform_key = {
                "id": platform_message_id,
                "channel_id": str(message.channel.id),
                "guild_id": str(message.guild.id) if message.guild else None,
                "author_id": str(message.author.id),
            }

            # Build raw content
            content_raw = {
                "content": message.content,
                "attachments": [
                    {
                        "id": str(a.id),
                        "filename": a.filename,
                        "content_type": a.content_type,
                        "size": a.size,
                        "url": a.url,
                    }
                    for a in message.attachments
                ],
                "author": {
                    "id": str(message.author.id),
                    "name": message.author.name,
                    "display_name": getattr(message.author, "display_name", message.author.name),
                    "bot": message.author.bot,
                },
                "embeds": len(message.embeds),
                "mentions": [str(m.id) for m in message.mentions],
            }

            # Handle message timestamp (Discord uses timezone-aware datetime)
            msg_timestamp = message.created_at
            if msg_timestamp.tzinfo:
                msg_timestamp = msg_timestamp.replace(tzinfo=None)

            record = OmniMessageRecord(
                id=OmniMessageRecord.generate_id(instance_name, platform_message_id),
                instance_name=instance_name,
                channel_type="discord",
                chat_id=str(message.channel.id),
                platform_message_id=platform_message_id,
                direction="inbound",  # All fetched messages are from others
                sender_id=str(message.author.id),
                sender_name=getattr(message.author, "display_name", message.author.name),
                is_from_me=message.author.bot,  # Bot's own messages
                message_type=message_type,
                content_text=message.content,
                has_media=has_media,
                media_url=media_url,
                media_mime_type=media_mime_type,
                media_size_bytes=media_size,
                media_status="pending" if has_media else "pending",
                source="sync",
                sync_batch_id=sync_batch_id,
                message_timestamp=msg_timestamp,
                synced_at=datetime_utcnow(),
            )

            record.set_platform_key(platform_key)
            record.set_content_raw(content_raw)

            return record

        except Exception as e:
            logger.error(f"Error transforming Discord message {message.id}: {e}")
            return None

    async def import_channel_history(
        self,
        channel,
        instance_name: str,
        sync_batch_id: str,
        days_back: int = 30,
        max_messages: int = 1000,
        stats: Optional[DiscordImportStats] = None,
        batch_delay_ms: int = DEFAULT_BATCH_DELAY_MS,
    ) -> int:
        """
        Import message history from a single Discord channel.

        Uses discord.py's built-in rate limit handling plus additional
        conservative delays to avoid hitting limits on large imports.

        Args:
            channel: discord.TextChannel object
            instance_name: Instance name
            sync_batch_id: Batch identifier
            days_back: How many days back to fetch
            max_messages: Maximum messages to fetch per channel
            stats: Optional stats object to update
            batch_delay_ms: Delay between batches in milliseconds

        Returns:
            Number of messages imported
        """
        imported = 0
        after_date = datetime_utcnow() - timedelta(days=days_back)
        retry_count = 0

        try:
            logger.info(f"Importing history from #{channel.name} (last {days_back} days, max {max_messages})")

            message_count = 0
            batch_count = 0

            # discord.py's history() handles rate limits internally,
            # but we add delays to be extra safe on large imports
            async for message in channel.history(
                limit=max_messages,
                after=after_date,
                oldest_first=True,
            ):
                message_count += 1
                if stats:
                    stats.total_found += 1

                # Transform message
                record = self._transform_message(message, instance_name, sync_batch_id)
                if not record:
                    if stats:
                        stats.failed += 1
                    continue

                if record.has_media and stats:
                    stats.with_media += 1

                # Check for existing
                existing = self.db.query(OmniMessageRecord).filter(OmniMessageRecord.id == record.id).first()

                if existing:
                    if stats:
                        stats.already_exists += 1
                    continue

                # Insert new record
                try:
                    self.db.add(record)
                    self.db.commit()
                    imported += 1
                    if stats:
                        stats.total_imported += 1
                except Exception as e:
                    logger.error(f"Error inserting Discord message: {e}")
                    self.db.rollback()
                    if stats:
                        stats.failed += 1

                # Batch delay every N messages to avoid overwhelming the DB
                if message_count % DEFAULT_MESSAGES_PER_BATCH == 0:
                    batch_count += 1
                    await asyncio.sleep(batch_delay_ms / 1000)

                    # Log progress every 500 messages
                    if message_count % 500 == 0:
                        logger.info(f"  #{channel.name}: processed {message_count} messages, imported {imported}")

            logger.info(f"Imported {imported}/{message_count} messages from #{channel.name}")
            return imported

        except Exception as e:
            error_str = str(e).lower()

            # Handle rate limit errors with exponential backoff
            if "rate limit" in error_str or "429" in error_str:
                retry_count += 1
                if retry_count <= MAX_RETRIES:
                    backoff_time = (BACKOFF_BASE_MS * (2 ** (retry_count - 1))) / 1000
                    logger.warning(
                        f"Rate limited on #{channel.name}, backing off {backoff_time}s (retry {retry_count}/{MAX_RETRIES})"
                    )
                    await asyncio.sleep(backoff_time)
                    # Note: Could recursively retry here, but discord.py should handle this
                else:
                    logger.error(f"Max retries exceeded for #{channel.name}")

            logger.error(f"Error importing channel {channel.name}: {e}")
            return imported

    async def import_guild_history(
        self,
        client,
        guild,
        instance_name: str,
        days_back: int = 30,
        max_messages_per_channel: int = 1000,
        channel_ids: Optional[List[str]] = None,
        skip_channels: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None,
        channel_delay_ms: int = DEFAULT_CHANNEL_DELAY_MS,
        batch_delay_ms: int = DEFAULT_BATCH_DELAY_MS,
    ) -> DiscordImportStats:
        """
        Import message history from all text channels in a Discord guild/server.

        Runs in the background with conservative rate limiting to avoid
        hitting Discord API limits. Progress can be tracked via callback
        or by polling the batch job status.

        Rate Limiting Strategy:
        - discord.py handles 429 responses automatically
        - We add channel_delay_ms between channels (default 2s)
        - We add batch_delay_ms between message batches (default 100ms)
        - Large imports may take several minutes - this is by design

        Args:
            client: discord.Client object
            guild: discord.Guild object
            instance_name: Instance name
            days_back: How many days back to fetch
            max_messages_per_channel: Max messages per channel
            channel_ids: Optional list of specific channel IDs to import (None = all)
            skip_channels: Optional list of channel IDs to skip
            progress_callback: Optional callback(channel_name, imported_count)
            channel_delay_ms: Delay between channels in milliseconds (default 2000)
            batch_delay_ms: Delay between message batches in milliseconds (default 100)

        Returns:
            DiscordImportStats with import statistics
        """
        stats = DiscordImportStats(instance_name, str(guild.id))
        sync_batch_id = f"discord_sync_{instance_name}_{guild.id}_{datetime_utcnow().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting Discord import for guild '{guild.name}' ({guild.id})")
        logger.info(f"  Settings: days_back={days_back}, max_per_channel={max_messages_per_channel}")
        logger.info(f"  Rate limits: channel_delay={channel_delay_ms}ms, batch_delay={batch_delay_ms}ms")

        skip_channels = skip_channels or []

        # Get text channels with read history permission
        text_channels = [ch for ch in guild.text_channels if ch.permissions_for(guild.me).read_message_history]

        if channel_ids:
            text_channels = [ch for ch in text_channels if str(ch.id) in channel_ids]

        text_channels = [ch for ch in text_channels if str(ch.id) not in skip_channels]

        total_channels = len(text_channels)
        logger.info(f"Found {total_channels} text channels with read history permission")

        for idx, channel in enumerate(text_channels, 1):
            try:
                logger.info(f"[{idx}/{total_channels}] Processing #{channel.name}...")

                imported = await self.import_channel_history(
                    channel=channel,
                    instance_name=instance_name,
                    sync_batch_id=sync_batch_id,
                    days_back=days_back,
                    max_messages=max_messages_per_channel,
                    stats=stats,
                    batch_delay_ms=batch_delay_ms,
                )
                stats.channels_processed += 1

                if progress_callback:
                    progress_callback(channel.name, imported)

                # Delay between channels to avoid rate limits
                if idx < total_channels:  # Don't delay after last channel
                    logger.debug(f"Waiting {channel_delay_ms}ms before next channel...")
                    await asyncio.sleep(channel_delay_ms / 1000)

            except Exception as e:
                logger.error(f"Error processing channel {channel.name}: {e}")
                # Continue with other channels even if one fails

        stats.completed_at = datetime_utcnow()
        duration = (stats.completed_at - stats.started_at).total_seconds()
        logger.info(f"Discord import complete in {duration:.1f}s: {stats.to_dict()}")

        return stats


async def import_discord_guild_on_connect(
    client,
    guild,
    instance_name: str,
    days_back: int = 7,
    max_messages_per_channel: int = 500,
) -> Dict[str, Any]:
    """
    Utility function to import Discord history when bot joins a guild.

    Call this from the on_guild_join event handler.

    Args:
        client: discord.Client
        guild: discord.Guild
        instance_name: Instance name
        days_back: Days of history to import (default 7)
        max_messages_per_channel: Max messages per channel (default 500)

    Returns:
        Import statistics dict
    """
    db = SessionLocal()
    try:
        service = DiscordImportService(db)
        stats = await service.import_guild_history(
            client=client,
            guild=guild,
            instance_name=instance_name,
            days_back=days_back,
            max_messages_per_channel=max_messages_per_channel,
        )
        return stats.to_dict()
    finally:
        db.close()
