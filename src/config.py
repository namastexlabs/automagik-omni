"""
Configuration management for Stan WhatsApp Agent.
Loads configuration from environment variables.
"""

import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Any
import pytz
from datetime import datetime

# Load environment variables from .env file
# This should be the ONLY place where load_dotenv is called in the entire application
load_dotenv(override=True)  

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

class RabbitMQConfig(BaseModel):
    """RabbitMQ configuration (DISABLED - HTTP webhooks only)."""
    uri: str = Field(default_factory=lambda: os.getenv("RABBITMQ_URI", ""))
    exchange_name: str = Field(default_factory=lambda: os.getenv("RABBITMQ_EXCHANGE", "evolution_exchange"))
    instance_name: str = Field(default_factory=lambda: os.getenv("WHATSAPP_INSTANCE", ""))
    global_mode: bool = False  # Always use instance-specific mode

class AgentApiConfig(BaseModel):
    """Agent API configuration."""
    url: str = Field(default_factory=lambda: os.getenv("AGENT_API_URL", ""))
    api_key: str = Field(default_factory=lambda: os.getenv("AGENT_API_KEY", ""))
    default_agent_name: str = Field(default_factory=lambda: os.getenv("DEFAULT_AGENT_NAME", ""))
    timeout: int = Field(default_factory=lambda: int(os.getenv("AGENT_API_TIMEOUT", "60")))

class EvolutionTranscriptConfig(BaseModel):
    """Evolution transcript API configuration."""
    api_url: str = Field(default_factory=lambda: os.getenv("EVOLUTION_TRANSCRIPT_API", ""))
    api_key: str = Field(default_factory=lambda: os.getenv("EVOLUTION_TRANSCRIPT_API_KEY", ""))

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = "%(asctime)s - \033[36m%(name)s\033[0m - %(levelname)s - %(message)s"
    date_format: str = "%H:%M:%S %Z"  # Time format with timezone info
    use_colors: bool = True
    shorten_paths: bool = Field(default_factory=lambda: os.getenv("LOG_VERBOSITY", "short").lower() != "full")
    log_folder: str = Field(default_factory=lambda: os.getenv("LOG_FOLDER", ""))
    enable_file_logging: bool = Field(default_factory=lambda: bool(os.getenv("LOG_FOLDER", "")))

class WhatsAppConfig(BaseModel):
    """WhatsApp configuration."""
    session_id_prefix: str = Field(default_factory=lambda: os.getenv("SESSION_ID_PREFIX", ""))
    minio_url: str = Field(default_factory=lambda: os.getenv("EVOLUTION_MINIO_URL", ""))
    api_use_https: bool = Field(default_factory=lambda: os.getenv("API_USE_HTTPS", "").lower() == "true")
    typing_indicator_duration: int = Field(default_factory=lambda: int(os.getenv("TYPING_INDICATOR_DURATION", "10")))
    instance: str = Field(default_factory=lambda: os.getenv("WHATSAPP_INSTANCE", ""))
    use_base64_media: bool = Field(default_factory=lambda: os.getenv("USE_BASE64_MEDIA", "false").lower() == "true")
    save_webhook_debug: bool = Field(default_factory=lambda: os.getenv("SAVE_WEBHOOK_DEBUG", "false").lower() == "true")

class DatabaseConfig(BaseModel):
    """Database configuration."""
    sqlite_path: str = Field(default_factory=lambda: os.getenv("SQLITE_DB_PATH", "./data/omnihub.db"))
    url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    
    @property
    def database_url(self) -> str:
        """Get the complete database URL."""
        if self.url:
            return self.url
        # Auto-construct SQLite URL from path
        return f"sqlite:///{self.sqlite_path}"

class TracingConfig(BaseModel):
    """Message tracing configuration."""
    enabled: bool = Field(default_factory=lambda: os.getenv("ENABLE_TRACING", "true").lower() == "true")
    retention_days: int = Field(default_factory=lambda: int(os.getenv("TRACE_RETENTION_DAYS", "30")))
    max_payload_size: int = Field(default_factory=lambda: int(os.getenv("TRACE_MAX_PAYLOAD_SIZE", "1048576")))  # 1MB
    include_sensitive_data: bool = Field(default_factory=lambda: os.getenv("TRACE_INCLUDE_SENSITIVE", "false").lower() == "true")

class ApiConfig(BaseModel):
    """API Server configuration."""
    host: str = Field(default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_API_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("AUTOMAGIK_OMNI_API_PORT", "8882")))
    api_key: str = Field(default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_API_KEY", ""))
    title: str = "Omni-Hub API"
    description: str = "Multi-tenant WhatsApp instance management API"
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

class Config(BaseModel):
    """Main application configuration."""
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    agent_api: AgentApiConfig = AgentApiConfig()
    evolution_transcript: EvolutionTranscriptConfig = EvolutionTranscriptConfig()
    logging: LoggingConfig = LoggingConfig()
    whatsapp: WhatsAppConfig = WhatsAppConfig()
    api: ApiConfig = ApiConfig()
    database: DatabaseConfig = DatabaseConfig()
    tracing: TracingConfig = TracingConfig()
    timezone: TimezoneConfig = TimezoneConfig()
    
    @property
    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        # RabbitMQ is now disabled - only check API configuration
        valid = bool(self.agent_api.url and self.agent_api.api_key)
        if valid:
            logger.info("✅ Configuration valid - RabbitMQ disabled, using HTTP webhooks only")
        return valid
    
    def get_env(self, key: str, default: Any = "") -> Any:
        """Get environment variable with fallback to default."""
        return os.getenv(key, default)

# Create the global config instance
config = Config() 