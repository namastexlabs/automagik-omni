"""
Settings Service for global application settings management.

Provides CRUD operations, type casting, validation, and audit trail.
"""

import logging
import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from src.db.models import GlobalSetting, SettingChangeHistory, SettingValueType
from src.utils.datetime_utils import datetime_utcnow

logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing global application settings."""

    def __init__(self):
        """Initialize the settings service."""
        pass

    # CRUD Operations

    def get_setting(self, key: str, db: Session) -> Optional[GlobalSetting]:
        """Get a setting by key.

        Args:
            key: Setting key
            db: Database session

        Returns:
            GlobalSetting object or None if not found
        """
        return db.query(GlobalSetting).filter_by(key=key).first()

    def get_setting_value(
        self,
        key: str,
        db: Session,
        default: Any = None,
        cast_type: bool = True
    ) -> Any:
        """
        Get a setting's value with type casting.

        Args:
            key: Setting key
            db: Database session
            default: Default value if not found
            cast_type: Whether to cast to the defined value_type

        Returns:
            Setting value (type-casted) or default
        """
        setting = self.get_setting(key, db)

        if not setting or setting.value is None:
            return default

        if not cast_type:
            return setting.value

        # Type casting based on value_type
        try:
            if setting.value_type == SettingValueType.BOOLEAN:
                return setting.value.lower() in ('true', '1', 'yes')
            elif setting.value_type == SettingValueType.INTEGER:
                return int(setting.value)
            elif setting.value_type == SettingValueType.JSON:
                return json.loads(setting.value)
            else:  # STRING, SECRET
                return setting.value
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to cast setting '{key}' to {setting.value_type}: {e}")
            return default

    def list_settings(
        self,
        db: Session,
        category: Optional[str] = None,
        include_secrets: bool = True
    ) -> List[GlobalSetting]:
        """
        List all settings, optionally filtered by category.

        Args:
            db: Database session
            category: Optional category filter
            include_secrets: Whether to include secret values (will be masked in API)

        Returns:
            List of GlobalSetting objects
        """
        query = db.query(GlobalSetting)

        if category:
            query = query.filter_by(category=category)

        return query.all()

    def create_setting(
        self,
        key: str,
        value: Any,
        value_type: str,
        db: Session,
        category: Optional[str] = None,
        description: Optional[str] = None,
        is_secret: bool = False,
        is_required: bool = False,
        default_value: Any = None,
        validation_rules: Optional[Dict] = None,
        created_by: Optional[str] = None
    ) -> GlobalSetting:
        """
        Create a new global setting.

        Args:
            key: Unique setting key
            value: Setting value (will be converted to string)
            value_type: Type from SettingValueType enum
            db: Database session
            category: Optional category grouping
            description: Human-readable description
            is_secret: Whether to mask in UI
            is_required: Whether required for app operation
            default_value: Default fallback value (will be converted to string)
            validation_rules: JSON validation rules
            created_by: User/API key identifier

        Returns:
            Created GlobalSetting

        Raises:
            ValueError: If setting with key already exists
        """
        # Convert value to string for storage
        value_str = self._serialize_value(value, value_type)

        # Convert default_value to string if provided
        default_val_str = self._serialize_value(default_value, value_type) if default_value is not None else None

        # Check if setting already exists
        existing = self.get_setting(key, db)
        if existing:
            raise ValueError(f"Setting with key '{key}' already exists")

        # Create setting
        setting = GlobalSetting(
            key=key,
            value=value_str,
            value_type=value_type,
            category=category,
            description=description,
            is_secret=is_secret,
            is_required=is_required,
            default_value=default_val_str,
            validation_rules=json.dumps(validation_rules) if validation_rules else None,
            created_at=datetime_utcnow(),
            updated_at=datetime_utcnow(),
            created_by=created_by,
            updated_by=created_by
        )

        db.add(setting)
        db.commit()
        db.refresh(setting)

        logger.info(f"Created setting '{key}' in category '{category}'")
        return setting

    def update_setting(
        self,
        key: str,
        value: Any,
        db: Session,
        updated_by: Optional[str] = None,
        change_reason: Optional[str] = None
    ) -> GlobalSetting:
        """
        Update an existing setting value with audit trail.

        Args:
            key: Setting key
            value: New value
            db: Database session
            updated_by: User/API key identifier
            change_reason: Optional reason for change

        Returns:
            Updated GlobalSetting

        Raises:
            ValueError: If setting not found
        """
        setting = self.get_setting(key, db)

        if not setting:
            raise ValueError(f"Setting '{key}' not found")

        # Record old value for audit
        old_value = setting.value

        # Convert new value to string
        value_type = setting.value_type or SettingValueType.STRING
        new_value_str = self._serialize_value(value, value_type)

        # Update setting
        setting.value = new_value_str
        setting.updated_by = updated_by
        setting.updated_at = datetime_utcnow()

        # Create audit record
        history = SettingChangeHistory(
            setting_id=setting.id,
            old_value=old_value,
            new_value=new_value_str,
            changed_by=updated_by,
            changed_at=datetime_utcnow(),
            change_reason=change_reason
        )

        db.add(history)
        db.commit()
        db.refresh(setting)

        logger.info(f"Updated setting '{key}' by '{updated_by}'")
        return setting

    def delete_setting(self, key: str, db: Session) -> bool:
        """Delete a setting (if not required).

        Args:
            key: Setting key
            db: Database session

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete a required setting
        """
        setting = self.get_setting(key, db)

        if not setting:
            return False

        if setting.is_required:
            raise ValueError(f"Cannot delete required setting '{key}'")

        db.delete(setting)
        db.commit()

        logger.info(f"Deleted setting '{key}'")
        return True

    # Helper methods

    def _serialize_value(self, value: Any, value_type: SettingValueType | str) -> str:
        """Serialize value to string for storage."""
        try:
            value_type_enum = value_type if isinstance(value_type, SettingValueType) else SettingValueType(value_type)
        except Exception:
            value_type_enum = SettingValueType.STRING

        if value is None:
            return ""

        if value_type_enum == SettingValueType.BOOLEAN:
            # Normalize boolean to "true"/"false"
            if isinstance(value, bool):
                return "true" if value else "false"
            if isinstance(value, str):
                return "true" if value.lower() in ("true", "1", "yes", "on") else "false"
            return "false"

        if value_type_enum == SettingValueType.INTEGER:
            try:
                return str(int(value))
            except (TypeError, ValueError):
                return "0"

        if value_type_enum == SettingValueType.JSON:
            try:
                return json.dumps(value)
            except TypeError:
                return ""

        return str(value)

    def validate_setting(self, setting: GlobalSetting, value: Any) -> bool:
        """
        Validate a value against setting's validation rules.

        Args:
            setting: GlobalSetting object
            value: Value to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if not setting.validation_rules:
            return True

        try:
            rules = json.loads(str(setting.validation_rules))
        except Exception:
            return True # Ignore invalid rules if we can't parse them

        # Type validation
        if setting.value_type == SettingValueType.INTEGER:
            if not isinstance(value, int):
                raise ValueError("Value must be an integer")
            if 'min' in rules and value < rules['min']:
                raise ValueError(f"Value must be >= {rules['min']}")
            if 'max' in rules and value > rules['max']:
                raise ValueError(f"Value must be <= {rules['max']}")

        elif setting.value_type == SettingValueType.STRING:
            if 'pattern' in rules:
                import re
                if not re.match(rules['pattern'], str(value)):
                    raise ValueError(f"Value does not match pattern: {rules['pattern']}")
            if 'min_length' in rules and len(str(value)) < rules['min_length']:
                raise ValueError(f"Value must be at least {rules['min_length']} characters")
            if 'max_length' in rules and len(str(value)) > rules['max_length']:
                raise ValueError(f"Value must be at most {rules['max_length']} characters")

        return True

    def get_change_history(
        self,
        key: str,
        db: Session,
        limit: int = 50
    ) -> List[SettingChangeHistory]:
        """Get change history for a setting.

        Args:
            key: Setting key
            db: Database session
            limit: Maximum number of history entries to return

        Returns:
            List of SettingChangeHistory objects
        """
        setting = self.get_setting(key, db)
        if not setting:
            return []

        return (
            db.query(SettingChangeHistory)
            .filter_by(setting_id=setting.id)
            .order_by(SettingChangeHistory.changed_at.desc())
            .limit(limit)
            .all()
        )


