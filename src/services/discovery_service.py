"""
Discovery service for auto-detecting Evolution instances and syncing with database.
"""

import logging
import secrets
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from src.channels.whatsapp.evolution_client import EvolutionInstance
from src.db.models import InstanceConfig
from src.utils.instance_utils import normalize_instance_name

logger = logging.getLogger(__name__)


def _generate_api_key() -> str:
    """Generate a secure random API key for Evolution instances.

    Returns:
        32-character hexadecimal string suitable for API authentication
    """
    return secrets.token_hex(16)


class DiscoveryService:
    """Service for discovering and syncing Evolution instances."""

    def __init__(self):
        """Initialize discovery service."""
        self.evolution_client = None

    async def discover_evolution_instances(self, db: Session) -> List[InstanceConfig]:
        """
        Discover Evolution instances using bootstrap credentials from environment.

        Always uses the bootstrap EVOLUTION_API_KEY from environment for authentication
        with Evolution API, regardless of database state. Per-instance evolution_keys
        are generated locally and stored for display/reference only.

        Args:
            db: Database session

        Returns:
            List of discovered/synced instances
        """
        logger.info("Starting Evolution instance discovery...")

        # Get bootstrap credentials from environment
        from src.config import config

        global_url = config.get_env("EVOLUTION_URL", "http://localhost:18082")
        bootstrap_key = config.get_env("EVOLUTION_API_KEY")

        if not bootstrap_key:
            logger.warning(
                "No EVOLUTION_API_KEY found in environment. "
                "Please set EVOLUTION_API_KEY in .env to enable WhatsApp instance discovery."
            )
            return []

        # Get existing WhatsApp instances to track which ones we've already synced
        existing_instances = (
            db.query(InstanceConfig)
            .filter(
                InstanceConfig.channel_type == "whatsapp",
            )
            .all()
        )

        existing_names = {inst.whatsapp_instance or inst.name for inst in existing_instances}
        logger.info(f"Found {len(existing_instances)} existing WhatsApp instances in database")

        synced_instances = []

        logger.info(f"Using bootstrap EVOLUTION_API_KEY for instance discovery (URL: {global_url})")

        # Query Evolution API using bootstrap credentials
        try:
            logger.debug(f"Querying Evolution API: {global_url}")

            from src.channels.whatsapp.evolution_client import EvolutionClient

            evolution_client = EvolutionClient(global_url, bootstrap_key)

            # Fetch all instances from Evolution API
            evolution_instances = await evolution_client.fetch_instances()
            logger.info(f"Found {len(evolution_instances)} instances on {global_url}")

            for evo_instance in evolution_instances:
                logger.debug(f"Processing Evolution instance: {evo_instance.instanceName}")

                # Check if instance already exists in database by WhatsApp instance name
                existing_instance = (
                    db.query(InstanceConfig).filter(
                        InstanceConfig.whatsapp_instance == evo_instance.instanceName
                    ).first()
                )

                if existing_instance:
                    # Update existing instance with latest Evolution data
                    updated = self._update_existing_instance(existing_instance, evo_instance)
                    if updated:
                        logger.info(f"Updated existing instance: {evo_instance.instanceName}")
                    synced_instances.append(existing_instance)
                else:
                    # Create new instance from Evolution data using bootstrap credentials
                    new_instance = await self._create_instance_from_evolution(
                        evo_instance, db, global_url, bootstrap_key
                    )
                    if new_instance:
                        logger.info(f"Created new instance from Evolution: {evo_instance.instanceName}")
                        synced_instances.append(new_instance)

        except Exception as e:
            logger.warning(f"Failed to query Evolution API {global_url}: {e}")
            import traceback
            logger.debug(f"Discovery error details: {traceback.format_exc()}")

        # Commit all changes
        try:
            db.commit()
            logger.info(f"Discovery complete - {len(synced_instances)} instances synced")
        except Exception as e:
            logger.error(f"Error committing discovery changes: {e}")
            db.rollback()

        return synced_instances

    def _update_existing_instance(self, db_instance: InstanceConfig, evo_instance: EvolutionInstance) -> bool:
        """
        Update existing database instance with Evolution data (conservative approach).

        Only updates the connection status, leaving user configuration intact.

        Args:
            db_instance: Database instance to update
            evo_instance: Evolution instance data

        Returns:
            True if instance was updated, False otherwise
        """
        updated = False

        # Only update the connection status - don't override user-configured fields
        evolution_status_map = {
            "open": True,
            "close": False,
            "connecting": False,
            "created": False,
        }

        expected_active = evolution_status_map.get(evo_instance.status, False)
        if db_instance.is_active != expected_active:
            db_instance.is_active = expected_active
            updated = True
            logger.debug(f"Updated {db_instance.name} status: {evo_instance.status} -> active={expected_active}")

        # Only update default_agent if it's currently empty/default and Evolution has profile data
        if (not db_instance.default_agent or db_instance.default_agent == "default-agent") and evo_instance.profileName:
            db_instance.default_agent = evo_instance.profileName
            updated = True
            logger.debug(f"Updated {db_instance.name} default_agent to Evolution profile: {evo_instance.profileName}")

        # Update profile information from Evolution API
        if evo_instance.profileName and db_instance.profile_name != evo_instance.profileName:
            db_instance.profile_name = evo_instance.profileName
            updated = True

        if evo_instance.profilePicUrl and db_instance.profile_pic_url != evo_instance.profilePicUrl:
            db_instance.profile_pic_url = evo_instance.profilePicUrl
            updated = True

        if evo_instance.ownerJid and db_instance.owner_jid != evo_instance.ownerJid:
            db_instance.owner_jid = evo_instance.ownerJid
            updated = True

        return updated

    async def _create_instance_from_evolution(
        self,
        evo_instance: EvolutionInstance,
        db: Session,
        evolution_url: str,
        evolution_key: str,
    ) -> Optional[InstanceConfig]:
        """
        Create a new database instance from Evolution instance data.

        Only creates instances that don't already exist in the database.

        Args:
            evo_instance: Evolution instance data
            db: Database session

        Returns:
            Created instance or None if creation failed
        """
        try:
            # Double-check that instance doesn't already exist
            existing = db.query(InstanceConfig).filter(InstanceConfig.name == evo_instance.instanceName).first()

            if existing:
                logger.debug(f"Instance {evo_instance.instanceName} already exists in database, skipping creation")
                return None

            # Map Evolution status to our boolean

            # Normalize the name for our database but keep original for Evolution API
            normalized_name = normalize_instance_name(evo_instance.instanceName)

            # Auto-generate a unique API key for this instance (transparent to user)
            auto_generated_key = _generate_api_key()

            new_instance = InstanceConfig(
                name=normalized_name,
                channel_type="whatsapp",
                default_agent=evo_instance.profileName or "default-agent",
                evolution_url=evolution_url,
                evolution_key=auto_generated_key,  # Use auto-generated key instead of passed-in credentials
                agent_api_url="http://localhost:8000",  # Default agent URL
                agent_api_key="default-key",  # Default agent key
                whatsapp_instance=evo_instance.instanceName,  # Preserve original case for Evolution API calls
                is_default=False,  # Never make auto-discovered instances default
                # Profile information from Evolution API
                profile_name=evo_instance.profileName,
                profile_pic_url=evo_instance.profilePicUrl,
                owner_jid=evo_instance.ownerJid,
            )

            logger.debug(f"Auto-generated API key for instance {normalized_name}")

            # Log normalization if name changed
            if evo_instance.instanceName != normalized_name:
                logger.info(
                    f"Auto-discovered instance name normalized: '{evo_instance.instanceName}' -> '{normalized_name}'"
                )

            db.add(new_instance)
            db.flush()  # Get the ID

            logger.info(f"Auto-created instance from Evolution: {new_instance.name} (ID: {new_instance.id})")
            return new_instance

        except Exception as e:
            logger.error(f"Error creating instance from Evolution data: {e}")
            return None

    async def sync_instance_status(self, instance_name: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Sync a specific instance's status with Evolution API.

        Args:
            instance_name: Name of instance to sync
            db: Database session

        Returns:
            Evolution connection state or None if sync failed
        """
        # Get the instance to get its Evolution API credentials
        db_instance = db.query(InstanceConfig).filter(InstanceConfig.name == instance_name).first()

        if not db_instance:
            logger.warning(f"Instance {instance_name} not found in database")
            return None

        if not db_instance.evolution_url or not db_instance.evolution_key:
            logger.warning(f"Instance {instance_name} missing Evolution API credentials")
            return None

        try:
            # Create Evolution client with instance-specific credentials
            from src.channels.whatsapp.evolution_client import EvolutionClient

            evolution_client = EvolutionClient(db_instance.evolution_url, db_instance.evolution_key)

            # Get current status from Evolution
            connection_state = await evolution_client.get_connection_state(instance_name)

            # Update status based on Evolution response
            if "instance" in connection_state:
                evo_state = connection_state["instance"].get("state", "unknown")
                new_active = evo_state == "open"

                if db_instance.is_active != new_active:
                    db_instance.is_active = new_active
                    db.commit()
                    logger.info(f"Updated {instance_name} status: {evo_state} -> active={new_active}")

            return connection_state

        except Exception as e:
            logger.error(f"Error syncing instance {instance_name} status: {e}")
            return None


# Global discovery service instance
discovery_service = DiscoveryService()
