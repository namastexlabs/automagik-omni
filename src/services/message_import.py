"""
Message Import Service

Imports messages from Evolution API's evo_Message table into the unified omni_messages store.
Enables media processing on ALL messages (not just webhook-received) and reduces Evolution API dependency.

Features:
- Batch import with progress tracking
- Deduplication via (instance_name, platform_message_id) constraint
- Full message data preservation for reprocessing
- Media metadata extraction for download service
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session as SQLAlchemySession

from src.db.database import get_db
from src.db.models import EvolutionInstance, EvolutionMessage
from src.db.trace_models import OmniMessageRecord
from src.services.chat_id_resolver import ChatIdResolver
from src.utils.datetime_utils import datetime_utcnow

logger = logging.getLogger(__name__)


# Message type mapping from Evolution to Omni
MESSAGE_TYPE_MAP = {
    "conversation": "text",
    "extendedTextMessage": "text",
    "audioMessage": "audio",
    "imageMessage": "image",
    "videoMessage": "video",
    "documentMessage": "document",
    "stickerMessage": "sticker",
    "contactMessage": "contact",
    "contactsArrayMessage": "contact",
    "locationMessage": "location",
    "liveLocationMessage": "location",
    "reactionMessage": "reaction",
    "pollCreationMessage": "text",  # Treat polls as text for now
    "buttonsResponseMessage": "text",
    "listResponseMessage": "text",
    "templateButtonReplyMessage": "text",
    "interactiveResponseMessage": "text",
    "protocolMessage": "system",
    "senderKeyDistributionMessage": "system",
}

# Media types that need download/processing
MEDIA_TYPES = {"audio", "image", "video", "document"}


class MessageImportStats:
    """Statistics for import operation."""

    def __init__(self, instance_name: str):
        self.instance_name = instance_name
        self.total_found = 0
        self.total_imported = 0
        self.already_exists = 0
        self.failed = 0
        self.with_media = 0
        self.started_at = datetime_utcnow()
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        duration = None
        if self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()

        return {
            "instance_name": self.instance_name,
            "total_found": self.total_found,
            "total_imported": self.total_imported,
            "already_exists": self.already_exists,
            "failed": self.failed,
            "with_media": self.with_media,
            "source": "evo_Message",
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": duration,
        }


class MessageImportService:
    """
    Service for importing messages from Evolution API tables into omni_messages.

    Supports:
    - Full history import for an instance
    - Incremental sync (only new messages)
    - Batch processing with progress callbacks
    """

    def __init__(self, db: SQLAlchemySession):
        self.db = db
        self._instance_cache: Dict[str, str] = {}  # instanceId -> instance_name
        self._chat_id_resolver = ChatIdResolver(db)

    def _get_instance_name(self, instance_id: str) -> Optional[str]:
        """Get instance name from Evolution instance ID."""
        if instance_id in self._instance_cache:
            return self._instance_cache[instance_id]

        evo_instance = self.db.query(EvolutionInstance).filter(EvolutionInstance.id == instance_id).first()
        if evo_instance:
            self._instance_cache[instance_id] = evo_instance.name
            return evo_instance.name
        return None

    def _extract_message_content(self, message: Dict[str, Any], message_type: str) -> Tuple[Optional[str], bool]:
        """
        Extract text content and determine if message has media.

        Returns:
            Tuple of (text_content, has_media)
        """
        text_content = None
        has_media = False

        if message_type == "conversation":
            text_content = message.get("conversation")
        elif message_type == "extendedTextMessage":
            ext_msg = message.get("extendedTextMessage", {})
            text_content = ext_msg.get("text")
        elif message_type in ("audioMessage", "imageMessage", "videoMessage", "documentMessage"):
            has_media = True
            # Extract caption if present
            msg_data = message.get(message_type, {})
            text_content = msg_data.get("caption")
        elif message_type == "stickerMessage":
            has_media = True
        elif message_type == "contactMessage":
            contact = message.get("contactMessage", {})
            text_content = contact.get("displayName")
        elif message_type == "locationMessage":
            loc = message.get("locationMessage", {})
            text_content = loc.get("name") or loc.get("address")

        return text_content, has_media

    def _extract_media_info(self, message: Dict[str, Any], message_type: str) -> Dict[str, Any]:
        """Extract media metadata from message."""
        media_info = {
            "media_url": None,
            "media_mime_type": None,
            "media_size_bytes": None,
            "media_duration_seconds": None,
            "media_key": None,
            "media_sha256": None,
        }

        if message_type not in ("audioMessage", "imageMessage", "videoMessage", "documentMessage", "stickerMessage"):
            return media_info

        msg_data = message.get(message_type, {})

        media_info["media_url"] = msg_data.get("url")
        media_info["media_mime_type"] = msg_data.get("mimetype")
        media_info["media_key"] = msg_data.get("mediaKey")

        # Handle file size (could be int or {low, high, unsigned} object)
        file_length = msg_data.get("fileLength")
        if isinstance(file_length, dict):
            media_info["media_size_bytes"] = file_length.get("low")
        elif isinstance(file_length, int):
            media_info["media_size_bytes"] = file_length

        # Duration for audio/video
        seconds = msg_data.get("seconds")
        if seconds:
            if isinstance(seconds, dict):
                media_info["media_duration_seconds"] = seconds.get("low")
            else:
                media_info["media_duration_seconds"] = seconds

        # SHA256 for deduplication
        file_sha256 = msg_data.get("fileSha256")
        if file_sha256:
            # Already base64 encoded, take first 64 chars
            media_info["media_sha256"] = file_sha256[:64]

        return media_info

    def _extract_context_info(
        self, context_info: Optional[Dict[str, Any]]
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Extract quoted message ID and context info.

        Returns:
            Tuple of (quoted_message_id, cleaned_context_info)
        """
        if not context_info:
            return None, None

        quoted_message_id = context_info.get("stanzaId")

        # Clean up context info to remove large nested data
        cleaned = {}
        for key in ("stanzaId", "participant", "quotedType", "mentionedJid"):
            if key in context_info:
                cleaned[key] = context_info[key]

        # Include quoted message text if present
        quoted_msg = context_info.get("quotedMessage")
        if quoted_msg:
            if "conversation" in quoted_msg:
                cleaned["quotedText"] = quoted_msg["conversation"][:500]  # Truncate
            elif "extendedTextMessage" in quoted_msg:
                cleaned["quotedText"] = quoted_msg["extendedTextMessage"].get("text", "")[:500]

        return quoted_message_id, cleaned if cleaned else None

    def _transform_message(
        self, evo_msg: EvolutionMessage, instance_name: str, sync_batch_id: str
    ) -> Optional[OmniMessageRecord]:
        """
        Transform Evolution message to OmniMessageRecord.

        Returns None if message cannot be transformed (e.g., unknown type).
        """
        try:
            # Parse key JSON
            key_data = evo_msg.key
            if isinstance(key_data, str):
                key_data = json.loads(key_data)

            # Parse message JSON
            message_data = evo_msg.message
            if isinstance(message_data, str):
                message_data = json.loads(message_data)

            # Parse context info JSON
            context_data = evo_msg.contextInfo
            if isinstance(context_data, str):
                context_data = json.loads(context_data)

            # Get platform message ID from key
            platform_message_id = key_data.get("id")
            if not platform_message_id:
                logger.warning(f"Message {evo_msg.id} has no key.id, skipping")
                return None

            # Determine message type
            omni_type = MESSAGE_TYPE_MAP.get(evo_msg.messageType, "unknown")

            # Extract content and media info
            text_content, has_media = self._extract_message_content(message_data, evo_msg.messageType)
            media_info = self._extract_media_info(message_data, evo_msg.messageType)

            # Extract context/quoting info
            quoted_message_id, context_info = self._extract_context_info(context_data)

            # Determine chat ID from key
            chat_id = key_data.get("remoteJid", "")

            # Determine sender
            is_from_me = key_data.get("fromMe", False)
            if is_from_me:
                sender_id = None  # Sent by instance owner
            else:
                # For groups, participant is the sender; for direct, remoteJid is sender
                sender_id = key_data.get("participant") or key_data.get("remoteJid")

            # Convert Unix timestamp to datetime
            msg_timestamp = datetime.utcfromtimestamp(evo_msg.messageTimestamp)

            # Resolve canonical chat ID for unified conversations
            canonical_chat_id = self._chat_id_resolver.get_canonical_id(instance_name, chat_id)

            # Create record
            record = OmniMessageRecord(
                id=OmniMessageRecord.generate_id(instance_name, platform_message_id),
                instance_name=instance_name,
                channel_type="whatsapp",
                chat_id=chat_id,
                canonical_chat_id=canonical_chat_id,
                platform_message_id=platform_message_id,
                direction="outbound" if is_from_me else "inbound",
                sender_id=sender_id,
                sender_name=evo_msg.pushName,
                is_from_me=is_from_me,
                message_type=omni_type,
                content_text=text_content,
                has_media=has_media,
                quoted_message_id=quoted_message_id,
                delivery_status=self._map_delivery_status(evo_msg.status),
                source="sync",
                sync_batch_id=sync_batch_id,
                message_timestamp=msg_timestamp,
                synced_at=datetime_utcnow(),
                media_status="pending" if has_media else "pending",  # Will be set to downloaded/processed later
            )

            # Set JSON fields
            record.set_platform_key(key_data)
            record.set_content_raw(message_data)
            if context_info:
                record.set_context_info(context_info)

            # Set media fields
            if has_media:
                record.media_url = media_info["media_url"]
                record.media_mime_type = media_info["media_mime_type"]
                record.media_size_bytes = media_info["media_size_bytes"]
                record.media_duration_seconds = media_info["media_duration_seconds"]
                record.media_key = media_info["media_key"]
                record.media_sha256 = media_info["media_sha256"]

            return record

        except Exception as e:
            logger.error(f"Error transforming message {evo_msg.id}: {e}")
            return None

    def _map_delivery_status(self, evo_status: Optional[str]) -> Optional[str]:
        """Map Evolution status to OmniMessage delivery status."""
        if not evo_status:
            return None

        status_map = {
            "PENDING": "pending",
            "SERVER_ACK": "sent",
            "DELIVERY_ACK": "delivered",
            "READ": "read",
            "PLAYED": "read",  # For audio
            "DELETED": None,
            "ERROR": "failed",
        }
        return status_map.get(evo_status)

    def import_from_evolution(
        self,
        instance_name: str,
        days: int = 30,
        batch_size: int = 500,
        progress_callback: Optional[callable] = None,
    ) -> MessageImportStats:
        """
        Import messages from Evolution's evo_Message table.

        Args:
            instance_name: The instance to import messages for
            days: Number of days of history to import
            batch_size: Number of messages to process per batch
            progress_callback: Optional callback(processed, total) for progress updates

        Returns:
            MessageImportStats with import statistics
        """
        stats = MessageImportStats(instance_name)
        sync_batch_id = f"sync_{instance_name}_{datetime_utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Get Evolution instance ID for this instance name
        evo_instance = self.db.query(EvolutionInstance).filter(EvolutionInstance.name == instance_name).first()
        if not evo_instance:
            logger.error(f"Instance {instance_name} not found in evo_Instance")
            stats.completed_at = datetime_utcnow()
            return stats

        # Calculate cutoff timestamp
        cutoff_date = datetime_utcnow() - timedelta(days=days)
        cutoff_timestamp = int(cutoff_date.timestamp())

        logger.info(f"Importing messages for {instance_name} from last {days} days (since {cutoff_date})")

        # Count total messages to import
        count_query = text("""
            SELECT COUNT(*) FROM "evo_Message"
            WHERE "instanceId" = :instance_id AND "messageTimestamp" >= :cutoff
        """)
        total_count = self.db.execute(
            count_query, {"instance_id": evo_instance.id, "cutoff": cutoff_timestamp}
        ).scalar()
        stats.total_found = total_count

        logger.info(f"Found {total_count} messages to import")

        # Process in batches
        offset = 0
        while offset < total_count:
            # Fetch batch of messages
            messages = (
                self.db.query(EvolutionMessage)
                .filter(EvolutionMessage.instanceId == evo_instance.id)
                .filter(EvolutionMessage.messageTimestamp >= cutoff_timestamp)
                .order_by(EvolutionMessage.messageTimestamp.asc())
                .offset(offset)
                .limit(batch_size)
                .all()
            )

            if not messages:
                break

            # Transform messages
            records_to_insert = []
            for evo_msg in messages:
                record = self._transform_message(evo_msg, instance_name, sync_batch_id)
                if record:
                    records_to_insert.append(record)
                    if record.has_media:
                        stats.with_media += 1

            # Bulk upsert using PostgreSQL ON CONFLICT
            if records_to_insert:
                self._bulk_upsert(records_to_insert, stats)

            offset += len(messages)

            # Progress callback
            if progress_callback:
                progress_callback(offset, total_count)

            logger.info(f"Processed {offset}/{total_count} messages")

        stats.completed_at = datetime_utcnow()
        logger.info(f"Import complete: {stats.to_dict()}")

        return stats

    def _bulk_upsert(self, records: List[OmniMessageRecord], stats: MessageImportStats) -> None:
        """
        Bulk upsert records using PostgreSQL ON CONFLICT.

        Updates stats with import/skip counts.
        """
        # Deduplicate within the batch first (keep last occurrence)
        seen_ids = {}
        for record in records:
            seen_ids[record.id] = record
        unique_records = list(seen_ids.values())

        for record in unique_records:
            try:
                # Check if exists
                existing = self.db.query(OmniMessageRecord).filter(OmniMessageRecord.id == record.id).first()

                if existing:
                    # Update only if source is different (prefer webhook over sync)
                    if existing.source == "webhook":
                        # Don't overwrite webhook data with sync data
                        stats.already_exists += 1
                        continue

                    # Update sync data
                    existing.synced_at = record.synced_at
                    existing.sync_batch_id = record.sync_batch_id
                    # Update delivery status if newer
                    if record.delivery_status and existing.delivery_status != record.delivery_status:
                        existing.delivery_status = record.delivery_status
                        existing.status_updated_at = datetime_utcnow()
                    stats.already_exists += 1
                else:
                    # Insert new record
                    self.db.add(record)
                    stats.total_imported += 1

            except Exception as e:
                logger.error(f"Error upserting message {record.id}: {e}")
                stats.failed += 1

        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Error committing batch: {e}")
            self.db.rollback()
            stats.failed += len(unique_records)

    def sync_new_messages(
        self,
        instance_name: str,
        since_timestamp: Optional[datetime] = None,
    ) -> MessageImportStats:
        """
        Incremental sync - only import messages newer than last sync.

        Args:
            instance_name: The instance to sync
            since_timestamp: Only sync messages after this time. If None, uses last synced_at.

        Returns:
            MessageImportStats with sync statistics
        """
        # Get last synced timestamp for this instance
        if since_timestamp is None:
            last_sync = (
                self.db.query(OmniMessageRecord.synced_at)
                .filter(OmniMessageRecord.instance_name == instance_name)
                .filter(OmniMessageRecord.source == "sync")
                .order_by(OmniMessageRecord.synced_at.desc())
                .first()
            )
            if last_sync and last_sync[0]:
                since_timestamp = last_sync[0]
            else:
                # No previous sync - sync last 7 days
                since_timestamp = datetime_utcnow() - timedelta(days=7)

        # Calculate days since timestamp
        # Normalize both to naive UTC for comparison (datetime_utcnow returns aware datetime)
        now = datetime_utcnow().replace(tzinfo=None)
        since_naive = (
            since_timestamp.replace(tzinfo=None)
            if hasattr(since_timestamp, "tzinfo") and since_timestamp.tzinfo
            else since_timestamp
        )
        days = (now - since_naive).days + 1

        logger.info(f"Incremental sync for {instance_name} since {since_timestamp}")

        return self.import_from_evolution(instance_name, days=days, batch_size=500)


def import_messages_for_instance(instance_name: str, days: int = 30, discover_mappings: bool = True) -> Dict[str, Any]:
    """
    Utility function to import messages for an instance.

    Args:
        instance_name: Instance to import
        days: Days of history to import
        discover_mappings: If True, run chat ID mapping discovery after import

    Returns:
        Import statistics dictionary with optional mapping stats
    """
    db = next(get_db())
    try:
        service = MessageImportService(db)
        stats = service.import_from_evolution(instance_name, days=days)
        result = stats.to_dict()

        # Optionally discover and apply chat ID mappings
        if discover_mappings:
            resolver = ChatIdResolver(db)

            # Discover mappings by matching sender names
            discovery_stats = resolver.discover_mappings_by_sender_name(instance_name)
            result["mapping_discovery"] = discovery_stats

            # Update canonical_chat_id for messages with known mappings
            update_stats = resolver.update_canonical_chat_ids(instance_name)
            result["mapping_updates"] = update_stats

        return result
    finally:
        db.close()
