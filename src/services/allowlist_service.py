"""
Allowlist service for managing user access control across multiple channels.

This service provides a centralized way to manage allowed users for different instances
and channels, supporting multi-tenant and multi-channel architecture.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging

from src.db.models import AllowedUser, InstanceConfig
from src.utils.datetime_utils import datetime_utcnow

logger = logging.getLogger(__name__)


class AllowlistService:
    """Service for managing user allowlists across instances and channels."""

    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db

    def is_user_allowed(self, instance_name: str, channel_type: str, user_identifier: str) -> bool:
        """
        Check if a user is allowed to interact with an instance.

        Args:
            instance_name: Name of the instance
            channel_type: Channel type (whatsapp, discord, etc.)
            user_identifier: Channel-specific user identifier

        Returns:
            True if user is allowed, False if not allowed, True if allowlist is disabled
        """
        try:
            # Get instance configuration
            instance = self.db.query(InstanceConfig).filter(InstanceConfig.name == instance_name).first()

            if not instance:
                logger.warning(f"Instance not found: {instance_name}")
                return True  # Fail-safe: allow if instance not found

            # If allowlist is not enabled, allow all users
            if not instance.allowlist_enabled:
                logger.debug(f"Allowlist disabled for instance '{instance_name}' - allowing user")
                return True

            # Check if user is in the allowlist
            allowed_user = (
                self.db.query(AllowedUser)
                .filter(
                    AllowedUser.instance_name == instance_name,
                    AllowedUser.channel_type == channel_type,
                    AllowedUser.user_identifier == user_identifier,
                    AllowedUser.is_active,
                )
                .first()
            )

            is_allowed = allowed_user is not None

            if is_allowed:
                logger.debug(f"User allowed: {channel_type}:{user_identifier} on {instance_name}")
            else:
                logger.info(f"User blocked: {channel_type}:{user_identifier} on {instance_name} (not in allowlist)")

            return is_allowed

        except Exception as e:
            logger.error(f"Error checking user allowlist: {str(e)}")
            return True  # Fail-safe: allow on error

    def add_user(
        self,
        instance_name: str,
        channel_type: str,
        user_identifier: str,
        display_name: Optional[str] = None,
        added_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AllowedUser:
        """
        Add a user to the allowlist.

        Args:
            instance_name: Name of the instance
            channel_type: Channel type (whatsapp, discord, etc.)
            user_identifier: Channel-specific user identifier
            display_name: Optional display name
            added_by: Who added this user
            notes: Optional notes

        Returns:
            The created AllowedUser object

        Raises:
            ValueError: If instance not found or user already exists
        """
        try:
            # Verify instance exists
            instance = self.db.query(InstanceConfig).filter(InstanceConfig.name == instance_name).first()

            if not instance:
                raise ValueError(f"Instance not found: {instance_name}")

            # Check if user already exists (including inactive ones)
            existing_user = (
                self.db.query(AllowedUser)
                .filter(
                    AllowedUser.instance_name == instance_name,
                    AllowedUser.channel_type == channel_type,
                    AllowedUser.user_identifier == user_identifier,
                )
                .first()
            )

            if existing_user:
                if existing_user.is_active:
                    raise ValueError(f"User already allowed: {channel_type}:{user_identifier}")
                else:
                    # Reactivate existing user
                    existing_user.is_active = True
                    existing_user.display_name = display_name or existing_user.display_name
                    existing_user.added_by = added_by or existing_user.added_by
                    existing_user.notes = notes or existing_user.notes
                    existing_user.updated_at = datetime_utcnow()

                    self.db.commit()
                    logger.info(f"Reactivated user: {channel_type}:{user_identifier} on {instance_name}")
                    return existing_user

            # Create new allowed user
            allowed_user = AllowedUser(
                instance_name=instance_name,
                channel_type=channel_type,
                user_identifier=user_identifier,
                display_name=display_name,
                added_by=added_by,
                notes=notes,
                is_active=True,
                created_at=datetime_utcnow(),
                updated_at=datetime_utcnow(),
            )

            self.db.add(allowed_user)
            self.db.commit()

            logger.info(f"Added user to allowlist: {channel_type}:{user_identifier} on {instance_name}")
            return allowed_user

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error adding user: {str(e)}")
            raise ValueError("Database constraint violation - user may already exist")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding user to allowlist: {str(e)}")
            raise

    def remove_user(self, instance_name: str, channel_type: str, user_identifier: str) -> bool:
        """
        Remove a user from the allowlist (soft delete).

        Args:
            instance_name: Name of the instance
            channel_type: Channel type (whatsapp, discord, etc.)
            user_identifier: Channel-specific user identifier

        Returns:
            True if user was removed, False if user was not found
        """
        try:
            allowed_user = (
                self.db.query(AllowedUser)
                .filter(
                    AllowedUser.instance_name == instance_name,
                    AllowedUser.channel_type == channel_type,
                    AllowedUser.user_identifier == user_identifier,
                    AllowedUser.is_active,
                )
                .first()
            )

            if not allowed_user:
                logger.warning(f"User not found in allowlist: {channel_type}:{user_identifier} on {instance_name}")
                return False

            # Soft delete by setting is_active to False
            allowed_user.is_active = False
            allowed_user.updated_at = datetime_utcnow()

            self.db.commit()

            logger.info(f"Removed user from allowlist: {channel_type}:{user_identifier} on {instance_name}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing user from allowlist: {str(e)}")
            raise

    def list_users(
        self, instance_name: Optional[str] = None, channel_type: Optional[str] = None, active_only: bool = True
    ) -> List[AllowedUser]:
        """
        List allowed users with optional filtering.

        Args:
            instance_name: Optional instance name filter
            channel_type: Optional channel type filter
            active_only: If True, only return active users

        Returns:
            List of AllowedUser objects
        """
        try:
            query = self.db.query(AllowedUser)

            if instance_name:
                query = query.filter(AllowedUser.instance_name == instance_name)

            if channel_type:
                query = query.filter(AllowedUser.channel_type == channel_type)

            if active_only:
                query = query.filter(AllowedUser.is_active)

            return query.order_by(AllowedUser.created_at.desc()).all()

        except Exception as e:
            logger.error(f"Error listing allowed users: {str(e)}")
            raise

    def enable_allowlist(self, instance_name: str) -> bool:
        """
        Enable the allowlist for an instance.

        Args:
            instance_name: Name of the instance

        Returns:
            True if enabled successfully
        """
        try:
            instance = self.db.query(InstanceConfig).filter(InstanceConfig.name == instance_name).first()

            if not instance:
                raise ValueError(f"Instance not found: {instance_name}")

            instance.allowlist_enabled = True
            instance.updated_at = datetime_utcnow()

            self.db.commit()

            logger.info(f"Enabled allowlist for instance: {instance_name}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error enabling allowlist: {str(e)}")
            raise

    def disable_allowlist(self, instance_name: str) -> bool:
        """
        Disable the allowlist for an instance.

        Args:
            instance_name: Name of the instance

        Returns:
            True if disabled successfully
        """
        try:
            instance = self.db.query(InstanceConfig).filter(InstanceConfig.name == instance_name).first()

            if not instance:
                raise ValueError(f"Instance not found: {instance_name}")

            instance.allowlist_enabled = False
            instance.updated_at = datetime_utcnow()

            self.db.commit()

            logger.info(f"Disabled allowlist for instance: {instance_name}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error disabling allowlist: {str(e)}")
            raise

    def get_instance_status(self, instance_name: str) -> Dict[str, Any]:
        """
        Get allowlist status and stats for an instance.

        Args:
            instance_name: Name of the instance

        Returns:
            Dictionary with status information
        """
        try:
            instance = self.db.query(InstanceConfig).filter(InstanceConfig.name == instance_name).first()

            if not instance:
                raise ValueError(f"Instance not found: {instance_name}")

            # Count allowed users by channel
            users_by_channel = {}
            total_users = 0

            for channel_type in ["whatsapp", "discord"]:  # Add more as needed
                count = (
                    self.db.query(AllowedUser)
                    .filter(
                        AllowedUser.instance_name == instance_name,
                        AllowedUser.channel_type == channel_type,
                        AllowedUser.is_active,
                    )
                    .count()
                )

                users_by_channel[channel_type] = count
                total_users += count

            return {
                "instance_name": instance_name,
                "allowlist_enabled": instance.allowlist_enabled,
                "total_allowed_users": total_users,
                "users_by_channel": users_by_channel,
                "status": "enabled" if instance.allowlist_enabled else "disabled",
            }

        except Exception as e:
            logger.error(f"Error getting instance status: {str(e)}")
            raise
