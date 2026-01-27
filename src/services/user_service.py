"""
User Service for stable identity management.

Provides user management with stable identity across different sessions,
agents, and interactions while tracking their most recent session info.
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from src.db.models import User, UserExternalId
from src.utils.datetime_utils import utcnow

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing user identity with stable UUIDs and session tracking."""

    def __init__(self):
        """Initialize the user service."""
        pass

    def _format_phone_to_jid(self, phone_number: str) -> str:
        """
        Format phone number to WhatsApp JID format.

        Args:
            phone_number: Phone number (with or without + and country code)

        Returns:
            str: WhatsApp JID format (e.g., 5511999999999@s.whatsapp.net)
        """
        # Remove any non-digit characters except +
        clean_phone = "".join(c for c in phone_number if c.isdigit() or c == "+")

        # Remove + if present
        if clean_phone.startswith("+"):
            clean_phone = clean_phone[1:]

        # Add @s.whatsapp.net if not present
        if "@" not in clean_phone:
            clean_phone = f"{clean_phone}@s.whatsapp.net"

        return clean_phone

    def get_or_create_user_by_phone(
        self,
        phone_number: str,
        instance_name: str,
        display_name: Optional[str] = None,
        session_name: Optional[str] = None,
        db: Session = None,
    ) -> User:
        """
        Get or create a user by phone number and instance.

        This is the primary method for incoming messages to ensure we have
        a stable user identity.

        Args:
            phone_number: WhatsApp phone number
            instance_name: Instance name
            display_name: Display name from pushName (optional)
            session_name: Current session name (optional)
            db: Database session

        Returns:
            User: The user record (existing or newly created)
        """
        if not db:
            raise ValueError("Database session is required")

        # Format phone to JID
        whatsapp_jid = self._format_phone_to_jid(phone_number)

        # Try to find existing user by phone + instance
        user = db.query(User).filter_by(phone_number=phone_number, instance_name=instance_name).first()

        if user:
            # Update existing user
            user.last_seen_at = utcnow()
            user.message_count += 1

            if display_name:
                user.display_name = display_name

            if session_name:
                user.last_session_name_interaction = session_name

            # Update whatsapp_jid in case formatting changed
            user.whatsapp_jid = whatsapp_jid
            user.updated_at = utcnow()

            db.commit()
            db.refresh(user)

            # Ensure WhatsApp external ID link exists
            try:
                self.link_external_id(user.id, "whatsapp", whatsapp_jid, instance_name, db)
            except Exception:
                logger.exception("Failed to ensure WhatsApp external ID link for existing user")

            logger.info(f"Updated existing user {user.id} for phone {phone_number}")
            return user

        # Create new user
        user = User(
            phone_number=phone_number,
            whatsapp_jid=whatsapp_jid,
            instance_name=instance_name,
            display_name=display_name,
            last_session_name_interaction=session_name,
            message_count=1,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # Create WhatsApp external ID link
        try:
            self.link_external_id(user.id, "whatsapp", whatsapp_jid, instance_name, db)
        except Exception:
            logger.exception("Failed to create WhatsApp external ID link for new user")

        logger.info(f"Created new user {user.id} for phone {phone_number} in instance {instance_name}")
        return user

    def link_external_id(
        self,
        user_id: str,
        provider: str,
        external_id: str,
        instance_name: Optional[str],
        db: Session,
    ) -> bool:
        """Ensure a link exists between a local user and an external provider ID.

        Unique per (provider, external_id). If link exists and points to another user,
        it will be reassigned to the provided user_id to enforce unification.
        """
        if not (user_id and provider and external_id):
            raise ValueError("user_id, provider and external_id are required")

        link = (
            db.query(UserExternalId)
            .filter(UserExternalId.provider == provider, UserExternalId.external_id == external_id)
            .first()
        )

        if link:
            if link.user_id != user_id:
                logger.warning(f"Reassigning external link {provider}:{external_id} from {link.user_id} to {user_id}")
                link.user_id = user_id
                link.instance_name = instance_name
                link.updated_at = utcnow()
                db.commit()
            return True

        # Create new link
        new_link = UserExternalId(
            user_id=user_id,
            provider=provider,
            external_id=external_id,
            instance_name=instance_name,
        )
        db.add(new_link)
        db.commit()
        return True

    def resolve_user_by_external(self, provider: str, external_id: str, db: Session) -> Optional[User]:
        """Resolve a User by provider/external_id mapping."""
        if not (provider and external_id):
            return None
        link = (
            db.query(UserExternalId)
            .filter(UserExternalId.provider == provider, UserExternalId.external_id == external_id)
            .first()
        )
        if not link:
            return None
        return db.query(User).filter_by(id=link.user_id).first()

    def get_user_by_id(self, user_id: str, db: Session) -> Optional[User]:
        """
        Get user by our stable internal UUID.

        Args:
            user_id: Our internal user UUID
            db: Database session

        Returns:
            Optional[User]: User record if found
        """
        user = db.query(User).filter_by(id=user_id).first()
        if user:
            logger.debug(f"Found user {user_id} with phone {user.phone_number}")
        else:
            logger.debug(f"User {user_id} not found")
        return user

    def update_user_session(self, user_id: str, session_name: str, db: Session) -> bool:
        """
        Update user's last session name interaction.

        Args:
            user_id: Our internal user UUID
            session_name: New session name
            db: Database session

        Returns:
            bool: Success status
        """
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            logger.warning(f"Cannot update session - user {user_id} not found")
            return False

        user.last_session_name_interaction = session_name
        user.last_seen_at = utcnow()
        user.updated_at = utcnow()

        db.commit()
        logger.info(f"Updated session for user {user_id} to {session_name}")
        return True

    def update_user_agent_id(self, user_id: str, agent_user_id: str, db: Session) -> bool:
        """
        Update user's last agent user ID.

        This is called when the agent API returns a user_id, which can
        change when users interact with different agents.

        Args:
            user_id: Our internal user UUID
            agent_user_id: Agent API user UUID
            db: Database session

        Returns:
            bool: Success status
        """
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            logger.warning(f"Cannot update agent ID - user {user_id} not found")
            return False

        user.last_agent_user_id = agent_user_id
        user.last_seen_at = utcnow()
        user.updated_at = utcnow()

        db.commit()
        logger.info(f"Updated agent user ID for user {user_id} to {agent_user_id}")
        return True

    def find_user_by_phone(self, phone_number: str, instance_name: str, db: Session) -> Optional[User]:
        """
        Find user by phone number and instance.

        Args:
            phone_number: WhatsApp phone number
            instance_name: Instance name
            db: Database session

        Returns:
            Optional[User]: User record if found
        """
        return db.query(User).filter_by(phone_number=phone_number, instance_name=instance_name).first()

    def get_user_by_agent_id(self, agent_user_id: str, db: Session) -> Optional[User]:
        """
        Get user by agent API user ID.

        Args:
            agent_user_id: Agent API user UUID
            db: Database session

        Returns:
            Optional[User]: User record if found
        """
        user = db.query(User).filter_by(last_agent_user_id=agent_user_id).first()
        if user:
            logger.debug(f"Found user {user.id} with agent user_id {agent_user_id}")
        else:
            logger.debug(f"No user found with agent user_id {agent_user_id}")
        return user

    def resolve_user_to_jid(self, user: User) -> str:
        """
        Resolve user to WhatsApp JID for message sending.

        Args:
            user: User record

        Returns:
            str: WhatsApp JID
        """
        return user.whatsapp_jid

    def get_or_create_user_by_discord(
        self,
        discord_user_id: str,
        instance_name: str,
        display_name: Optional[str] = None,
        username: Optional[str] = None,
        session_name: Optional[str] = None,
        db: Session = None,
    ) -> User:
        """
        Get or create a user by Discord user ID and instance.

        For Discord users, we create a synthetic phone number and JID
        since the User model requires these fields.

        Args:
            discord_user_id: Discord user ID (snowflake)
            instance_name: Instance name
            display_name: Display name from Discord (optional)
            username: Discord username (optional)
            session_name: Current session name (optional)
            db: Database session

        Returns:
            User: The user record (existing or newly created)
        """
        if not db:
            raise ValueError("Database session is required")

        # First check if we have an existing external ID link
        existing_link = (
            db.query(UserExternalId)
            .filter(
                UserExternalId.provider == "discord",
                UserExternalId.external_id == discord_user_id,
            )
            .first()
        )

        if existing_link:
            # Found existing link, get the user
            user = db.query(User).filter_by(id=existing_link.user_id).first()
            if user:
                # Update activity tracking
                user.last_seen_at = utcnow()
                user.message_count += 1

                if display_name:
                    user.display_name = display_name

                if session_name:
                    user.last_session_name_interaction = session_name

                user.updated_at = utcnow()
                db.commit()
                db.refresh(user)

                logger.info(f"Updated existing Discord user {user.id} for discord_id {discord_user_id}")
                return user

        # No existing link or user - check if we can find by synthetic phone
        synthetic_phone = f"discord_{discord_user_id}"
        synthetic_jid = f"{discord_user_id}@discord.user"

        user = db.query(User).filter_by(phone_number=synthetic_phone, instance_name=instance_name).first()

        if user:
            # Found user by synthetic phone, update and ensure external link
            user.last_seen_at = utcnow()
            user.message_count += 1

            if display_name:
                user.display_name = display_name

            if session_name:
                user.last_session_name_interaction = session_name

            user.updated_at = utcnow()
            db.commit()
            db.refresh(user)

            # Ensure Discord external ID link exists
            try:
                self.link_external_id(user.id, "discord", discord_user_id, instance_name, db)
            except Exception:
                logger.exception("Failed to ensure Discord external ID link for existing user")

            logger.info(
                f"Updated existing Discord user {user.id} (by synthetic phone) for discord_id {discord_user_id}"
            )
            return user

        # Create new user with synthetic phone/JID for Discord
        user = User(
            phone_number=synthetic_phone,
            whatsapp_jid=synthetic_jid,
            instance_name=instance_name,
            display_name=display_name or username or f"Discord User {discord_user_id}",
            last_session_name_interaction=session_name,
            message_count=1,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # Create Discord external ID link
        try:
            self.link_external_id(user.id, "discord", discord_user_id, instance_name, db)
        except Exception:
            logger.exception("Failed to create Discord external ID link for new user")

        logger.info(f"Created new Discord user {user.id} for discord_id {discord_user_id} in instance {instance_name}")
        return user

    def merge_users(
        self,
        target_user_id: str,
        source_user_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Merge source user into target user.

        All external IDs from source are transferred to target.
        Source user is deleted after merge.

        Args:
            target_user_id: The user to keep (merge destination)
            source_user_id: The user to merge and delete (merge source)
            db: Database session

        Returns:
            Dict with merge statistics
        """
        if target_user_id == source_user_id:
            raise ValueError("Cannot merge user into itself")

        target_user = db.query(User).filter_by(id=target_user_id).first()
        source_user = db.query(User).filter_by(id=source_user_id).first()

        if not target_user:
            raise ValueError(f"Target user {target_user_id} not found")
        if not source_user:
            raise ValueError(f"Source user {source_user_id} not found")

        stats = {
            "target_user_id": target_user_id,
            "source_user_id": source_user_id,
            "external_ids_transferred": 0,
            "message_count_added": source_user.message_count or 0,
        }

        # Transfer all external IDs from source to target
        source_external_ids = db.query(UserExternalId).filter_by(user_id=source_user_id).all()
        for ext_id in source_external_ids:
            ext_id.user_id = target_user_id
            ext_id.updated_at = utcnow()
            stats["external_ids_transferred"] += 1

        # Merge stats: combine message counts
        target_user.message_count = (target_user.message_count or 0) + (source_user.message_count or 0)

        # Keep the earliest created_at
        if source_user.created_at and (not target_user.created_at or source_user.created_at < target_user.created_at):
            target_user.created_at = source_user.created_at

        # Keep the latest last_seen_at
        if source_user.last_seen_at and (
            not target_user.last_seen_at or source_user.last_seen_at > target_user.last_seen_at
        ):
            target_user.last_seen_at = source_user.last_seen_at

        # Update display_name if target doesn't have one
        if not target_user.display_name and source_user.display_name:
            target_user.display_name = source_user.display_name

        target_user.updated_at = utcnow()

        # Delete source user
        db.delete(source_user)
        db.commit()

        logger.info(
            f"Merged user {source_user_id} into {target_user_id}: "
            f"{stats['external_ids_transferred']} external IDs transferred, "
            f"{stats['message_count_added']} messages added"
        )

        return stats

    def get_all_users(
        self,
        db: Session,
        instance_name: Optional[str] = None,
        provider: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[User]:
        """
        Get all users with optional filtering.

        Args:
            db: Database session
            instance_name: Filter by instance (optional)
            provider: Filter by external ID provider (optional)
            limit: Max results
            offset: Pagination offset

        Returns:
            List of users
        """
        query = db.query(User)

        if instance_name:
            query = query.filter(User.instance_name == instance_name)

        if provider:
            # Filter to users that have an external ID for this provider
            query = query.join(UserExternalId).filter(UserExternalId.provider == provider)

        query = query.order_by(User.last_seen_at.desc().nullsfirst())
        return query.offset(offset).limit(limit).all()

    def get_user_with_external_ids(self, user_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Get user with all their external IDs.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            User dict with external_ids list, or None if not found
        """
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return None

        external_ids = db.query(UserExternalId).filter_by(user_id=user_id).all()

        return {
            "id": user.id,
            "phone_number": user.phone_number,
            "whatsapp_jid": user.whatsapp_jid,
            "instance_name": user.instance_name,
            "display_name": user.display_name,
            "last_session_name_interaction": user.last_session_name_interaction,
            "last_agent_user_id": user.last_agent_user_id,
            "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
            "message_count": user.message_count,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "external_ids": [
                {
                    "id": ext.id,
                    "provider": ext.provider,
                    "external_id": ext.external_id,
                    "instance_name": ext.instance_name,
                    "created_at": ext.created_at.isoformat() if ext.created_at else None,
                }
                for ext in external_ids
            ],
        }

    def delete_user(self, user_id: str, db: Session) -> bool:
        """
        Delete a user and their external IDs.

        Args:
            user_id: User ID to delete
            db: Database session

        Returns:
            True if deleted, False if user not found
        """
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return False

        # External IDs are cascade deleted via FK constraint
        db.delete(user)
        db.commit()

        logger.info(f"Deleted user {user_id}")
        return True

    def try_agent_api_lookup(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Try to lookup user via agent API (fallback/compatibility).

        Args:
            user_id: User ID to lookup

        Returns:
            Optional[Dict]: User data from agent API if found
        """
        # Global agent API client is disabled - using instance-specific configurations
        logger.debug("Global agent API lookup skipped - using instance-specific configurations")
        return None


# Singleton instance
user_service = UserService()
