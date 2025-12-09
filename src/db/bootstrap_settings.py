"""
Bootstrap global settings with defaults and migrate from .env.

This module initializes global settings on application startup, including
auto-generation of the unified Omni API key.

## Unified Key Architecture

A single `omni_api_key` is used for:
1. Client → Omni API authentication (x-api-key header)
2. Omni → Evolution API authentication (apikey header)
3. Evolution server configuration (AUTHENTICATION_API_KEY)

Legacy `evolution_api_key` is deprecated and migrated to use `omni_api_key`.
Helper functions (get_evolution_api_key_global, get_whatsapp_web_api_key_global)
now return `omni_api_key` for backward compatibility.
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
    # Note: evolution_* keys are kept for backward compatibility
    # New code should use whatsapp_web_* keys (see aliases below)
    default_settings = [
        {
            "key": "evolution_api_key",
            "value": None,  # Will be set below
            "value_type": SettingValueType.SECRET,
            "category": "integration",
            "description": "WhatsApp Web API authentication key (alias: whatsapp_web_api_key)",
            "is_secret": True,
            "is_required": True,
            "default_value": "",
        },
        {
            "key": "evolution_api_url",
            # Use gateway proxy URL - Evolution runs on dynamic ports managed by gateway
            "value": config.get_env(
                "EVOLUTION_URL", f"http://localhost:{config.get_env('OMNI_PORT', '8882')}/evolution"
            ),
            "value_type": SettingValueType.STRING,
            "category": "integration",
            "description": "Default WhatsApp Web API base URL (alias: whatsapp_web_api_url)",
            "is_secret": False,
            "is_required": False,
            "default_value": f"http://localhost:{config.get_env('OMNI_PORT', '8882')}/evolution",
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
        # Channel configuration settings
        {
            "key": "channel_whatsapp_enabled",
            "value": "true",  # WhatsApp enabled by default (primary channel)
            "value_type": SettingValueType.BOOLEAN,
            "category": "channels",
            "description": "Enable WhatsApp Web channel via Evolution API",
            "is_secret": False,
            "is_required": False,
            "default_value": "true",
        },
        {
            "key": "channel_discord_enabled",
            "value": "false",  # Discord requires manual configuration
            "value_type": SettingValueType.BOOLEAN,
            "category": "channels",
            "description": "Enable Discord channel (requires bot token setup)",
            "is_secret": False,
            "is_required": False,
            "default_value": "false",
        },
    ]

    # Handle Omni API key FIRST (unified key architecture)
    # All other keys derive from omni_api_key
    _bootstrap_omni_api_key(db)

    # Handle Evolution API key migration (deprecated - uses omni_api_key)
    _bootstrap_evolution_key(db)

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
                    created_by="system_bootstrap",
                )
                logger.info(f"Created default setting: {setting_def['key']}")
            except Exception as e:
                logger.error(f"Failed to create setting '{setting_def['key']}': {e}")
        else:
            logger.debug(f"Setting '{setting_def['key']}' already exists, skipping")

    logger.info("Global settings bootstrap complete")


def _bootstrap_evolution_key(db: Session) -> None:
    """
    DEPRECATED: Evolution now uses unified omni_api_key.

    This function handles migration for existing installations that have
    a separate evolution_api_key. New installs use omni_api_key directly.

    Migration strategy:
    1. If evolution_api_key exists and differs from omni_api_key → backup and remove
    2. If evolution_api_key doesn't exist → no action needed (use omni_api_key)

    Args:
        db: Database session
    """
    # Check if legacy evolution_api_key exists
    existing_evo_key = settings_service.get_setting("evolution_api_key", db)
    omni_key = settings_service.get_setting("omni_api_key", db)

    if not existing_evo_key:
        # No legacy key - fresh install or already migrated
        logger.info("No separate evolution_api_key found - using unified omni_api_key")
        return

    if not omni_key:
        # Edge case: evolution_api_key exists but omni_api_key doesn't
        # This shouldn't happen since _bootstrap_omni_api_key runs first
        logger.warning("evolution_api_key exists but omni_api_key missing - keeping evolution_api_key")
        return

    # Check if keys are different (need migration)
    if existing_evo_key.value == omni_key.value:
        # Keys already match - remove the duplicate
        logger.info("evolution_api_key matches omni_api_key - removing duplicate")
        try:
            # Mark as deprecated but don't delete yet (for backward compatibility)
            settings_service.update_setting(
                "evolution_api_key",
                omni_key.value,  # Ensure it matches omni_api_key
                db,
                updated_by="system_bootstrap",
                change_reason="Unified with omni_api_key (deprecated)",
            )
        except Exception as e:
            logger.warning(f"Could not update evolution_api_key: {e}")
    else:
        # Keys differ - migrate to unified key
        logger.info("Migrating evolution_api_key to use unified omni_api_key")
        logger.info("Old evolution_api_key will be replaced with omni_api_key")

        # Backup old key for reference
        try:
            backup_key = f"evolution_api_key_backup_{secrets.token_hex(4)}"
            settings_service.create_setting(
                key=backup_key,
                value=existing_evo_key.value,
                value_type=SettingValueType.SECRET,
                category="integration",
                description="Backup of legacy evolution_api_key before unification",
                is_secret=True,
                is_required=False,
                default_value="",
                created_by="system_bootstrap",
                db=db,
            )
            logger.info(f"Backed up old evolution_api_key to {backup_key}")
        except Exception as e:
            logger.warning(f"Could not backup evolution_api_key: {e}")

        # Update evolution_api_key to match omni_api_key
        try:
            settings_service.update_setting(
                "evolution_api_key",
                omni_key.value,
                db,
                updated_by="system_bootstrap",
                change_reason="Unified with omni_api_key",
            )
            logger.info("evolution_api_key now unified with omni_api_key")
        except Exception as e:
            logger.error(f"Failed to unify evolution_api_key: {e}")
            # Non-fatal - system will still work via omni_api_key alias


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

    # Strict validation: Keys must follow the standard format (sk-omni-...)
    # This automatically filters out insecure defaults/placeholders from previous installs
    if existing:
        if existing.value and existing.value.startswith("sk-omni-"):
            logger.info(f"Omni API key already exists in database (key: {existing.key})")
            return
        else:
            logger.warning("Existing Omni API key does not match security format (sk-omni-...). Regenerating.")
            # Delete the invalid setting so we can recreate it below
            db.delete(existing)
            db.commit()

    # Try to read from .env first (migration path for existing installations)
    # DEPRECATED: .env support removed. Only DB or auto-gen.

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
            db=db,
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
        current_is_true = (existing.value or "false").lower() in ("true", "1", "yes")
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
                db=db,
            )
            logger.info(f"setup_completed flag created: '{setup_value_str}' ({description})")
        except Exception as e:
            logger.error(f"Failed to create setup_completed setting: {e}")
            raise
