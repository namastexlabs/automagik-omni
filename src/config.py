"""
Configuration management for Stan WhatsApp Agent.
Loads configuration from environment variables.
"""

import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field, PostgresDsn
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class RabbitMQConfig(BaseModel):
    """RabbitMQ configuration."""
    uri: str = Field(default_factory=lambda: os.getenv("RABBITMQ_URI", ""))
    exchange_name: str = Field(default_factory=lambda: os.getenv("RABBITMQ_EXCHANGE", "evolution_exchange"))
    instance_name: str = Field(default_factory=lambda: os.getenv("WHATSAPP_INSTANCE", ""))
    global_mode: bool = False  # Always use instance-specific mode

class DatabaseConfig(BaseModel):
    """Database configuration."""
    uri: PostgresDsn = Field(default_factory=lambda: os.getenv("AGENT_MESSAGE_DB", ""))
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30

class MinioConfig(BaseModel):
    """Minio configuration."""
    endpoint: str = Field(default_factory=lambda: os.getenv("S3_ENDPOINT", "minio"))
    port: str = Field(default_factory=lambda: os.getenv("S3_PORT", "9000"))
    access_key: str = Field(default_factory=lambda: os.getenv("S3_ACCESS_KEY", "minio_access"))
    secret_key: str = Field(default_factory=lambda: os.getenv("S3_SECRET_KEY", "Duassenha2024"))
    region: str = Field(default_factory=lambda: os.getenv("S3_REGION", "us-east-1"))
    bucket: str = Field(default_factory=lambda: os.getenv("S3_BUCKET", "evolution"))
    use_https: bool = Field(default_factory=lambda: os.getenv("S3_USE_HTTPS", "").lower() == "true")

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class Config(BaseModel):
    """Main application configuration."""
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    database: DatabaseConfig = DatabaseConfig()
    logging: LoggingConfig = LoggingConfig()
    minio: MinioConfig = MinioConfig()
    public_media_url: str = Field(default_factory=lambda: os.getenv("PUBLIC_MEDIA_URL", "http://evo.namastex.io:8080"))
    
    @property
    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        return bool(self.rabbitmq.uri and self.rabbitmq.instance_name and self.database.uri)

# Singleton instance
config = Config() 