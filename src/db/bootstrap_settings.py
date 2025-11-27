"""
Bootstrap global settings with defaults and migrate from .env.

This module initializes global settings on application startup, including
auto-generation of the Evolution API key if not present.
"""

import logging
import secrets
from sqlalchemy.orm import Session

from src.db.models import SettingValueType
from src.services.settings_service import settings_service
from src.config import config

logger = logging.getLogger(__name__)


def bootstrap_global_settings(db: Session) -> None:
    """
    Initialize global settings with defaults and migrate from .env.

    This is called during application startup to ensure critical settings exist.
    For fresh installs, it auto-generates secure keys. For existing installs,
    it migrates settings from .env to database.

    Args:
        db: Database session
    """

    logger.info("Bootstrapping global settings...")

    # Define default settings
    default_settings = [
        {
            "key": "evolution_api_key",
            "value": None,  # Will be set below
            "value_type": SettingValueType.SECRET,
            "category": "integration",
            "description": "Global Evolution API authentication key (auto-generated or migrated from .env)",
            "is_secret": True,
            "is_required": True,
            "default_value": "",
        },
        {
            "key": "evolution_api_url",
            "value": config.get_env("EVOLUTION_URL", "http://localhost:18082"),
            "value_type": SettingValueType.STRING,
            "category": "integration",
            "description": "Default Evolution API base URL",
            "is_secret": False,
            "is_required": False,
            "default_value": "http://localhost:18082",
        },
        {
            "key": "max_instances_per_user",
            "value": "10",
            "value_type": SettingValueType.INTEGER,
            "category": "system",
            "description": "Maximum number of instances per user/tenant",
            "is_secret": False,
            "is_required": False,
            "default_value": "10",
            "validation_rules": {"min": 1, "max": 100},
        },
        {
            "key": "enable_analytics",
            "value": "true",
            "value_type": SettingValueType.BOOLEAN,
            "category": "system",
            "description": "Enable telemetry and analytics collection",
            "is_secret": False,
            "is_required": False,
            "default_value": "true",
        },
    ]

    # Handle Evolution API key separately (auto-generation or migration)
    _bootstrap_evolution_key(db)

    # Create other default settings
    for setting_def in default_settings:
        # Skip evolution_api_key (handled separately above)
        if setting_def["key"] == "evolution_api_key":
            continue

        existing = settings_service.get_setting(setting_def["key"], db)

        if not existing:
            try:
                settings_service.create_setting(
                    key=setting_def["key"],
                    value=setting_def["value"],
                    value_type=setting_def["value_type"],
                    db=db,
                    category=setting_def.get("category"),
                    description=setting_def.get("description"),
                    is_secret=setting_def.get("is_secret", False),
                    is_required=setting_def.get("is_required", False),
                    default_value=setting_def.get("default_value"),
                    validation_rules=setting_def.get("validation_rules"),
                    created_by="system_bootstrap"
                )
                logger.info(f"Created default setting: {setting_def['key']}")
            except Exception as e:
                logger.error(f"Failed to create setting '{setting_def['key']}': {e}")
        else:
            logger.debug(f"Setting '{setting_def['key']}' already exists, skipping")

    logger.info("Global settings bootstrap complete")


def _bootstrap_evolution_key(db: Session) -> None:
    """
    Bootstrap Evolution API key with auto-generation or .env migration.

    This handles three scenarios:
    1. Fresh install (no .env, no database) → Auto-generate secure key
    2. Existing .env, no database → Migrate from .env to database
    3. Database exists → Keep existing value

    Args:
        db: Database session
    """
    # Check if evolution_api_key already exists in database
    existing = settings_service.get_setting("evolution_api_key", db)

    if existing:
        logger.info(f"Evolution API key already exists in database (key: {existing.key})")
        return

    # Try to read from .env first (migration path for existing installations)
    env_key = config.get_env("EVOLUTION_API_KEY", "")

    if env_key:
        # Migrate from .env to database
        logger.info("Migrating Evolution API key from .env to database")
        key_value = env_key
        migration_source = "migrated from .env"
    else:
        # Auto-generate secure key for fresh install
        key_value = secrets.token_hex(16)  # 32-character hexadecimal string
        logger.info(f"Auto-generated Evolution API key: {key_value[:8]}***{key_value[-4:]}")
        migration_source = "auto-generated on first startup"

    # Create setting in database
    try:
        settings_service.create_setting(
            key="evolution_api_key",
            value=key_value,
            value_type=SettingValueType.SECRET,
            category="integration",
            description=f"Global Evolution API authentication key ({migration_source})",
            is_secret=True,
            is_required=True,
            default_value="",
            created_by="system_bootstrap",
            db=db
        )
        logger.info(f"Evolution API key stored in database ({migration_source})")
    except Exception as e:
        logger.error(f"Failed to create evolution_api_key setting: {e}")
        raise
