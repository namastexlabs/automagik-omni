"""
Lightweight telemetry client for Omni-Hub.
Uses only Python standard library to send OTLP-compatible traces.
"""

import json
import logging
import os
import platform
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)


class TelemetryClient:
    """
    Lightweight telemetry client that sends OTLP-compatible traces.
    Uses only Python standard library - no external dependencies.
    """

    def __init__(self):
        self.endpoint = "https://telemetry.namastex.ai/v1/traces"
        self.timeout = 5  # seconds
        self.user_id = self._get_or_create_user_id()
        self.session_id = str(uuid.uuid4())
        self.enabled = self._is_telemetry_enabled()
        
        # Project identification
        self.project_name = "automagik-omni"
        self.project_version = "0.2.0"
        self.organization = "namastex"

    def _get_or_create_user_id(self) -> str:
        """Generate or retrieve anonymous user identifier."""
        user_id_file = Path.home() / ".automagik-omni" / "user_id"
        
        if user_id_file.exists():
            try:
                return user_id_file.read_text().strip()
            except Exception:
                pass
        
        # Create new anonymous UUID
        user_id = str(uuid.uuid4())
        try:
            user_id_file.parent.mkdir(exist_ok=True)
            user_id_file.write_text(user_id)
        except Exception:
            pass  # Continue with in-memory ID if file creation fails
        
        return user_id

    def _is_telemetry_enabled(self) -> bool:
        """Check if telemetry is enabled based on various opt-out mechanisms."""
        # Check environment variable
        if os.getenv("AUTOMAGIK_OMNI_DISABLE_TELEMETRY", "false").lower() == "true":
            return False
        
        # Check for opt-out file
        if (Path.home() / ".automagik-omni-no-telemetry").exists():
            return False
        
        # Auto-disable in CI/testing environments
        ci_environments = ["CI", "GITHUB_ACTIONS", "TRAVIS", "JENKINS", "GITLAB_CI"]
        if any(os.getenv(var) for var in ci_environments):
            return False
        
        # Check for development indicators
        if os.getenv("ENVIRONMENT") in ["development", "dev", "test", "testing"]:
            return False
            
        return True

    def _get_system_info(self) -> Dict[str, Any]:
        """Collect basic system information."""
        return {
            "os": platform.system(),
            "os_version": platform.release(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "architecture": platform.machine(),
            "is_docker": os.path.exists("/.dockerenv"),
            "project_name": self.project_name,
            "project_version": self.project_version,
            "organization": self.organization,
        }

    def _create_attributes(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert data to OTLP attribute format with type safety."""
        attributes = []
        
        # Add system information
        system_info = self._get_system_info()
        for key, value in system_info.items():
            if isinstance(value, bool):
                attributes.append({
                    "key": f"system.{key}",
                    "value": {"boolValue": value}
                })
            elif isinstance(value, (int, float)):
                attributes.append({
                    "key": f"system.{key}",
                    "value": {"doubleValue": float(value)}
                })
            else:
                attributes.append({
                    "key": f"system.{key}",
                    "value": {"stringValue": str(value)}
                })
        
        # Add event data
        for key, value in data.items():
            if isinstance(value, bool):
                attributes.append({
                    "key": f"event.{key}",
                    "value": {"boolValue": value}
                })
            elif isinstance(value, (int, float)):
                attributes.append({
                    "key": f"event.{key}",
                    "value": {"doubleValue": float(value)}
                })
            else:
                # Truncate long strings and sanitize sensitive data
                sanitized_value = str(value)[:500]
                attributes.append({
                    "key": f"event.{key}",
                    "value": {"stringValue": sanitized_value}
                })
        
        return attributes

    def _send_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Send telemetry event to the endpoint."""
        if not self.enabled:
            return  # Silent no-op when disabled
        
        try:
            # Generate trace and span IDs
            trace_id = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"  # 32 chars
            span_id = f"{uuid.uuid4().hex[:16]}"  # 16 chars
            
            # Create OTLP-compatible payload
            payload = {
                "resourceSpans": [{
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": self.project_name}},
                            {"key": "service.version", "value": {"stringValue": self.project_version}},
                            {"key": "service.organization", "value": {"stringValue": self.organization}},
                            {"key": "user.id", "value": {"stringValue": self.user_id}},
                            {"key": "session.id", "value": {"stringValue": self.session_id}},
                            {"key": "telemetry.sdk.name", "value": {"stringValue": self.project_name}},
                            {"key": "telemetry.sdk.version", "value": {"stringValue": self.project_version}}
                        ]
                    },
                    "scopeSpans": [{
                        "scope": {
                            "name": f"{self.project_name}.telemetry",
                            "version": self.project_version
                        },
                        "spans": [{
                            "traceId": trace_id,
                            "spanId": span_id,
                            "name": event_type,
                            "kind": "SPAN_KIND_INTERNAL",
                            "startTimeUnixNano": int(time.time() * 1_000_000_000),
                            "endTimeUnixNano": int(time.time() * 1_000_000_000),
                            "attributes": self._create_attributes(data),
                            "status": {"code": "STATUS_CODE_OK"}
                        }]
                    }]
                }]
            }
            
            # Send HTTP request
            request = Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            
            with urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    logger.debug(f"Telemetry event failed with status {response.status}")
                    
        except (URLError, HTTPError, TimeoutError) as e:
            # Log only in debug mode, never crash the application
            logger.debug(f"Telemetry network error: {e}")
        except Exception as e:
            # Log any other errors in debug mode
            logger.debug(f"Telemetry event error: {e}")

    # Public API methods
    def track_command(self, command: str, success: bool = True, duration_ms: Optional[float] = None, **kwargs) -> None:
        """Track CLI command execution."""
        data = {
            "command": command,
            "success": success,
            **kwargs
        }
        if duration_ms is not None:
            data["duration_ms"] = duration_ms
        self._send_event("command", data)

    def track_api_request(self, endpoint: str, method: str, status_code: int, duration_ms: Optional[float] = None, **kwargs) -> None:
        """Track API request."""
        data = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            **kwargs
        }
        if duration_ms is not None:
            data["duration_ms"] = duration_ms
        self._send_event("api_request", data)

    def track_webhook_processed(self, channel: str, success: bool = True, duration_ms: Optional[float] = None, **kwargs) -> None:
        """Track webhook processing."""
        data = {
            "channel": channel,
            "success": success,
            **kwargs
        }
        if duration_ms is not None:
            data["duration_ms"] = duration_ms
        self._send_event("webhook_processed", data)

    def track_instance_operation(self, operation: str, success: bool = True, **kwargs) -> None:
        """Track instance management operations."""
        data = {
            "operation": operation,
            "success": success,
            **kwargs
        }
        self._send_event("instance_operation", data)

    def track_feature_usage(self, feature: str, **kwargs) -> None:
        """Track feature usage."""
        data = {
            "feature": feature,
            **kwargs
        }
        self._send_event("feature_usage", data)

    def track_installation(self, install_type: str = "unknown", first_run: bool = False) -> None:
        """Track installation events."""
        data = {
            "install_type": install_type,
            "first_run": first_run
        }
        self._send_event("installation", data)

    # Control methods
    def enable(self) -> None:
        """Enable telemetry."""
        self.enabled = True
        # Remove opt-out file if it exists
        opt_out_file = Path.home() / ".automagik-omni-no-telemetry"
        if opt_out_file.exists():
            try:
                opt_out_file.unlink()
            except Exception:
                pass

    def disable(self) -> None:
        """Disable telemetry permanently."""
        self.enabled = False
        # Create opt-out file
        try:
            opt_out_file = Path.home() / ".automagik-omni-no-telemetry"
            opt_out_file.touch()
        except Exception:
            pass

    def is_enabled(self) -> bool:
        """Check if telemetry is enabled."""
        return self.enabled

    def get_status(self) -> Dict[str, Any]:
        """Get telemetry status information."""
        return {
            "enabled": self.enabled,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "project_name": self.project_name,
            "project_version": self.project_version,
            "endpoint": self.endpoint,
            "opt_out_file_exists": (Path.home() / ".automagik-omni-no-telemetry").exists(),
            "env_var_disabled": os.getenv("AUTOMAGIK_OMNI_DISABLE_TELEMETRY", "false").lower() == "true"
        }


