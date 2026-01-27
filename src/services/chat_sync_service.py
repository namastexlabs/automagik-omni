"""
Chat Sync Service

Syncs chat metadata from Evolution API (evo_Chat) to local omni_chats table.
Computes message stats from omni_messages for unified local-first queries.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.trace_models import OmniChatRecord, OmniMessageRecord
from src.db.models import EvolutionInstance
from src.services.chat_id_resolver import ChatIdResolver
from src.utils.datetime_utils import datetime_utcnow

logger = logging.getLogger(__name__)


class ChatSyncService:
    """
    Service for syncing chat metadata to local omni_chats table.

    Combines data from:
    - evo_Chat: Group names, archived status, etc.
    - omni_messages: Message counts, last message, contact names
    - chat_id_mappings: Canonical chat IDs for unified queries
    """

    def __init__(self, db: Session):
        self.db = db
        self._resolver = ChatIdResolver(db)

    def sync_chats_for_instance(self, instance_name: str) -> Dict[str, Any]:
        """
        Sync all chats for an instance from evo_Chat and omni_messages.

        Returns:
            Dict with sync statistics
        """
        stats = {
            "instance_name": instance_name,
            "synced": 0,
            "updated": 0,
            "from_evo_chat": 0,
            "from_messages": 0,
            "errors": 0,
        }

        try:
            # Get Evolution instance ID
            evo_instance = self.db.query(EvolutionInstance).filter(EvolutionInstance.name == instance_name).first()

            if not evo_instance:
                logger.warning(f"Instance {instance_name} not found in evo_Instance")
                return stats

            # Step 1: Get chats from evo_Chat (has group names, archived status)
            evo_chats = self._get_evo_chats(evo_instance.id, instance_name)
            stats["from_evo_chat"] = len(evo_chats)

            # Step 2: Get unique chats from omni_messages (may have chats not in evo_Chat)
            message_chats = self._get_chats_from_messages(instance_name)
            stats["from_messages"] = len(message_chats)

            # Step 3: Merge and sync
            all_chat_ids = set(evo_chats.keys()) | set(message_chats.keys())

            for chat_id in all_chat_ids:
                try:
                    evo_data = evo_chats.get(chat_id, {})
                    msg_data = message_chats.get(chat_id, {})

                    result = self._sync_chat(instance_name, chat_id, evo_data, msg_data)
                    if result == "created":
                        stats["synced"] += 1
                    elif result == "updated":
                        stats["updated"] += 1
                except Exception as e:
                    logger.error(f"Error syncing chat {chat_id}: {e}")
                    stats["errors"] += 1

            self.db.commit()
            logger.info(f"Chat sync complete for {instance_name}: {stats}")

        except Exception as e:
            logger.error(f"Chat sync failed for {instance_name}: {e}")
            self.db.rollback()
            raise

        return stats

    def _get_evo_chats(self, instance_id: str, instance_name: str) -> Dict[str, Dict]:
        """Get chat metadata from evo_Chat table."""
        result = self.db.execute(
            text("""
                SELECT
                    c."remoteJid" as chat_id,
                    c.name,
                    c."unreadMessages" as unread_count,
                    c.id as evo_id
                FROM "evo_Chat" c
                WHERE c."instanceId" = :instance_id
            """),
            {"instance_id": instance_id},
        ).fetchall()

        chats = {}
        for row in result:
            chat_id = row.chat_id
            chats[chat_id] = {
                "name": row.name if row.name and row.name != "None" else None,
                "unread_count": row.unread_count or 0,
                "evo_id": row.evo_id,
            }

        return chats

    def _get_chats_from_messages(self, instance_name: str) -> Dict[str, Dict]:
        """Get chat stats from omni_messages table."""
        # Query aggregated stats per chat
        results = (
            self.db.query(
                func.coalesce(OmniMessageRecord.canonical_chat_id, OmniMessageRecord.chat_id).label("chat_id"),
                func.count(OmniMessageRecord.id).label("message_count"),
                func.max(OmniMessageRecord.message_timestamp).label("last_message_at"),
            )
            .filter(OmniMessageRecord.instance_name == instance_name)
            .group_by(func.coalesce(OmniMessageRecord.canonical_chat_id, OmniMessageRecord.chat_id))
            .all()
        )

        chats = {}
        for row in results:
            chat_id = row.chat_id
            chats[chat_id] = {
                "message_count": row.message_count,
                "last_message_at": row.last_message_at,
            }

        return chats

    def _get_contact_name(self, instance_name: str, chat_id: str) -> Optional[str]:
        """Get contact name from inbound messages for direct chats."""
        result = (
            self.db.query(OmniMessageRecord.sender_name)
            .filter(
                OmniMessageRecord.instance_name == instance_name,
                func.coalesce(OmniMessageRecord.canonical_chat_id, OmniMessageRecord.chat_id) == chat_id,
                OmniMessageRecord.is_from_me == False,  # noqa: E712
                OmniMessageRecord.sender_name.isnot(None),
                OmniMessageRecord.sender_name != "",
            )
            .order_by(OmniMessageRecord.message_timestamp.desc())
            .first()
        )

        return result[0] if result else None

    def _get_last_message_preview(self, instance_name: str, chat_id: str) -> Optional[str]:
        """Get preview of last message for chat list display."""
        result = (
            self.db.query(
                OmniMessageRecord.content_text,
                OmniMessageRecord.message_type,
            )
            .filter(
                OmniMessageRecord.instance_name == instance_name,
                func.coalesce(OmniMessageRecord.canonical_chat_id, OmniMessageRecord.chat_id) == chat_id,
            )
            .order_by(OmniMessageRecord.message_timestamp.desc())
            .first()
        )

        if not result:
            return None

        text, msg_type = result
        if text:
            return text[:250]  # Truncate to 250 chars

        # Return message type indicator for media
        type_labels = {
            "audio": "🎵 Audio",
            "image": "📷 Image",
            "video": "🎬 Video",
            "document": "📄 Document",
            "sticker": "🎨 Sticker",
            "location": "📍 Location",
            "contact": "👤 Contact",
        }
        return type_labels.get(msg_type, msg_type)

    def _determine_chat_type(self, chat_id: str) -> str:
        """Determine chat type from chat ID format."""
        if not chat_id:
            return "direct"
        if chat_id.endswith("@g.us"):
            return "group"
        if chat_id.endswith("@broadcast"):
            return "channel"
        return "direct"

    def _extract_phone(self, chat_id: str) -> Optional[str]:
        """Extract phone number from @s.whatsapp.net chat ID."""
        if chat_id and chat_id.endswith("@s.whatsapp.net"):
            return chat_id.replace("@s.whatsapp.net", "")
        return None

    def _sync_chat(
        self,
        instance_name: str,
        chat_id: str,
        evo_data: Dict,
        msg_data: Dict,
    ) -> str:
        """
        Sync a single chat to omni_chats.

        Returns: 'created', 'updated', or 'unchanged'
        """
        record_id = OmniChatRecord.generate_id(instance_name, chat_id)
        chat_type = self._determine_chat_type(chat_id)

        # Get canonical chat ID
        canonical_id = self._resolver.get_canonical_id(instance_name, chat_id)

        # Determine display name
        if chat_type == "group" or chat_type == "channel":
            # Use evo_Chat name for groups
            name = evo_data.get("name") or chat_id
        else:
            # Use contact name from messages for direct chats
            name = self._get_contact_name(instance_name, chat_id)
            if not name:
                # Fall back to phone number
                name = self._extract_phone(chat_id) or chat_id

        # Get last message preview
        preview = self._get_last_message_preview(instance_name, chat_id)

        # Check if record exists
        existing = self.db.query(OmniChatRecord).filter(OmniChatRecord.id == record_id).first()

        if existing:
            # Update existing record
            existing.name = name
            existing.canonical_chat_id = canonical_id
            existing.message_count = msg_data.get("message_count", 0)
            existing.last_message_at = msg_data.get("last_message_at")
            existing.last_message_preview = preview
            existing.unread_count = evo_data.get("unread_count", 0)
            existing.synced_at = datetime_utcnow()
            existing.updated_at = datetime_utcnow()
            return "updated"
        else:
            # Create new record
            record = OmniChatRecord(
                id=record_id,
                instance_name=instance_name,
                channel_type="whatsapp",
                chat_id=chat_id,
                canonical_chat_id=canonical_id,
                name=name,
                chat_type=chat_type,
                message_count=msg_data.get("message_count", 0),
                last_message_at=msg_data.get("last_message_at"),
                last_message_preview=preview,
                unread_count=evo_data.get("unread_count", 0),
                evo_chat_id=evo_data.get("evo_id"),
                contact_name=name if chat_type == "direct" else None,
                contact_phone=self._extract_phone(chat_id) if chat_type == "direct" else None,
                synced_at=datetime_utcnow(),
            )
            self.db.add(record)
            return "created"


def sync_chats_for_instance(instance_name: str) -> Dict[str, Any]:
    """
    Utility function to sync chats for an instance.

    Args:
        instance_name: Instance to sync

    Returns:
        Sync statistics dictionary
    """
    db = SessionLocal()
    try:
        service = ChatSyncService(db)
        return service.sync_chats_for_instance(instance_name)
    finally:
        db.close()
