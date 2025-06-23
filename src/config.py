"""
Configuration management for Stan WhatsApp Agent.
Loads configuration from environment variables.
"""

import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Any

# Load environment variables from .env file
# This should be the ONLY place where load_dotenv is called in the entire application
load_dotenv(override=True)  

# Get logger for this module
logger = logging.getLogger(__name__)

class RabbitMQConfig(BaseModel):
    """RabbitMQ configuration (DISABLED - HTTP webhooks only)."""
    uri: str = Field(default_factory=lambda: os.getenv("RABBITMQ_URI", ""))
    exchange_name: str = Field(default_factory=lambda: os.getenv("RABBITMQ_EXCHANGE", "evolution_exchange"))
    instance_name: str = Field(default_factory=lambda: os.getenv("WHATSAPP_INSTANCE", ""))
    global_mode: bool = False  # Always use instance-specific mode

class AgentApiConfig(BaseModel):
    """Agent API configuration."""
    url: str = Field(default_factory=lambda: os.getenv("AGENT_API_URL", "http://localhost:8000"))
    api_key: str = Field(default_factory=lambda: os.getenv("AGENT_API_KEY", ""))
    default_agent_name: str = Field(default_factory=lambda: os.getenv("DEFAULT_AGENT_NAME", "simple_agent"))
    timeout: int = Field(default_factory=lambda: int(os.getenv("AGENT_API_TIMEOUT", "60")))

class EvolutionTranscriptConfig(BaseModel):
    """Evolution transcript API configuration."""
    api_url: str = Field(default_factory=lambda: os.getenv("EVOLUTION_TRANSCRIPT_API", ""))
    api_key: str = Field(default_factory=lambda: os.getenv("EVOLUTION_TRANSCRIPT_API_KEY", ""))

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = "%(asctime)s - \033[36m%(name)s\033[0m - %(levelname)s - %(message)s"
    date_format: str = "%H:%M:%S"  # Shorter time format without date
    use_colors: bool = True
    shorten_paths: bool = Field(default_factory=lambda: os.getenv("LOG_VERBOSITY", "short").lower() != "full")

class WhatsAppConfig(BaseModel):
    """WhatsApp configuration."""
    session_id_prefix: str = Field(default_factory=lambda: os.getenv("SESSION_ID_PREFIX", ""))
    minio_url: str = Field(default_factory=lambda: os.getenv("EVOLUTION_MINIO_URL", ""))
    api_use_https: bool = Field(default_factory=lambda: os.getenv("API_USE_HTTPS", "").lower() == "true")
    typing_indicator_duration: int = Field(default_factory=lambda: int(os.getenv("TYPING_INDICATOR_DURATION", "10")))
    instance: str = Field(default_factory=lambda: os.getenv("WHATSAPP_INSTANCE", "dev_wpp"))

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

class ApiConfig(BaseModel):
    """API Server configuration."""
    host: str = Field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    api_key: str = Field(default_factory=lambda: os.getenv("OMNI_HUB_API_KEY", ""))
    title: str = "Omni-Hub API"
    description: str = "Multi-tenant WhatsApp instance management API"
    version: str = "0.2.0"

class Config(BaseModel):
    """Main application configuration."""
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    agent_api: AgentApiConfig = AgentApiConfig()
    evolution_transcript: EvolutionTranscriptConfig = EvolutionTranscriptConfig()
    logging: LoggingConfig = LoggingConfig()
    whatsapp: WhatsAppConfig = WhatsAppConfig()
    api: ApiConfig = ApiConfig()
    database: DatabaseConfig = DatabaseConfig()
    
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