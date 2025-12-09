"""
Discovery service for auto-detecting WhatsApp Web instances and syncing with database.

Note: Uses Evolution API as the underlying protocol for WhatsApp Web connectivity.
"""

import logging
import os
import secrets
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from src.channels.whatsapp.evolution_client import EvolutionInstance
from src.db.models import InstanceConfig
from src.utils.instance_utils import normalize_instance_name
from src.ip_utils import replace_localhost_with_ipv4

logger = logging.getLogger(__name__)


def _generate_api_key() -> str:
    """Generate a secure random API key for Evolution instances.

    Returns:
        32-character hexadecimal string suitable for API authentication
    """
    return secrets.token_hex(16)


class DiscoveryService:
    """Service for discovering and syncing WhatsApp Web instances via Evolution API."""

    def __init__(self):
        """Initialize discovery service."""
        self.whatsapp_web_client = None  # EvolutionClient instance for API calls

    async def discover_evolution_instances(self, db: Session) -> List[InstanceConfig]:
        """
        Discover WhatsApp Web instances using bootstrap credentials from database.

        Always uses the bootstrap WhatsApp Web API key from database for authentication
        with Evolution API, regardless of per-instance state. Per-instance whatsapp_web_keys
        are generated locally and stored for display/reference only.

        Note: Method name kept as 'discover_evolution_instances' for backward compatibility.

        Args:
            db: Database session

        Returns:
            List of discovered/synced instances
        """
        logger.info("Starting WhatsApp Web instance discovery via Evolution API...")

        # Get bootstrap credentials from database (with .env fallback)
        from src.config import config
        from src.services.settings_service import settings_service, get_omni_api_key_global

        # Use gateway proxy URL - Evolution runs on dynamic ports managed by gateway
        gateway_port = os.getenv("OMNI_PORT", "8882")
        global_url = settings_service.get_setting_value("evolution_api_url", db, default=f"http://localhost:{gateway_port}/evolution")

        # Use unified omni_api_key (same key for Omni API and Evolution API)
        bootstrap_key = get_omni_api_key_global()

        if not bootstrap_key:
            logger.warning(
                "No API key found in database or environment. "
                "The key should be auto-generated on first startup."
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

        logger.info(f"Found {len(existing_instances)} existing WhatsApp instances in database")

        # 2. Get list of instances from Evolution API

        synced_instances = []

        logger.info(f"Using bootstrap WhatsApp Web API key for instance discovery (URL: {global_url})")

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

        # Sync webhook URLs for all discovered instances to ensure they point to current API port
        if synced_instances:
            await self._sync_webhook_urls(synced_instances, evolution_client, config)

        return synced_instances

    async def _sync_webhook_urls(self, instances: List[InstanceConfig], evolution_client, config) -> None:
        """
        Sync webhook URLs for all instances to point to the current Python API port.

        This ensures that after a restart (when ports may change dynamically),
        Evolution webhooks are automatically updated to reach the Python API.

        Args:
            instances: List of instances to sync
            evolution_client: EvolutionClient instance
            config: Config module with api.host and api.port
        """
        if not hasattr(config, 'api') or not config.api.port:
            logger.warning("Cannot sync webhook URLs: config.api.port not available")
            return

        current_host = config.api.host or "127.0.0.1"
        current_port = config.api.port

        logger.info(f"Syncing webhook URLs to http://{current_host}:{current_port}/webhook/evolution/...")

        for instance in instances:
            instance_name = instance.whatsapp_instance or instance.name
            expected_webhook_url = replace_localhost_with_ipv4(
                f"http://{current_host}:{current_port}/webhook/evolution/{instance_name}"
            )

            try:
                # Check current webhook URL
                current_webhook = await evolution_client.get_webhook(instance_name)
                current_url = current_webhook.get("url", "") if current_webhook else ""

                # Only update if URL is different (wrong port or host)
                if current_url != expected_webhook_url:
                    logger.info(f"Updating webhook for {instance_name}: {current_url} -> {expected_webhook_url}")
                    await evolution_client.set_webhook(
                        instance_name,
                        expected_webhook_url,
                        events=["MESSAGES_UPSERT"],
                        webhook_base64=True
                    )
                    logger.info(f"✓ Webhook synced for {instance_name}")
                else:
                    logger.debug(f"Webhook already correct for {instance_name}")

            except Exception as e:
                logger.warning(f"Failed to sync webhook for {instance_name}: {e}")
                # Continue with other instances even if one fails

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

        # DEPRECATED: Token sync removed (Option A: Bootstrap Key Only)
        # Per-instance tokens are no longer used for authentication

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

            # Use Evolution's instance token as the auth key (per-instance authentication)
            # If Evolution doesn't provide a token, fall back to generating one
            instance_token = evo_instance.token if evo_instance.token else _generate_api_key()

            new_instance = InstanceConfig(
                name=normalized_name,
                channel_type="whatsapp",
                default_agent=evo_instance.profileName or "default-agent",
                evolution_url=evolution_url,
                evolution_key=instance_token,  # Use Evolution's per-instance token
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
        Sync a specific instance's status with WhatsApp Web API (via Evolution).

        Args:
            instance_name: Name of instance to sync
            db: Database session

        Returns:
            WhatsApp Web connection state or None if sync failed
        """
        # Get the instance to get its WhatsApp Web API credentials
        db_instance = db.query(InstanceConfig).filter(InstanceConfig.name == instance_name).first()

        if not db_instance:
            logger.warning(f"Instance {instance_name} not found in database")
            return None

        if not db_instance.whatsapp_web_url:  # Use alias
            logger.warning(f"Instance {instance_name} missing WhatsApp Web API URL")
            return None

        try:
            # Create Evolution client with bootstrap key from database
            from src.channels.whatsapp.evolution_client import EvolutionClient
            from src.services.settings_service import get_omni_api_key_global

            # Use unified omni_api_key (same key for Omni API and Evolution API)
            bootstrap_key = get_omni_api_key_global()

            if not bootstrap_key:
                logger.warning("No API key found in database or environment, cannot sync instance status")
                return None

            # Pass instance name for logging/debugging only (auth uses bootstrap key)
            whatsapp_instance_name = db_instance.whatsapp_instance or instance_name
            evolution_client = EvolutionClient(db_instance.evolution_url, bootstrap_key, whatsapp_instance_name)

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
