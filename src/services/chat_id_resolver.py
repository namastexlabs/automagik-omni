"""
Chat ID Resolver Service

Handles the mapping between different WhatsApp chat ID formats:
- @s.whatsapp.net: Phone number format (canonical)
- @lid: Linked device ID format
- @g.us: Group format

Enables unified conversation queries across different ID formats.
"""

import logging
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.db.trace_models import OmniMessageRecord, ChatIdMapping
from src.utils.datetime_utils import datetime_utcnow

logger = logging.getLogger(__name__)


class ChatIdResolver:
    """
    Resolves and manages chat ID mappings for unified conversation queries.
    """

    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[str, str] = {}  # alternate -> canonical

    def is_lid_format(self, chat_id: str) -> bool:
        """Check if chat_id is in @lid format."""
        return chat_id.endswith("@lid") if chat_id else False

    def is_phone_format(self, chat_id: str) -> bool:
        """Check if chat_id is in @s.whatsapp.net format (phone number)."""
        return chat_id.endswith("@s.whatsapp.net") if chat_id else False

    def is_group_format(self, chat_id: str) -> bool:
        """Check if chat_id is a group."""
        return chat_id.endswith("@g.us") if chat_id else False

    def extract_phone_number(self, chat_id: str) -> Optional[str]:
        """Extract phone number from @s.whatsapp.net format."""
        if self.is_phone_format(chat_id):
            return chat_id.replace("@s.whatsapp.net", "")
        return None

    def get_canonical_id(self, instance_name: str, chat_id: str) -> str:
        """
        Get the canonical chat ID for a given chat_id.

        For @lid format, looks up the mapping.
        For @s.whatsapp.net format, returns as-is (already canonical).
        For groups, returns as-is.
        """
        if not chat_id:
            return chat_id

        # Groups and phone numbers are already canonical
        if self.is_group_format(chat_id) or self.is_phone_format(chat_id):
            return chat_id

        # Check cache first
        cache_key = f"{instance_name}:{chat_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Look up in database
        if self.is_lid_format(chat_id):
            mapping = (
                self.db.query(ChatIdMapping)
                .filter(
                    and_(
                        ChatIdMapping.instance_name == instance_name,
                        ChatIdMapping.alternate_chat_id == chat_id,
                    )
                )
                .first()
            )

            if mapping:
                self._cache[cache_key] = mapping.canonical_chat_id
                return mapping.canonical_chat_id

        # No mapping found, return original
        return chat_id

    def add_mapping(
        self,
        instance_name: str,
        canonical_chat_id: str,
        alternate_chat_id: str,
        contact_name: Optional[str] = None,
        discovery_method: str = "auto",
    ) -> ChatIdMapping:
        """Add a new chat ID mapping."""
        # Check if mapping already exists
        existing = (
            self.db.query(ChatIdMapping)
            .filter(
                and_(
                    ChatIdMapping.instance_name == instance_name,
                    ChatIdMapping.alternate_chat_id == alternate_chat_id,
                )
            )
            .first()
        )

        if existing:
            # Update if contact name is provided and missing
            if contact_name and not existing.contact_name:
                existing.contact_name = contact_name
                existing.updated_at = datetime_utcnow()
                self.db.commit()
            return existing

        # Create new mapping
        phone = self.extract_phone_number(canonical_chat_id)
        mapping = ChatIdMapping(
            instance_name=instance_name,
            canonical_chat_id=canonical_chat_id,
            alternate_chat_id=alternate_chat_id,
            contact_name=contact_name,
            phone_number=phone,
            discovery_method=discovery_method,
        )
        self.db.add(mapping)
        self.db.commit()

        # Update cache
        cache_key = f"{instance_name}:{alternate_chat_id}"
        self._cache[cache_key] = canonical_chat_id

        logger.info(f"Added chat ID mapping: {alternate_chat_id} -> {canonical_chat_id} ({contact_name})")
        return mapping

    def discover_mappings_by_sender_name(self, instance_name: str) -> Dict[str, any]:
        """
        Discover chat ID mappings by matching sender names.

        Finds cases where the same sender_name appears in both @lid and @s.whatsapp.net chats,
        indicating they're the same contact.

        Returns:
            Dict with discovery stats
        """
        stats = {
            "discovered": 0,
            "already_exists": 0,
            "mappings": [],
        }

        # Find sender names that appear in @lid chats
        lid_senders = (
            self.db.query(
                OmniMessageRecord.sender_name,
                OmniMessageRecord.chat_id,
            )
            .filter(
                and_(
                    OmniMessageRecord.instance_name == instance_name,
                    OmniMessageRecord.chat_id.like("%@lid"),
                    OmniMessageRecord.sender_name.isnot(None),
                    OmniMessageRecord.is_from_me == False,  # noqa: E712
                )
            )
            .distinct()
            .all()
        )

        for sender_name, lid_chat_id in lid_senders:
            if not sender_name or not lid_chat_id:
                continue

            # Find matching @s.whatsapp.net chat with same sender name
            phone_chat = (
                self.db.query(OmniMessageRecord.chat_id)
                .filter(
                    and_(
                        OmniMessageRecord.instance_name == instance_name,
                        OmniMessageRecord.sender_name == sender_name,
                        OmniMessageRecord.chat_id.like("%@s.whatsapp.net"),
                        OmniMessageRecord.is_from_me == False,  # noqa: E712
                    )
                )
                .first()
            )

            if phone_chat:
                canonical_id = phone_chat[0]

                # Check if mapping exists
                existing = (
                    self.db.query(ChatIdMapping)
                    .filter(
                        and_(
                            ChatIdMapping.instance_name == instance_name,
                            ChatIdMapping.alternate_chat_id == lid_chat_id,
                        )
                    )
                    .first()
                )

                if existing:
                    stats["already_exists"] += 1
                else:
                    self.add_mapping(
                        instance_name=instance_name,
                        canonical_chat_id=canonical_id,
                        alternate_chat_id=lid_chat_id,
                        contact_name=sender_name,
                        discovery_method="sender_name",
                    )
                    stats["discovered"] += 1
                    stats["mappings"].append(
                        {
                            "canonical": canonical_id,
                            "alternate": lid_chat_id,
                            "contact": sender_name,
                        }
                    )

        logger.info(f"Mapping discovery complete: {stats['discovered']} new, {stats['already_exists']} existing")
        return stats

    def update_canonical_chat_ids(self, instance_name: str) -> Dict[str, any]:
        """
        Update canonical_chat_id for all messages in an instance.

        Returns:
            Dict with update stats
        """
        stats = {
            "updated": 0,
            "already_set": 0,
            "no_mapping": 0,
        }

        # Get all messages with @lid chat_id that don't have canonical_chat_id set
        lid_messages = (
            self.db.query(OmniMessageRecord)
            .filter(
                and_(
                    OmniMessageRecord.instance_name == instance_name,
                    OmniMessageRecord.chat_id.like("%@lid"),
                    or_(
                        OmniMessageRecord.canonical_chat_id.is_(None),
                        OmniMessageRecord.canonical_chat_id == "",
                    ),
                )
            )
            .all()
        )

        for msg in lid_messages:
            canonical = self.get_canonical_id(instance_name, msg.chat_id)
            if canonical != msg.chat_id:
                msg.canonical_chat_id = canonical
                stats["updated"] += 1
            else:
                stats["no_mapping"] += 1

        # Update messages that already have @s.whatsapp.net format
        phone_messages = (
            self.db.query(OmniMessageRecord)
            .filter(
                and_(
                    OmniMessageRecord.instance_name == instance_name,
                    OmniMessageRecord.chat_id.like("%@s.whatsapp.net"),
                    or_(
                        OmniMessageRecord.canonical_chat_id.is_(None),
                        OmniMessageRecord.canonical_chat_id == "",
                    ),
                )
            )
            .all()
        )

        for msg in phone_messages:
            msg.canonical_chat_id = msg.chat_id
            stats["updated"] += 1

        self.db.commit()
        logger.info(f"Updated canonical_chat_id: {stats['updated']} messages")
        return stats

    def get_all_chat_ids_for_contact(self, instance_name: str, chat_id: str) -> List[str]:
        """
        Get all chat IDs associated with a contact.

        Given any chat ID (canonical or alternate), returns all known IDs for that contact.
        """
        result = [chat_id]

        # If it's a phone format, look for alternates
        if self.is_phone_format(chat_id):
            alternates = (
                self.db.query(ChatIdMapping.alternate_chat_id)
                .filter(
                    and_(
                        ChatIdMapping.instance_name == instance_name,
                        ChatIdMapping.canonical_chat_id == chat_id,
                    )
                )
                .all()
            )
            result.extend([a[0] for a in alternates])

        # If it's a lid format, look for canonical
        elif self.is_lid_format(chat_id):
            mapping = (
                self.db.query(ChatIdMapping)
                .filter(
                    and_(
                        ChatIdMapping.instance_name == instance_name,
                        ChatIdMapping.alternate_chat_id == chat_id,
                    )
                )
                .first()
            )

            if mapping:
                result.append(mapping.canonical_chat_id)
                # Also get other alternates for this canonical
                other_alternates = (
                    self.db.query(ChatIdMapping.alternate_chat_id)
                    .filter(
                        and_(
                            ChatIdMapping.instance_name == instance_name,
                            ChatIdMapping.canonical_chat_id == mapping.canonical_chat_id,
                            ChatIdMapping.alternate_chat_id != chat_id,
                        )
                    )
                    .all()
                )
                result.extend([a[0] for a in other_alternates])

        return list(set(result))  # Remove duplicates


def discover_and_update_mappings(instance_name: str) -> Dict[str, any]:
    """
    Utility function to discover mappings and update canonical_chat_ids.
    """
    from src.db.database import SessionLocal

    db = SessionLocal()
    try:
        resolver = ChatIdResolver(db)

        # Discover mappings
        discovery_stats = resolver.discover_mappings_by_sender_name(instance_name)

        # Update canonical_chat_ids
        update_stats = resolver.update_canonical_chat_ids(instance_name)

        return {
            "discovery": discovery_stats,
            "updates": update_stats,
        }
    finally:
        db.close()
