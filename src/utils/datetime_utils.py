"""
Timezone-aware datetime utilities.
Provides consistent datetime handling across the application using configured timezone.
"""

from datetime import datetime
import pytz


def get_config_timezone():
    """Get the configured timezone, avoiding circular imports."""
    try:
        from src.config import config

        return config.timezone
    except ImportError:
        # Fallback for cases where config isn't available
        import os

        timezone_str = os.getenv("AUTOMAGIK_TIMEZONE", "UTC")
        # Remove quotes if present
        if timezone_str.startswith('"') and timezone_str.endswith('"'):
            timezone_str = timezone_str[1:-1]
        if timezone_str.startswith("'") and timezone_str.endswith("'"):
            timezone_str = timezone_str[1:-1]
        try:
            return pytz.timezone(timezone_str)
        except pytz.UnknownTimeZoneError:
            return pytz.UTC


def utcnow() -> datetime:
    """
    Get current UTC datetime.
    Replacement for datetime.utcnow() that ensures timezone awareness.

    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(pytz.UTC)


def now() -> datetime:
    """
    Get current datetime in configured timezone.

    Returns:
        datetime: Current time in configured timezone
    """
    tz_config = get_config_timezone()
    if hasattr(tz_config, "now"):
        return tz_config.now()
    else:
        # Fallback when tz_config is a timezone object
        return datetime.now(tz_config)


def to_utc(dt: datetime) -> datetime:
    """
    Convert datetime to UTC.

    Args:
        dt: Datetime to convert (can be naive or timezone-aware)

    Returns:
        datetime: UTC datetime with timezone info
    """
    if dt.tzinfo is None:
        # Assume naive datetime is in configured timezone
        tz_config = get_config_timezone()
        if hasattr(tz_config, "tz"):
            tz = tz_config.tz
        else:
            tz = tz_config
        dt = tz.localize(dt)

    return dt.astimezone(pytz.UTC)


def to_local(dt: datetime) -> datetime:
    """
    Convert datetime to configured local timezone.

    Args:
        dt: Datetime to convert (can be naive or timezone-aware)

    Returns:
        datetime: Datetime in configured timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = pytz.UTC.localize(dt)

    tz_config = get_config_timezone()
    if hasattr(tz_config, "tz"):
        target_tz = tz_config.tz
    else:
        target_tz = tz_config

    return dt.astimezone(target_tz)


def format_local(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """
    Format datetime in local timezone.

    Args:
        dt: Datetime to format
        format_str: Format string (default includes timezone)

    Returns:
        str: Formatted datetime string in local timezone
    """
    local_dt = to_local(dt)
    return local_dt.strftime(format_str)


# For backwards compatibility and database defaults
def datetime_utcnow() -> datetime:
    """UTC datetime for use as SQLAlchemy default."""
    return utcnow()
