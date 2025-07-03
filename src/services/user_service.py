"""
User Service for stable identity management.

Provides user management with stable identity across different sessions,
agents, and interactions while tracking their most recent session info.
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from src.db.models import User
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
        user = (
            db.query(User)
            .filter_by(phone_number=phone_number, instance_name=instance_name)
            .first()
        )

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

        logger.info(
            f"Created new user {user.id} for phone {phone_number} in instance {instance_name}"
        )
        return user

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

    def update_user_agent_id(
        self, user_id: str, agent_user_id: str, db: Session
    ) -> bool:
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

    def find_user_by_phone(
        self, phone_number: str, instance_name: str, db: Session
    ) -> Optional[User]:
        """
        Find user by phone number and instance.

        Args:
            phone_number: WhatsApp phone number
            instance_name: Instance name
            db: Database session

        Returns:
            Optional[User]: User record if found
        """
        return (
            db.query(User)
            .filter_by(phone_number=phone_number, instance_name=instance_name)
            .first()
        )

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

    def try_agent_api_lookup(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Try to lookup user via agent API (fallback/compatibility).

        Args:
            user_id: User ID to lookup

        Returns:
            Optional[Dict]: User data from agent API if found
        """
        # Global agent API client is disabled - using instance-specific configurations
        logger.debug(
            "Global agent API lookup skipped - using instance-specific configurations"
        )
        return None


# Singleton instance
user_service = UserService()
