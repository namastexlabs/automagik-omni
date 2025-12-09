"""
Database state service for comparing runtime vs saved configuration.

This service provides utilities to:
1. Extract runtime configuration from frozen config object
2. Extract saved configuration from omni_global_settings table
3. Compare states to detect if restart is required
4. Check if database type is locked (instances exist)

Solves the bug where GET /database/config reads from frozen runtime config
instead of persisted settings in the database.
"""

import logging
from typing import Optional, Tuple
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from src.config import config
from src.services.settings_service import settings_service

logger = logging.getLogger(__name__)


class DatabaseStateService:
    """Service for managing database configuration state."""

    def get_runtime_config(self) -> dict:
        """Get current runtime configuration from frozen config object.

        The config object is populated from environment variables at startup
        and is immutable during application runtime.

        Returns:
            Dictionary with runtime configuration values
        """
        return {
            "db_type": "postgresql",  # PostgreSQL only - no SQLite support
            "postgres_url_masked": self._mask_url(config.database.postgres_url),
            "table_prefix": config.database.table_prefix,
            "pool_size": config.database.pool_size,
            "pool_max_overflow": config.database.pool_max_overflow,
        }

    def get_saved_config(self, db: Session) -> Optional[dict]:
        """Get saved configuration from omni_global_settings table.

        Args:
            db: Database session

        Returns:
            Dictionary with saved configuration, or None if never configured via wizard
        """
        db_type = settings_service.get_setting_value("database_type", db)

        if db_type is None:
            return None  # Never configured via wizard

        postgres_url = settings_service.get_setting_value("postgres_url", db)
        redis_uri = settings_service.get_setting_value("cache_redis_uri", db)

        # Get the last updated timestamp from database_type setting
        db_type_setting = settings_service.get_setting("database_type", db)
        last_updated = None
        if db_type_setting and db_type_setting.updated_at:
            last_updated = db_type_setting.updated_at.isoformat()

        # Parse PostgreSQL URL for display fields (without sensitive data)
        postgres_host = None
        postgres_port = None
        postgres_database = None
        if postgres_url:
            try:
                parsed = urlparse(postgres_url)
                postgres_host = parsed.hostname
                postgres_port = str(parsed.port) if parsed.port else "5432"
                postgres_database = parsed.path.lstrip("/") if parsed.path else None
            except Exception as e:
                logger.warning(f"Failed to parse postgres URL: {e}")

        return {
            "db_type": db_type,
            "postgres_url_masked": self._mask_url(postgres_url) if postgres_url else None,
            "postgres_host": postgres_host,
            "postgres_port": postgres_port,
            "postgres_database": postgres_database,
            "redis_enabled": settings_service.get_setting_value("cache_redis_enabled", db, default=False),
            "redis_url_masked": self._mask_url(redis_uri) if redis_uri else None,
            "redis_prefix_key": settings_service.get_setting_value("cache_redis_prefix_key", db),
            "redis_ttl": settings_service.get_setting_value("cache_redis_ttl", db),
            "redis_save_instances": settings_service.get_setting_value("cache_redis_save_instances", db),
            "last_updated_at": last_updated,
        }

    def check_requires_restart(self, runtime: dict, saved: Optional[dict]) -> Tuple[bool, Optional[str]]:
        """Compare runtime vs saved configuration to detect restart requirement.

        Args:
            runtime: Runtime configuration dictionary
            saved: Saved configuration dictionary (may be None)

        Returns:
            Tuple of (requires_restart, reason_message)
        """
        if saved is None:
            return False, None

        # Check database type mismatch (PostgreSQL only - no SQLite support)
        runtime_type = runtime.get("db_type", "postgresql").lower()
        saved_type = (saved.get("db_type") or "postgresql").lower()

        if runtime_type != saved_type:
            return True, f"Database type changed from {runtime_type} to {saved_type}"

        # Check PostgreSQL URL change (when using PostgreSQL)
        if saved_type == "postgresql":
            runtime_masked = runtime.get("postgres_url_masked")
            saved_masked = saved.get("postgres_url_masked")

            # Both should be masked the same way, so we can compare
            if runtime_masked != saved_masked:
                return True, "PostgreSQL connection URL changed"

        return False, None

    def is_db_locked(self, db: Session) -> bool:
        """Check if database type is locked (instances exist).

        Database type cannot be changed after instances are created
        because the data schema depends on it.

        Args:
            db: Database session

        Returns:
            True if locked (instances exist), False otherwise
        """
        from src.db.models import InstanceConfig

        try:
            instance_count = db.query(InstanceConfig).count()
            return instance_count > 0
        except Exception as e:
            logger.warning(f"Failed to check instance count: {e}")
            return False

    def is_setup_completed(self, db: Session) -> bool:
        """Check if initial setup has been completed.

        Args:
            db: Database session

        Returns:
            True if setup_completed flag is true
        """
        return settings_service.get_setting_value("setup_completed", db, default=False)

    def _mask_url(self, url: Optional[str]) -> Optional[str]:
        """Mask sensitive parts of a URL (password, partial host).

        Args:
            url: Full URL string

        Returns:
            Masked URL string or None
        """
        if not url:
            return None

        try:
            parsed = urlparse(url)

            # Build masked userinfo
            if parsed.username:
                userinfo = f"{parsed.username[:4]}***"
                if parsed.password:
                    userinfo += ":****"
            else:
                userinfo = None

            # Build host part
            if userinfo:
                host_part = f"{userinfo}@{parsed.hostname}"
            else:
                host_part = parsed.hostname or ""

            if parsed.port:
                host_part += f":{parsed.port}"

            return f"{parsed.scheme}://{host_part}{parsed.path or ''}"

        except Exception as e:
            logger.warning(f"Failed to mask URL: {e}")
            return "***masked***"


# Singleton instance
database_state_service = DatabaseStateService()
