"""
Core functionality for Omni-Hub.
"""

from .telemetry import (
    telemetry_client,
    track_command,
    track_api_request,
    track_webhook_processed,
    track_instance_operation,
    track_feature_usage,
    enable_telemetry,
    disable_telemetry,
    is_telemetry_enabled,
    get_telemetry_status,
)

__all__ = [
    "telemetry_client",
    "track_command",
    "track_api_request",
    "track_webhook_processed",
    "track_instance_operation",
    "track_feature_usage",
    "enable_telemetry",
    "disable_telemetry",
    "is_telemetry_enabled",
    "get_telemetry_status",
]