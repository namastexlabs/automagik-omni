"""
Discovery service for auto-detecting Evolution instances and syncing with database.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from src.channels.whatsapp.evolution_client import EvolutionInstance
from src.db.models import InstanceConfig
from src.utils.instance_utils import normalize_instance_name

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Service for discovering and syncing Evolution instances."""

    def __init__(self):
        """Initialize discovery service."""
        self.evolution_client = None

    async def discover_evolution_instances(self, db: Session) -> List[InstanceConfig]:
        """
        Discover Evolution instances using existing database configurations.

        Uses Evolution API credentials from existing instances in the database
        to discover additional instances from those Evolution API servers.

        Args:
            db: Database session

        Returns:
            List of discovered/synced instances
        """
        logger.info("Starting Evolution instance discovery...")

        # Get existing WhatsApp instances with Evolution API configuration
        existing_instances = (
            db.query(InstanceConfig)
            .filter(
                InstanceConfig.channel_type == "whatsapp",
                InstanceConfig.evolution_url.isnot(None),
                InstanceConfig.evolution_key.isnot(None),
            )
            .all()
        )

        if not existing_instances:
            logger.info(
                "No existing WhatsApp instances with Evolution API config found"
            )
            return []

        synced_instances = []

        # Group instances by unique Evolution API servers
        evolution_servers = {}
        for instance in existing_instances:
            server_key = f"{instance.evolution_url}::{instance.evolution_key}"
            if server_key not in evolution_servers:
                evolution_servers[server_key] = {
                    "url": instance.evolution_url,
                    "key": instance.evolution_key,
                    "instances": [],
                }
            evolution_servers[server_key]["instances"].append(instance)

        logger.info(f"Found {len(evolution_servers)} unique Evolution API servers")

        # Query each Evolution API server
        for server_info in evolution_servers.values():
            try:
                logger.debug(f"Querying Evolution API: {server_info['url']}")

                # Create client for this specific server
                from src.channels.whatsapp.evolution_client import EvolutionClient

                evolution_client = EvolutionClient(
                    server_info["url"], server_info["key"]
                )

                # Fetch all instances from this Evolution API
                evolution_instances = await evolution_client.fetch_instances()
                logger.info(
                    f"Found {len(evolution_instances)} instances on {server_info['url']}"
                )

                for evo_instance in evolution_instances:
                    logger.debug(
                        f"Processing Evolution instance: {evo_instance.instanceName}"
                    )

                    # Check if instance already exists in database
                    existing_instance = (
                        db.query(InstanceConfig)
                        .filter(InstanceConfig.name == evo_instance.instanceName)
                        .first()
                    )

                    if existing_instance:
                        # Update existing instance with latest Evolution data
                        updated = self._update_existing_instance(
                            existing_instance, evo_instance
                        )
                        if updated:
                            logger.info(
                                f"Updated existing instance: {evo_instance.instanceName}"
                            )
                        synced_instances.append(existing_instance)
                    else:
                        # Create new instance from Evolution data using this server's config
                        new_instance = await self._create_instance_from_evolution(
                            evo_instance, db, server_info["url"], server_info["key"]
                        )
                        if new_instance:
                            logger.info(
                                f"Created new instance from Evolution: {evo_instance.instanceName}"
                            )
                            synced_instances.append(new_instance)

            except Exception as e:
                logger.warning(
                    f"Failed to query Evolution API {server_info['url']}: {e}"
                )
                continue

        # Commit all changes
        try:
            db.commit()
            logger.info(
                f"Discovery complete - {len(synced_instances)} instances synced"
            )
        except Exception as e:
            logger.error(f"Error committing discovery changes: {e}")
            db.rollback()

        return synced_instances

    def _update_existing_instance(
        self, db_instance: InstanceConfig, evo_instance: EvolutionInstance
    ) -> bool:
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
            logger.debug(
                f"Updated {db_instance.name} status: {evo_instance.status} -> active={expected_active}"
            )

        # Only update default_agent if it's currently empty/default and Evolution has profile data
        if (
            not db_instance.default_agent
            or db_instance.default_agent == "default-agent"
        ) and evo_instance.profileName:
            db_instance.default_agent = evo_instance.profileName
            updated = True
            logger.debug(
                f"Updated {db_instance.name} default_agent to Evolution profile: {evo_instance.profileName}"
            )

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
            existing = (
                db.query(InstanceConfig)
                .filter(InstanceConfig.name == evo_instance.instanceName)
                .first()
            )

            if existing:
                logger.debug(
                    f"Instance {evo_instance.instanceName} already exists in database, skipping creation"
                )
                return None

            # Map Evolution status to our boolean

            # Normalize the name for our database but keep original for Evolution API
            normalized_name = normalize_instance_name(evo_instance.instanceName)

            new_instance = InstanceConfig(
                name=normalized_name,
                channel_type="whatsapp",
                default_agent=evo_instance.profileName or "default-agent",
                evolution_url=evolution_url,
                evolution_key=evolution_key,
                agent_api_url="http://localhost:8000",  # Default agent URL
                agent_api_key="default-key",  # Default agent key
                whatsapp_instance=evo_instance.instanceName,  # Preserve original case for Evolution API calls
                is_default=False,  # Never make auto-discovered instances default
            )

            # Log normalization if name changed
            if evo_instance.instanceName != normalized_name:
                logger.info(
                    f"Auto-discovered instance name normalized: '{evo_instance.instanceName}' -> '{normalized_name}'"
                )

            db.add(new_instance)
            db.flush()  # Get the ID

            logger.info(
                f"Auto-created instance from Evolution: {new_instance.name} (ID: {new_instance.id})"
            )
            return new_instance

        except Exception as e:
            logger.error(f"Error creating instance from Evolution data: {e}")
            return None

    async def sync_instance_status(
        self, instance_name: str, db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Sync a specific instance's status with Evolution API.

        Args:
            instance_name: Name of instance to sync
            db: Database session

        Returns:
            Evolution connection state or None if sync failed
        """
        # Get the instance to get its Evolution API credentials
        db_instance = (
            db.query(InstanceConfig)
            .filter(InstanceConfig.name == instance_name)
            .first()
        )

        if not db_instance:
            logger.warning(f"Instance {instance_name} not found in database")
            return None

        if not db_instance.evolution_url or not db_instance.evolution_key:
            logger.warning(
                f"Instance {instance_name} missing Evolution API credentials"
            )
            return None

        try:
            # Create Evolution client with instance-specific credentials
            from src.channels.whatsapp.evolution_client import EvolutionClient

            evolution_client = EvolutionClient(
                db_instance.evolution_url, db_instance.evolution_key
            )

            # Get current status from Evolution
            connection_state = await evolution_client.get_connection_state(
                instance_name
            )

            # Update status based on Evolution response
            if "instance" in connection_state:
                evo_state = connection_state["instance"].get("state", "unknown")
                new_active = evo_state == "open"

                if db_instance.is_active != new_active:
                    db_instance.is_active = new_active
                    db.commit()
                    logger.info(
                        f"Updated {instance_name} status: {evo_state} -> active={new_active}"
                    )

            return connection_state

        except Exception as e:
            logger.error(f"Error syncing instance {instance_name} status: {e}")
            return None


# Global discovery service instance
discovery_service = DiscoveryService()
