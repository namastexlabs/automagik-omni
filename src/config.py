"""
Configuration management for Stan WhatsApp Agent.
Loads configuration from environment variables.
"""

import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# Load environment variables from .env file
# This should be the ONLY place where load_dotenv is called in the entire application
load_dotenv(override=True)  

class RabbitMQConfig(BaseModel):
    """RabbitMQ configuration."""
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

class ApiConfig(BaseModel):
    """API Server configuration."""
    host: str = Field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))

class Config(BaseModel):
    """Main application configuration."""
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    agent_api: AgentApiConfig = AgentApiConfig()
    evolution_transcript: EvolutionTranscriptConfig = EvolutionTranscriptConfig()
    logging: LoggingConfig = LoggingConfig()
    whatsapp: WhatsAppConfig = WhatsAppConfig()
    api: ApiConfig = ApiConfig()
    
    @property
    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        # Remove RabbitMQ URI check since we're not using it anymore
        return bool(self.agent_api.url and self.agent_api.api_key)
    
    def get_env(self, key: str, default: Any = "") -> Any:
        """Get environment variable with fallback to default."""
        return os.getenv(key, default)

# Singleton instance
config = Config() 