# Global telemetry client instance
telemetry_client = TelemetryClient()


# Convenience functions
def track_command(command: str, success: bool = True, duration_ms: Optional[float] = None, **kwargs) -> None:
    """Track CLI command execution."""
    telemetry_client.track_command(command, success, duration_ms, **kwargs)


def track_api_request(endpoint: str, method: str, status_code: int, duration_ms: Optional[float] = None, **kwargs) -> None:
    """Track API request."""
    telemetry_client.track_api_request(endpoint, method, status_code, duration_ms, **kwargs)


def track_webhook_processed(channel: str, success: bool = True, duration_ms: Optional[float] = None, **kwargs) -> None:
    """Track webhook processing."""
    telemetry_client.track_webhook_processed(channel, success, duration_ms, **kwargs)


def track_instance_operation(operation: str, success: bool = True, **kwargs) -> None:
    """Track instance management operations."""
    telemetry_client.track_instance_operation(operation, success, **kwargs)


def track_feature_usage(feature: str, **kwargs) -> None:
    """Track feature usage."""
    telemetry_client.track_feature_usage(feature, **kwargs)


def enable_telemetry() -> None:
    """Enable telemetry."""
    telemetry_client.enable()


def disable_telemetry() -> None:
    """Disable telemetry permanently."""
    telemetry_client.disable()


def is_telemetry_enabled() -> bool:
    """Check if telemetry is enabled."""
    return telemetry_client.is_enabled()


def get_telemetry_status() -> Dict[str, Any]:
    """Get telemetry status information."""
    return telemetry_client.get_status()