# Singleton instance
settings_service = SettingsService()


# =============================================================================
# Unified API Key Architecture
# =============================================================================
# A single omni_api_key is used for:
# 1. Client → Omni API authentication (x-api-key header)
# 2. Omni → Evolution API authentication (apikey header)
# 3. Evolution server configuration (AUTHENTICATION_API_KEY)
#
# All legacy functions (get_evolution_api_key_global, get_whatsapp_web_api_key_global)
# now return omni_api_key for backward compatibility.
# =============================================================================


def get_omni_api_key_global() -> str:
    """
    Get the unified Omni API key from database with .env fallback.

    This is the PRIMARY key used for:
    - Client authentication to Omni API
    - Omni authentication to Evolution API
    - Evolution server configuration

    Returns:
        Unified API key string (format: sk-omni-{token})
    """
    from src.db.database import SessionLocal
    from src.config import config

    # Try database first (primary source)
    try:
        with SessionLocal() as db:
            key = settings_service.get_setting_value("omni_api_key", db, default=None)
            if key:
                return key
    except Exception as e:
        logger.warning(f"Failed to get Omni API key from database: {e}")

    # Fallback to .env (backward compatibility)
    return config.get_env("AUTOMAGIK_OMNI_API_KEY", "")


def get_whatsapp_web_api_key_global() -> str:
    """
    Get WhatsApp Web API key (returns unified omni_api_key).

    This is an alias for get_omni_api_key_global() for backward compatibility.
    The unified key architecture uses omni_api_key for all authentication.

    Returns:
        Unified API key string
    """
    return get_omni_api_key_global()


def get_whatsapp_web_api_url_global() -> str:
    """
    Get WhatsApp Web API URL from database with .env fallback.

    Returns:
        WhatsApp Web API URL string
    """
    from src.db.database import SessionLocal
    from src.config import config

    # Try database first (stored as evolution_api_url for backward compatibility)
    try:
        with SessionLocal() as db:
            url = settings_service.get_setting_value("evolution_api_url", db, default=None)
            if url:
                return url
    except Exception as e:
        logger.warning(f"Failed to get WhatsApp Web API URL from database: {e}")

    # Fallback to .env
    return config.get_env("EVOLUTION_URL", "http://localhost:18082")


# Backward compatibility alias
def get_evolution_api_key_global() -> str:
    """
    Get Evolution API key (returns unified omni_api_key).

    DEPRECATED: Use get_omni_api_key_global() instead.
    This alias exists for backward compatibility only.

    Returns:
        Unified API key string
    """
    return get_omni_api_key_global()
