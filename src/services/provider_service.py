"""
Provider Service for Agent Provider management.

Provides CRUD operations, health checks, and agent/team fetching for reusable
agent provider configurations that can be shared across instances.
"""

import logging
import httpx
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from src.db.models import AgentProvider
from src.utils.datetime_utils import datetime_utcnow

logger = logging.getLogger(__name__)


class ProviderService:
    """Service for managing Agent Provider configurations."""

    def __init__(self):
        """Initialize the provider service."""
        self._http_timeout = 10.0  # seconds

    # CRUD Operations

    def get_provider(self, provider_id: int, db: Session) -> Optional[AgentProvider]:
        """Get a provider by ID.

        Args:
            provider_id: Provider ID
            db: Database session

        Returns:
            AgentProvider object or None if not found
        """
        return db.query(AgentProvider).filter_by(id=provider_id).first()

    def get_provider_by_name(self, name: str, db: Session) -> Optional[AgentProvider]:
        """Get a provider by name.

        Args:
            name: Provider name
            db: Database session

        Returns:
            AgentProvider object or None if not found
        """
        return db.query(AgentProvider).filter_by(name=name).first()

    def list_providers(self, db: Session, include_inactive: bool = False) -> List[AgentProvider]:
        """List all providers.

        Args:
            db: Database session
            include_inactive: Whether to include inactive providers

        Returns:
            List of AgentProvider objects
        """
        query = db.query(AgentProvider)

        if not include_inactive:
            query = query.filter_by(is_active=True)

        return query.order_by(AgentProvider.name).all()

    def create_provider(
        self,
        name: str,
        api_url: str,
        api_key: str,
        db: Session,
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> AgentProvider:
        """Create a new agent provider.

        Args:
            name: Unique display name
            api_url: Base API URL
            api_key: API authentication key
            db: Database session
            description: Optional description
            is_active: Whether the provider is active

        Returns:
            Created AgentProvider

        Raises:
            ValueError: If provider with name already exists
        """
        # Check if provider already exists
        existing = self.get_provider_by_name(name, db)
        if existing:
            raise ValueError(f"Provider with name '{name}' already exists")

        # Create provider
        provider = AgentProvider(
            name=name,
            api_url=api_url.rstrip("/"),  # Normalize URL
            api_key=api_key,
            description=description,
            is_active=is_active,
            last_health_status="unknown",
            created_at=datetime_utcnow(),
            updated_at=datetime_utcnow(),
        )

        db.add(provider)
        db.commit()
        db.refresh(provider)

        logger.info(f"Created agent provider '{name}'")
        return provider

    def update_provider(
        self,
        provider_id: int,
        db: Session,
        name: Optional[str] = None,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> AgentProvider:
        """Update an existing provider.

        Args:
            provider_id: Provider ID
            db: Database session
            name: New name (optional)
            api_url: New API URL (optional)
            api_key: New API key (optional)
            description: New description (optional)
            is_active: New active status (optional)

        Returns:
            Updated AgentProvider

        Raises:
            ValueError: If provider not found or name conflict
        """
        provider = self.get_provider(provider_id, db)

        if not provider:
            raise ValueError(f"Provider with ID {provider_id} not found")

        # Check for name conflict if changing name
        if name and name != provider.name:
            existing = self.get_provider_by_name(name, db)
            if existing:
                raise ValueError(f"Provider with name '{name}' already exists")
            provider.name = name

        if api_url is not None:
            provider.api_url = api_url.rstrip("/")

        if api_key is not None:
            provider.api_key = api_key

        if description is not None:
            provider.description = description

        if is_active is not None:
            provider.is_active = is_active

        provider.updated_at = datetime_utcnow()

        db.commit()
        db.refresh(provider)

        logger.info(f"Updated agent provider '{provider.name}'")
        return provider

    def delete_provider(self, provider_id: int, db: Session) -> bool:
        """Delete a provider.

        Note: Instances using this provider will have their agent_provider_id
        set to NULL due to ON DELETE SET NULL constraint.

        Args:
            provider_id: Provider ID
            db: Database session

        Returns:
            True if deleted, False if not found
        """
        provider = self.get_provider(provider_id, db)

        if not provider:
            return False

        db.delete(provider)
        db.commit()

        logger.info(f"Deleted agent provider '{provider.name}'")
        return True

    # Health Check

    async def check_health(self, provider_id: int, db: Session) -> Dict[str, Any]:
        """Check the health of a provider's API.

        Calls GET /health on the provider's API URL.

        Args:
            provider_id: Provider ID
            db: Database session

        Returns:
            Dict with health status information
        """
        provider = self.get_provider(provider_id, db)

        if not provider:
            return {"status": "error", "message": "Provider not found"}

        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                response = await client.get(
                    f"{provider.api_url}/health",
                    headers={"x-api-key": provider.api_key},
                )

                if response.status_code == 200:
                    status = "healthy"
                else:
                    status = "unhealthy"

                # Update provider health status
                provider.last_health_check = datetime_utcnow()
                provider.last_health_status = status
                db.commit()

                return {
                    "status": status,
                    "http_status": response.status_code,
                    "checked_at": provider.last_health_check.isoformat(),
                }

        except httpx.TimeoutException:
            status = "unhealthy"
            provider.last_health_check = datetime_utcnow()
            provider.last_health_status = status
            db.commit()

            return {
                "status": status,
                "message": "Connection timeout",
                "checked_at": provider.last_health_check.isoformat(),
            }

        except Exception as e:
            status = "unhealthy"
            provider.last_health_check = datetime_utcnow()
            provider.last_health_status = status
            db.commit()

            logger.warning(f"Health check failed for provider '{provider.name}': {e}")
            return {
                "status": status,
                "message": str(e),
                "checked_at": provider.last_health_check.isoformat(),
            }

    # Agent/Team Fetching

    async def fetch_agents(self, provider_id: int, db: Session) -> List[Dict[str, Any]]:
        """Fetch available agents from the provider's API.

        Calls GET /agents on the provider's API URL.

        Args:
            provider_id: Provider ID
            db: Database session

        Returns:
            List of agent dictionaries
        """
        provider = self.get_provider(provider_id, db)

        if not provider:
            raise ValueError("Provider not found")

        if not provider.is_active:
            raise ValueError("Provider is not active")

        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                response = await client.get(
                    f"{provider.api_url}/agents",
                    headers={"x-api-key": provider.api_key},
                )

                if response.status_code == 200:
                    data = response.json()
                    # Handle both list response and dict with 'agents' key
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "agents" in data:
                        return data["agents"]
                    return []
                else:
                    logger.warning(
                        f"Failed to fetch agents from provider '{provider.name}': HTTP {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Error fetching agents from provider '{provider.name}': {e}")
            raise ValueError(f"Failed to fetch agents: {str(e)}")

    async def fetch_teams(self, provider_id: int, db: Session) -> List[Dict[str, Any]]:
        """Fetch available teams from the provider's API.

        Calls GET /teams on the provider's API URL.

        Args:
            provider_id: Provider ID
            db: Database session

        Returns:
            List of team dictionaries
        """
        provider = self.get_provider(provider_id, db)

        if not provider:
            raise ValueError("Provider not found")

        if not provider.is_active:
            raise ValueError("Provider is not active")

        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                response = await client.get(
                    f"{provider.api_url}/teams",
                    headers={"x-api-key": provider.api_key},
                )

                if response.status_code == 200:
                    data = response.json()
                    # Handle both list response and dict with 'teams' key
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "teams" in data:
                        return data["teams"]
                    return []
                else:
                    logger.warning(
                        f"Failed to fetch teams from provider '{provider.name}': HTTP {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Error fetching teams from provider '{provider.name}': {e}")
            raise ValueError(f"Failed to fetch teams: {str(e)}")

    # Auto-discovery from existing instances

    def auto_discover_providers(self, db: Session) -> List[AgentProvider]:
        """Auto-discover and create providers from existing instance configurations.

        Scans all instances that have agent_api_url configured but no provider linked.
        Groups by api_url and creates providers for each unique URL.
        Links instances to the newly created providers.

        Args:
            db: Database session

        Returns:
            List of newly created AgentProvider objects
        """
        from src.db.models import InstanceConfig

        created_providers = []

        # Find instances with agent credentials but no provider linked
        instances_without_provider = (
            db.query(InstanceConfig)
            .filter(
                InstanceConfig.agent_api_url.isnot(None),
                InstanceConfig.agent_api_url != "",
                InstanceConfig.agent_provider_id.is_(None),
            )
            .all()
        )

        if not instances_without_provider:
            logger.info("No instances with agent credentials found for provider auto-discovery")
            return created_providers

        # Group instances by api_url
        url_groups: Dict[str, List[Any]] = {}
        for instance in instances_without_provider:
            url = instance.agent_api_url.rstrip("/") if instance.agent_api_url else ""
            if url:
                if url not in url_groups:
                    url_groups[url] = []
                url_groups[url].append(instance)

        logger.info(f"Found {len(url_groups)} unique agent API URLs for provider auto-discovery")

        # Create providers for each unique URL
        for api_url, instances in url_groups.items():
            # Check if a provider with this URL already exists
            existing = db.query(AgentProvider).filter(AgentProvider.api_url == api_url).first()
            if existing:
                # Link instances to existing provider
                for instance in instances:
                    instance.agent_provider_id = existing.id
                    logger.info(f"Linked instance '{instance.name}' to existing provider '{existing.name}'")
                continue

            # Get API key from first instance (they should all have the same key for the same URL)
            api_key = None
            for instance in instances:
                if instance.agent_api_key:
                    api_key = instance.agent_api_key
                    break

            if not api_key:
                logger.warning(f"No API key found for URL {api_url}, skipping provider creation")
                continue

            # Generate provider name from URL
            try:
                from urllib.parse import urlparse

                parsed = urlparse(api_url)
                hostname = parsed.hostname or "unknown"
                # Create a descriptive name
                base_name = f"Auto: {hostname}"

                # Ensure unique name
                name = base_name
                counter = 1
                while self.get_provider_by_name(name, db):
                    name = f"{base_name} ({counter})"
                    counter += 1

                # Create the provider
                provider = AgentProvider(
                    name=name,
                    api_url=api_url,
                    api_key=api_key,
                    description=f"Auto-discovered from {len(instances)} instance(s)",
                    is_active=True,
                    last_health_status="unknown",
                    created_at=datetime_utcnow(),
                    updated_at=datetime_utcnow(),
                )
                db.add(provider)
                db.flush()  # Get the ID

                # Link all instances to this provider
                for instance in instances:
                    instance.agent_provider_id = provider.id
                    logger.info(f"Linked instance '{instance.name}' to new provider '{provider.name}'")

                created_providers.append(provider)
                logger.info(f"Auto-created provider '{name}' from {len(instances)} instance(s)")

            except Exception as e:
                logger.error(f"Failed to auto-create provider for {api_url}: {e}")
                continue

        db.commit()

        if created_providers:
            logger.info(f"Auto-discovery complete: created {len(created_providers)} new provider(s)")
        else:
            logger.info("Auto-discovery complete: no new providers created")

        return created_providers


# Singleton instance
provider_service = ProviderService()


def auto_discover_providers_on_startup():
    """Run provider auto-discovery on application startup.

    This function is called during app startup to automatically create
    providers from existing instance configurations.
    """
    from src.db.database import SessionLocal

    try:
        with SessionLocal() as db:
            providers = provider_service.auto_discover_providers(db)
            if providers:
                logger.info(f"Startup: Auto-discovered {len(providers)} agent provider(s)")
    except Exception as e:
        logger.warning(f"Startup: Provider auto-discovery failed: {e}")
