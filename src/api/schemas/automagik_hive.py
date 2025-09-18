"""
Pydantic schemas for AutomagikHive integration validation.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class AutomagikHiveConfigCreate(BaseModel):
    """Schema for creating AutomagikHive configuration."""

    hive_enabled: bool = Field(default=False, description="Enable AutomagikHive intelligent routing")
    hive_api_url: Optional[str] = Field(None, description="AutomagikHive API URL")
    hive_api_key: Optional[str] = Field(None, description="AutomagikHive API key")
    hive_agent_id: Optional[str] = Field(None, description="AutomagikHive agent ID")
    hive_team_id: Optional[str] = Field(None, description="AutomagikHive team ID")
    hive_timeout: int = Field(default=30, ge=5, le=300, description="AutomagikHive request timeout in seconds")
    hive_stream_mode: bool = Field(default=True, description="Enable streaming responses from AutomagikHive")

    @field_validator("hive_api_url")
    @classmethod
    def validate_hive_api_url(cls, v):
        """Validate AutomagikHive API URL format."""
        if v is not None:
            if not v.startswith(("http://", "https://")):
                raise ValueError("AutomagikHive API URL must start with http:// or https://")
            if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", v):
                raise ValueError("Invalid AutomagikHive API URL format")
        return v

    @field_validator("hive_api_key")
    @classmethod
    def validate_hive_api_key(cls, v):
        """Validate AutomagikHive API key format."""
        if v is not None:
            if len(v.strip()) < 8:
                raise ValueError("AutomagikHive API key must be at least 8 characters")
            if not re.match(r"^[a-zA-Z0-9_\-\.]+$", v.strip()):
                raise ValueError("AutomagikHive API key contains invalid characters")
        return v.strip() if v else v

    @field_validator("hive_agent_id")
    @classmethod
    def validate_hive_agent_id(cls, v):
        """Validate AutomagikHive agent ID format."""
        if v is not None:
            if not v.strip():
                raise ValueError("AutomagikHive agent ID cannot be empty")
            if len(v.strip()) > 255:
                raise ValueError("AutomagikHive agent ID too long (max 255 characters)")
        return v.strip() if v else v

    @field_validator("hive_team_id")
    @classmethod
    def validate_hive_team_id(cls, v):
        """Validate AutomagikHive team ID format."""
        if v is not None:
            if not v.strip():
                raise ValueError("AutomagikHive team ID cannot be empty")
            if len(v.strip()) > 255:
                raise ValueError("AutomagikHive team ID too long (max 255 characters)")
        return v.strip() if v else v

    def validate_hive_config_completeness(self):
        """Validate that if hive is enabled, all required fields are provided."""
        if self.hive_enabled:
            missing_fields = []
            if not self.hive_api_url:
                missing_fields.append("hive_api_url")
            if not self.hive_api_key:
                missing_fields.append("hive_api_key")
            if not self.hive_agent_id:
                missing_fields.append("hive_agent_id")

            if missing_fields:
                raise ValueError(f"When hive_enabled is True, these fields are required: {', '.join(missing_fields)}")


class AutomagikHiveConfigUpdate(BaseModel):
    """Schema for updating AutomagikHive configuration."""

    hive_enabled: Optional[bool] = None
    hive_api_url: Optional[str] = None
    hive_api_key: Optional[str] = None
    hive_agent_id: Optional[str] = None
    hive_team_id: Optional[str] = None
    hive_timeout: Optional[int] = Field(None, ge=5, le=300)
    hive_stream_mode: Optional[bool] = None

    # Validators for update schema
    @field_validator("hive_api_url")
    @classmethod
    def validate_hive_api_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return AutomagikHiveConfigCreate.validate_hive_api_url(v)

    @field_validator("hive_api_key")
    @classmethod
    def validate_hive_api_key(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return AutomagikHiveConfigCreate.validate_hive_api_key(v)

    @field_validator("hive_agent_id")
    @classmethod
    def validate_hive_agent_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return AutomagikHiveConfigCreate.validate_hive_agent_id(v)

    @field_validator("hive_team_id")
    @classmethod
    def validate_hive_team_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return AutomagikHiveConfigCreate.validate_hive_team_id(v)


class AutomagikHiveConfigResponse(BaseModel):
    """Schema for AutomagikHive configuration in responses."""

    hive_enabled: bool
    hive_api_url: Optional[str]
    hive_api_key: Optional[str] = Field(None, description="API key (masked for security)")
    hive_agent_id: Optional[str]
    hive_team_id: Optional[str]
    hive_timeout: int
    hive_stream_mode: bool

    def mask_sensitive_fields(self):
        """Mask sensitive fields for logging/response."""
        if self.hive_api_key:
            self.hive_api_key = (
                f"{self.hive_api_key[:4]}***{self.hive_api_key[-4:]}" if len(self.hive_api_key) > 8 else "***"
            )
