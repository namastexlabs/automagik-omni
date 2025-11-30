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
        {
            "key": "setup_completed",
            "value": None,  # Will be set by auto-detection below
            "value_type": SettingValueType.BOOLEAN,
            "category": "system",
            "description": "Tracks whether initial setup wizard has been completed",
            "is_secret": False,
            "is_required": False,
            "default_value": "false",
        },
    ]

    # Handle Evolution API key separately (auto-generation or migration)
    _bootstrap_evolution_key(db)

    # Handle Omni API key separately (auto-generation or migration)
    _bootstrap_omni_api_key(db)

    # Handle setup_completed flag with auto-detection
    _bootstrap_setup_completed(db)

    # Create other default settings
    for setting_def in default_settings:
        # Skip evolution_api_key and setup_completed (handled separately above)
        if setting_def["key"] in ("evolution_api_key", "setup_completed"):
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


def _bootstrap_omni_api_key(db: Session) -> None:
    """
    Bootstrap Omni API key with auto-generation or .env migration.

    This handles three scenarios:
    1. Fresh install (no .env, no database) → Auto-generate secure key
    2. Existing .env, no database → Migrate from .env to database
    3. Database exists → Keep existing value

    Args:
        db: Database session
    """
    # Check if omni_api_key already exists in database
    existing = settings_service.get_setting("omni_api_key", db)

    if existing:
        logger.info(f"Omni API key already exists in database (key: {existing.key})")
        return

    # Try to read from .env first (migration path for existing installations)
    env_key = config.get_env("AUTOMAGIK_OMNI_API_KEY", "")

    # Check if env key is a placeholder value
    placeholder_values = ["", "your-secret-api-key-here", "changeme"]
    if env_key and env_key not in placeholder_values:
        # Migrate from .env to database
        logger.info("Migrating Omni API key from .env to database")
        key_value = env_key
        migration_source = "migrated from .env"
    else:
        # Auto-generate secure key for fresh install
        key_value = f"sk-omni-{secrets.token_urlsafe(32)}"
        logger.info(f"Auto-generated Omni API key: {key_value[:12]}***{key_value[-4:]}")
        migration_source = "auto-generated on first startup"

    # Create setting in database
    try:
        settings_service.create_setting(
            key="omni_api_key",
            value=key_value,
            value_type=SettingValueType.SECRET,
            category="security",
            description=f"Omni API authentication key ({migration_source})",
            is_secret=True,
            is_required=True,
            default_value="",
            created_by="system_bootstrap",
            db=db
        )
        logger.info(f"Omni API key stored in database ({migration_source})")
    except Exception as e:
        logger.error(f"Failed to create omni_api_key setting: {e}")
        raise


def _bootstrap_setup_completed(db: Session) -> None:
    """
    Bootstrap setup_completed flag with auto-detection of existing installations.

    This handles two scenarios:
    1. Fresh install → Set to "false" (requires onboarding)
    2. Existing install → Set to "true" (skip onboarding)

    Auto-detection checks for:
    - Existing instances in omni_instance_configs table
    - Existing database_type configuration

    The flag is recalculated on every startup to handle cases where users
    delete their database for a fresh install.

    Args:
        db: Database session
    """
    from src.db.models import InstanceConfig

    # Check if setup_completed already exists in database
    existing = settings_service.get_setting("setup_completed", db)

    # ALWAYS run auto-detection (don't return early)
    # This ensures we detect fresh installs even if flag previously existed
    is_existing_install = False

    # Check 1: Do any instances exist?
    instance_count = db.query(InstanceConfig).count()
    if instance_count > 0:
        is_existing_install = True
        logger.info(f"Existing installation detected: {instance_count} instances found")

    # Check 2: Is database_type already configured?
    if not is_existing_install:
        db_type_setting = settings_service.get_setting("database_type", db)
        if db_type_setting:
            is_existing_install = True
            logger.info(f"Existing installation detected: database_type = {db_type_setting.value}")

    # Calculate what value SHOULD be based on current state
    # Use boolean values (not strings) for proper serialization
    setup_value_bool = is_existing_install
    setup_value_str = "true" if is_existing_install else "false"
    description = (
        "Initial setup wizard completed (existing installation detected)"
        if is_existing_install
        else "Initial setup wizard has not been completed yet"
    )

    if existing:
        # Setting exists - check if it needs updating
        current_is_true = existing.value.lower() in ("true", "1", "yes")
        should_be_true = is_existing_install

        if current_is_true == should_be_true:
            # Value is already correct, no update needed
            logger.info(f"setup_completed flag is correct: {existing.value}")
            return
        else:
            # Value changed (e.g., user deleted DB for fresh install)
            logger.info(f"Recalculating setup_completed: {existing.value} -> {setup_value_str}")
            try:
                # Pass boolean (not string) for proper type conversion
                settings_service.update_setting("setup_completed", setup_value_bool, db)
                logger.info(f"setup_completed flag updated to '{setup_value_str}'")
            except Exception as e:
                logger.error(f"Failed to update setup_completed setting: {e}")
                raise
    else:
        # Create new setting (first time)
        try:
            # Pass boolean (not string) for proper type conversion
            settings_service.create_setting(
                key="setup_completed",
                value=setup_value_bool,
                value_type=SettingValueType.BOOLEAN,
                category="system",
                description=description,
                is_secret=False,
                is_required=False,
                default_value=False,  # Use boolean, not string
                created_by="system_bootstrap",
                db=db
            )
            logger.info(f"setup_completed flag created: '{setup_value_str}' ({description})")
        except Exception as e:
            logger.error(f"Failed to create setup_completed setting: {e}")
            raise
