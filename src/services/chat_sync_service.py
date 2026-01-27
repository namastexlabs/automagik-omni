"""
Chat Sync Service

Syncs chat metadata from Evolution API (evo_Chat) to local omni_chats table.
Computes message stats from omni_messages for unified local-first queries.

Name Resolution Priority (for direct chats):
1. evo_Contact.pushName - WhatsApp contact's display name (most reliable)
2. omni_messages.sender_name - Name from recent messages
3. Phone number extracted from chat_id
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
    - evo_Contact: Contact names (pushName) and profile pictures
    - evo_Chat: Group names, archived status, etc.
    - omni_messages: Message counts, last message, sender names (fallback)
    - chat_id_mappings: Canonical chat IDs for unified queries
    """

    def __init__(self, db: Session):
        self.db = db
        self._resolver = ChatIdResolver(db)
        self._contacts_cache: Dict[str, Dict] = {}  # remoteJid -> contact data

    def sync_chats_for_instance(self, instance_name: str) -> Dict[str, Any]:
        """
        Sync all chats for an instance from evo_Chat, evo_Contact, and omni_messages.

        Returns:
            Dict with sync statistics
        """
        stats = {
            "instance_name": instance_name,
            "synced": 0,
            "updated": 0,
            "from_evo_chat": 0,
            "from_evo_contact": 0,
            "from_messages": 0,
            "errors": 0,
        }

        try:
            # Get Evolution instance ID
            evo_instance = self.db.query(EvolutionInstance).filter(EvolutionInstance.name == instance_name).first()

            if not evo_instance:
                logger.warning(f"Instance {instance_name} not found in evo_Instance")
                return stats

            # Step 1: Load contacts into cache (for name/avatar resolution)
            self._contacts_cache = self._get_evo_contacts(evo_instance.id)
            stats["from_evo_contact"] = len(self._contacts_cache)

            # Step 2: Get chats from evo_Chat (has group names, archived status)
            evo_chats = self._get_evo_chats(evo_instance.id, instance_name)
            stats["from_evo_chat"] = len(evo_chats)

            # Step 3: Get unique chats from omni_messages (may have chats not in evo_Chat)
            message_chats = self._get_chats_from_messages(instance_name)
            stats["from_messages"] = len(message_chats)

            # Step 4: Merge and sync
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
        finally:
            # Clear cache after sync
            self._contacts_cache = {}

        return stats

    def _get_evo_contacts(self, instance_id: str) -> Dict[str, Dict]:
        """
        Get contact data from evo_Contact table.

        Returns:
            Dict mapping remoteJid -> {push_name, profile_pic_url}
        """
        result = self.db.execute(
            text("""
                SELECT
                    "remoteJid",
                    "pushName",
                    "profilePicUrl"
                FROM "evo_Contact"
                WHERE "instanceId" = :instance_id
            """),
            {"instance_id": instance_id},
        ).fetchall()

        contacts = {}
        for row in result:
            jid = row.remoteJid
            # Store contact data, filtering out empty/None values
            push_name = row.pushName if row.pushName and row.pushName.strip() else None
            profile_pic = row.profilePicUrl if row.profilePicUrl and row.profilePicUrl.strip() else None

            if push_name or profile_pic:
                contacts[jid] = {
                    "push_name": push_name,
                    "profile_pic_url": profile_pic,
                }

        logger.debug(f"Loaded {len(contacts)} contacts from evo_Contact")
        return contacts

    def _get_evo_chats(self, instance_id: str, instance_name: str) -> Dict[str, Dict]:
        """Get chat metadata from evo_Chat table."""
        result = self.db.execute(
            text("""
                SELECT
                    c."remoteJid" as chat_id,
                    c.name,
                    c."unreadMessages" as unread_count,
                    c.id as evo_id,
                    c."updatedAt" as updated_at
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
                "updated_at": row.updated_at,  # Last message timestamp from Evolution
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
        """Get preview of last message for chat list display.

        Checks both evo_Message (all messages) and omni_messages (webhook messages)
        and returns the most recent one.
        """
        # First try evo_Message which has all messages
        evo_preview = self._get_last_message_from_evo(instance_name, chat_id)

        # Then try omni_messages
        omni_result = (
            self.db.query(
                OmniMessageRecord.content_text,
                OmniMessageRecord.message_type,
                OmniMessageRecord.message_timestamp,
            )
            .filter(
                OmniMessageRecord.instance_name == instance_name,
                func.coalesce(OmniMessageRecord.canonical_chat_id, OmniMessageRecord.chat_id) == chat_id,
            )
            .order_by(OmniMessageRecord.message_timestamp.desc())
            .first()
        )

        omni_preview = None
        omni_ts = None
        if omni_result:
            text, msg_type, omni_ts = omni_result
            if text:
                omni_preview = text[:250]
            else:
                type_labels = {
                    "audio": "🎵 Audio",
                    "image": "📷 Image",
                    "video": "🎬 Video",
                    "document": "📄 Document",
                    "sticker": "🎨 Sticker",
                    "location": "📍 Location",
                    "contact": "👤 Contact",
                }
                omni_preview = type_labels.get(msg_type, msg_type)

        # Return the most recent preview
        if evo_preview and omni_preview:
            # Compare timestamps - evo_preview is tuple (text, timestamp)
            evo_text, evo_ts = evo_preview
            if evo_ts and omni_ts:
                # Normalize types: evo_ts is int (Unix), omni_ts is datetime
                omni_ts_int = int(omni_ts.timestamp()) if hasattr(omni_ts, "timestamp") else omni_ts
                evo_ts_int = int(evo_ts) if not hasattr(evo_ts, "timestamp") else int(evo_ts.timestamp())
                return evo_text if evo_ts_int > omni_ts_int else omni_preview
            return evo_text  # Prefer evo if we can't compare
        elif evo_preview:
            return evo_preview[0]
        else:
            return omni_preview

    def _get_last_message_from_evo(self, instance_name: str, chat_id: str) -> Optional[tuple]:
        """Get last message preview from evo_Message table.

        Returns tuple of (preview_text, timestamp) or None.
        """
        try:
            # Get instance ID first
            instance_result = self.db.execute(
                text('SELECT id FROM "evo_Instance" WHERE name = :name'),
                {"name": instance_name},
            ).fetchone()

            if not instance_result:
                return None

            instance_id = instance_result[0]

            # Query evo_Message for the last message in this chat
            result = self.db.execute(
                text("""
                    SELECT
                        m.message,
                        m."messageType",
                        m."messageTimestamp"
                    FROM "evo_Message" m
                    WHERE m."instanceId" = :instance_id
                      AND m.key->>'remoteJid' = :chat_id
                    ORDER BY m."messageTimestamp" DESC
                    LIMIT 1
                """),
                {"instance_id": instance_id, "chat_id": chat_id},
            ).fetchone()

            if not result:
                return None

            message_json, msg_type, timestamp = result

            # Extract text from message JSON
            preview = self._extract_message_preview(message_json, msg_type)
            return (preview, timestamp) if preview else None

        except Exception as e:
            logger.debug(f"Error getting evo_Message preview for {chat_id}: {e}")
            return None

    def _extract_message_preview(self, message_json: dict, msg_type: str) -> Optional[str]:
        """Extract preview text from Evolution message JSON."""
        if not message_json:
            return None

        # Try common text fields
        if "conversation" in message_json:
            return message_json["conversation"][:250]

        if "extendedTextMessage" in message_json:
            text = message_json["extendedTextMessage"].get("text", "")
            return text[:250] if text else None

        # Media type indicators
        type_labels = {
            "imageMessage": "📷 Image",
            "videoMessage": "🎬 Video",
            "audioMessage": "🎵 Audio",
            "documentMessage": "📄 Document",
            "stickerMessage": "🎨 Sticker",
            "locationMessage": "📍 Location",
            "contactMessage": "👤 Contact",
            "reactionMessage": "reaction",
        }

        for key, label in type_labels.items():
            if key in message_json:
                # For documents, try to get filename
                if key == "documentMessage":
                    filename = message_json[key].get("fileName", "")
                    return f"📄 {filename}" if filename else label
                # For images/videos, try to get caption
                if key in ("imageMessage", "videoMessage"):
                    caption = message_json[key].get("caption", "")
                    return caption[:250] if caption else label
                return label

        return msg_type if msg_type else None

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

    def _get_contact_info(self, chat_id: str) -> Dict[str, Optional[str]]:
        """
        Get contact info from evo_Contact cache.

        Returns:
            Dict with 'push_name' and 'profile_pic_url' if found
        """
        return self._contacts_cache.get(chat_id, {})

    def _resolve_display_name(
        self,
        instance_name: str,
        chat_id: str,
        chat_type: str,
        evo_data: Dict,
    ) -> str:
        """
        Resolve the best display name for a chat.

        Priority for direct chats:
        1. evo_Contact.pushName (WhatsApp contact name)
        2. omni_messages.sender_name (name from recent messages)
        3. Phone number (extracted from chat_id)

        For groups/channels:
        1. evo_Chat.name (group name)
        2. chat_id as fallback
        """
        if chat_type in ("group", "channel"):
            return evo_data.get("name") or chat_id

        # Direct chat - try multiple sources
        contact_info = self._get_contact_info(chat_id)

        # Priority 1: evo_Contact.pushName
        if contact_info.get("push_name"):
            return contact_info["push_name"]

        # Priority 2: sender_name from messages
        msg_name = self._get_contact_name(instance_name, chat_id)
        if msg_name:
            return msg_name

        # Priority 3: Phone number
        phone = self._extract_phone(chat_id)
        if phone:
            return phone

        return chat_id

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

        # Resolve display name with priority logic
        name = self._resolve_display_name(instance_name, chat_id, chat_type, evo_data)

        # Get contact info for avatar
        contact_info = self._get_contact_info(chat_id)
        avatar_url = contact_info.get("profile_pic_url")

        # Get last message preview
        preview = self._get_last_message_preview(instance_name, chat_id)

        # Determine best last_message_at: prefer more recent of evo_data or msg_data
        evo_updated = evo_data.get("updated_at")  # From evo_Chat.updatedAt
        msg_updated = msg_data.get("last_message_at")  # From omni_messages

        # Use the most recent timestamp
        if evo_updated and msg_updated:
            last_message_at = max(evo_updated, msg_updated)
        else:
            last_message_at = evo_updated or msg_updated

        # Check if record exists
        existing = self.db.query(OmniChatRecord).filter(OmniChatRecord.id == record_id).first()

        if existing:
            # Update existing record
            existing.name = name
            existing.canonical_chat_id = canonical_id
            existing.message_count = msg_data.get("message_count", 0)
            existing.last_message_at = last_message_at
            existing.last_message_preview = preview
            existing.unread_count = evo_data.get("unread_count", 0)
            existing.synced_at = datetime_utcnow()
            existing.updated_at = datetime_utcnow()

            # Update avatar if we have one
            if avatar_url:
                existing.avatar_url = avatar_url

            # Update contact fields for direct chats
            if chat_type == "direct":
                existing.contact_name = name
                existing.contact_phone = self._extract_phone(chat_id)

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
                avatar_url=avatar_url,
                message_count=msg_data.get("message_count", 0),
                last_message_at=last_message_at,
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
