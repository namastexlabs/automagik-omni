"""Configuration for OMNI MCP tool"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Literal


class OmniConfig(BaseSettings):
    """Configuration for OMNI multi-tenant messaging API tool"""

    api_key: str = Field(
        default="", description="API key for OMNI authentication", alias="OMNI_API_KEY"
    )

    base_url: str = Field(
        default="http://localhost:8882",
        description="Base URL for the OMNI API",
        alias="OMNI_BASE_URL",
    )

    default_instance: Optional[str] = Field(
        default=None,
        description="Default instance name for operations",
        alias="OMNI_DEFAULT_INSTANCE",
    )

    timeout: int = Field(
        default=30, description="Request timeout in seconds", alias="OMNI_TIMEOUT"
    )

    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        alias="OMNI_MAX_RETRIES",
    )

    # Master context (context isolation & safety)
    master_phone: Optional[str] = Field(
        default=None,
        description="Master phone number (context isolation) - e.g., '5511999999999'",
        alias="OMNI_MASTER_PHONE",
    )

    master_group: Optional[str] = Field(
        default=None,
        description="Master group ID (context isolation) - e.g., '120363xxx@g.us'",
        alias="OMNI_MASTER_GROUP",
    )

    mode: Literal["agent_owned", "act_on_behalf"] = Field(
        default="agent_owned",
        description="Operation mode: 'agent_owned' (agent has own number) or 'act_on_behalf' (using owner's number)",
        alias="OMNI_MODE",
    )

    media_download_folder: str = Field(
        default="/tmp/genie-omni-media",
        description="Folder for downloaded media files (images, videos, audio, documents)",
        alias="OMNI_MEDIA_DOWNLOAD_FOLDER",
    )

    model_config = {
        "env_prefix": "OMNI_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def validate_for_use(self):
        """Validate configuration is ready for use"""
        if not self.api_key:
            raise ValueError("OMNI_API_KEY is required")
        if not self.base_url:
            raise ValueError("OMNI_BASE_URL is required")

    def has_master_context(self) -> bool:
        """Check if master context is defined (safe mode)"""
        return bool(self.master_phone or self.master_group)

    def get_master_id(self) -> Optional[str]:
        """Get master identifier (phone or group)"""
        return self.master_phone or self.master_group

    def is_safe_mode(self) -> bool:
        """Check if operating in safe mode (context isolation enabled)"""
        return self.has_master_context()

    def get_safety_warning(self) -> str:
        """Get safety warning if in dangerous mode"""
        if self.has_master_context():
            master = "phone " + self.master_phone if self.master_phone else "group " + self.master_group
            return f"✅ SAFE MODE: Context isolated to {master}"
        else:
            return (
                "⚠️ WARNING: FULL WhatsApp ACCESS MODE\n"
                "No master context defined. Agent can send messages to ANYONE.\n"
                "This is DANGEROUS. Configure master_phone or master_group for safety.\n"
                "Set via: OMNI_MASTER_PHONE=5511999999999 or OMNI_MASTER_GROUP=120363xxx@g.us"
            )

    def validate_recipient(self, recipient: str) -> tuple[bool, str]:
        """
        Validate if recipient is allowed based on master context.

        Args:
            recipient: Phone number or group ID to send to

        Returns:
            Tuple of (is_allowed, message)
        """
        if not self.has_master_context():
            # No master context = full access mode (dangerous)
            return True, self.get_safety_warning()

        # Check if recipient matches master context
        if self.master_phone and recipient == self.master_phone:
            return True, "✅ Allowed: Sending to master phone"

        if self.master_group and recipient == self.master_group:
            return True, "✅ Allowed: Sending to master group"

        # Recipient outside master context
        master = self.master_phone or self.master_group
        return (
            False,
            f"❌ BLOCKED: Context isolation enabled.\n"
            f"Master: {master}\n"
            f"Attempted: {recipient}\n"
            f"Only messages to master are allowed.",
        )
