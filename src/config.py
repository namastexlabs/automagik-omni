"""
Configuration management for Stan WhatsApp Agent.
Loads configuration from environment variables.
"""

import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any
import pytz
from datetime import datetime

# Load environment variables from .env file (optional - only if file exists)
# This should be the ONLY place where load_dotenv is called in the entire application
# .env is now optional - all settings can be configured via database or auto-generated

# Get logger for this module
logger = logging.getLogger(__name__)


def _clean_timezone_env() -> str:
    """Clean timezone environment variable by removing quotes."""
    tz = os.getenv("AUTOMAGIK_TIMEZONE", "UTC")
    # Remove quotes if present
    if tz.startswith('"') and tz.endswith('"'):
        tz = tz[1:-1]
    if tz.startswith("'") and tz.endswith("'"):
        tz = tz[1:-1]
    return tz


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = "%(asctime)s - \033[36m%(name)s\033[0m - %(levelname)s - %(message)s"
    date_format: str = "%H:%M:%S %Z"  # Time format with timezone info
    use_colors: bool = True
    shorten_paths: bool = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_LOG_VERBOSITY", "short").lower() != "full"
    )
    log_folder: str = Field(default_factory=lambda: os.getenv("LOG_FOLDER", "./logs"))
    enable_file_logging: bool = Field(default_factory=lambda: bool(os.getenv("LOG_FOLDER", "./logs")))


class DatabaseConfig(BaseModel):
    """Database configuration - PostgreSQL only (embedded via pgserve)."""

    # PostgreSQL configuration (embedded PostgreSQL via pgserve)
    postgres_url: str = Field(
        default_factory=lambda: os.getenv(
            "AUTOMAGIK_OMNI_POSTGRES_URL",
            "postgresql://postgres:postgres@127.0.0.1:5432/automagik_omni"  # Default embedded pgserve
        )
    )

    # Legacy: explicit database URL override (takes precedence)
    url: str = Field(default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_DATABASE_URL", ""))

    # Table prefix for PostgreSQL (to coexist with Evolution tables)
    table_prefix: str = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_TABLE_PREFIX", "omni_")
    )

    # Connection pooling settings (for PostgreSQL)
    pool_size: int = Field(
        default_factory=lambda: int(os.getenv("AUTOMAGIK_OMNI_DB_POOL_SIZE", "5"))
    )
    pool_max_overflow: int = Field(
        default_factory=lambda: int(os.getenv("AUTOMAGIK_OMNI_DB_POOL_MAX_OVERFLOW", "10"))
    )
    pool_recycle: int = Field(
        default_factory=lambda: int(os.getenv("AUTOMAGIK_OMNI_DB_POOL_RECYCLE", "3600"))
    )

    @property
    def database_url(self) -> str:
        """Get the complete database URL for runtime data (PostgreSQL only)."""
        # Explicit URL override takes precedence
        if self.url:
            return self.url
        # Use PostgreSQL (always)
        return self.postgres_url


class TracingConfig(BaseModel):
    """Message tracing configuration."""

    enabled: bool = Field(default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_ENABLE_TRACING", "true").lower() == "true")
    retention_days: int = Field(default_factory=lambda: int(os.getenv("AUTOMAGIK_OMNI_TRACE_RETENTION_DAYS", "30")))
    max_payload_size: int = Field(
        default_factory=lambda: int(os.getenv("AUTOMAGIK_OMNI_TRACE_MAX_PAYLOAD_SIZE", "1048576"))
    )  # 1MB
    include_sensitive_data: bool = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_TRACE_INCLUDE_SENSITIVE", "false").lower() == "true"
    )


class ApiConfig(BaseModel):
    """API Server configuration."""

    host: str = Field(default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_API_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("AUTOMAGIK_OMNI_API_PORT", "8881")))
    api_key: str = Field(default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_API_KEY", ""))
    prod_server_url: str = Field(default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_PROD_SERVER_URL", ""))
    title: str = "Automagik Omni API"
    description: str = "Multi-tenant omnichannel messaging API"
    version: str = "0.2.0"


class TimezoneConfig(BaseModel):
    """Timezone configuration."""

    timezone: str = Field(default_factory=lambda: _clean_timezone_env())

    @property
    def tz(self) -> pytz.BaseTzInfo:
        """Get the timezone object."""
        try:
            return pytz.timezone(self.timezone)
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone '{self.timezone}', falling back to UTC")
            return pytz.UTC

    def now(self) -> datetime:
        """Get current datetime in configured timezone."""
        return datetime.now(self.tz)

    def utc_to_local(self, utc_dt: datetime) -> datetime:
        """Convert UTC datetime to local timezone."""
        if utc_dt.tzinfo is None:
            utc_dt = pytz.UTC.localize(utc_dt)
        return utc_dt.astimezone(self.tz)

    def local_to_utc(self, local_dt: datetime) -> datetime:
        """Convert local datetime to UTC."""
        if local_dt.tzinfo is None:
            local_dt = self.tz.localize(local_dt)
        return local_dt.astimezone(pytz.UTC)


class EnvironmentConfig(BaseModel):
    """Environment configuration for unified Python architecture."""

    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"


class CorsConfig(BaseModel):
    """CORS configuration for API server."""

    allowed_origins: list[str] = Field(default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_ORIGINS", "*").split(","))
    allow_credentials: bool = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_CREDENTIALS", "true").lower() == "true"
    )
    allow_methods: list[str] = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    )
    allow_headers: list[str] = Field(default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_HEADERS", "*").split(","))


class LegacyConfig(BaseModel):
    """Legacy Hive API compatibility configuration."""

    skip_health_check: bool = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_SKIP_LEGACY_HEALTH_CHECK", "false").lower() == "true"
    )


class Config(BaseModel):
    """Main application configuration."""

    environment: EnvironmentConfig = EnvironmentConfig()
    logging: LoggingConfig = LoggingConfig()
    api: ApiConfig = ApiConfig()
    database: DatabaseConfig = DatabaseConfig()
    tracing: TracingConfig = TracingConfig()
    timezone: TimezoneConfig = TimezoneConfig()
    cors: CorsConfig = CorsConfig()
    legacy: LegacyConfig = LegacyConfig()

    @property
    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        # Basic configuration validation - API key required
        valid = bool(self.api.api_key)
        if valid:
            logger.info("✅ Configuration valid - Multi-tenant webhook mode")
        return valid

    def get_env(self, key: str, default: Any = "") -> Any:
        """Get environment variable with fallback to default."""
        return os.getenv(key, default)


# Create the global config instance
config = Config()
